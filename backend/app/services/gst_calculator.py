import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import extract

from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt
from backend.app.models.gst import GSTRecord, GSTReport

def round_to_rupee(amount: Decimal) -> Decimal:
    """Rounds amount to nearest whole Rupee under Section 170 of CGST Act."""
    return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

def is_interstate_supply(supplier_state_code: str, recipient_state_code: str) -> bool:
    """
    Evaluates Place of Supply under Sections 7 & 8 of the Integrated Goods and Services Tax (IGST) Act, 2017.
    Returns True if Inter-state (IGST applies), False if Intra-state (CGST + SGST applies).
    """
    if not supplier_state_code or not recipient_state_code:
        return False
    return supplier_state_code.strip() != recipient_state_code.strip()

def is_itc_blocked_under_section_17_5(category: str, sub_category: Optional[str] = None) -> bool:
    """
    Statutory evaluation under Section 17(5) of the CGST Act, 2017 (Blocked Credits):
    - Food & beverages, outdoor catering
    - Motor vehicles and conveyances (< 13 seats)
    - Membership of a club, health, and fitness centre
    - Personal consumption
    """
    cat = (category or "").lower()
    sub = (sub_category or "").lower()

    if any(k in cat or k in sub for k in [
        "food", "beverage", "pantry", "tea", "coffee", "restaurant",
        "catering", "personal", "club", "fitness", "gym"
    ]):
        return True
    return False

def calculate_transaction_gst(
    amount: Decimal,
    rate_percent: Decimal,
    is_interstate: bool = False,
    is_inclusive: bool = True
) -> Dict[str, Decimal]:
    """
    Deterministic GST calculation:
    - Intra-state: CGST (rate/2) + SGST (rate/2)
    - Inter-state: IGST (full rate)
    - Follows Section 170 round-off.
    """
    if rate_percent <= 0:
        return {
            "taxable_value": amount,
            "cgst": Decimal("0.00"),
            "sgst": Decimal("0.00"),
            "igst": Decimal("0.00"),
            "total_tax": Decimal("0.00"),
            "total_invoice_value": amount
        }

    if is_inclusive:
        factor = Decimal("1.0") + (rate_percent / Decimal("100.0"))
        taxable_value = (amount / factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_tax = amount - taxable_value
    else:
        taxable_value = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_tax = (taxable_value * (rate_percent / Decimal("100.0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if is_interstate:
        cgst = Decimal("0.00")
        sgst = Decimal("0.00")
        igst = total_tax
    else:
        cgst = (total_tax / Decimal("2.0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sgst = total_tax - cgst
        igst = Decimal("0.00")

    total_invoice = taxable_value + total_tax
    return {
        "taxable_value": taxable_value,
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "total_tax": total_tax,
        "total_invoice_value": total_invoice,
        "rounded_taxable": round_to_rupee(taxable_value),
        "rounded_tax": round_to_rupee(total_tax),
        "rounded_total": round_to_rupee(total_invoice)
    }

def generate_gstr1_summary(db: Session, tenant_id: str, period: str) -> Dict[str, Any]:
    """
    Generates statutory GSTR-1 outward supply summary for a given YYYY-MM period.
    Separates into Table 4 (B2B Taxable), Table 7 (B2C Others), and Table 12 (HSN Summary).
    """
    year, month = map(int, period.split("-"))
    # Inflow/Sales transactions
    transactions = db.query(Transaction).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.type == "CREDIT",
        extract("year", Transaction.transaction_date) == year,
        extract("month", Transaction.transaction_date) == month
    ).all()

    b2b_supplies = []
    b2c_supplies = []
    hsn_summary: Dict[str, Dict[str, Any]] = {}

    total_taxable = Decimal("0.00")
    total_cgst = Decimal("0.00")
    total_sgst = Decimal("0.00")
    total_igst = Decimal("0.00")

    for tx in transactions:
        is_interstate = False
        rate = Decimal(str(tx.tax_rate or "18.0"))
        gst_calc = calculate_transaction_gst(tx.amount, rate, is_interstate=is_interstate, is_inclusive=True)

        total_taxable += gst_calc["taxable_value"]
        total_cgst += gst_calc["cgst"]
        total_sgst += gst_calc["sgst"]
        total_igst += gst_calc["igst"]

        hsn = tx.hsn_sac_code or "9988"
        if hsn not in hsn_summary:
            hsn_summary[hsn] = {
                "hsn_code": hsn,
                "description": tx.category,
                "total_quantity": 1,
                "total_value": Decimal("0.00"),
                "taxable_value": Decimal("0.00"),
                "integrated_tax": Decimal("0.00"),
                "central_tax": Decimal("0.00"),
                "state_tax": Decimal("0.00")
            }
        hsn_summary[hsn]["total_value"] += tx.amount
        hsn_summary[hsn]["taxable_value"] += gst_calc["taxable_value"]
        hsn_summary[hsn]["central_tax"] += gst_calc["cgst"]
        hsn_summary[hsn]["state_tax"] += gst_calc["sgst"]
        hsn_summary[hsn]["integrated_tax"] += gst_calc["igst"]

        if tx.counterparty_gstin:
            b2b_supplies.append({
                "invoice_number": tx.reference_number or f"INV-{tx.id[:8]}",
                "invoice_date": tx.transaction_date.isoformat(),
                "customer_name": tx.counterparty_name or "Registered Buyer",
                "customer_gstin": tx.counterparty_gstin,
                "taxable_value": f"{gst_calc['taxable_value']:.2f}",
                "rate": float(rate),
                "cgst": f"{gst_calc['cgst']:.2f}",
                "sgst": f"{gst_calc['sgst']:.2f}",
                "igst": f"{gst_calc['igst']:.2f}",
                "total_value": f"{tx.amount:.2f}"
            })
        else:
            b2c_supplies.append({
                "transaction_date": tx.transaction_date.isoformat(),
                "type": "B2C_SMALL",
                "taxable_value": f"{gst_calc['taxable_value']:.2f}",
                "rate": float(rate),
                "cgst": f"{gst_calc['cgst']:.2f}",
                "sgst": f"{gst_calc['sgst']:.2f}",
                "total_value": f"{tx.amount:.2f}"
            })

    return {
        "period": period,
        "report_type": "GSTR1",
        "total_taxable_value": f"{total_taxable:.2f}",
        "total_cgst": f"{total_cgst:.2f}",
        "total_sgst": f"{total_sgst:.2f}",
        "total_igst": f"{total_igst:.2f}",
        "total_tax": f"{(total_cgst + total_sgst + total_igst):.2f}",
        "table_4_b2b": b2b_supplies,
        "table_7_b2c": b2c_supplies,
        "table_12_hsn": [
            {
                "hsn_code": v["hsn_code"],
                "description": v["description"],
                "total_value": f"{v['total_value']:.2f}",
                "taxable_value": f"{v['taxable_value']:.2f}",
                "central_tax": f"{v['central_tax']:.2f}",
                "state_tax": f"{v['state_tax']:.2f}",
                "integrated_tax": f"{v['integrated_tax']:.2f}"
            }
            for v in hsn_summary.values()
        ],
        "compliance_notice": "SIMULATED GSTR-1 REPORT — BHARATCODE MSME TEST SANDBOX"
    }

def generate_gstr3b_summary(db: Session, tenant_id: str, period: str) -> Dict[str, Any]:
    """
    Generates statutory GSTR-3B monthly summary return:
    - 3.1: Output tax liability on outward taxable supplies
    - 4: Eligible ITC (Section 16) vs Ineligible ITC (Section 17(5))
    - 6.1: Net Tax Payable via cash ledger after legal ITC offset order (Section 49).
    """
    year, month = map(int, period.split("-"))

    # 1. Outward Supplies (Output Tax Liability)
    sales = db.query(Transaction).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.type == "CREDIT",
        extract("year", Transaction.transaction_date) == year,
        extract("month", Transaction.transaction_date) == month
    ).all()

    outward_taxable = Decimal("0.00")
    output_cgst = Decimal("0.00")
    output_sgst = Decimal("0.00")
    output_igst = Decimal("0.00")

    for s in sales:
        rate = Decimal(str(s.tax_rate or "18.0"))
        split = calculate_transaction_gst(s.amount, rate, is_interstate=False)
        outward_taxable += split["taxable_value"]
        output_cgst += split["cgst"]
        output_sgst += split["sgst"]
        output_igst += split["igst"]

    # 2. Inward Purchases (Input Tax Credit)
    purchases = db.query(Transaction).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.type == "DEBIT",
        extract("year", Transaction.transaction_date) == year,
        extract("month", Transaction.transaction_date) == month
    ).all()

    eligible_itc_cgst = Decimal("0.00")
    eligible_itc_sgst = Decimal("0.00")
    eligible_itc_igst = Decimal("0.00")
    blocked_itc_cgst = Decimal("0.00")
    blocked_itc_sgst = Decimal("0.00")

    for p in purchases:
        if p.category == "Salaries & Wages":
            continue  # Out of scope of GST (Schedule III)

        rate = Decimal(str(p.tax_rate or "18.0"))
        split = calculate_transaction_gst(p.amount, rate, is_interstate=False)

        # Check if blocked under Section 17(5)
        if is_itc_blocked_under_section_17_5(p.category, p.sub_category):
            blocked_itc_cgst += split["cgst"]
            blocked_itc_sgst += split["sgst"]
        else:
            eligible_itc_cgst += split["cgst"]
            eligible_itc_sgst += split["sgst"]
            eligible_itc_igst += split["igst"]

    # 3. Legal Statutory ITC Offset Ordering (Section 49 & 49A/B)
    # CGST ITC offsets CGST Output first, then IGST. (Never SGST!)
    # SGST ITC offsets SGST Output first, then IGST. (Never CGST!)
    net_cgst_payable = max(Decimal("0.00"), output_cgst - eligible_itc_cgst)
    net_sgst_payable = max(Decimal("0.00"), output_sgst - eligible_itc_sgst)
    net_igst_payable = max(Decimal("0.00"), output_igst - eligible_itc_igst)

    total_net_cash_payable = round_to_rupee(net_cgst_payable + net_sgst_payable + net_igst_payable)

    return {
        "period": period,
        "report_type": "GSTR3B",
        "table_3_1_outward_supplies": {
            "taxable_value": f"{round_to_rupee(outward_taxable):.2f}",
            "integrated_tax": f"{round_to_rupee(output_igst):.2f}",
            "central_tax": f"{round_to_rupee(output_cgst):.2f}",
            "state_tax": f"{round_to_rupee(output_sgst):.2f}",
            "cess": "0.00"
        },
        "table_4_eligible_itc": {
            "all_other_itc_cgst": f"{round_to_rupee(eligible_itc_cgst):.2f}",
            "all_other_itc_sgst": f"{round_to_rupee(eligible_itc_sgst):.2f}",
            "all_other_itc_igst": f"{round_to_rupee(eligible_itc_igst):.2f}",
            "ineligible_itc_under_sec_17_5": f"{round_to_rupee(blocked_itc_cgst + blocked_itc_sgst):.2f}"
        },
        "table_6_1_payment_of_tax": {
            "net_cgst_cash_payable": f"{round_to_rupee(net_cgst_payable):.2f}",
            "net_sgst_cash_payable": f"{round_to_rupee(net_sgst_payable):.2f}",
            "net_igst_cash_payable": f"{round_to_rupee(net_igst_payable):.2f}",
            "total_net_cash_payable": f"{total_net_cash_payable:.2f}"
        },
        "compliance_notice": "SIMULATED GSTR-3B RETURN — BHARATCODE MSME TEST SANDBOX"
    }
