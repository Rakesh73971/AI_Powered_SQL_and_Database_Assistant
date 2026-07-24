from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class SchemaCacheOut(BaseModel):
    id: int
    connection_id: int
    table_name: str
    column_definitions: List[Dict[str, Any]]
    sample_values: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None
    last_indexed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
