from datetime import datetime
import asyncio
from sqlalchemy import create_engine, inspect, text, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
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


def _inspect_database(sqlalchemy_url: str) -> list[dict]:
    """
    Synchronous helper executed in a thread pool to perform dynamic DB connection inspection.
    """
    temp_engine = create_engine(sqlalchemy_url)
    inspector = inspect(temp_engine)
    table_names = inspector.get_table_names()
    
    results = []
    
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

        results.append({
            "table_name": table_name,
            "column_definitions": column_definitions,
            "sample_values": sample_values,
            "row_count": row_count
        })
        
    return results


async def sync_connection_schema(db: AsyncSession, connection_id: int, user_id: int) -> dict:
    # Fetch connection loading connection schemas to avoid lazy loading issues in async context
    stmt = (
        select(DatabaseConnection)
        .filter(DatabaseConnection.id == connection_id, DatabaseConnection.user_id == user_id)
        .options(selectinload(DatabaseConnection.schema))
    )
    res = await db.execute(stmt)
    connection = res.scalars().first()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database connection not found or unauthorized"
        )
    
    # Try connecting and inspecting the user's database in a separate thread
    try:
        table_data = await asyncio.to_thread(_inspect_database, connection.sqlalchemy_url)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect to the database: {exc}"
        )

    # Clear the session's collection to avoid SQLAlchemy attempting to update FKs to NULL
    connection.schema.clear()
    await db.execute(delete(SchemaCache).where(SchemaCache.connection_id == connection_id))
    await db.flush()
    
    # Clear ChromaDB documents for this connection
    try:
        from app.ai.rag import delete_connection_schemas, index_table_schema
        await asyncio.to_thread(delete_connection_schemas, connection_id)
        rag_enabled = True
    except Exception:
        rag_enabled = False
    
    tables_synced = 0
    
    for item in table_data:
        table_name = item["table_name"]
        column_definitions = item["column_definitions"]
        sample_values = item["sample_values"]
        row_count = item["row_count"]

        chroma_doc_id = None
        if rag_enabled:
            try:
                chroma_doc_id = await asyncio.to_thread(
                    index_table_schema, connection_id, table_name, column_definitions, sample_values
                )
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
    await db.commit()
    await db.refresh(connection)

    return {
        "tables_synced": tables_synced,
        "is_schema_indexed": connection.is_schema_indexed,
        "last_synced_at": connection.last_synced_at
    }


async def get_cached_schema(db: AsyncSession, connection_id: int, user_id: int) -> list[SchemaCache]:
    # Ensure ownership first
    await get_connection_or_404(db, connection_id, user_id)
    res = await db.execute(
        select(SchemaCache).filter(SchemaCache.connection_id == connection_id)
    )
    return list(res.scalars().all())
