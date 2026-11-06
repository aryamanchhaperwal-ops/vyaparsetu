from decimal import Decimal
from typing import Dict, Any, Optional
from pydantic import BaseModel
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_tenant, require_roles
from backend.app.models.user import Tenant, Membership
from backend.app.models.gst import GSTReport
from backend.app.services.gst_calculator import (
    calculate_transaction_gst,
    generate_gstr1_summary,
    generate_gstr3b_summary,
    round_to_rupee
)

router = APIRouter()

class GSTCalcRequest(BaseModel):
    amount: float
    rate_percent: float = 18.0
    is_interstate: bool = False
    is_inclusive: bool = True

class FileSimulatedReturnRequest(BaseModel):
    period: str  # YYYY-MM
    report_type: str  # GSTR1 or GSTR3B

@router.post("/compute")
def compute_gst(req: GSTCalcRequest):
    """Instant deterministic GST calculation endpoint."""
    res = calculate_transaction_gst(
        amount=Decimal(str(req.amount)),
        rate_percent=Decimal(str(req.rate_percent)),
        is_interstate=req.is_interstate,
        is_inclusive=req.is_inclusive
    )
    return {
        "amount": req.amount,
        "rate_percent": req.rate_percent,
        "is_interstate": req.is_interstate,
        "taxable_value": f"{res['taxable_value']:.2f}",
        "cgst": f"{res['cgst']:.2f}",
        "sgst": f"{res['sgst']:.2f}",
        "igst": f"{res['igst']:.2f}",
        "total_tax": f"{res['total_tax']:.2f}",
        "total_invoice_value": f"{res['total_invoice_value']:.2f}",
        "section_170_rounded_tax": f"{res['rounded_tax']:.2f}",
        "section_170_rounded_total": f"{res['rounded_total']:.2f}"
    }

@router.get("/gstr1/{period}")
def get_gstr1_report(
    period: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Generates simulated GSTR-1 outward supply report for the tenant."""
    return generate_gstr1_summary(db, tenant.id, period)

@router.get("/gstr3b/{period}")
def get_gstr3b_report(
    period: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Generates simulated GSTR-3B monthly return & legal ITC net offset summary."""
    return generate_gstr3b_summary(db, tenant.id, period)

@router.post("/simulate-filing")
def simulate_return_filing(
    req: FileSimulatedReturnRequest,
    tenant: Tenant = Depends(get_current_tenant),
    _role: Membership = Depends(require_roles(["OWNER", "ADMIN", "ACCOUNTANT"])),
    db: Session = Depends(get_db)
):
    """Simulates filing of GSTR-1 or GSTR-3B return in the test sandbox."""
    if req.report_type == "GSTR1":
        summary = generate_gstr1_summary(db, tenant.id, req.period)
    elif req.report_type == "GSTR3B":
        summary = generate_gstr3b_summary(db, tenant.id, req.period)
    else:
        raise HTTPException(status_code=400, detail="Invalid return type: must be GSTR1 or GSTR3B")

    existing_report = db.query(GSTReport).filter(
        GSTReport.tenant_id == tenant.id,
        GSTReport.period == req.period,
        GSTReport.report_type == req.report_type
    ).first()

    if existing_report:
        existing_report.summary_payload = summary
        existing_report.status = "SIMULATED_FILED"
        existing_report.filed_at = datetime.datetime.utcnow()
        report = existing_report
    else:
        report = GSTReport(
            tenant_id=tenant.id,
            period=req.period,
            report_type=req.report_type,
            total_taxable_value=Decimal("0.00"),
            total_cgst=Decimal("0.00"),
            total_sgst=Decimal("0.00"),
            total_igst=Decimal("0.00"),
            total_itc_claimed=Decimal("0.00"),
            net_tax_liability=Decimal("0.00"),
            summary_payload=summary,
            status="SIMULATED_FILED",
            filed_at=datetime.datetime.utcnow()
        )
        db.add(report)

    db.commit()
    db.refresh(report)

    return {
        "status": "SIMULATED_FILED",
        "report_id": report.id,
        "period": report.period,
        "report_type": report.report_type,
        "filed_at": report.filed_at.isoformat(),
        "arn": f"AA{tenant.state_code}{datetime.datetime.utcnow().strftime('%m%y')}{report.id[:8].upper()}",
        "notice": "SIMULATED FILING — TEST SANDBOX ONLY (NO GOVERNMENT PORTAL CONNECTION)"
    }

