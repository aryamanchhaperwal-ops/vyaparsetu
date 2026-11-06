import io
import csv
import datetime
from decimal import Decimal
from typing import List, Dict, Any, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from backend.app.models.transaction import Transaction

def parse_indian_date(date_str: str) -> datetime.date:
    """Parses various Indian date formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD)."""
    clean_str = date_str.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.datetime.strptime(clean_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date: {date_str}")

def parse_currency(amount_str: Any) -> Decimal:
    """Parses Indian currency strings like '1,25,000.50' or '₹ 15,000' to Decimal."""
    if not amount_str or pd.isna(amount_str):
        return Decimal("0.00")
    s = str(amount_str).replace("₹", "").replace(",", "").replace(" ", "").strip()
    if not s or s == "-":
        return Decimal("0.00")
    return Decimal(s)

def parse_bank_statement_csv(csv_content: str) -> List[Dict[str, Any]]:
    """
    Parses arbitrary Indian bank statement CSVs (HDFC, SBI, ICICI, Axis, Kotak).
    Normalizes columns to: date, narration, reference_number, type, amount, channel.
    """
    df = pd.read_csv(io.StringIO(csv_content))
    df.columns = [c.strip().lower() for c in df.columns]

    # Map column names
    date_col = next((c for c in df.columns if any(k in c for k in ["date", "txn dt", "txndate"])), None)
    narration_col = next((c for c in df.columns if any(k in c for k in ["narration", "description", "particulars", "remarks"])), None)
    ref_col = next((c for c in df.columns if any(k in c for k in ["chq", "ref", "utr", "cheque", "reference"])), None)
    withdrawal_col = next((c for c in df.columns if any(k in c for k in ["withdrawal", "debit", "dr", "paid out"])), None)
    deposit_col = next((c for c in df.columns if any(k in c for k in ["deposit", "credit", "cr", "paid in"])), None)

    if not date_col or not narration_col:
        raise ValueError("CSV missing required columns (Date and Narration/Particulars)")

    parsed_records = []
    for _, row in df.iterrows():
        try:
            tx_date = parse_indian_date(str(row[date_col]))
            narration = str(row[narration_col]).strip()
            ref_no = str(row[ref_col]).strip() if ref_col and pd.notna(row[ref_col]) else None

            # Determine amount and direction
            debit_amt = parse_currency(row[withdrawal_col]) if withdrawal_col and pd.notna(row[withdrawal_col]) else Decimal("0.00")
            credit_amt = parse_currency(row[deposit_col]) if deposit_col and pd.notna(row[deposit_col]) else Decimal("0.00")

            if debit_amt > 0:
                tx_type = "DEBIT"
                amount = debit_amt
            elif credit_amt > 0:
                tx_type = "CREDIT"
                amount = credit_amt
            else:
                continue  # Skip zero-balance or empty rows

            # Detect channel
            channel = "BANK"
            narr_lower = narration.lower()
            if "upi" in narr_lower:
                channel = "UPI"
            elif "neft" in narr_lower:
                channel = "NEFT"
            elif "rtgs" in narr_lower:
                channel = "RTGS"
            elif "imps" in narr_lower:
                channel = "IMPS"
            elif "cash" in narr_lower:
                channel = "CASH"
            elif "chq" in narr_lower or "cheque" in narr_lower:
                channel = "CHEQUE"

            parsed_records.append({
                "transaction_date": tx_date,
                "description": narration[:250],
                "raw_narration": narration,
                "amount": amount,
                "type": tx_type,
                "channel": channel,
                "reference_number": ref_no,
            })
        except Exception:
            continue

    return parsed_records

def ingest_transactions_to_tenant(
    db: Session,
    tenant_id: str,
    records: List[Dict[str, Any]]
) -> Tuple[int, int]:
    """
    Inserts normalized transactions into the tenant's transaction ledger.
    Skips exact duplicate reference numbers for the tenant.
    Returns (num_inserted, num_duplicates_skipped).
    """
    inserted = 0
    duplicates = 0

    for r in records:
        ref_no = r.get("reference_number")
        if ref_no:
            existing = db.query(Transaction).filter(
                Transaction.tenant_id == tenant_id,
                Transaction.reference_number == ref_no
            ).first()
            if existing:
                duplicates += 1
                continue

        tx = Transaction(
            tenant_id=tenant_id,
            transaction_date=r["transaction_date"],
            description=r["description"],
            raw_narration=r["raw_narration"],
            amount=r["amount"],
            type=r["type"],
            channel=r["channel"],
            reference_number=ref_no,
            category="Uncategorized",
            confidence_score=0.5,
            status="CONFIRMED"
        )
        db.add(tx)
        inserted += 1

    db.commit()
    return inserted, duplicates

