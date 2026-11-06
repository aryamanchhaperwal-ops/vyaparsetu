from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Tuple
import datetime
from sqlalchemy.orm import Session

from backend.app.models.transaction import Transaction
from backend.app.models.ledger import LedgerAccount, LedgerEntry

class LedgerImbalanceError(Exception):
    """Raised when debit and credit sums do not match exactly down to the paisa."""
    pass

def round_paisa(amount: Decimal) -> Decimal:
    """Rounds an amount to 2 decimal places (paisa) using ROUND_HALF_UP (Section 170 CGST Act)."""
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def compute_gst_split(
    total_amount: Decimal,
    rate_percent: Decimal,
    is_interstate: bool = False
) -> Dict[str, Decimal]:
    """
    Deterministically computes base taxable value and GST split.
    If inclusive: taxable_value = total_amount / (1 + rate/100)
    Intra-state: CGST = tax/2, SGST = tax/2
    Inter-state: IGST = tax
    """
    if rate_percent <= 0:
        return {
            "taxable_value": round_paisa(total_amount),
            "cgst": Decimal("0.00"),
            "sgst": Decimal("0.00"),
            "igst": Decimal("0.00"),
            "total_tax": Decimal("0.00")
        }

    tax_factor = Decimal("1.0") + (rate_percent / Decimal("100.0"))
    taxable_value = round_paisa(total_amount / tax_factor)
    total_tax = round_paisa(total_amount - taxable_value)

    if is_interstate:
        return {
            "taxable_value": taxable_value,
            "cgst": Decimal("0.00"),
            "sgst": Decimal("0.00"),
            "igst": total_tax,
            "total_tax": total_tax
        }
    else:
        cgst = round_paisa(total_tax / Decimal("2.0"))
        # Ensure CGST + SGST exactly equals total_tax down to 1 paisa rounding variance
        sgst = total_tax - cgst
        return {
            "taxable_value": taxable_value,
            "cgst": cgst,
            "sgst": sgst,
            "igst": Decimal("0.00"),
            "total_tax": total_tax
        }

def post_transaction_to_ledger(
    db: Session,
    transaction: Transaction,
    is_interstate: bool = False
) -> List[LedgerEntry]:
    """
    Creates double-entry journal vouchers for a business transaction.
    Guarantees strict mathematical balancing: sum(debits) == sum(credits).
    """
    tenant_id = transaction.tenant_id
    total_amt = round_paisa(transaction.amount)
    tax_rate = Decimal(str(transaction.tax_rate or "0.0"))
    tax_split = compute_gst_split(total_amt, tax_rate, is_interstate)

    # Fetch accounts map for tenant
    accounts = {
        acc.code: acc for acc in db.query(LedgerAccount).filter(LedgerAccount.tenant_id == tenant_id).all()
    }
    
    # Identify payment medium account (Cash vs Bank)
    payment_code = "1010" if transaction.channel == "CASH" else "1020"
    payment_acc = accounts.get(payment_code)
    if not payment_acc:
        raise ValueError(f"Required account code {payment_code} not found for tenant")

    entries: List[LedgerEntry] = []

    if transaction.type == "DEBIT":
        # Outflow / Expense
        # 1. Debit Expense or Inventory Account (Base Taxable Value)
        expense_code = "5010" if transaction.category == "Raw Materials" else (
            "5020" if transaction.category == "Rent & Utilities" else (
                "5030" if transaction.category == "Salaries & Wages" else (
                    "5040" if transaction.category == "Logistics & Transport" else "5050"
                )
            )
        )
        expense_acc = accounts.get(expense_code, accounts["5050"])
        entries.append(LedgerEntry(
            tenant_id=tenant_id,
            transaction_id=transaction.id,
            account_id=expense_acc.id,
            entry_date=transaction.transaction_date,
            debit=tax_split["taxable_value"],
            credit=Decimal("0.00"),
            narration=f"Expense: {transaction.description}"
        ))

        # 2. Debit Input Tax Credit Receivable (if applicable and eligible)
        if tax_split["total_tax"] > 0 and transaction.category != "Salaries & Wages":
            if is_interstate:
                igst_acc = accounts["1060"]
                entries.append(LedgerEntry(
                    tenant_id=tenant_id,
                    transaction_id=transaction.id,
                    account_id=igst_acc.id,
                    entry_date=transaction.transaction_date,
                    debit=tax_split["igst"],
                    credit=Decimal("0.00"),
                    narration="Input Tax Credit - IGST"
                ))
            else:
                cgst_acc = accounts["1040"]
                sgst_acc = accounts["1050"]
                entries.append(LedgerEntry(
                    tenant_id=tenant_id,
                    transaction_id=transaction.id,
                    account_id=cgst_acc.id,
                    entry_date=transaction.transaction_date,
                    debit=tax_split["cgst"],
                    credit=Decimal("0.00"),
                    narration="Input Tax Credit - CGST"
                ))
                entries.append(LedgerEntry(
                    tenant_id=tenant_id,
                    transaction_id=transaction.id,
                    account_id=sgst_acc.id,
                    entry_date=transaction.transaction_date,
                    debit=tax_split["sgst"],
                    credit=Decimal("0.00"),
                    narration="Input Tax Credit - SGST"
                ))

        # 3. Credit Cash or Bank Account (Total Amount Outflow)
        entries.append(LedgerEntry(
            tenant_id=tenant_id,
            transaction_id=transaction.id,
            account_id=payment_acc.id,
            entry_date=transaction.transaction_date,
            debit=Decimal("0.00"),
            credit=total_amt,
            narration=f"Payment via {transaction.channel}: {transaction.description}"
        ))

    else:
        # Inflow / Sales Revenue
        # 1. Debit Cash or Bank Account (Total Amount Inflow)
        entries.append(LedgerEntry(
            tenant_id=tenant_id,
            transaction_id=transaction.id,
            account_id=payment_acc.id,
            entry_date=transaction.transaction_date,
            debit=total_amt,
            credit=Decimal("0.00"),
            narration=f"Receipt via {transaction.channel}: {transaction.description}"
        ))

        # 2. Credit Sales Revenue Account (Base Taxable Value)
        revenue_acc = accounts["4010"]
        entries.append(LedgerEntry(
            tenant_id=tenant_id,
            transaction_id=transaction.id,
            account_id=revenue_acc.id,
            entry_date=transaction.transaction_date,
            debit=Decimal("0.00"),
            credit=tax_split["taxable_value"],
            narration=f"Sales Revenue: {transaction.description}"
        ))

        # 3. Credit Output GST Payable (if applicable)
        if tax_split["total_tax"] > 0:
            if is_interstate:
                igst_payable = accounts["2040"]
                entries.append(LedgerEntry(
                    tenant_id=tenant_id,
                    transaction_id=transaction.id,
                    account_id=igst_payable.id,
                    entry_date=transaction.transaction_date,
                    debit=Decimal("0.00"),
                    credit=tax_split["igst"],
                    narration="Output GST Liability - IGST"
                ))
            else:
                cgst_payable = accounts["2020"]
                sgst_payable = accounts["2030"]
                entries.append(LedgerEntry(
                    tenant_id=tenant_id,
                    transaction_id=transaction.id,
                    account_id=cgst_payable.id,
                    entry_date=transaction.transaction_date,
                    debit=Decimal("0.00"),
                    credit=tax_split["cgst"],
                    narration="Output GST Liability - CGST"
                ))
                entries.append(LedgerEntry(
                    tenant_id=tenant_id,
                    transaction_id=transaction.id,
                    account_id=sgst_payable.id,
                    entry_date=transaction.transaction_date,
                    debit=Decimal("0.00"),
                    credit=tax_split["sgst"],
                    narration="Output GST Liability - SGST"
                ))

    # --- Verification of Mathematical Balancing (Invariant Dr == Cr) ---
    sum_debits = sum(e.debit for e in entries)
    sum_credits = sum(e.credit for e in entries)
    if sum_debits != sum_credits:
        raise LedgerImbalanceError(
            f"Double-entry balancing violated! Debits ({sum_debits}) != Credits ({sum_credits}). Discrepancy: {sum_debits - sum_credits}"
        )

    # Persist entries and update balances
    for entry in entries:
        db.add(entry)
        # Update account running balance
        acc = accounts.get(next(k for k, v in accounts.items() if v.id == entry.account_id))
        if acc:
            if acc.account_type in ("ASSET", "EXPENSE"):
                acc.balance += (entry.debit - entry.credit)
            else:
                acc.balance += (entry.credit - entry.debit)

    transaction.is_reconciled = True
    db.commit()
    return entries

def generate_trial_balance(db: Session, tenant_id: str) -> Dict[str, Any]:
    """Generates the Trial Balance report verifying total debits == total credits across the business."""
    accounts = db.query(LedgerAccount).filter(LedgerAccount.tenant_id == tenant_id).order_by(LedgerAccount.code).all()
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    rows = []
    for acc in accounts:
        # Compute net debit and credit from ledger entries
        entries = db.query(LedgerEntry).filter(
            LedgerEntry.tenant_id == tenant_id,
            LedgerEntry.account_id == acc.id
        ).all()
        dr = sum((e.debit for e in entries), Decimal("0.00"))
        cr = sum((e.credit for e in entries), Decimal("0.00"))

        if dr > cr:
            net_dr = dr - cr
            net_cr = Decimal("0.00")
        else:
            net_dr = Decimal("0.00")
            net_cr = cr - dr

        total_debit += net_dr
        total_credit += net_cr

        rows.append({
            "account_code": acc.code,
            "account_name": acc.name,
            "account_type": acc.account_type,
            "debit": f"{net_dr:.2f}",
            "credit": f"{net_cr:.2f}"
        })

    is_balanced = (total_debit == total_credit)
    return {
        "tenant_id": tenant_id,
        "is_balanced": is_balanced,
        "total_debit": f"{total_debit:.2f}",
        "total_credit": f"{total_credit:.2f}",
        "accounts": rows
    }
