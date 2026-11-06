import uuid
import datetime
from sqlalchemy import Column, String, DateTime, Integer, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    billing_period = Column(String(7), nullable=False, index=True)  # YYYY-MM
    transactions_processed = Column(Integer, default=0, nullable=False)
    ocr_scans_processed = Column(Integer, default=0, nullable=False)
    llm_tokens_used = Column(Integer, default=0, nullable=False)
    plan_limit_exceeded = Column(Boolean, default=False, nullable=False)
    
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="usage_records")

    __table_args__ = (
        Index("ix_usage_records_tenant_period", "tenant_id", "billing_period", unique=True),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    action = Column(String(100), nullable=False)  # CREATE_TRANSACTION, APPROVE_WORKFLOW, FILE_GST, UPDATE_LEDGER
    entity_name = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

    tenant = relationship("Tenant", back_populates="audit_logs")

