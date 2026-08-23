from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.query_history import QueryRequest, QueryHistoryOut, FeedbackUpdate
from app.models.user import User
from app.core.dependencies import get_current_user
from app.services import query_service

router = APIRouter(prefix="/queries", tags=["Queries"])


@router.post("/{connection_id}/execute", response_model=QueryHistoryOut)
async def run_query(
    connection_id: int,
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await query_service.execute_nl_query(
        db,
        connection_id,
        request.nl_query,
        current_user.id
    )


@router.get("/{connection_id}/history", response_model=list[QueryHistoryOut])
async def get_history(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await query_service.get_query_history_by_connection(db, connection_id, current_user.id)


@router.patch("/{query_id}/feedback", response_model=QueryHistoryOut)
async def give_feedback(
    query_id: int,
    feedback_data: FeedbackUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await query_service.submit_query_feedback(
        db,
        query_id,
        feedback_data.feedback,
        current_user.id
    )
