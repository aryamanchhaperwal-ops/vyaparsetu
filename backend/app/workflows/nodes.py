import logging
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from langchain_core.runnables import RunnableConfig

from backend.app.core.database import SessionLocal
from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt
from backend.app.llm.client import bharatcode_client, BharatCodeAPIError
from backend.app.services.financial_engine import post_transaction_to_ledger
from backend.app.services.anomaly_service import detect_transaction_anomalies
from backend.app.workflows.state import TransactionWorkflowState

logger = logging.getLogger("workflow_nodes")

def get_workflow_db(config: Optional[RunnableConfig] = None) -> Tuple[Session, bool]:
    """Retrieves the DB session from LangGraph config or falls back to SessionLocal."""
    if config and isinstance(config, dict):
        configurable = config.get("configurable", {})
        if "db" in configurable and configurable["db"] is not None:
            return configurable["db"], False
    return SessionLocal(), True

async def deduplication_node(state: TransactionWorkflowState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Deterministic Node: Checks for duplicate transactions and flags financial anomalies."""
    ref_no = state.get("reference_number")
    tenant_id = state["tenant_id"]
    amount = Decimal(str(state.get("amount", 0.0)))
    direction = state.get("direction", "DEBIT")
    channel = state.get("channel", "UPI")

    import datetime
    tx_date = datetime.date.today()

    db, should_close = get_workflow_db(config)
    try:
        anomaly_res = detect_transaction_anomalies(
            db=db,
            tenant_id=tenant_id,
            amount=amount,
            direction=direction,
            channel=channel,
            tx_date=tx_date,
            reference_number=ref_no,
            narration=state.get("raw_narration", "")
        )

        if anomaly_res.get("is_duplicate"):
            return {
                "is_duplicate": True,
                "is_anomaly": True,
                "anomaly_score": 1.0,
                "anomaly_reasons": anomaly_res.get("anomalies", []),
                "error": f"Duplicate transaction detected: Reference {ref_no} already exists."
            }

        return {
            "is_duplicate": False,
            "is_anomaly": anomaly_res.get("is_anomaly", False),
            "anomaly_score": anomaly_res.get("anomaly_score", 0.0),
            "anomaly_reasons": anomaly_res.get("anomalies", [])
        }
    finally:
        if should_close:
            db.close()

async def classification_node(state: TransactionWorkflowState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """AI Agent Node: Invokes BharatCode to classify Indian mercantile transaction."""
    if state.get("is_duplicate"):
        return {}

    narration = state["raw_narration"]
    amount = state["amount"]
    direction = state["direction"]
    req_ai_mode = state.get("ai_mode")

    try:
        res = await bharatcode_client.classify_transaction(
            narration=narration,
            amount=amount,
            direction=direction,
            ai_mode=req_ai_mode
        )

        return {
            "category": res.get("category", "Uncategorized"),
            "sub_category": res.get("sub_category"),
            "counterparty_name": res.get("counterparty_name"),
            "hsn_sac_code": res.get("suggested_hsn_sac"),
            "gst_rate": float(res.get("gst_rate", 0.0)),
            "confidence_score": float(res.get("confidence_score", 0.5)),
            "rationale": res.get("rationale", ""),
            "ai_source": res.get("source", "DEV_SIMULATION"),
            "ai_mode": res.get("ai_mode", "DEV_SIMULATION"),
            "live_api": res.get("live_api", False),
            "accounting_suggestions": res.get("accounting_suggestions", []),
            "gst_advisory": res.get("gst_advisory"),
            "hsn_advisory": res.get("hsn_advisory")
        }
    except BharatCodeAPIError as e:
        logger.error(f"Live BharatCode API classification failure: {e.message}")
        return {
            "category": "Uncategorized",
            "sub_category": None,
            "counterparty_name": None,
            "hsn_sac_code": None,
            "gst_rate": 0.0,
            "confidence_score": 0.0,
            "rationale": f"Live BharatCode inference unavailable: {e.message}",
            "ai_source": "FAILED",
            "ai_mode": getattr(bharatcode_client, "ai_mode", "PRODUCTION_LIVE"),
            "live_api": False,
            "accounting_suggestions": ["AI service unavailable. Manual classification and approval required."],
            "error": f"Live BharatCode error ({e.status_code}): {e.message}",
            "needs_human_review": True
        }

def confidence_router(state: TransactionWorkflowState) -> str:
    """Conditional Edge Router: Decides whether to auto-approve or route to human review queue."""
    if state.get("is_duplicate"):
        return "end_duplicate"
    
    # If live AI failed or error occurred, ALWAYS route to human review for financial safety
    if state.get("error") or state.get("ai_source") == "FAILED":
        return "human_review"

    # If high anomaly score, route to human review for financial safety
    if state.get("is_anomaly") and state.get("anomaly_score", 0.0) >= 0.40:
        return "human_review"

    # If confidence < 0.85 or category is Uncategorized -> Route to Human Review
    if state.get("confidence_score", 0.0) < 0.85 or state.get("category") == "Uncategorized":
        return "human_review"
    
    return "reconcile_receipt"

async def human_review_node(state: TransactionWorkflowState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Human-in-the-Loop Checkpoint Node: Flags state for merchant or accountant approval."""
    return {
        "needs_human_review": True,
        "human_approved": False
    }

async def reconciliation_node(state: TransactionWorkflowState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Deterministic Node: Matches transaction against unlinked receipts/invoices."""
    tenant_id = state["tenant_id"]
    tx_amt = Decimal(str(state["amount"]))

    db, should_close = get_workflow_db(config)
    try:
        # Look for an unlinked receipt with matching total amount (+/- 1.00 variance)
        unlinked_receipt = db.query(Receipt).filter(
            Receipt.tenant_id == tenant_id,
            Receipt.transaction_id == None,
            Receipt.total_amount >= (tx_amt - Decimal("1.00")),
            Receipt.total_amount <= (tx_amt + Decimal("1.00"))
        ).first()

        if unlinked_receipt:
            return {
                "reconciled_receipt_id": unlinked_receipt.id,
                "counterparty_gstin": unlinked_receipt.vendor_gstin
            }
        return {"reconciled_receipt_id": None}
    finally:
        if should_close:
            db.close()

async def ledger_posting_node(state: TransactionWorkflowState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Deterministic Math Node: Generates balanced double-entry vouchers."""
    tenant_id = state["tenant_id"]
    db, should_close = get_workflow_db(config)
    try:
        # Create or update transaction record
        tx_id = state.get("transaction_id")
        if tx_id:
            tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
        else:
            tx = None

        import datetime
        if not tx:
            tx = Transaction(
                tenant_id=tenant_id,
                transaction_date=datetime.date.today(),
                description=state["raw_narration"][:250],
                raw_narration=state["raw_narration"],
                amount=Decimal(str(state["amount"])),
                type=state["direction"],
                channel=state.get("channel", "UPI"),
                reference_number=state.get("reference_number"),
                category=state["category"],
                sub_category=state.get("sub_category"),
                hsn_sac_code=state.get("hsn_sac_code"),
                counterparty_name=state.get("counterparty_name"),
                counterparty_gstin=state.get("counterparty_gstin"),
                tax_rate=Decimal(str(state.get("gst_rate", 0.0))),
                confidence_score=state.get("confidence_score", 1.0),
                status="CONFIRMED"
            )
            db.add(tx)
            db.flush()

        # Link receipt if reconciled
        receipt_id = state.get("reconciled_receipt_id")
        if receipt_id:
            rcpt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
            if rcpt:
                rcpt.transaction_id = tx.id
                rcpt.status = "RECONCILED"

        # Post to double entry ledger
        is_interstate = state.get("is_interstate", False)
        entries = post_transaction_to_ledger(db, tx, is_interstate=is_interstate)

        return {
            "transaction_id": tx.id,
            "ledger_entries_created": len(entries),
            "needs_human_review": False,
            "human_approved": True
        }
    except Exception as e:
        logger.error(f"Ledger posting error: {e}")
        return {"error": str(e), "ledger_entries_created": 0}
    finally:
        if should_close:
            db.close()
