from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_tenant
from backend.app.models.user import Tenant
from backend.app.services.analytics_service import (
    compute_cash_flow_analytics,
    compute_cash_flow_forecast,
    compute_indicative_credit_insights
)
from backend.app.services.knowledge_graph import build_financial_knowledge_graph

router = APIRouter()

@router.get("/cashflow")
def get_cashflow_analytics(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Returns cash-flow breakdown, liquid balance, and runway analysis."""
    return compute_cash_flow_analytics(db, tenant.id)

@router.get("/forecast")
def get_cashflow_forecast(
    days: int = 30,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Returns 30-day forward predictive cash flow forecast and liquidity buffers."""
    return compute_cash_flow_forecast(db, tenant.id, projection_days=days)

@router.get("/credit-health")
def get_credit_insights(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Returns indicative MSME credit health score and working capital insights."""
    return compute_indicative_credit_insights(db, tenant.id)

@router.get("/knowledge-graph")
def get_financial_knowledge_graph(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Returns the tenant's complete Financial Knowledge Graph:
    Vendors -> Categories -> HSN/SAC Codes -> Ledger Accounts -> GST Return Tables.
    """
    return build_financial_knowledge_graph(db, tenant.id)

