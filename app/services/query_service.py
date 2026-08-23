from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.query_history import QueryHistory, QueryStatus, Feedback
from app.services.connection_service import get_connection_or_404


async def create_query_history(
    db: AsyncSession,
    connection_id: int,
    nl_query: str,
    generated_sql: str,
    status_val: QueryStatus,
    user_id: int,
    execution_time_ms: int = None,
    row_count: int = None,
    result_preview: list = None,
    ai_explanation: str = None,
    error_message: str = None
) -> QueryHistory:
    # Ensure database connection exists and belongs to the user
    await get_connection_or_404(db, connection_id, user_id)
    
    db_history = QueryHistory(
        user_id=user_id,
        connection_id=connection_id,
        nl_query=nl_query,
        generated_sql=generated_sql,
        execution_time_ms=execution_time_ms,
        row_count=row_count,
        result_preview=result_preview,
        ai_explanation=ai_explanation,
        status=status_val,
        error_message=error_message,
        feedback=Feedback.NONE
    )
    db.add(db_history)
    await db.commit()
    await db.refresh(db_history)
    return db_history


async def execute_nl_query(
    db: AsyncSession,
    connection_id: int,
    nl_query: str,
    user_id: int
) -> QueryHistory:
    """
    Executes a natural language query against the target database connection using AI.
    Translates language to SQL with RAG-based context schemas, validates query safety,
    executes it, and explains results.
    """
    from app.ai.services.query_flow import run_ai_query_flow
    return await run_ai_query_flow(db, connection_id, nl_query, user_id)


async def get_query_history_by_id(db: AsyncSession, query_id: int, user_id: int) -> QueryHistory:
    result = await db.execute(
        select(QueryHistory).filter(
            QueryHistory.id == query_id,
            QueryHistory.user_id == user_id
        )
    )
    record = result.scalars().first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query history record not found."
        )
    return record


async def get_query_history_by_connection(
    db: AsyncSession,
    connection_id: int,
    user_id: int
) -> list[QueryHistory]:
    # Ensure connection ownership
    await get_connection_or_404(db, connection_id, user_id)
    result = await db.execute(
        select(QueryHistory)
        .filter(QueryHistory.connection_id == connection_id)
        .order_by(QueryHistory.created_at.desc())
    )
    return list(result.scalars().all())


async def submit_query_feedback(
    db: AsyncSession,
    query_id: int,
    feedback: Feedback,
    user_id: int
) -> QueryHistory:
    record = await get_query_history_by_id(db, query_id, user_id)
    record.feedback = feedback
    await db.commit()
    await db.refresh(record)
    return record


async def delete_query_history(db: AsyncSession, query_id: int, user_id: int) -> None:
    record = await get_query_history_by_id(db, query_id, user_id)
    await db.delete(record)
    await db.commit()
