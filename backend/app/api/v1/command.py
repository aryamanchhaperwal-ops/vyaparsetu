import uuid
import datetime
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_membership
from backend.app.models.user import Membership
from backend.app.models.workflow import WorkflowRun
from backend.app.models.usage import AuditLog
from backend.app.models.transaction import Transaction
from backend.app.services.financial_engine import post_transaction_to_ledger
from backend.app.services.ingestion import parse_indian_date
from backend.app.workflows.supervisor import (
    supervisor_graph,
    SupervisorWorkflowState,
    execution_agent_node
)

logger = logging.getLogger("command_centre_api")
router = APIRouter()

# Multi-turn conversational memory store isolated per tenant: {tenant_id: {conversation_id: [messages]}}
CONVERSATION_STORE: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}


def make_json_safe(obj: Any) -> Any:
    """Recursively converts Decimals, dates, and bytes into JSON-serializable formats."""
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items() if not str(k).startswith("_")}
    elif isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    elif isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, bytes):
        return f"<binary data: {len(obj)} bytes>"
    return obj


class ExecuteCommandRequest(BaseModel):
    instruction: str
    language: Optional[str] = "en"
    financial_period: Optional[str] = None
    idempotency_key: Optional[str] = None
    conversation_id: Optional[str] = None


class ApproveCommandRequest(BaseModel):
    run_id: str
    approved: bool = True
    modifications: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None


async def run_supervisor_pipeline(
    tenant_id: str,
    user_id: Optional[str],
    instruction: str,
    language: str,
    financial_period: Optional[str],
    idempotency_key: Optional[str],
    attached_files: List[Dict[str, Any]],
    db: Session,
    conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Core executor for Autonomous Command Centre workflows."""
    run_id = f"cmd_{uuid.uuid4().hex[:12]}"
    idemp_key = idempotency_key or run_id
    conv_id = conversation_id or f"conv_{tenant_id}"

    # Retrieve multi-turn conversation history for this tenant session
    if tenant_id not in CONVERSATION_STORE:
        CONVERSATION_STORE[tenant_id] = {}
    history = list(CONVERSATION_STORE[tenant_id].get(conv_id, []))

    initial_state: SupervisorWorkflowState = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "run_id": run_id,
        "idempotency_key": idemp_key,
        "conversation_id": conv_id,
        "conversation_history": history,
        "instruction": instruction,
        "language": language or "en",
        "financial_period": financial_period,
        "attached_files": attached_files,
        "intent": "",
        "entities": {},
        "selected_tools": [],
        "dynamic_tool_results": None,
        "execution_plan": [],
        "task_dependencies": {},
        "completed_tasks": [],
        "pending_tasks": [],
        "current_task": None,
        "retry_counts": {},
        "max_retries": 2,
        "errors": [],
        "agent_results": {},
        "missing_information": [],
        "clarification_question": None,
        "extracted_documents": [],
        "proposed_transactions": [],
        "reconciliation_results": None,
        "audit_anomalies": None,
        "gst_summary": None,
        "financial_reports": None,
        "requires_approval": False,
        "approval_summary": None,
        "consolidated_report": None,
        "retrieval_strategy": None,
        "retrieved_evidence": None,
        "retrieval_citations": [],
        "retrieval_confidence": 0.0,
        "is_approved": False,
        "execution_results": None,
        "spoken_response": "",
        "status": "RUNNING",
        "error": None
    }

    # Record initial WorkflowRun in database
    workflow_run = WorkflowRun(
        tenant_id=tenant_id,
        run_id=run_id,
        workflow_name="autonomous_command_centre",
        status="RUNNING",
        current_node="planner",
        input_payload=make_json_safe({
            "instruction": instruction,
            "language": language,
            "financial_period": financial_period,
            "conversation_id": conv_id,
            "file_count": len(attached_files)
        })
    )
    db.add(workflow_run)
    db.commit()

    try:
        final_state = await supervisor_graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": run_id, "db": db}}
        )

        safe_state = make_json_safe(final_state)
        safe_state["conversation_id"] = conv_id

        # Update multi-turn conversation memory
        user_msg = {
            "role": "user",
            "content": instruction,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        assistant_resp_text = (
            safe_state.get("spoken_response") or
            (safe_state.get("execution_results") or {}).get("summary") or
            "Instruction executed successfully."
        )
        assistant_msg = {
            "role": "assistant",
            "content": assistant_resp_text,
            "run_id": run_id,
            "intent": safe_state.get("intent"),
            "metadata": {
                "intent_type": safe_state.get("intent"),
                "vendor_name": (safe_state.get("entities") or {}).get("vendor_name"),
                "period": safe_state.get("financial_period"),
                "selected_tools": safe_state.get("selected_tools")
            },
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        if conv_id not in CONVERSATION_STORE[tenant_id]:
            CONVERSATION_STORE[tenant_id][conv_id] = []
        CONVERSATION_STORE[tenant_id][conv_id].extend([user_msg, assistant_msg])

        # Update WorkflowRun status and payloads
        workflow_run.status = safe_state.get("status", "COMPLETED")
        workflow_run.current_node = safe_state.get("intent", "planner")
        workflow_run.checkpoint_state = safe_state.get("approval_summary")
        workflow_run.output_payload = {
            "conversation_id": conv_id,
            "intent": safe_state.get("intent"),
            "entities": safe_state.get("entities"),
            "selected_tools": safe_state.get("selected_tools"),
            "dynamic_tool_results": safe_state.get("dynamic_tool_results"),
            "execution_plan": safe_state.get("execution_plan"),
            "execution_results": safe_state.get("execution_results"),
            "proposed_transactions": safe_state.get("proposed_transactions"),
            "reconciliation_results": safe_state.get("reconciliation_results"),
            "audit_anomalies": safe_state.get("audit_anomalies"),
            "gst_summary": safe_state.get("gst_summary"),
            "financial_reports": safe_state.get("financial_reports"),
            "spoken_response": safe_state.get("spoken_response"),
            "missing_information": safe_state.get("missing_information"),
            "clarification_question": safe_state.get("clarification_question"),
            "consolidated_report": safe_state.get("consolidated_report"),
            "agent_results": safe_state.get("agent_results"),
            "errors": safe_state.get("errors"),
            "completed_tasks": safe_state.get("completed_tasks"),
            "retrieval_strategy": safe_state.get("retrieval_strategy"),
            "retrieved_evidence": safe_state.get("retrieved_evidence"),
            "retrieval_citations": safe_state.get("retrieval_citations"),
            "retrieval_confidence": safe_state.get("retrieval_confidence")
        }
        if safe_state.get("error"):
            workflow_run.error_message = safe_state["error"]

        db.commit()
        return safe_state

    except Exception as e:
        logger.error(f"Error executing supervisor pipeline for {run_id}: {e}")
        db.rollback()
        workflow_run.status = "FAILED"
        workflow_run.error_message = str(e)
        db.commit()
        return {
            "tenant_id": tenant_id,
            "run_id": run_id,
            "conversation_id": conv_id,
            "status": "FAILED",
            "error": str(e),
            "spoken_response": "An error occurred while processing your request.",
            "execution_plan": [
                {"step": 1, "title": "Execution Error", "agent": "Supervisor", "status": "FAILED", "details": str(e)}
            ]
        }


@router.post("/execute")
async def execute_text_command(
    req: ExecuteCommandRequest,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db)
):
    """
    Executes a text, voice-transcribed, or high-level command through the LangGraph Supervisor.
    """
    return await run_supervisor_pipeline(
        tenant_id=membership.tenant_id,
        user_id=membership.user_id,
        instruction=req.instruction,
        language=req.language or "en",
        financial_period=req.financial_period,
        idempotency_key=req.idempotency_key,
        attached_files=[],
        db=db,
        conversation_id=req.conversation_id
    )


@router.post("/execute-upload")
async def execute_upload_command(
    instruction: str = Form(""),
    language: str = Form("en"),
    financial_period: Optional[str] = Form(None),
    idempotency_key: Optional[str] = Form(None),
    conversation_id: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db)
):
    """
    Executes a command with multiple document attachments (bank statements, receipts, invoices).
    """
    attached_files = []
    for f in files:
        content = await f.read()
        attached_files.append({
            "filename": f.filename,
            "content_bytes": content
        })

    return await run_supervisor_pipeline(
        tenant_id=membership.tenant_id,
        user_id=membership.user_id,
        instruction=instruction,
        language=language,
        financial_period=financial_period,
        idempotency_key=idempotency_key,
        attached_files=attached_files,
        db=db,
        conversation_id=conversation_id
    )


@router.post("/approve")
async def approve_workflow_run(
    req: ApproveCommandRequest,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db)
):
    """
    Human-in-the-Loop Approval Checkpoint:
    Commits proposed ledger entries, applies reconciliation links, and logs an audit trail.
    Enforces idempotency and tenant isolation.
    """
    # 1. Tenant-isolated lookup
    run = db.query(WorkflowRun).filter(
        WorkflowRun.run_id == req.run_id,
        WorkflowRun.tenant_id == membership.tenant_id
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run '{req.run_id}' not found for current tenant."
        )

    # 2. Idempotency Check: If already COMPLETED, return current state without re-executing
    if run.status == "COMPLETED":
        return {
            "status": "COMPLETED",
            "run_id": req.run_id,
            "message": "Workflow run has already been approved and committed previously (idempotent).",
            "output_payload": run.output_payload
        }

    # 3. If user rejected / cancelled
    if not req.approved:
        run.status = "CANCELLED"
        run.human_feedback = "Rejected by user at approval checkpoint."
        db.commit()
        return {
            "status": "CANCELLED",
            "run_id": req.run_id,
            "message": "Workflow run cancelled by user."
        }

    # 4. Resume execution and commit proposed modifications
    output_payload = run.output_payload or {}
    proposed_txs = output_payload.get("proposed_transactions") or []

    # If modifications provided, override
    if req.modifications and "proposed_transactions" in req.modifications:
        proposed_txs = req.modifications["proposed_transactions"]

    # Construct execution state
    orig_lang = "en"
    if run.input_payload and isinstance(run.input_payload, dict):
        orig_lang = run.input_payload.get("language", "en")

    resume_state: SupervisorWorkflowState = {
        "tenant_id": membership.tenant_id,
        "user_id": membership.user_id,
        "run_id": req.run_id,
        "idempotency_key": req.idempotency_key or req.run_id,
        "instruction": run.input_payload.get("instruction", "") if run.input_payload else "",
        "language": orig_lang,
        "financial_period": run.input_payload.get("financial_period") if run.input_payload else None,
        "attached_files": [],
        "intent": run.current_node or "CLOSE_ACCOUNTS",
        "execution_plan": output_payload.get("execution_plan", []),
        "task_dependencies": {},
        "completed_tasks": output_payload.get("completed_tasks", []),
        "pending_tasks": [],
        "current_task": "execution_agent",
        "retry_counts": {},
        "max_retries": 2,
        "errors": output_payload.get("errors", []),
        "agent_results": output_payload.get("agent_results", {}),
        "consolidated_report": output_payload.get("consolidated_report"),
        "current_step_index": 0,
        "missing_information": [],
        "clarification_question": None,
        "extracted_documents": [],
        "proposed_transactions": proposed_txs,
        "reconciliation_results": output_payload.get("reconciliation_results"),
        "audit_anomalies": output_payload.get("audit_anomalies"),
        "gst_summary": output_payload.get("gst_summary"),
        "financial_reports": output_payload.get("financial_reports"),
        "requires_approval": True,
        "approval_summary": run.checkpoint_state,
        "retrieval_strategy": output_payload.get("retrieval_strategy"),
        "retrieved_evidence": output_payload.get("retrieved_evidence"),
        "retrieval_citations": output_payload.get("retrieval_citations", []),
        "retrieval_confidence": output_payload.get("retrieval_confidence", 0.0),
        "is_approved": True,
        "execution_results": None,
        "spoken_response": "",
        "status": "RUNNING",
        "error": None
    }

    # Execute approved operations
    res = await execution_agent_node(resume_state, config={"configurable": {"db": db}})
    safe_res = make_json_safe(res)

    return {
        "status": safe_res.get("status", "COMPLETED"),
        "run_id": req.run_id,
        "execution_results": safe_res.get("execution_results"),
        "spoken_response": safe_res.get("spoken_response"),
        "execution_plan": safe_res.get("execution_plan"),
        "consolidated_report": safe_res.get("consolidated_report") or output_payload.get("consolidated_report")
    }


@router.get("/runs")
def list_workflow_runs(
    limit: int = 20,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db)
):
    """Lists past autonomous workflow runs for the active tenant."""
    runs = db.query(WorkflowRun).filter(
        WorkflowRun.tenant_id == membership.tenant_id
    ).order_by(desc(WorkflowRun.created_at)).limit(limit).all()

    return [
        {
            "id": r.id,
            "run_id": r.run_id,
            "workflow_name": r.workflow_name,
            "status": r.status,
            "current_node": r.current_node,
            "input_payload": r.input_payload,
            "checkpoint_state": r.checkpoint_state,
            "output_payload": r.output_payload,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None
        }
        for r in runs
    ]


@router.get("/runs/{run_id}")
def get_workflow_run(
    run_id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db)
):
    """Retrieves live execution DAG and state of a specific workflow run."""
    run = db.query(WorkflowRun).filter(
        WorkflowRun.run_id == run_id,
        WorkflowRun.tenant_id == membership.tenant_id
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run '{run_id}' not found."
        )

    return {
        "id": run.id,
        "run_id": run.run_id,
        "workflow_name": run.workflow_name,
        "status": run.status,
        "current_node": run.current_node,
        "input_payload": run.input_payload,
        "checkpoint_state": run.checkpoint_state,
        "output_payload": run.output_payload,
        "error_message": run.error_message,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None
    }


class VoiceParseRequest(BaseModel):
    transcript: str
    language: Optional[str] = "en"
    financial_period: Optional[str] = None


class SpeakRequest(BaseModel):
    text: str
    language: Optional[str] = "en"


@router.post("/voice-parse")
def parse_voice_transcript(
    req: VoiceParseRequest,
    membership: Membership = Depends(get_current_membership)
):
    """
    Parses vernacular spoken transcription (Hindi, Hinglish, Indian English),
    extracting amounts, dates, counterparties, directions, channels, and missing fields.
    Provides structured tokens and an editable transcript before execution.
    """
    from backend.app.services.voice_service import parse_vernacular_voice_narration
    parsed = parse_vernacular_voice_narration(req.transcript)
    return {
        "tenant_id": membership.tenant_id,
        "input_transcript": req.transcript,
        "editable_transcript": req.transcript,
        "parsed_data": parsed,
        "is_complete": not parsed.get("requires_clarification", False),
        "clarification_question": parsed.get("clarification_question")
    }


@router.post("/speak")
def format_spoken_response(
    req: SpeakRequest,
    membership: Membership = Depends(get_current_membership)
):
    """
    Cleans markdown formatting and formula codes to produce phonetically natural audio text.
    """
    import re
    clean = re.sub(r"[*#_`$]", "", req.text)
    clean = re.sub(r"\[.*?\]\(.*?\)", "", clean)
    clean = clean.replace("₹", "Rupees ").replace("  ", " ").strip()
    return {
        "original_text": req.text,
        "spoken_text": clean,
        "language": req.language or "en"
    }


@router.get("/conversation/{conversation_id}")
def get_conversation_history(
    conversation_id: str,
    membership: Membership = Depends(get_current_membership)
):
    """
    Retrieves multi-turn conversation memory for the session.
    Strictly tenant isolated.
    """
    tenant_convs = CONVERSATION_STORE.get(membership.tenant_id, {})
    messages = tenant_convs.get(conversation_id, [])
    return {
        "tenant_id": membership.tenant_id,
        "conversation_id": conversation_id,
        "messages": messages
    }


@router.delete("/conversation/{conversation_id}")
def clear_conversation_history(
    conversation_id: str,
    membership: Membership = Depends(get_current_membership)
):
    """
    Resets multi-turn conversational memory for a session.
    Strictly tenant isolated.
    """
    if membership.tenant_id in CONVERSATION_STORE and conversation_id in CONVERSATION_STORE[membership.tenant_id]:
        del CONVERSATION_STORE[membership.tenant_id][conversation_id]
    return {
        "tenant_id": membership.tenant_id,
        "conversation_id": conversation_id,
        "status": "CLEARED"
    }
