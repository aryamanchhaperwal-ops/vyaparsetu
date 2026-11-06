import uuid
import datetime
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    run_id = Column(String(100), unique=True, index=True, nullable=False)
    workflow_name = Column(String(100), default="transaction_processing", nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, RUNNING, INTERRUPTED, COMPLETED, FAILED
    current_node = Column(String(100), nullable=True)
    
    checkpoint_state = Column(JSON, nullable=True)
    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)
    
    human_feedback = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    tenant = relationship("Tenant", back_populates="workflow_runs")

    __table_args__ = (
        Index("ix_workflow_runs_tenant_status", "tenant_id", "status"),
    )
