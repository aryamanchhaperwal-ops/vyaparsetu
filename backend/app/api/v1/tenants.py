from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user, get_current_tenant
from backend.app.models.user import User, Tenant, Membership
from backend.app.schemas.tenant import TenantOut, MembershipOut

router = APIRouter()

@router.get("/current", response_model=TenantOut)
def get_active_tenant(tenant: Tenant = Depends(get_current_tenant)):
    return tenant

@router.get("/{tenant_id}/members", response_model=List[MembershipOut])
def get_tenant_members(
    tenant_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    if tenant.id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to tenant")
    return db.query(Membership).filter(Membership.tenant_id == tenant_id).all()
