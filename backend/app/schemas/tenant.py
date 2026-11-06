from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional, List
import datetime

class TenantCreate(BaseModel):
    name: str
    trade_name: Optional[str] = None
    simulated_gstin: Optional[str] = None
    state_code: str = "27"  # Default Maharashtra
    business_category: str = "Retail/Wholesale"
    turnover_tier: str = "Micro (< 5 Cr)"
    
    # Global Multi-Tenant Settings
    country_code: str = "IN"  # IN, US, AE, GB, SG
    tax_jurisdiction: str = "INDIA_GST"  # INDIA_GST, US_SALES_TAX, UAE_VAT, UK_VAT
    base_currency: str = "INR"  # INR, USD, AED, EUR, GBP
    currency_symbol: str = "₹"  # ₹, $, AED, €, £
    financial_year_start_month: int = 4  # 4 for April (India/UK), 1 for Jan (US/UAE)
    timezone: str = "Asia/Kolkata"

class TenantSettingsUpdate(BaseModel):
    name: Optional[str] = None
    trade_name: Optional[str] = None
    business_category: Optional[str] = None
    turnover_tier: Optional[str] = None
    country_code: Optional[str] = None
    tax_jurisdiction: Optional[str] = None
    base_currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    financial_year_start_month: Optional[int] = None
    timezone: Optional[str] = None

class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    trade_name: Optional[str]
    simulated_gstin: str
    state_code: str
    business_category: str
    turnover_tier: str
    subscription_plan: str
    country_code: str
    tax_jurisdiction: str
    base_currency: str
    currency_symbol: str
    financial_year_start_month: int
    timezone: str
    created_at: datetime.datetime

class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    tenant: TenantOut

class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str = "ACCOUNTANT"  # OWNER, ADMIN, ACCOUNTANT, EMPLOYEE

class TenantMemberOut(BaseModel):
    membership_id: str
    user_id: str
    email: str
    full_name: str
    role: str
    created_at: datetime.datetime
