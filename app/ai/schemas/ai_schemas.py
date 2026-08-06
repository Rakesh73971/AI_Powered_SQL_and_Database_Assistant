from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class SQLChainInput(BaseModel):
    dialect: str
    schema_context: str
    question: str

class SQLChainOutput(BaseModel):
    sql: str

class ExplainChainInput(BaseModel):
    question: str
    sql: str
    results: str

class ExplainChainOutput(BaseModel):
    explanation: str
