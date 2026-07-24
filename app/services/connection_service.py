from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.database_connection import DatabaseConnection
from app.schemas.database_connection import ConnectionCreate


def register_connection(db: Session, conn_data: ConnectionCreate, user_id: int) -> DatabaseConnection:
    # Check if a connection with the same name already exists for this user
    existing = db.query(DatabaseConnection).filter(
        DatabaseConnection.user_id == user_id,
        DatabaseConnection.name == conn_data.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a connection registered with this name"
        )
    
    db_conn = DatabaseConnection(
        user_id=user_id,
        name=conn_data.name,
        db_type=conn_data.db_type,
        connection_string=conn_data.connection_string,
        db_name=conn_data.db_name
    )
    db.add(db_conn)
    db.commit()
    db.refresh(db_conn)
    return db_conn


def get_connections_by_user(db: Session, user_id: int) -> list[DatabaseConnection]:
    return db.query(DatabaseConnection).filter(DatabaseConnection.user_id == user_id).all()


def get_connection_or_404(db: Session, connection_id: int, user_id: int) -> DatabaseConnection:
    conn = db.query(DatabaseConnection).filter(
        DatabaseConnection.id == connection_id,
        DatabaseConnection.user_id == user_id
    ).first()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database connection not found or unauthorized"
        )
    return conn


def delete_connection(db: Session, connection_id: int, user_id: int) -> None:
    conn = get_connection_or_404(db, connection_id, user_id)
    try:
        from app.ai.rag import delete_connection_schemas
        delete_connection_schemas(connection_id)
    except Exception:
        pass
    db.delete(conn)
    db.commit()
