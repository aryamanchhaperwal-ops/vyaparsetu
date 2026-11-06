import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_password_hash
from backend.app.core.dependencies import get_current_user, get_current_tenant, get_current_membership, require_roles
from backend.app.models.user import User, Tenant, Membership
from backend.app.schemas.tenant import (
    TenantOut,
    TenantSettingsUpdate,
    InviteMemberRequest,
    TenantMemberOut
)

router = APIRouter()

@router.get("/current", response_model=TenantOut)
def get_active_tenant(tenant: Tenant = Depends(get_current_tenant)):
    """Returns the current active business workspace settings."""
    return tenant

@router.patch("/current/settings", response_model=TenantOut)
def update_tenant_settings(
    settings_in: TenantSettingsUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    _role: Membership = Depends(require_roles(["OWNER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Updates workspace configuration (country, base currency, timezone, financial year)."""
    update_data = settings_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(tenant, field, val)

    db.commit()
    db.refresh(tenant)
    return tenant

@router.get("/{tenant_id}/members", response_model=List[TenantMemberOut])
def get_tenant_members(
    tenant_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    _role: Membership = Depends(require_roles(["OWNER", "ADMIN", "ACCOUNTANT"])),
    db: Session = Depends(get_db)
):
    """Lists all members and their assigned roles in this business workspace."""
    if tenant.id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to tenant")

    memberships = db.query(Membership).filter(Membership.tenant_id == tenant_id).all()
    results = []
    for m in memberships:
        user = m.user
        results.append(TenantMemberOut(
            membership_id=m.id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=m.role,
            created_at=m.created_at
        ))
    return results

@router.post("/{tenant_id}/invite", response_model=TenantMemberOut, status_code=status.HTTP_201_CREATED)
def invite_member_to_workspace(
    tenant_id: str,
    req: InviteMemberRequest,
    tenant: Tenant = Depends(get_current_tenant),
    _role: Membership = Depends(require_roles(["OWNER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Invites a team member or external accountant to the business workspace.
    Supports multi-business accountant accounts (an accountant can belong to multiple businesses).
    """
    if tenant.id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to tenant")

    normalized_role = req.role.upper()
    if normalized_role not in ("OWNER", "ADMIN", "ACCOUNTANT", "EMPLOYEE"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be one of: OWNER, ADMIN, ACCOUNTANT, EMPLOYEE"
        )

    # Check if user already exists in platform
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        # Create an account for the invited member with temporary credentials
        user = User(
            email=req.email,
            password_hash=get_password_hash("VyaparSetu@Invite2026"),
            full_name=req.email.split("@")[0].replace(".", " ").title(),
            is_active=True
        )
        db.add(user)
        db.flush()

    # Check if user is already a member of this tenant
    existing_membership = db.query(Membership).filter(
        Membership.tenant_id == tenant_id,
        Membership.user_id == user.id
    ).first()

    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {req.email} is already a member of this workspace with role {existing_membership.role}"
        )

    membership = Membership(
        user_id=user.id,
        tenant_id=tenant_id,
        role=normalized_role
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    return TenantMemberOut(
        membership_id=membership.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        created_at=membership.created_at
    )

@router.delete("/{tenant_id}/members/{membership_id}")
def remove_member_from_workspace(
    tenant_id: str,
    membership_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    _role: Membership = Depends(require_roles(["OWNER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Removes a member from the workspace."""
    if tenant.id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to tenant")

    membership = db.query(Membership).filter(
        Membership.id == membership_id,
        Membership.tenant_id == tenant_id
    ).first()

    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

    if membership.role == "OWNER":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove the workspace OWNER")

    db.delete(membership)
    db.commit()
    return {"status": "success", "message": "Member removed from workspace"}
