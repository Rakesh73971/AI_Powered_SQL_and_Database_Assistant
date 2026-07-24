from datetime import datetime
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.database_connection import DatabaseConnection
from app.models.schema_cache import SchemaCache
from app.services.connection_service import get_connection_or_404


def serialize_value(val):
    if val is None:
        return None
    if isinstance(val, (int, float, str, bool)):
        return val
    # Handle decimals, dates, UUIDs, bytes, etc. by converting to string
    return str(val)


def sync_connection_schema(db: Session, connection_id: int, user_id: int) -> dict:
    connection = get_connection_or_404(db, connection_id, user_id)
    
    # Try connecting to the user's database
    try:
        temp_engine = create_engine(connection.sqlalchemy_url)
        inspector = inspect(temp_engine)
        table_names = inspector.get_table_names()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect to the database: {exc}"
        )

    # Clear the session's collection to avoid SQLAlchemy attempting to update FKs to NULL
    connection.schema.clear()
    db.query(SchemaCache).filter(SchemaCache.connection_id == connection_id).delete()
    db.flush()
    
    # Clear ChromaDB documents for this connection
    try:
        from app.ai.rag import delete_connection_schemas, index_table_schema
        delete_connection_schemas(connection_id)
        rag_enabled = True
    except Exception:
        rag_enabled = False
    
    tables_synced = 0
    
    for table_name in table_names:
        # Get column definitions
        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_cols = pk_constraint.get("constrained_columns", [])
        
        column_definitions = []
        for col in columns:
            column_definitions.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "pk": col["name"] in pk_cols,
                "default": str(col["default"]) if col.get("default") is not None else None
            })
            
        sample_values = []
        row_count = 0
        
        # Try retrieving row count and sample rows
        try:
            with temp_engine.connect() as temp_conn:
                # Get count
                count_res = temp_conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = count_res.scalar() or 0
                
                # Get samples
                sample_res = temp_conn.execute(text(f"SELECT * FROM {table_name} LIMIT 5"))
                # mapping returns a row mapping which behaves like a dict
                for row in sample_res:
                    row_dict = {k: serialize_value(v) for k, v in row._mapping.items()}
                    sample_values.append(row_dict)
        except Exception:
            # Swallow errors for individual tables (e.g. permission issues or system tables)
            pass

        chroma_doc_id = None
        if rag_enabled:
            try:
                chroma_doc_id = index_table_schema(connection_id, table_name, column_definitions, sample_values)
            except Exception:
                pass

        db_schema = SchemaCache(
            connection_id=connection_id,
            table_name=table_name,
            column_definitions=column_definitions,
            sample_values=sample_values,
            row_count=row_count,
            chroma_doc_id=chroma_doc_id,
            last_indexed_at=datetime.utcnow()
        )
        db.add(db_schema)
        tables_synced += 1

    # Update connection status
    connection.is_schema_indexed = True
    connection.last_synced_at = datetime.utcnow()
    db.commit()
    db.refresh(connection)

    return {
        "tables_synced": tables_synced,
        "is_schema_indexed": connection.is_schema_indexed,
        "last_synced_at": connection.last_synced_at
    }


def get_cached_schema(db: Session, connection_id: int, user_id: int) -> list[SchemaCache]:
    # Ensure ownership first
    get_connection_or_404(db, connection_id, user_id)
    return db.query(SchemaCache).filter(SchemaCache.connection_id == connection_id).all()
