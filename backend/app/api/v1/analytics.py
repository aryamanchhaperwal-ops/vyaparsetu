from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_tenant
from backend.app.models.user import Tenant
from backend.app.services.analytics_service import (
    compute_cash_flow_analytics,
    compute_indicative_credit_insights
)

router = APIRouter()

@router.get("/cashflow")
def get_cashflow_analytics(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Returns cash-flow breakdown, liquid balance, and runway analysis."""
    return compute_cash_flow_analytics(db, tenant.id)

@router.get("/credit-health")
def get_credit_insights(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Returns indicative MSME credit health score and working capital insights."""
    return compute_indicative_credit_insights(db, tenant.id)
