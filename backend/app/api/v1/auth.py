import uuid
import random
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import verify_password, get_password_hash, create_access_token
from backend.app.core.dependencies import get_current_user
from backend.app.core.init_db import seed_standard_accounts_for_tenant
from backend.app.models.user import User, Tenant, Membership
from backend.app.schemas.auth import UserCreate, UserLogin, UserOut, Token
from backend.app.schemas.tenant import TenantCreate, TenantOut, MembershipOut

router = APIRouter()

def generate_simulated_gstin(state_code: str = "27") -> str:
    """Generates an Indian format test GSTIN: 2 digits state + 10 char PAN + 1 entity + Z + 1 check."""
    letters = "ABCDE"
    digits = f"{random.randint(1000, 9999)}"
    pan = f"{letters[random.randint(0,4)]}PS{letters[random.randint(0,4)]}{digits}{letters[random.randint(0,4)]}"
    return f"{state_code}{pan}1Z{random.randint(1,9)}"

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # 1. Create user
    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        phone_number=user_in.phone_number,
        is_active=True
    )
    db.add(user)
    db.flush()

    # 2. Create default business workspace (tenant)
    business_name = user_in.business_name or f"{user_in.full_name}'s Enterprise"
    tenant = Tenant(
        name=business_name,
        trade_name=business_name,
        simulated_gstin=generate_simulated_gstin(user_in.state_code or "27"),
        state_code=user_in.state_code or "27",
        business_category="Retail/Wholesale",
        turnover_tier="Micro (< 5 Cr)",
        subscription_plan="FREE",
        country_code="IN",
        tax_jurisdiction="INDIA_GST",
        base_currency="INR",
        currency_symbol="₹",
        financial_year_start_month=4,
        timezone="Asia/Kolkata"
    )
    db.add(tenant)
    db.flush()

    # 3. Create Owner Membership
    membership = Membership(
        user_id=user.id,
        tenant_id=tenant.id,
        role="OWNER"
    )
    db.add(membership)
    db.commit()
    db.refresh(user)

    # Seed standard Chart of Accounts for new tenant
    seed_standard_accounts_for_tenant(db, tenant.id)

    # Generate JWT
    access_token = create_access_token(subject=user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token = create_access_token(subject=user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )

@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/workspaces", response_model=List[MembershipOut])
def list_user_workspaces(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memberships = db.query(Membership).filter(Membership.user_id == current_user.id).all()
    return memberships

@router.post("/workspaces", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    tenant_in: TenantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    currency_map = {"INR": "₹", "USD": "$", "AED": "AED ", "EUR": "€", "GBP": "£"}
    curr_sym = tenant_in.currency_symbol or currency_map.get(tenant_in.base_currency, "$")

    tenant = Tenant(
        name=tenant_in.name,
        trade_name=tenant_in.trade_name or tenant_in.name,
        simulated_gstin=tenant_in.simulated_gstin or generate_simulated_gstin(tenant_in.state_code),
        state_code=tenant_in.state_code,
        business_category=tenant_in.business_category,
        turnover_tier=tenant_in.turnover_tier,
        subscription_plan="FREE",
        country_code=tenant_in.country_code or "IN",
        tax_jurisdiction=tenant_in.tax_jurisdiction or ("INDIA_GST" if tenant_in.country_code == "IN" else "STANDARD_TAX"),
        base_currency=tenant_in.base_currency or "INR",
        currency_symbol=curr_sym,
        financial_year_start_month=tenant_in.financial_year_start_month or (4 if tenant_in.country_code in ("IN", "GB") else 1),
        timezone=tenant_in.timezone or ("Asia/Kolkata" if tenant_in.country_code == "IN" else "UTC")
    )
    db.add(tenant)
    db.flush()

    membership = Membership(
        user_id=current_user.id,
        tenant_id=tenant.id,
        role="OWNER"
    )
    db.add(membership)
    db.commit()
    db.refresh(tenant)

    # Seed MSME standard accounts
    seed_standard_accounts_for_tenant(db, tenant.id)
    return tenant

