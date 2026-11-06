import uuid
import datetime
from sqlalchemy import Column, String, DateTime, Date, Numeric, Float, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    transaction_date = Column(Date, nullable=False, index=True)
    value_date = Column(Date, nullable=True)
    description = Column(String(500), nullable=False)
    raw_narration = Column(String(1000), nullable=False)
    
    amount = Column(Numeric(14, 2), nullable=False)
    type = Column(String(10), nullable=False)  # DEBIT, CREDIT
    channel = Column(String(50), default="UPI", nullable=False)  # UPI, NEFT, RTGS, CASH, CHEQUE
    reference_number = Column(String(100), nullable=True, index=True)  # UTR or UPI ref
    
    category = Column(String(100), default="Uncategorized", nullable=False)
    sub_category = Column(String(100), nullable=True)
    hsn_sac_code = Column(String(20), nullable=True)
    tax_rate = Column(Numeric(5, 2), default=0.0, nullable=False)
    
    confidence_score = Column(Float, default=1.0, nullable=False)
    status = Column(String(50), default="CONFIRMED", nullable=False)  # CONFIRMED, NEEDS_APPROVAL, REJECTED
    is_reconciled = Column(Boolean, default=False, nullable=False)
    
    counterparty_name = Column(String(255), nullable=True)
    counterparty_gstin = Column(String(15), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="transactions")
    receipt = relationship("Receipt", back_populates="transaction", uselist=False)
    ledger_entries = relationship("LedgerEntry", back_populates="transaction", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_transactions_tenant_date", "tenant_id", "transaction_date"),
        Index("ix_transactions_tenant_status", "tenant_id", "status"),
    )
