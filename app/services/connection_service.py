from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
import asyncio
from app.models.database_connection import DatabaseConnection
from app.schemas.database_connection import ConnectionCreate


async def register_connection(db: AsyncSession, conn_data: ConnectionCreate, user_id: int) -> DatabaseConnection:
    # Check if a connection with the same name already exists for this user
    result = await db.execute(
        select(DatabaseConnection).filter(
            DatabaseConnection.user_id == user_id,
            DatabaseConnection.name == conn_data.name
        )
    )
    existing = result.scalars().first()
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
    await db.commit()
    await db.refresh(db_conn)
    return db_conn


async def get_connections_by_user(db: AsyncSession, user_id: int) -> list[DatabaseConnection]:
    result = await db.execute(
        select(DatabaseConnection).filter(DatabaseConnection.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_connection_or_404(db: AsyncSession, connection_id: int, user_id: int) -> DatabaseConnection:
    result = await db.execute(
        select(DatabaseConnection).filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.user_id == user_id
        )
    )
    conn = result.scalars().first()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database connection not found or unauthorized"
        )
    return conn


async def delete_connection(db: AsyncSession, connection_id: int, user_id: int) -> None:
    conn = await get_connection_or_404(db, connection_id, user_id)
    try:
        from app.ai.rag import delete_connection_schemas
        await asyncio.to_thread(delete_connection_schemas, connection_id)
    except Exception:
        pass
    await db.delete(conn)
    await db.commit()
