from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.database_connection import DBType


class ConnectionCreate(BaseModel):
    name: str
    db_type: DBType
    connection_string: str
    db_name: str


class ConnectionOut(BaseModel):
    id: int
    user_id: int
    name: str
    db_type: DBType
    connection_string: str  # In production, we'd obscure or encrypt this, but let's expose it safely for now
    db_name: str
    schema_collection_id: Optional[str] = None
    is_schema_indexed: bool
    last_synced_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
