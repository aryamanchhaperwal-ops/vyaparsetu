import datetime
from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.transaction import Transaction
from backend.app.models.ledger import LedgerAccount

def compute_cash_flow_analytics(db: Session, tenant_id: str) -> Dict[str, Any]:
    """
    Computes cash-flow trends, operating margins, daily net balances, and runway for the MSME.
    """
    transactions = db.query(Transaction).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.status == "CONFIRMED"
    ).all()

    total_inflow = Decimal("0.00")
    total_outflow = Decimal("0.00")
    category_breakdown: Dict[str, Decimal] = {}

    for tx in transactions:
        amt = tx.amount
        if tx.type == "CREDIT":
            total_inflow += amt
        else:
            total_outflow += amt
            cat = tx.category or "Other"
            category_breakdown[cat] = category_breakdown.get(cat, Decimal("0.00")) + amt

    net_cash_flow = total_inflow - total_outflow

    # Fetch cash & bank balances from chart of accounts
    liquid_accounts = db.query(LedgerAccount).filter(
        LedgerAccount.tenant_id == tenant_id,
        LedgerAccount.code.in_(["1010", "1020"])
    ).all()
    current_liquidity = sum((acc.balance for acc in liquid_accounts), Decimal("0.00"))

    # Compute runway: assuming monthly burn rate
    monthly_burn = max(Decimal("1.00"), total_outflow / Decimal("3.0"))  # Approximate 90 day window
    runway_months = (current_liquidity / monthly_burn).quantize(Decimal("0.1")) if current_liquidity > 0 else Decimal("0.0")

    return {
        "tenant_id": tenant_id,
        "total_inflows": f"{total_inflow:.2f}",
        "total_outflows": f"{total_outflow:.2f}",
        "net_cash_flow": f"{net_cash_flow:.2f}",
        "current_liquid_balance": f"{current_liquidity:.2f}",
        "estimated_monthly_burn": f"{monthly_burn:.2f}",
        "cash_runway_months": float(runway_months),
        "expense_category_breakdown": [
            {"category": k, "amount": f"{v:.2f}", "percentage": round(float(v / total_outflow * 100), 1) if total_outflow > 0 else 0}
            for k, v in category_breakdown.items()
        ]
    }

def compute_indicative_credit_insights(db: Session, tenant_id: str) -> Dict[str, Any]:
    """
    Computes an indicative, explainable MSME credit health score (0 - 100).
    Provides banking lenders and NBFCs with transparent solvency and working capital metrics.
    """
    txs = db.query(Transaction).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.status == "CONFIRMED"
    ).all()

    if not txs:
        return {
            "credit_score": 50,
            "grade": "NEW_BUSINESS",
            "indicative_credit_limit": "0.00",
            "summary": "Insufficient transaction history. Ingest banking data to compute credit insights."
        }

    inflows = sum((t.amount for t in txs if t.type == "CREDIT"), Decimal("0.00"))
    outflows = sum((t.amount for t in txs if t.type == "DEBIT"), Decimal("0.00"))

    score = 0
    factors = []

    # Factor 1: Turnover Volume & Health (Max 30 pts)
    if inflows >= Decimal("500000.00"):
        score += 30
        factors.append({"name": "Turnover Scale", "status": "EXCELLENT", "points": 30, "detail": "Healthy commercial transaction volume > ₹5L"})
    elif inflows >= Decimal("100000.00"):
        score += 24
        factors.append({"name": "Turnover Scale", "status": "GOOD", "points": 24, "detail": "Moderate turnover volume > ₹1L"})
    else:
        score += 15
        factors.append({"name": "Turnover Scale", "status": "FAIR", "points": 15, "detail": "Micro merchant volume < ₹1L"})

    # Factor 2: Inflow-to-Outflow Coverage Ratio (Max 35 pts)
    coverage_ratio = (inflows / outflows) if outflows > 0 else Decimal("1.5")
    if coverage_ratio >= Decimal("1.25"):
        score += 35
        factors.append({"name": "Cash Coverage", "status": "EXCELLENT", "points": 35, "detail": "Inflows exceed operating expenses by >25%"})
    elif coverage_ratio >= Decimal("1.0"):
        score += 25
        factors.append({"name": "Cash Coverage", "status": "STABLE", "points": 25, "detail": "Inflows cover all operating expenses"})
    else:
        score += 10
        factors.append({"name": "Cash Coverage", "status": "DEFICIT", "points": 10, "detail": "Operating at cash-flow deficit"})

    # Factor 3: Transaction Regularity & Banking Diversity (Max 35 pts)
    unique_channels = {t.channel for t in txs}
    if len(unique_channels) >= 3 and len(txs) >= 15:
        score += 35
        factors.append({"name": "Banking Regularity", "status": "EXCELLENT", "points": 35, "detail": "Consistent multi-channel banking (UPI, NEFT, Cheques)"})
    else:
        score += 20
        factors.append({"name": "Banking Regularity", "status": "MODERATE", "points": 20, "detail": "Limited channel diversity"})

    # Grade determination
    if score >= 85:
        grade = "PRIME (AAA)"
        multiplier = Decimal("0.25")  # Up to 25% of annual turnover
    elif score >= 70:
        grade = "STABLE (A)"
        multiplier = Decimal("0.18")
    elif score >= 55:
        grade = "MODERATE (BBB)"
        multiplier = Decimal("0.12")
    else:
        grade = "HIGH_MONITORING (BB)"
        multiplier = Decimal("0.05")

    indicative_credit_limit = (inflows * multiplier).quantize(Decimal("1.00"))

    return {
        "tenant_id": tenant_id,
        "indicative_credit_score": score,
        "maximum_score": 100,
        "credit_grade": grade,
        "indicative_working_capital_limit": f"{indicative_credit_limit:.2f}",
        "inflow_outflow_ratio": round(float(coverage_ratio), 2),
        "score_factors": factors,
        "notice": "INDICATIVE PRE-ASSESSMENT — NOT AN OFFICIAL CREDIT GUARANTEE"
    }

