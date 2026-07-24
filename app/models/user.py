from sqlalchemy import (
    Column, Integer, String, Boolean, Text,
    JSON, TIMESTAMP, ForeignKey, text
)
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SAEnum
from enum import Enum as PyEnum
from app.db.database import Base


# ── Enums ────────────────────────────────────────────────────────────────

class UserRole(PyEnum):
    ADMIN = "admin"
    USER  = "user"


# ── Model 1: User ────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True)
    full_name       = Column(String, nullable=False)
    email           = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role            = Column(
                        SAEnum(UserRole, values_callable=lambda x: [e.value for e in x]),
                        default=UserRole.USER, nullable=False
                      )
    is_active       = Column(Boolean, server_default="True", nullable=False)
    created_at      = Column(TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False)

    connections = relationship("DatabaseConnection", back_populates="user")
    queries     = relationship("QueryHistory", back_populates="user")
