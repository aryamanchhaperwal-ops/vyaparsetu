from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_tenant, get_current_user
from backend.app.models.user import Tenant, User
from backend.app.models.usage import AuditLog
from backend.app.services.usage_service import (
    get_or_create_usage_record,
    log_audit_trail,
    PLAN_LIMITS
)

router = APIRouter()

class UpgradePlanRequest(BaseModel):
    plan: str  # PRO, ENTERPRISE

@router.get("/usage")
def get_current_usage(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    usage = get_or_create_usage_record(db, tenant.id)
    limits = PLAN_LIMITS.get(tenant.subscription_plan, PLAN_LIMITS["FREE"])

    return {
        "tenant_id": tenant.id,
        "subscription_plan": tenant.subscription_plan,
        "billing_period": usage.billing_period,
        "transactions_used": usage.transactions_processed,
        "transactions_limit": limits["max_monthly_transactions"],
        "ocr_scans_used": usage.ocr_scans_processed,
        "ocr_scans_limit": limits["max_monthly_ocr"],
        "llm_tokens_used": usage.llm_tokens_used,
        "llm_tokens_limit": limits["max_monthly_tokens"],
        "plan_limit_exceeded": usage.plan_limit_exceeded
    }

@router.post("/upgrade")
def upgrade_subscription_tier(
    req: UpgradePlanRequest,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    if req.plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail="Invalid plan name. Choose from PRO or ENTERPRISE")

    old_plan = tenant.subscription_plan
    tenant.subscription_plan = req.plan

    # Log audit
    log_audit_trail(
        db=db,
        tenant_id=tenant.id,
        action="UPGRADE_SUBSCRIPTION_PLAN",
        entity_name="Tenant",
        entity_id=tenant.id,
        user_id=current_user.id,
        old_value={"plan": old_plan},
        new_value={"plan": req.plan}
    )

    db.commit()
    return {
        "status": "success",
        "previous_plan": old_plan,
        "new_plan": req.plan,
        "message": f"Successfully upgraded workspace to {req.plan} tier."
    }

@router.get("/audit-logs")
def get_tenant_audit_logs(
    tenant: Tenant = Depends(get_current_tenant),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    logs = db.query(AuditLog).filter(
        AuditLog.tenant_id == tenant.id
    ).order_by(desc(AuditLog.timestamp)).limit(limit).all()

    return [
        {
            "id": l.id,
            "action": l.action,
            "entity_name": l.entity_name,
            "entity_id": l.entity_id,
            "old_value": l.old_value,
            "new_value": l.new_value,
            "timestamp": l.timestamp.isoformat()
        }
        for l in logs
    ]
