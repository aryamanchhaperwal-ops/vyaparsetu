import uuid
import datetime
from sqlalchemy import Column, String, DateTime, Date, Numeric, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)

    invoice_number = Column(String(100), nullable=True, index=True)
    invoice_date = Column(Date, nullable=True)
    vendor_name = Column(String(255), nullable=True)
    vendor_gstin = Column(String(15), nullable=True)
    
    total_amount = Column(Numeric(14, 2), nullable=True)
    taxable_amount = Column(Numeric(14, 2), nullable=True)
    cgst_amount = Column(Numeric(14, 2), default=0.0, nullable=False)
    sgst_amount = Column(Numeric(14, 2), default=0.0, nullable=False)
    igst_amount = Column(Numeric(14, 2), default=0.0, nullable=False)
    
    file_path = Column(String(500), nullable=True)
    ocr_raw_text = Column(Text, nullable=True)
    ocr_extracted_data = Column(JSON, nullable=True)
    
    status = Column(String(50), default="EXTRACTED", nullable=False)  # PENDING, EXTRACTED, RECONCILED, MANUAL
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="receipts")
    transaction = relationship("Transaction", back_populates="receipt")

    __table_args__ = (
        Index("ix_receipts_tenant_invoice", "tenant_id", "invoice_number"),
    )

