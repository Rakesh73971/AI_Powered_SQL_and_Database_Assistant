from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.database_connection import ConnectionCreate, ConnectionOut
from app.schemas.schema_cache import SchemaCacheOut
from app.models.user import User
from app.core.dependencies import get_current_user
from app.services import connection_service, schema_service

router = APIRouter(prefix="/connections", tags=["Database Connections"])


@router.post("/", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED)
def register_conn(
    conn_data: ConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return connection_service.register_connection(db, conn_data, current_user.id)


@router.get("/", response_model=list[ConnectionOut])
def list_conns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return connection_service.get_connections_by_user(db, current_user.id)


@router.get("/{connection_id}", response_model=ConnectionOut)
def get_conn(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return connection_service.get_connection_or_404(db, connection_id, current_user.id)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conn(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    connection_service.delete_connection(db, connection_id, current_user.id)
    return None


@router.post("/{connection_id}/sync", status_code=status.HTTP_200_OK)
def sync_schema(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return schema_service.sync_connection_schema(db, connection_id, current_user.id)


@router.get("/{connection_id}/schema", response_model=list[SchemaCacheOut])
def get_schema(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return schema_service.get_cached_schema(db, connection_id, current_user.id)
