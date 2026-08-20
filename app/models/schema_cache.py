from sqlalchemy import Column,Integer,String,JSON,TIMESTAMP,ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base



class SchemaCache(Base):
    __tablename__ = "schema_cache"

    id                 = Column(Integer, primary_key=True)
    connection_id      = Column(Integer, ForeignKey("database_connections.id"), nullable=False)
    table_name         = Column(String, nullable=False)
    column_definitions = Column(JSON, nullable=False)   
    sample_values      = Column(JSON, nullable=True)    
    row_count          = Column(Integer, nullable=True)  
    chroma_doc_id      = Column(String, nullable=True)
    last_indexed_at    = Column(TIMESTAMP(timezone=True), nullable=True)

    connection = relationship("DatabaseConnection", back_populates="schema")