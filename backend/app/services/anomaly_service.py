import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.transaction import Transaction

def detect_transaction_anomalies(
    db: Session,
    tenant_id: str,
    amount: Decimal,
    direction: str,
    channel: str,
    tx_date: datetime.date,
    reference_number: Optional[str] = None,
    narration: str = ""
) -> Dict[str, Any]:
    """
    Evaluates transaction against historical tenant patterns to detect:
    1. Reference number duplicates.
    2. Same-day duplicate debit risks (double swipe / double transfer).
    3. High-value cash outflow violations (Section 40A(3) Income Tax Act: cash > ₹10,000).
    4. Outlier amount spikes (> 3x historical mean).
    """
    anomalies: List[str] = []
    anomaly_score = 0.0

    # 1. Exact Reference Duplicate
    if reference_number:
        ref_exists = db.query(Transaction).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.reference_number == reference_number
        ).first()
        if ref_exists:
            return {
                "is_duplicate": True,
                "is_anomaly": True,
                "anomaly_score": 1.0,
                "anomalies": [f"Exact UTR / Reference duplicate: {reference_number} already recorded on {ref_exists.transaction_date}"],
                "action": "BLOCK_DUPLICATE"
            }

    # 2. Same-day same-amount debit risk
    if direction == "DEBIT":
        window_start = tx_date - datetime.timedelta(days=1)
        window_end = tx_date + datetime.timedelta(days=1)
        potential_double_pay = db.query(Transaction).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.type == "DEBIT",
            Transaction.amount == amount,
            Transaction.transaction_date >= window_start,
            Transaction.transaction_date <= window_end
        ).first()
        if potential_double_pay:
            anomalies.append(f"Potential double-payment risk: Identical debit of ₹{amount:.2f} detected on {potential_double_pay.transaction_date}")
            anomaly_score += 0.45

    # 3. Section 40A(3) Indian Income Tax Cash Payment Threshold (Cash > ₹10,000)
    if channel.upper() == "CASH" and direction == "DEBIT" and amount > Decimal("10000.00"):
        anomalies.append("Section 40A(3) statutory alert: Cash business payment exceeds ₹10,000 threshold (disallowance risk).")
        anomaly_score += 0.50

    # 4. Outlier Amount Spike (> 3x Average Inflow/Outflow)
    avg_stat = db.query(
        func.avg(Transaction.amount),
        func.count(Transaction.id)
    ).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.type == direction
    ).first()

    if avg_stat and avg_stat[1] and avg_stat[1] >= 5 and avg_stat[0]:
        avg_amt = Decimal(str(avg_stat[0]))
        if amount > (avg_amt * Decimal("3.0")) and amount > Decimal("50000.00"):
            anomalies.append(f"High-value volume spike: ₹{amount:.2f} is >3x average {direction.lower()} size (₹{avg_amt:.2f}).")
            anomaly_score += 0.30

    is_anomaly = len(anomalies) > 0
    anomaly_score = min(1.0, anomaly_score)

    action = "HUMAN_REVIEW" if anomaly_score >= 0.40 else "AUTO_APPROVE"

    return {
        "is_duplicate": False,
        "is_anomaly": is_anomaly,
        "anomaly_score": round(anomaly_score, 2),
        "anomalies": anomalies,
        "action": action
    }
