"""Admin tenant management endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import generate_api_key, hash_pii
from app.core.config import settings
from app.models.tenant import Tenant

router = APIRouter(prefix="/api/v1/admin/tenants", tags=["admin"])


class TenantCreate(BaseModel):
    name: str


class TenantCreated(BaseModel):
    id: str
    name: str
    api_key: str  # returned plaintext once only
    created_at: datetime


class TenantSummary(BaseModel):
    id: str
    name: str
    created_at: datetime


@router.post("", response_model=TenantCreated, status_code=201)
def create_tenant(body: TenantCreate, db: Session = Depends(get_db)):
    """
    Create a new tenant. No auth required — bootstrapping endpoint.
    Returns the plaintext API key once; the DB stores only the hash.
    """
    plaintext_key = generate_api_key()
    hashed_key = hash_pii(plaintext_key, settings.SECRET_KEY)

    tenant = Tenant(name=body.name, api_key=hashed_key)
    db.add(tenant)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Tenant '{body.name}' already exists")

    db.refresh(tenant)
    return TenantCreated(
        id=tenant.id,
        name=tenant.name,
        api_key=plaintext_key,
        created_at=tenant.created_at,
    )


@router.get("", response_model=list[TenantSummary])
def list_tenants(db: Session = Depends(get_db)):
    """List all tenants. Returns id, name, created_at — no API keys."""
    tenants = db.query(Tenant).order_by(Tenant.created_at).all()
    return [TenantSummary(id=t.id, name=t.name, created_at=t.created_at) for t in tenants]
