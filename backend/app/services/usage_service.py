import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.user import Tenant
from backend.app.models.usage import UsageRecord, AuditLog

PLAN_LIMITS: Dict[str, Dict[str, int]] = {
    "FREE": {
        "max_monthly_transactions": 100,
        "max_monthly_ocr": 15,
        "max_monthly_tokens": 15000
    },
    "PRO": {
        "max_monthly_transactions": 2500,
        "max_monthly_ocr": 300,
        "max_monthly_tokens": 200000
    },
    "ENTERPRISE": {
        "max_monthly_transactions": 100000,
        "max_monthly_ocr": 10000,
        "max_monthly_tokens": 5000000
    }
}

def get_or_create_usage_record(db: Session, tenant_id: str) -> UsageRecord:
    current_period = datetime.datetime.utcnow().strftime("%Y-%m")
    usage = db.query(UsageRecord).filter(
        UsageRecord.tenant_id == tenant_id,
        UsageRecord.billing_period == current_period
    ).first()

    if not usage:
        usage = UsageRecord(
            tenant_id=tenant_id,
            billing_period=current_period,
            transactions_processed=0,
            ocr_scans_processed=0,
            llm_tokens_used=0,
            plan_limit_exceeded=False
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)
    return usage

def check_and_record_usage(
    db: Session,
    tenant: Tenant,
    resource_type: str,  # "transaction", "ocr", "tokens"
    count: int = 1
) -> UsageRecord:
    """Checks tenant quota against their subscription tier and records usage."""
    usage = get_or_create_usage_record(db, tenant.id)
    limits = PLAN_LIMITS.get(tenant.subscription_plan, PLAN_LIMITS["FREE"])

    if resource_type == "transaction":
        if usage.transactions_processed + count > limits["max_monthly_transactions"]:
            usage.plan_limit_exceeded = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly transaction limit ({limits['max_monthly_transactions']}) exceeded for {tenant.subscription_plan} tier. Please upgrade to PRO."
            )
        usage.transactions_processed += count
    elif resource_type == "ocr":
        if usage.ocr_scans_processed + count > limits["max_monthly_ocr"]:
            usage.plan_limit_exceeded = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly receipt OCR limit ({limits['max_monthly_ocr']}) exceeded for {tenant.subscription_plan} tier. Please upgrade to PRO."
            )
        usage.ocr_scans_processed += count
    elif resource_type == "tokens":
        usage.llm_tokens_used += count

    db.commit()
    return usage

def log_audit_trail(
    db: Session,
    tenant_id: str,
    action: str,
    entity_name: str,
    entity_id: str,
    user_id: Optional[str] = None,
    old_value: Optional[Dict[str, Any]] = None,
    new_value: Optional[Dict[str, Any]] = None
):
    """Creates an immutable audit log for compliance and multi-tenant security tracking."""
    audit = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        entity_name=entity_name,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        timestamp=datetime.datetime.utcnow()
    )
    db.add(audit)
    db.commit()

