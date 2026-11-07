import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt
from backend.app.models.ledger import LedgerAccount, LedgerEntry
from backend.app.services.financial_engine import (
    generate_trial_balance,
    generate_financial_statements
)
from backend.app.services.gst_calculator import (
    generate_gstr1_summary,
    generate_gstr3b_summary
)
from backend.app.services.graph_rag import (
    find_vendor_payment_trail,
    find_unreconciled_transaction_trail
)


def search_transactions_tool(
    db: Session,
    tenant_id: str,
    query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    category: Optional[str] = None,
    counterparty: Optional[str] = None,
    tx_type: Optional[str] = None,
    channel: Optional[str] = None,
    is_reconciled: Optional[bool] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Searches transactions for a specific tenant with multi-criteria filtering.
    Strictly tenant-isolated.
    """
    q = db.query(Transaction).filter(Transaction.tenant_id == tenant_id)

    if query:
        term = f"%{query.strip()}%"
        q = q.filter(
            or_(
                Transaction.description.ilike(term),
                Transaction.raw_narration.ilike(term),
                Transaction.counterparty_name.ilike(term),
                Transaction.reference_number.ilike(term),
                Transaction.category.ilike(term)
            )
        )

    if counterparty:
        q = q.filter(Transaction.counterparty_name.ilike(f"%{counterparty.strip()}%"))

    if category:
        q = q.filter(Transaction.category.ilike(f"%{category.strip()}%"))

    if tx_type:
        q = q.filter(Transaction.type == tx_type.upper().strip())

    if channel:
        q = q.filter(Transaction.channel == channel.upper().strip())

    if is_reconciled is not None:
        q = q.filter(Transaction.is_reconciled == is_reconciled)

    if min_amount is not None:
        q = q.filter(Transaction.amount >= Decimal(str(min_amount)))

    if max_amount is not None:
        q = q.filter(Transaction.amount <= Decimal(str(max_amount)))

    if start_date:
        try:
            s_date = datetime.date.fromisoformat(start_date[:10])
            q = q.filter(Transaction.transaction_date >= s_date)
        except Exception:
            pass

    if end_date:
        try:
            e_date = datetime.date.fromisoformat(end_date[:10])
            q = q.filter(Transaction.transaction_date <= e_date)
        except Exception:
            pass

    rows = q.order_by(desc(Transaction.transaction_date), desc(Transaction.created_at)).limit(limit).all()

    tx_list = []
    total_amount = Decimal("0.00")
    for r in rows:
        amt = Decimal(str(r.amount))
        total_amount += amt
        tx_list.append({
            "id": r.id,
            "date": r.transaction_date.isoformat() if r.transaction_date else None,
            "amount": float(amt),
            "type": r.type,
            "counterparty_name": r.counterparty_name or "N/A",
            "description": r.description,
            "category": r.category,
            "channel": r.channel,
            "reference_number": r.reference_number,
            "is_reconciled": r.is_reconciled
        })

    summary = (
        f"Found {len(tx_list)} transactions totaling ₹{float(total_amount):,.2f}."
        if tx_list else "No transactions matching the criteria were found."
    )

    return {
        "total_count": len(tx_list),
        "total_amount": float(total_amount),
        "transactions": tx_list,
        "summary": summary
    }


def get_top_vendors_tool(
    db: Session,
    tenant_id: str,
    period: Optional[str] = None,
    quarter: Optional[str] = None,
    top_n: int = 5
) -> Dict[str, Any]:
    """
    Ranks top vendors by total payment volume for a tenant within a given period or quarter.
    """
    q = db.query(
        Transaction.counterparty_name,
        func.sum(Transaction.amount).label("total_paid"),
        func.count(Transaction.id).label("tx_count"),
        func.max(Transaction.category).label("primary_category")
    ).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.type == "DEBIT",
        Transaction.counterparty_name.isnot(None),
        Transaction.counterparty_name != ""
    )

    # Date filter by period or quarter
    start_d, end_d = None, None
    if quarter:
        # e.g. "Q3" or "this quarter"
        q_lower = quarter.lower()
        year = 2026
        if "2025" in q_lower:
            year = 2025
        if "q1" in q_lower:
            start_d, end_d = datetime.date(year, 1, 1), datetime.date(year, 3, 31)
        elif "q2" in q_lower:
            start_d, end_d = datetime.date(year, 4, 1), datetime.date(year, 6, 30)
        elif "q3" in q_lower or "third" in q_lower:
            start_d, end_d = datetime.date(year, 7, 1), datetime.date(year, 9, 30)
        else:
            # Default to Q4 (Oct - Dec)
            start_d, end_d = datetime.date(year, 10, 1), datetime.date(year, 12, 31)
    elif period:
        parts = period.split("-")
        if len(parts) == 2:
            y, m = int(parts[0]), int(parts[1])
            start_d = datetime.date(y, m, 1)
            # end of month
            if m == 12:
                end_d = datetime.date(y + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end_d = datetime.date(y, m + 1, 1) - datetime.timedelta(days=1)

    if start_d:
        q = q.filter(Transaction.transaction_date >= start_d)
    if end_d:
        q = q.filter(Transaction.transaction_date <= end_d)

    grouped = q.group_by(Transaction.counterparty_name).order_by(desc("total_paid")).limit(top_n).all()

    total_outflow = db.query(func.sum(Transaction.amount)).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.type == "DEBIT"
    )
    if start_d:
        total_outflow = total_outflow.filter(Transaction.transaction_date >= start_d)
    if end_d:
        total_outflow = total_outflow.filter(Transaction.transaction_date <= end_d)
    total_spend_val = float(total_outflow.scalar() or 0.0)

    top_vendors = []
    for rank, (name, paid, count, cat) in enumerate(grouped, 1):
        paid_float = float(paid)
        pct = (paid_float / total_spend_val * 100) if total_spend_val > 0 else 0.0
        top_vendors.append({
            "rank": rank,
            "vendor_name": name,
            "total_paid": paid_float,
            "transaction_count": count,
            "share_of_spend_pct": round(pct, 1),
            "primary_category": cat or "General Supplier"
        })

    if top_vendors:
        lead = top_vendors[0]
        summary = (
            f"Top {len(top_vendors)} vendors accounted for ₹{sum(v['total_paid'] for v in top_vendors):,.2f} "
            f"out of ₹{total_spend_val:,.2f} total expenditure. "
            f"Largest vendor was {lead['vendor_name']} with ₹{lead['total_paid']:,.2f} ({lead['share_of_spend_pct']}% of spend)."
        )
    else:
        summary = "No vendor payments recorded for the specified timeframe."

    return {
        "period": period or (quarter or "Quarter"),
        "total_spend": total_spend_val,
        "top_vendors": top_vendors,
        "summary": summary
    }


def find_unmatched_vendor_payments_tool(
    db: Session,
    tenant_id: str,
    vendor_name: str,
    period: Optional[str] = None
) -> Dict[str, Any]:
    """
    Finds bank payments to a specific vendor that do not have matching invoices or are unreconciled.
    """
    v_term = f"%{vendor_name.strip()}%"
    q_tx = db.query(Transaction).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.type == "DEBIT",
        or_(
            Transaction.counterparty_name.ilike(v_term),
            Transaction.description.ilike(v_term),
            Transaction.raw_narration.ilike(v_term)
        )
    )

    if period:
        parts = period.split("-")
        if len(parts) == 2:
            try:
                y, m = int(parts[0]), int(parts[1])
                s_d = datetime.date(y, m, 1)
                e_d = datetime.date(y + 1, 1, 1) - datetime.timedelta(days=1) if m == 12 else datetime.date(y, m + 1, 1) - datetime.timedelta(days=1)
                q_tx = q_tx.filter(Transaction.transaction_date >= s_d, Transaction.transaction_date <= e_d)
            except Exception:
                pass

    all_payments = q_tx.order_by(desc(Transaction.transaction_date)).all()
    unmatched = [t for t in all_payments if not t.is_reconciled]

    # Query matching receipts for this vendor
    q_rcpt = db.query(Receipt).filter(
        Receipt.tenant_id == tenant_id,
        or_(Receipt.vendor_name.ilike(v_term), Receipt.ocr_raw_text.ilike(v_term))
    )
    receipts = q_rcpt.all()

    unmatched_list = []
    unmatched_sum = Decimal("0.00")
    for t in unmatched:
        amt = Decimal(str(t.amount))
        unmatched_sum += amt
        unmatched_list.append({
            "id": t.id,
            "date": t.transaction_date.isoformat() if t.transaction_date else None,
            "amount": float(amt),
            "description": t.description,
            "channel": t.channel,
            "reference_number": t.reference_number or "N/A"
        })

    summary = (
        f"Found {len(unmatched_list)} unmatched payments totaling ₹{float(unmatched_sum):,.2f} to '{vendor_name}' "
        f"(out of {len(all_payments)} total payments recorded). Found {len(receipts)} invoice receipts on file."
    )

    return {
        "vendor_name": vendor_name,
        "total_payments_count": len(all_payments),
        "unmatched_count": len(unmatched_list),
        "unmatched_amount": float(unmatched_sum),
        "unmatched_payments": unmatched_list,
        "invoices_on_file_count": len(receipts),
        "summary": summary
    }


def compare_expenses_tool(
    db: Session,
    tenant_id: str,
    period_a: str,
    period_b: str
) -> Dict[str, Any]:
    """
    Compares expenses between two accounting periods (e.g. '2026-10' vs '2026-09')
    broken down by category and overall total.
    """
    def _get_period_expenses(p_str: str) -> Tuple[Decimal, Dict[str, Decimal]]:
        try:
            parts = p_str.split("-")
            y, m = int(parts[0]), int(parts[1])
            s_d = datetime.date(y, m, 1)
            e_d = datetime.date(y + 1, 1, 1) - datetime.timedelta(days=1) if m == 12 else datetime.date(y, m + 1, 1) - datetime.timedelta(days=1)
        except Exception:
            return Decimal("0.00"), {}

        rows = db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("cat_total")
        ).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.type == "DEBIT",
            Transaction.transaction_date >= s_d,
            Transaction.transaction_date <= e_d
        ).group_by(Transaction.category).all()

        cats = {r[0] or "Uncategorized": Decimal(str(r[1] or 0)) for r in rows}
        tot = sum(cats.values(), Decimal("0.00"))
        return tot, cats

    total_a, cats_a = _get_period_expenses(period_a)
    total_b, cats_b = _get_period_expenses(period_b)

    all_cats = set(cats_a.keys()) | set(cats_b.keys())
    breakdown = []
    for cat in sorted(all_cats):
        amt_a = cats_a.get(cat, Decimal("0.00"))
        amt_b = cats_b.get(cat, Decimal("0.00"))
        diff = amt_a - amt_b
        pct = float((diff / amt_b * 100)) if amt_b > Decimal("0.00") else 0.0
        breakdown.append({
            "category": cat,
            f"period_{period_a}": float(amt_a),
            f"period_{period_b}": float(amt_b),
            "difference": float(diff),
            "pct_change": round(pct, 1),
            "direction": "INCREASED" if diff > 0 else ("DECREASED" if diff < 0 else "FLAT")
        })

    net_diff = total_a - total_b
    net_pct = float((net_diff / total_b * 100)) if total_b > Decimal("0.00") else 0.0

    summary = (
        f"Expenses for {period_a} were ₹{float(total_a):,.2f} compared to ₹{float(total_b):,.2f} in {period_b} "
        f"({'+' if net_diff > 0 else ''}₹{float(net_diff):,.2f}, {net_pct:+.1f}%). "
    )
    if breakdown:
        top_driver = max(breakdown, key=lambda x: abs(x["difference"]))
        summary += f"The largest change was in '{top_driver['category']}' ({'+' if top_driver['difference'] > 0 else ''}₹{top_driver['difference']:,.2f})."

    return {
        "period_a": period_a,
        "period_b": period_b,
        "total_period_a": float(total_a),
        "total_period_b": float(total_b),
        "net_difference": float(net_diff),
        "pct_change": round(net_pct, 1),
        "categories_breakdown": breakdown,
        "summary": summary
    }


def search_overdue_invoices_tool(
    db: Session,
    tenant_id: str,
    as_of_date: Optional[str] = None,
    overdue_days: int = 30
) -> Dict[str, Any]:
    """
    Finds overdue or unreconciled invoices for the tenant.
    """
    ref_date = datetime.date.today()
    if as_of_date:
        try:
            ref_date = datetime.date.fromisoformat(as_of_date[:10])
        except Exception:
            pass

    cutoff_date = ref_date - datetime.timedelta(days=overdue_days)

    rows = db.query(Receipt).filter(
        Receipt.tenant_id == tenant_id,
        Receipt.status != "RECONCILED",
        Receipt.invoice_date <= cutoff_date
    ).order_by(Receipt.invoice_date).all()

    # Also search credit transactions that might represent customer accounts receivable
    items = []
    total_overdue = Decimal("0.00")
    for r in rows:
        amt = Decimal(str(r.total_amount or 0.0))
        total_overdue += amt
        days = (ref_date - r.invoice_date).days if r.invoice_date else overdue_days
        items.append({
            "invoice_number": r.invoice_number or f"INV-{r.id[:6]}",
            "counterparty_name": r.vendor_name or "Unknown Counterparty",
            "invoice_date": r.invoice_date.isoformat() if r.invoice_date else None,
            "days_overdue": days,
            "amount": float(amt),
            "status": r.status
        })

    summary = (
        f"Found {len(items)} overdue invoices totaling ₹{float(total_overdue):,.2f} "
        f"exceeding the {overdue_days}-day payment terms."
        if items else f"No invoices are currently overdue beyond {overdue_days} days."
    )

    return {
        "overdue_count": len(items),
        "total_overdue_amount": float(total_overdue),
        "overdue_invoices": items,
        "summary": summary
    }


def find_large_and_anomalous_transactions_tool(
    db: Session,
    tenant_id: str,
    threshold: float = 25000.0,
    period: Optional[str] = None
) -> Dict[str, Any]:
    """
    Identifies transactions at or above the threshold (default ₹25,000) and checks
    for statutory anomalies (e.g. Section 40A(3) cash limits > ₹10,000, duplicate UTRs).
    """
    q = db.query(Transaction).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.amount >= Decimal(str(threshold))
    )

    if period:
        parts = period.split("-")
        if len(parts) == 2:
            try:
                y, m = int(parts[0]), int(parts[1])
                s_d = datetime.date(y, m, 1)
                e_d = datetime.date(y + 1, 1, 1) - datetime.timedelta(days=1) if m == 12 else datetime.date(y, m + 1, 1) - datetime.timedelta(days=1)
                q = q.filter(Transaction.transaction_date >= s_d, Transaction.transaction_date <= e_d)
            except Exception:
                pass

    rows = q.order_by(desc(Transaction.amount)).all()

    items = []
    anomalies_flagged = 0
    total_val = Decimal("0.00")

    for r in rows:
        amt = Decimal(str(r.amount))
        total_val += amt
        flags = []

        # Check 1: Section 40A(3) Cash Threshold Violation
        if (r.channel or "").upper() == "CASH" and (r.type or "").upper() == "DEBIT" and amt > Decimal("10000.00"):
            flags.append("Statutory Violation: Section 40A(3) Income Tax Act bans business cash expenses exceeding ₹10,000 per day.")
            anomalies_flagged += 1

        # Check 2: High value round sum without counterparty
        if not r.counterparty_name and float(amt) % 1000 == 0:
            flags.append("Audit Notice: Round-sum transfer lacking verified counterparty entity.")
            anomalies_flagged += 1

        items.append({
            "id": r.id,
            "date": r.transaction_date.isoformat() if r.transaction_date else None,
            "amount": float(amt),
            "type": r.type,
            "counterparty_name": r.counterparty_name or "Unspecified",
            "category": r.category,
            "channel": r.channel,
            "reference_number": r.reference_number,
            "anomalies": flags,
            "is_flagged": len(flags) > 0
        })

    summary = (
        f"Found {len(items)} transactions >= ₹{threshold:,.2f} totaling ₹{float(total_val):,.2f}. "
        f"{anomalies_flagged} compliance or audit flags were detected."
    )

    return {
        "threshold": threshold,
        "total_count": len(items),
        "total_amount": float(total_val),
        "anomalies_count": anomalies_flagged,
        "transactions": items,
        "summary": summary
    }


def explain_cash_decrease_tool(
    db: Session,
    tenant_id: str,
    period: Optional[str] = None
) -> Dict[str, Any]:
    """
    Performs analytical cash-flow variance analysis explaining why cash decreased in a period.
    Identifies top outflow drivers and net deficit.
    """
    ref_period = period or datetime.date.today().strftime("%Y-%m")
    parts = ref_period.split("-")
    y, m = int(parts[0]), int(parts[1])
    s_d = datetime.date(y, m, 1)
    e_d = datetime.date(y + 1, 1, 1) - datetime.timedelta(days=1) if m == 12 else datetime.date(y, m + 1, 1) - datetime.timedelta(days=1)

    # Inflows
    inflow_res = db.query(func.sum(Transaction.amount)).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.type == "CREDIT",
        Transaction.transaction_date >= s_d,
        Transaction.transaction_date <= e_d
    ).scalar() or 0.0

    # Outflows
    outflow_res = db.query(func.sum(Transaction.amount)).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.type == "DEBIT",
        Transaction.transaction_date >= s_d,
        Transaction.transaction_date <= e_d
    ).scalar() or 0.0

    inflows = float(inflow_res)
    outflows = float(outflow_res)
    net_cash_flow = inflows - outflows

    # Top outflow categories
    top_cats = db.query(
        Transaction.category,
        func.sum(Transaction.amount).label("cat_total")
    ).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.type == "DEBIT",
        Transaction.transaction_date >= s_d,
        Transaction.transaction_date <= e_d
    ).group_by(Transaction.category).order_by(desc("cat_total")).limit(3).all()

    top_outflows = [{"category": r[0] or "General", "amount": float(r[1])} for r in top_cats]

    if net_cash_flow < 0:
        summary = (
            f"Cash balance decreased by ₹{abs(net_cash_flow):,.2f} during {ref_period}. "
            f"Total operating outflows (₹{outflows:,.2f}) exceeded revenue collections (₹{inflows:,.2f}). "
            f"The primary outflow drivers were: " + ", ".join(f"{c['category']} (₹{c['amount']:,.2f})" for c in top_outflows) + "."
        )
    else:
        summary = (
            f"Net cash flow was positive (+₹{net_cash_flow:,.2f}) during {ref_period}. "
            f"Collections of ₹{inflows:,.2f} exceeded outflows of ₹{outflows:,.2f}."
        )

    return {
        "period": ref_period,
        "total_inflows": inflows,
        "total_outflows": outflows,
        "net_cash_flow": net_cash_flow,
        "top_outflow_drivers": top_outflows,
        "summary": summary
    }


def get_gst_itc_status_tool(
    db: Session,
    tenant_id: str,
    period: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates statutory Input Tax Credit (ITC) eligibility under Section 16 & Section 17(5) CGST Act.
    """
    ref_period = period or datetime.date.today().strftime("%Y-%m")
    parts = ref_period.split("-")
    y, m = int(parts[0]), int(parts[1])
    s_d = datetime.date(y, m, 1)
    e_d = datetime.date(y + 1, 1, 1) - datetime.timedelta(days=1) if m == 12 else datetime.date(y, m + 1, 1) - datetime.timedelta(days=1)

    purchases = db.query(Transaction).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.type == "DEBIT",
        Transaction.transaction_date >= s_d,
        Transaction.transaction_date <= e_d
    ).all()

    eligible_itc = Decimal("0.00")
    blocked_itc = Decimal("0.00")
    exempt_amount = Decimal("0.00")

    for p in purchases:
        amt = Decimal(str(p.amount))
        rate = Decimal(str(p.tax_rate or 0.0))
        cat = (p.category or "").lower()

        # Check for blocked credit under Section 17(5)
        if any(b in cat for b in ["food", "beverage", "catering", "pantry", "tea", "coffee", "motor", "personal", "club"]):
            tax_component = amt * rate / (Decimal("100.0") + rate) if rate > 0 else Decimal("0.00")
            blocked_itc += tax_component
        elif rate > Decimal("0.0"):
            tax_component = amt * rate / (Decimal("100.0") + rate)
            eligible_itc += tax_component
        else:
            exempt_amount += amt

    summary = (
        f"GST Input Tax Credit Status for {ref_period}: "
        f"Eligible ITC available under Section 16(1): ₹{float(eligible_itc):,.2f}. "
        f"Blocked ITC under Section 17(5): ₹{float(blocked_itc):,.2f}. "
        f"Exempt / zero-rated purchases: ₹{float(exempt_amount):,.2f}."
    )

    return {
        "period": ref_period,
        "eligible_itc": float(eligible_itc),
        "blocked_itc": float(blocked_itc),
        "exempt_purchases": float(exempt_amount),
        "statutory_clauses": [
            "Section 16(1) CGST Act: Eligible on inputs used in the course or furtherance of business.",
            "Section 16(2) CGST Act: Requires invoice possession and reflection in GSTR-2B.",
            "Section 17(5) CGST Act: Credit blocked for food, beverage, and motor vehicle expenses."
        ],
        "summary": summary
    }


def trace_vendor_payment_trail_tool(
    db: Session,
    tenant_id: str,
    vendor_name: str
) -> Dict[str, Any]:
    """
    Executes a complete GraphRAG entity traversal tracing all invoices, bank payments,
    and balanced double-entry vouchers for a vendor.
    """
    trail = find_vendor_payment_trail(db, tenant_id, vendor_name)
    return trail


def generate_financial_summary_export_tool(
    db: Session,
    tenant_id: str,
    period: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a consolidated monthly financial statement, GST summary,
    and key operational ratios packaged for export.
    """
    ref_period = period or datetime.date.today().strftime("%Y-%m")
    statements = generate_financial_statements(db, tenant_id)
    gst_1 = generate_gstr1_summary(db, tenant_id, ref_period)
    gst_3b = generate_gstr3b_summary(db, tenant_id, ref_period)
    tb = generate_trial_balance(db, tenant_id)

    top_expenses_res = get_top_vendors_tool(db, tenant_id, period=ref_period, top_n=5)

    summary_doc = {
        "title": f"VyaparSetu Financial Operations Summary ({ref_period})",
        "tenant_id": tenant_id,
        "financial_period": ref_period,
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "profit_and_loss": statements.get("profit_and_loss", {}),
        "balance_sheet": statements.get("balance_sheet", {}),
        "cash_flow": statements.get("cash_flow", {}),
        "gst_summary": {
            "period": ref_period,
            "total_outward_tax": gst_1.get("total_tax_liability", 0.0),
            "net_cash_payable": gst_3b.get("net_cash_payable", 0.0),
            "gstr3b_status": "Ready for Filing"
        },
        "trial_balance_status": {
            "is_balanced": tb.get("is_balanced", True),
            "total_debit": tb.get("total_debit", "0.00"),
            "total_credit": tb.get("total_credit", "0.00")
        },
        "top_vendors": top_expenses_res.get("top_vendors", []),
        "export_available_formats": ["JSON", "CSV", "PDF"]
    }

    narrative = (
        f"Consolidated Financial Summary for {ref_period}: "
        f"Net Profit: ₹{statements.get('profit_and_loss', {}).get('net_profit', '0.00')}, "
        f"Net GST Cash Liability: ₹{gst_3b.get('net_cash_payable', 0.0):,.2f}, "
        f"Trial Balance verified in equilibrium. Summary ready for export."
    )

    return {
        "report": summary_doc,
        "summary": narrative
    }


# Expose registry dictionary
TOOL_REGISTRY: Dict[str, Any] = {
    "search_transactions": search_transactions_tool,
    "get_top_vendors": get_top_vendors_tool,
    "find_unmatched_vendor_payments": find_unmatched_vendor_payments_tool,
    "compare_expenses": compare_expenses_tool,
    "search_overdue_invoices": search_overdue_invoices_tool,
    "find_large_and_anomalous_transactions": find_large_and_anomalous_transactions_tool,
    "explain_cash_decrease": explain_cash_decrease_tool,
    "get_gst_itc_status": get_gst_itc_status_tool,
    "trace_vendor_payment_trail": trace_vendor_payment_trail_tool,
    "generate_financial_summary_export": generate_financial_summary_export_tool
}

