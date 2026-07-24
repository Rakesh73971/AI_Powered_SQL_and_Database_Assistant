from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict
from app.models.query_history import QueryStatus, Feedback


class QueryRequest(BaseModel):
    nl_query: str


class QueryHistoryOut(BaseModel):
    id: int
    user_id: int
    connection_id: int
    nl_query: str
    generated_sql: Optional[str] = None
    execution_time_ms: Optional[int] = None
    row_count: Optional[int] = None
    result_preview: Optional[Any] = None
    ai_explanation: Optional[str] = None
    schema_context_used: Optional[Any] = None
    status: QueryStatus
    error_message: Optional[str] = None
    feedback: Feedback
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackUpdate(BaseModel):
    feedback: Feedback
