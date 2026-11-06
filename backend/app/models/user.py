import uuid
import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    trade_name = Column(String(255), nullable=True)
    simulated_gstin = Column(String(15), unique=True, index=True, nullable=False)
    state_code = Column(String(2), default="27", nullable=False)  # e.g., 27 for Maharashtra
    business_category = Column(String(100), default="Retail/Wholesale", nullable=False)
    turnover_tier = Column(String(50), default="Micro (< 5 Cr)", nullable=False)
    subscription_plan = Column(String(50), default="FREE", nullable=False)  # FREE, PRO, ENTERPRISE

    # Global Multi-Tenant & Regional Localization Settings
    country_code = Column(String(3), default="IN", nullable=False)  # ISO 3166-1 alpha-2: IN, US, AE, GB, SG
    tax_jurisdiction = Column(String(50), default="INDIA_GST", nullable=False)  # INDIA_GST, US_SALES_TAX, UAE_VAT, UK_VAT
    base_currency = Column(String(3), default="INR", nullable=False)  # INR, USD, AED, EUR, GBP
    currency_symbol = Column(String(10), default="₹", nullable=False)  # ₹, $, AED, €, £
    financial_year_start_month = Column(Integer, default=4, nullable=False)  # 4 for April (India/UK), 1 for Jan (US/UAE)
    timezone = Column(String(50), default="Asia/Kolkata", nullable=False)  # e.g. Asia/Kolkata, America/New_York, Asia/Dubai

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    memberships = relationship("Membership", back_populates="tenant", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="tenant", cascade="all, delete-orphan")
    receipts = relationship("Receipt", back_populates="tenant", cascade="all, delete-orphan")
    ledger_accounts = relationship("LedgerAccount", back_populates="tenant", cascade="all, delete-orphan")
    gst_reports = relationship("GSTReport", back_populates="tenant", cascade="all, delete-orphan")
    workflow_runs = relationship("WorkflowRun", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="tenant", cascade="all, delete-orphan")


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default="OWNER", nullable=False)  # OWNER, ACCOUNTANT, VIEWER
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="memberships")
    tenant = relationship("Tenant", back_populates="memberships")

