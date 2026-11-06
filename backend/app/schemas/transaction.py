from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
import datetime
from decimal import Decimal

class TransactionBase(BaseModel):
    transaction_date: datetime.date
    description: str
    raw_narration: str
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("INR", description="ISO 4217 Currency Code (INR, USD, AED, EUR, GBP)")
    exchange_rate: Decimal = Field(Decimal("1.0"), description="Exchange rate to tenant base currency")
    base_amount: Optional[Decimal] = None
    type: str = Field(..., description="DEBIT or CREDIT")
    channel: str = Field("UPI", description="UPI, NEFT, RTGS, CASH, CHEQUE")
    reference_number: Optional[str] = None
    category: str = "Uncategorized"
    sub_category: Optional[str] = None
    hsn_sac_code: Optional[str] = None
    tax_rate: Decimal = Decimal("0.0")
    counterparty_name: Optional[str] = None
    counterparty_gstin: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionOut(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    confidence_score: float
    status: str
    is_reconciled: bool
    created_at: datetime.datetime

class TransactionFilter(BaseModel):
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    status: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 50
