from pydantic import BaseModel, ConfigDict
from typing import Optional, List
import datetime

class TenantCreate(BaseModel):
    name: str
    trade_name: Optional[str] = None
    state_code: str = "27"  # Default Maharashtra
    business_category: str = "Retail/Wholesale"
    turnover_tier: str = "Micro (< 5 Cr)"

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
    created_at: datetime.datetime

class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    tenant: TenantOut
