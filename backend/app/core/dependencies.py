from typing import Optional, List, Callable
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.models.user import User, Tenant, Membership

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_membership(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Membership:
    """Resolves active membership ensuring tenant context and role validation."""
    if not x_tenant_id:
        membership = db.query(Membership).filter(Membership.user_id == current_user.id).first()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User does not belong to any business tenant"
            )
        return membership

    membership = (
        db.query(Membership)
        .filter(Membership.user_id == current_user.id, Membership.tenant_id == x_tenant_id)
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You are not a member of this business tenant"
        )
    return membership

def get_current_tenant(
    membership: Membership = Depends(get_current_membership)
) -> Tenant:
    """Returns the validated tenant for the current request."""
    return membership.tenant

def require_roles(allowed_roles: List[str]) -> Callable:
    """Enforces Role-Based Access Control (OWNER, ADMIN, ACCOUNTANT, EMPLOYEE)."""
    def role_verifier(membership: Membership = Depends(get_current_membership)) -> Membership:
        normalized_allowed = [r.upper() for r in allowed_roles]
        if membership.role.upper() not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: Action requires one of roles: {allowed_roles}. Current role: {membership.role}"
            )
        return membership
    return role_verifier
