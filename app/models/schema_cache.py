from sqlalchemy import Column,Integer,String,JSON,TIMESTAMP,ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base



class SchemaCache(Base):
    __tablename__ = "schema_cache"

    id                 = Column(Integer, primary_key=True)
    connection_id      = Column(Integer, ForeignKey("database_connections.id"), nullable=False)
    table_name         = Column(String, nullable=False)
    column_definitions = Column(JSON, nullable=False)   # [{name, type, nullable, pk, fk}]
    sample_values      = Column(JSON, nullable=True)    # 3-5 sample rows for LLM context
    row_count          = Column(Integer, nullable=True)  # approximate size of table
    chroma_doc_id      = Column(String, nullable=True)  # ChromaDB ID for updates
    last_indexed_at    = Column(TIMESTAMP(timezone=True), nullable=True)

    connection = relationship("DatabaseConnection", back_populates="schema")