from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_admin_user
from app.services import analytics_service

router = APIRouter(prefix="/admin", tags=["Admin Operations"])


@router.get("/analytics", status_code=status.HTTP_200_OK)
def get_analytics(
    slow_threshold_ms: int = 1000,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Exposes system-wide SQL query metrics, execution speed ranges,
    user feedback stats, frequent queries, and slow query logs.
    Restricted to Admins.
    """
    return analytics_service.get_admin_analytics(db, slow_threshold_ms)


@router.post("/optimize/{query_id}", status_code=status.HTTP_200_OK)
def optimize_query(
    query_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Triggers AI-driven diagnostics on a query by ID. Returns recommendations,
    including index statements (DDL) and SQL rewrites.
    Restricted to Admins.
    """
    return analytics_service.optimize_query_by_id(db, query_id)
