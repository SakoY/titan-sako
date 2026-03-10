"""FastAPI dependencies — tenant authentication."""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_pii
from app.models.tenant import Tenant


def require_tenant(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Tenant:
    """
    Resolve the calling tenant from the X-API-Key header.
    Raises HTTP 401 if the header is missing or the key doesn't match any tenant.
    """
    hashed = hash_pii(x_api_key, settings.SECRET_KEY)
    tenant = db.query(Tenant).filter_by(api_key=hashed).first()
    if tenant is None:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return tenant
