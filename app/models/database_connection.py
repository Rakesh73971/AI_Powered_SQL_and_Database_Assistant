from sqlalchemy import Column, Integer, ForeignKey, String, Boolean, TIMESTAMP, text
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SAEnum
from enum import Enum as PyEnum
from app.db.database import Base


class DBType(PyEnum):
    POSTGRESQL = "postgresql"
    MYSQL      = "mysql"
    SQLITE     = "sqlite"


class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id                  = Column(Integer, primary_key=True)
    user_id             = Column(Integer, ForeignKey("users.id"), nullable=False)
    name                = Column(String, nullable=False)
    db_type             = Column(
                            SAEnum(DBType, values_callable=lambda x: [e.value for e in x]),
                            nullable=False
                          )
    connection_string   = Column(String, nullable=False)  # store encrypted in production
    db_name             = Column(String, nullable=False)
    schema_collection_id= Column(String, unique=True, nullable=True)  # ChromaDB collection
    is_schema_indexed   = Column(Boolean, default=False, nullable=False)
    last_synced_at      = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active           = Column(Boolean, server_default="True", nullable=False)
    created_at          = Column(TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False)

    user    = relationship("User", back_populates="connections")
    queries = relationship("QueryHistory", back_populates="connection", cascade="all, delete-orphan")
    schema  = relationship("SchemaCache", back_populates="connection", cascade="all, delete-orphan")

    @property
    def sqlalchemy_url(self) -> str:
        """
        Builds the correct connection URL for SQLAlchemy based on the db_type and connection_string.
        Automatically appends standard drivers for PostgreSQL and MySQL if not present.
        """
        url = self.connection_string
        if self.db_type == DBType.POSTGRESQL:
            if url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        elif self.db_type == DBType.MYSQL:
            if url.startswith("mysql://"):
                return url.replace("mysql://", "mysql+pymysql://", 1)
        elif self.db_type == DBType.SQLITE:
            if not url.startswith("sqlite://"):
                return f"sqlite:///{url}"
        return url
