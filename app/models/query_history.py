from sqlalchemy import Column, ForeignKey, Text, JSON, TIMESTAMP, Integer, text
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SAEnum
from enum import Enum as PyEnum
from app.db.database import Base



class QueryStatus(PyEnum):
    SUCCESS = "success"
    FAILED  = "failed"
    BLOCKED = "blocked"  # unsafe query detected

class Feedback(PyEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NONE     = "none"



class QueryHistory(Base):
    __tablename__ = "query_history"

    id                  = Column(Integer, primary_key=True)
    user_id             = Column(Integer, ForeignKey("users.id"), nullable=False)
    connection_id       = Column(Integer, ForeignKey("database_connections.id"), nullable=False)
    nl_query            = Column(Text, nullable=False)        # natural language input
    generated_sql       = Column(Text, nullable=True)         # NULL if blocked before generation
    execution_time_ms   = Column(Integer, nullable=True)      # NULL if failed/blocked
    row_count           = Column(Integer, nullable=True)       # NULL if failed/blocked
    result_preview      = Column(JSON, nullable=True)         # first 5 rows
    ai_explanation      = Column(Text, nullable=True)         # plain-English result summary
    schema_context_used = Column(JSON, nullable=True)         # RAG-retrieved table definitions
    status              = Column(
                            SAEnum(QueryStatus, values_callable=lambda x: [e.value for e in x]),
                            nullable=False
                          )
    error_message       = Column(Text, nullable=True)         # DB error if status=failed
    feedback            = Column(
                            SAEnum(Feedback, values_callable=lambda x: [e.value for e in x]),
                            default=Feedback.NONE, nullable=False
                          )
    created_at          = Column(TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False)

    user       = relationship("User", back_populates="queries")
    connection = relationship("DatabaseConnection", back_populates="queries")