import logging
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from langchain_core.runnables import RunnableConfig

from backend.app.core.database import SessionLocal
from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt
from backend.app.llm.client import bharatcode_client
from backend.app.services.financial_engine import post_transaction_to_ledger
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
    """Deterministic Node: Checks if reference number or identical transaction already exists."""
    ref_no = state.get("reference_number")
    tenant_id = state["tenant_id"]

    if not ref_no:
        return {"is_duplicate": False}

    db, should_close = get_workflow_db(config)
    try:
        existing = db.query(Transaction).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.reference_number == ref_no
        ).first()
        if existing and existing.id != state.get("transaction_id"):
            return {
                "is_duplicate": True,
                "error": f"Duplicate transaction detected: Reference {ref_no} already posted on {existing.transaction_date}"
            }
        return {"is_duplicate": False}
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

    res = await bharatcode_client.classify_transaction(
        narration=narration,
        amount=amount,
        direction=direction
    )

    return {
        "category": res.get("category", "Uncategorized"),
        "sub_category": res.get("sub_category"),
        "counterparty_name": res.get("counterparty_name"),
        "hsn_sac_code": res.get("suggested_hsn_sac"),
        "gst_rate": float(res.get("gst_rate", 0.0)),
        "confidence_score": float(res.get("confidence_score", 0.5)),
        "rationale": res.get("rationale", "")
    }

def confidence_router(state: TransactionWorkflowState) -> str:
    """Conditional Edge Router: Decides whether to auto-approve or route to human review queue."""
    if state.get("is_duplicate"):
        return "end_duplicate"
    
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
