import uuid
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_tenant
from backend.app.models.user import Tenant
from backend.app.models.transaction import Transaction
from backend.app.models.workflow import WorkflowRun
from backend.app.workflows.graph import transaction_graph
from backend.app.services.financial_engine import post_transaction_to_ledger

router = APIRouter()

class ProcessTransactionRequest(BaseModel):
    raw_narration: str
    amount: float
    direction: str = "DEBIT"  # DEBIT or CREDIT
    channel: str = "UPI"
    reference_number: Optional[str] = None
    is_interstate: bool = False

class ApproveTransactionRequest(BaseModel):
    transaction_id: str
    category: str
    sub_category: Optional[str] = None
    gst_rate: float = 18.0
    counterparty_name: Optional[str] = None
    counterparty_gstin: Optional[str] = None
    human_feedback: Optional[str] = None
    is_interstate: bool = False

@router.post("/process")
async def process_transaction_workflow(
    req: ProcessTransactionRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Executes the LangGraph multi-agent financial workflow for an incoming transaction.
    """
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    initial_state = {
        "tenant_id": tenant.id,
        "transaction_id": None,
        "raw_narration": req.raw_narration,
        "amount": req.amount,
        "direction": req.direction,
        "channel": req.channel,
        "reference_number": req.reference_number,
        "is_duplicate": False,
        "category": "",
        "sub_category": None,
        "hsn_sac_code": None,
        "gst_rate": 0.0,
        "counterparty_name": None,
        "counterparty_gstin": None,
        "confidence_score": 0.0,
        "needs_human_review": False,
        "human_approved": False,
        "human_feedback": None,
        "reconciled_receipt_id": None,
        "ledger_entries_created": 0,
        "is_interstate": req.is_interstate,
        "rationale": "",
        "error": None
    }

    config = {"configurable": {"thread_id": run_id, "db": db}}
    result = await transaction_graph.ainvoke(initial_state, config=config)

    # If flagged for human review, create transaction in NEEDS_APPROVAL state and log WorkflowRun
    if result.get("needs_human_review"):
        import datetime
        tx = Transaction(
            tenant_id=tenant.id,
            transaction_date=datetime.date.today(),
            description=req.raw_narration[:250],
            raw_narration=req.raw_narration,
            amount=Decimal(str(req.amount)),
            type=req.direction,
            channel=req.channel,
            reference_number=req.reference_number,
            category=result.get("category", "Uncategorized"),
            sub_category=result.get("sub_category"),
            tax_rate=Decimal(str(result.get("gst_rate", 0.0))),
            confidence_score=result.get("confidence_score", 0.5),
            status="NEEDS_APPROVAL",
            is_reconciled=False
        )
        db.add(tx)
        db.flush()

        wf_run = WorkflowRun(
            tenant_id=tenant.id,
            run_id=run_id,
            workflow_name="transaction_classification",
            status="INTERRUPTED",
            current_node="human_review",
            checkpoint_state=result,
            input_payload=req.model_dump()
        )
        db.add(wf_run)
        db.commit()

        return {
            "status": "NEEDS_APPROVAL",
            "run_id": run_id,
            "transaction_id": tx.id,
            "confidence_score": result.get("confidence_score"),
            "category": result.get("category"),
            "rationale": result.get("rationale"),
            "message": "Low confidence or ambiguous transaction flagged for human approval."
        }

    # If duplicate
    if result.get("is_duplicate"):
        return {
            "status": "DUPLICATE_REJECTED",
            "message": result.get("error")
        }

    # Successfully auto-approved and posted to ledger
    return {
        "status": "CONFIRMED",
        "run_id": run_id,
        "transaction_id": result.get("transaction_id"),
        "category": result.get("category"),
        "confidence_score": result.get("confidence_score"),
        "ledger_entries_created": result.get("ledger_entries_created"),
        "reconciled_receipt_id": result.get("reconciled_receipt_id"),
        "rationale": result.get("rationale")
    }

@router.get("/approval-queue")
def get_approval_queue(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Lists transactions needing human approval/correction."""
    pending = db.query(Transaction).filter(
        Transaction.tenant_id == tenant.id,
        Transaction.status == "NEEDS_APPROVAL"
    ).order_by(desc(Transaction.created_at)).all()

    return [
        {
            "id": tx.id,
            "transaction_date": tx.transaction_date.isoformat(),
            "raw_narration": tx.raw_narration,
            "amount": f"{tx.amount:.2f}",
            "type": tx.type,
            "channel": tx.channel,
            "category": tx.category,
            "confidence_score": tx.confidence_score,
            "status": tx.status
        }
        for tx in pending
    ]

@router.post("/approve")
def approve_transaction(
    req: ApproveTransactionRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Submits human confirmation or correction, updating the transaction and posting to ledger."""
    tx = db.query(Transaction).filter(
        Transaction.id == req.transaction_id,
        Transaction.tenant_id == tenant.id
    ).first()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    # Apply merchant feedback
    tx.category = req.category
    tx.sub_category = req.sub_category or tx.sub_category
    tx.tax_rate = Decimal(str(req.gst_rate))
    tx.counterparty_name = req.counterparty_name or tx.counterparty_name
    tx.counterparty_gstin = req.counterparty_gstin or tx.counterparty_gstin
    tx.confidence_score = 1.0  # Certified by human
    tx.status = "CONFIRMED"

    # Post to double-entry ledger
    entries = post_transaction_to_ledger(db, tx, is_interstate=req.is_interstate)

    return {
        "status": "APPROVED_AND_POSTED",
        "transaction_id": tx.id,
        "category": tx.category,
        "entries_created": len(entries),
        "total_balanced_amount": f"{sum(e.debit for e in entries):.2f}"
    }
