import uuid
import datetime
from sqlalchemy import Column, String, DateTime, Date, Numeric, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class GSTRecord(Base):
    __tablename__ = "gst_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=True, index=True)

    period = Column(String(7), nullable=False, index=True)  # YYYY-MM, e.g. 2026-11
    supply_type = Column(String(50), nullable=False)  # OUTWARD_TAXABLE, INWARD_TAXABLE, EXEMPT, NIL_RATED
    is_interstate = Column(Boolean, default=False, nullable=False)
    
    taxable_value = Column(Numeric(14, 2), default=0.0, nullable=False)
    rate_percent = Column(Numeric(5, 2), default=18.0, nullable=False)
    cgst = Column(Numeric(14, 2), default=0.0, nullable=False)
    sgst = Column(Numeric(14, 2), default=0.0, nullable=False)
    igst = Column(Numeric(14, 2), default=0.0, nullable=False)
    cess = Column(Numeric(14, 2), default=0.0, nullable=False)
    
    itc_eligible = Column(Boolean, default=True, nullable=False)
    rcm_applicable = Column(Boolean, default=False, nullable=False)  # Reverse Charge Mechanism
    counterparty_gstin = Column(String(15), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_gst_records_tenant_period", "tenant_id", "period"),
    )


class GSTReport(Base):
    __tablename__ = "gst_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    period = Column(String(7), nullable=False, index=True)  # YYYY-MM
    report_type = Column(String(20), nullable=False)  # GSTR1, GSTR3B
    
    total_taxable_value = Column(Numeric(14, 2), default=0.0, nullable=False)
    total_cgst = Column(Numeric(14, 2), default=0.0, nullable=False)
    total_sgst = Column(Numeric(14, 2), default=0.0, nullable=False)
    total_igst = Column(Numeric(14, 2), default=0.0, nullable=False)
    total_itc_claimed = Column(Numeric(14, 2), default=0.0, nullable=False)
    net_tax_liability = Column(Numeric(14, 2), default=0.0, nullable=False)
    
    summary_payload = Column(JSON, nullable=False)
    status = Column(String(50), default="SIMULATED_DRAFT", nullable=False)  # SIMULATED_DRAFT, SIMULATED_FILED
    filed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="gst_reports")

    __table_args__ = (
        Index("ix_gst_reports_tenant_period_type", "tenant_id", "period", "report_type", unique=True),
    )
