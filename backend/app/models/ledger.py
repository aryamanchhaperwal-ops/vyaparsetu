import uuid
import datetime
from sqlalchemy import Column, String, DateTime, Date, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    code = Column(String(50), nullable=False)  # e.g., 1000, 2000, 4000
    name = Column(String(255), nullable=False)  # e.g., "Cash in Hand", "Sales", "GST Payable"
    account_type = Column(String(50), nullable=False)  # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
    balance = Column(Numeric(14, 2), default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="ledger_accounts")
    entries = relationship("LedgerEntry", back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_ledger_accounts_tenant_code", "tenant_id", "code", unique=True),
    )


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=True, index=True)
    account_id = Column(String(36), ForeignKey("ledger_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    entry_date = Column(Date, nullable=False, index=True)
    debit = Column(Numeric(14, 2), default=0.0, nullable=False)
    credit = Column(Numeric(14, 2), default=0.0, nullable=False)
    narration = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    transaction = relationship("Transaction", back_populates="ledger_entries")
    account = relationship("LedgerAccount", back_populates="entries")

    __table_args__ = (
        Index("ix_ledger_entries_tenant_date", "tenant_id", "entry_date"),
    )
