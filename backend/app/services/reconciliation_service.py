import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt

def reconcile_tenant_records(
    db: Session,
    tenant_id: str,
    auto_link_threshold: float = 0.90
) -> Dict[str, Any]:
    """
    Automated Invoice-Payment Matching and Bank Reconciliation Engine.
    Correlates unlinked bank/UPI transactions against unlinked OCR receipts & vendor invoices.
    
    Matching Strategy:
    1. Exact invoice number or reference matching in narration -> Score: 0.99
    2. Exact amount matching (+/- 1.00 rounding variance) within 14-day window -> Score: 0.92
    3. Vendor name token overlap + amount matching -> Score: 0.95
    """
    unlinked_txs = db.query(Transaction).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.is_reconciled == False
    ).order_by(desc(Transaction.transaction_date)).all()

    unlinked_receipts = db.query(Receipt).filter(
        Receipt.tenant_id == tenant_id,
        Receipt.transaction_id == None
    ).order_by(desc(Receipt.invoice_date)).all()

    matched_pairs: List[Dict[str, Any]] = []
    auto_linked_count = 0
    suggested_count = 0

    used_receipt_ids = set()

    for tx in unlinked_txs:
        best_match = None
        best_score = 0.0
        best_reason = ""

        tx_amount = tx.amount
        tx_narr_lower = (tx.raw_narration or "").lower()
        tx_ref_lower = (tx.reference_number or "").lower()

        for rcpt in unlinked_receipts:
            if rcpt.id in used_receipt_ids:
                continue

            rcpt_amt = rcpt.total_amount or Decimal("0.00")
            amt_diff = abs(tx_amount - rcpt_amt)

            # Rule 1: Invoice number mentioned in transaction narration or ref
            inv_no = (rcpt.invoice_number or "").lower()
            if inv_no and len(inv_no) >= 3 and (inv_no in tx_narr_lower or inv_no in tx_ref_lower):
                best_match = rcpt
                best_score = 0.99
                best_reason = f"Exact invoice number match ({rcpt.invoice_number}) in bank narration."
                break

            # Rule 2: Amount matches within ₹1.00 tolerance
            if amt_diff <= Decimal("1.00"):
                score = 0.85
                reason = f"Amount match (₹{tx_amount:.2f} vs ₹{rcpt_amt:.2f})"

                # Proximity bonus (within 7 days)
                if rcpt.invoice_date and tx.transaction_date:
                    days_apart = abs((tx.transaction_date - rcpt.invoice_date).days)
                    if days_apart <= 7:
                        score += 0.08
                        reason += f" within {days_apart} days."
                    elif days_apart <= 30:
                        score += 0.03
                        reason += f" within {days_apart} days."

                # Vendor name keyword bonus
                if rcpt.vendor_name:
                    vendor_words = [w for w in rcpt.vendor_name.lower().split() if len(w) > 3]
                    if any(w in tx_narr_lower for w in vendor_words):
                        score += 0.06
                        reason += f" and vendor name token matched ({rcpt.vendor_name})."

                if score > best_score:
                    best_score = min(1.0, score)
                    best_match = rcpt
                    best_reason = reason

        if best_match and best_score >= 0.70:
            is_auto_linked = best_score >= auto_link_threshold
            if is_auto_linked:
                # Execute automated reconciliation link
                best_match.transaction_id = tx.id
                best_match.status = "RECONCILED"
                tx.is_reconciled = True
                if best_match.vendor_gstin and not tx.counterparty_gstin:
                    tx.counterparty_gstin = best_match.vendor_gstin
                if best_match.vendor_name and not tx.counterparty_name:
                    tx.counterparty_name = best_match.vendor_name
                used_receipt_ids.add(best_match.id)
                auto_linked_count += 1
            else:
                suggested_count += 1

            matched_pairs.append({
                "transaction_id": tx.id,
                "transaction_date": tx.transaction_date.isoformat(),
                "narration": tx.description,
                "amount": f"{tx.amount:.2f}",
                "receipt_id": best_match.id,
                "invoice_number": best_match.invoice_number,
                "vendor_name": best_match.vendor_name,
                "receipt_amount": f"{best_match.total_amount:.2f}" if best_match.total_amount else "0.00",
                "match_score": round(best_score, 2),
                "reason": best_reason,
                "status": "RECONCILED" if is_auto_linked else "SUGGESTED_MATCH"
            })

    if auto_linked_count > 0:
        db.commit()

    # Calculate overall tenant reconciliation health
    total_tx = db.query(Transaction).filter(Transaction.tenant_id == tenant_id).count()
    reconciled_tx = db.query(Transaction).filter(Transaction.tenant_id == tenant_id, Transaction.is_reconciled == True).count()
    reconciliation_rate = round((reconciled_tx / total_tx * 100), 1) if total_tx > 0 else 100.0

    return {
        "tenant_id": tenant_id,
        "total_transactions": total_tx,
        "reconciled_transactions": reconciled_tx,
        "unlinked_transactions": total_tx - reconciled_tx,
        "unlinked_receipts": len(unlinked_receipts) - auto_linked_count,
        "auto_linked_count": auto_linked_count,
        "suggested_count": suggested_count,
        "reconciliation_rate_percent": reconciliation_rate,
        "matches": matched_pairs
    }

