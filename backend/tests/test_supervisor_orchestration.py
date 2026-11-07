import io
import pytest
import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.user import Tenant, User, Membership
from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt
from backend.app.models.ledger import LedgerAccount, LedgerEntry
from backend.app.models.workflow import WorkflowRun
from backend.app.models.usage import AuditLog
from backend.app.workflows.supervisor import (
    supervisor_router,
    accounting_router,
    reconciliation_router,
    audit_router,
    gst_router,
    financial_analysis_router,
    SupervisorWorkflowState
)


def get_auth_headers_and_tenant(client: TestClient, db: Session, email: str, business_name: str, gstin: str):
    """Registers/authenticates a merchant for isolated test execution."""
    login_data = {"username": email, "password": "SecurePassword@123"}
    res = client.post("/api/v1/auth/login", data=login_data)
    if res.status_code != 200:
        reg_payload = {
            "email": email,
            "password": "SecurePassword@123",
            "full_name": f"{business_name} Admin",
            "business_name": business_name,
            "state_code": gstin[:2] if len(gstin) >= 2 else "27"
        }
        res = client.post("/api/v1/auth/register", json=reg_payload)
        assert res.status_code in (200, 201), res.text

    data = res.json()
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws_res = client.get("/api/v1/auth/workspaces", headers=headers)
    assert ws_res.status_code == 200, ws_res.text
    workspaces = ws_res.json()
    tenant_id = workspaces[0]["tenant"]["id"] if workspaces and "tenant" in workspaces[0] else None

    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
        db.query(LedgerEntry).filter(LedgerEntry.tenant_id == tenant_id).delete()
        db.query(Transaction).filter(Transaction.tenant_id == tenant_id).delete()
        db.query(Receipt).filter(Receipt.tenant_id == tenant_id).delete()
        db.query(WorkflowRun).filter(WorkflowRun.tenant_id == tenant_id).delete()
        db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id).delete()
        db.commit()

    return headers, tenant_id


# ==============================================================================
# Scenario 1: Simple Single-Agent Requests
# ==============================================================================
def test_simple_single_agent_requests(client: TestClient, db_session: Session):
    """
    Verifies single-agent requests route directly to that agent and produce the
    expected results without executing unrelated agents unnecessarily.
    """
    headers, tenant_id = get_auth_headers_and_tenant(
        client, db_session, "single.agent@kirana.in", "Single Agent MSME", "27AAAAA1001A1Z1"
    )

    # 1a. GST return inquiry (GST Agent)
    gst_res = client.post(
        "/api/v1/command/execute",
        json={"instruction": "Prepare my GSTR-3B tax summary for 2026-10", "financial_period": "2026-10"},
        headers=headers
    )
    assert gst_res.status_code == 200, gst_res.text
    gst_data = gst_res.json()
    assert gst_data["intent"] == "GST_RETURN"
    assert "gst_agent" in gst_data.get("completed_tasks", [])
    assert gst_data.get("gst_summary") is not None
    assert gst_data["gst_summary"]["period"] == "2026-10"
    assert gst_data["requires_approval"] is False

    # 1b. Compliance audit inquiry (Audit Agent)
    audit_res = client.post(
        "/api/v1/command/execute",
        json={"instruction": "Run compliance audit and check for Section 40A(3) cash limit violations"},
        headers=headers
    )
    assert audit_res.status_code == 200, audit_res.text
    audit_data = audit_res.json()
    assert audit_data["intent"] == "AUDIT_CHECK"
    assert "audit_agent" in audit_data.get("completed_tasks", [])
    assert audit_data.get("audit_anomalies") is not None
    assert "trial_balance_balanced" in audit_data["audit_anomalies"]
    assert audit_data["requires_approval"] is False

    # 1c. Financial analysis inquiry (Financial Analysis Agent)
    fin_res = client.post(
        "/api/v1/command/execute",
        json={"instruction": "Generate financial report and profit and loss statement"},
        headers=headers
    )
    assert fin_res.status_code == 200, fin_res.text
    fin_data = fin_res.json()
    assert fin_data["intent"] == "FINANCIAL_ANALYSIS"
    assert "financial_analysis_agent" in fin_data.get("completed_tasks", [])
    assert fin_data.get("financial_reports") is not None
    assert "profit_and_loss" in fin_data["financial_reports"]
    assert "balance_sheet" in fin_data["financial_reports"]
    assert fin_data["requires_approval"] is False

    # 1d. General conversational query (General Query Agent with BharatCode)
    query_res = client.post(
        "/api/v1/command/execute",
        json={"instruction": "What are the requirements for Section 16 input tax credit under GST?"},
        headers=headers
    )
    assert query_res.status_code == 200, query_res.text
    query_data = query_res.json()
    assert query_data["intent"] == "GENERAL_QUERY"
    assert "general_query_agent" in query_data.get("completed_tasks", [])
    assert len(query_data.get("spoken_response", "")) > 10
    assert query_data["requires_approval"] is False


# ==============================================================================
# Scenario 2: Multi-Agent Workflow — Close October Accounts
# ==============================================================================
def test_multi_agent_workflow_close_october_accounts(client: TestClient, db_session: Session):
    """
    Tests the exact full multi-agent prompt:
    'Close my October accounts, classify transactions, reconcile bank statements,
     identify discrepancies, prepare my GST summary and generate financial reports.'

    Verifies execution across all 7 specialized agents in dependency order,
    halts at the supervisor approval checkpoint, generates a consolidated report,
    and maintains financial safety (zero unapproved ledger mutations).
    """
    headers, tenant_id = get_auth_headers_and_tenant(
        client, db_session, "close.october@kirana.in", "October Closing Mart", "27BBBBB2002B1Z2"
    )

    # Seed an October confirmed transaction to generate real numbers in GST and P&L
    tx_oct = Transaction(
        tenant_id=tenant_id,
        transaction_date=datetime.date(2026, 10, 18),
        description="Wholesale Hardware Sales Oct",
        raw_narration="Wholesale Hardware Sales Oct",
        amount=Decimal("59000.00"),
        type="CREDIT",
        channel="BANK",
        reference_number="OCT_SALE_59K",
        category="Sales Revenue",
        tax_rate=Decimal("18.0"),
        status="CONFIRMED"
    )
    db_session.add(tx_oct)
    db_session.commit()

    prompt = (
        "Close my October accounts, classify transactions, reconcile bank statements, "
        "identify discrepancies, prepare my GST summary and generate financial reports."
    )
    payload = {
        "instruction": prompt,
        "language": "en",
        "financial_period": "2026-10"
    }

    res = client.post("/api/v1/command/execute", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    # 1. State and approval checkpoint verification
    assert data["intent"] == "CLOSE_ACCOUNTS"
    assert data["status"] == "WAITING_APPROVAL"
    assert data["requires_approval"] is True

    # 2. Verify all 7 specialized agents executed in dependency order
    completed_tasks = data.get("completed_tasks", [])
    expected_agents = [
        "document_agent",
        "classification_agent",
        "accounting_agent",
        "reconciliation_agent",
        "audit_agent",
        "gst_agent",
        "financial_analysis_agent",
        "approval_checkpoint"
    ]
    for agent in expected_agents:
        assert agent in completed_tasks, f"Agent '{agent}' was not executed in multi-agent workflow"

    # Verify dependency order of completed tasks
    doc_idx = completed_tasks.index("document_agent")
    cls_idx = completed_tasks.index("classification_agent")
    acc_idx = completed_tasks.index("accounting_agent")
    rec_idx = completed_tasks.index("reconciliation_agent")
    aud_idx = completed_tasks.index("audit_agent")
    gst_idx = completed_tasks.index("gst_agent")
    fin_idx = completed_tasks.index("financial_analysis_agent")
    chk_idx = completed_tasks.index("approval_checkpoint")

    assert doc_idx < cls_idx < acc_idx < rec_idx < aud_idx < gst_idx < fin_idx < chk_idx

    # 3. Verify execution plan steps
    plan = data.get("execution_plan", [])
    assert len(plan) >= 8
    plan_agents = [step["agent"] for step in plan]
    assert "Document Extraction Agent" in plan_agents
    assert "Transaction Classification Agent" in plan_agents
    assert "Accounting Agent" in plan_agents
    assert "Reconciliation Agent" in plan_agents
    assert "Audit Agent" in plan_agents
    assert "GST Agent" in plan_agents
    assert "Financial Analysis Agent" in plan_agents
    assert "Supervisor Checkpoint" in plan_agents

    # 4. Verify Consolidated Report contents
    report = data.get("consolidated_report")
    assert report is not None, "Consolidated report missing from workflow output"
    assert report["financial_period"] == "2026-10"
    assert report["status"] == "WAITING_APPROVAL"

    # Verify all required sub-reports inside the consolidated report
    assert "task_summary" in report
    assert report["task_summary"]["total_tasks"] == len(plan)
    assert len(report["task_summary"]["completed_tasks"]) >= 7

    assert "documents" in report
    assert "extracted_count" in report["documents"]

    assert "classification_and_accounting" in report
    assert "candidate_transactions_count" in report["classification_and_accounting"]

    assert "reconciliation" in report
    assert "auto_linked_count" in report["reconciliation"]

    assert "audit_and_compliance" in report
    assert "anomalies_detected" in report["audit_and_compliance"]
    assert "trial_balance_balanced" in report["audit_and_compliance"]

    assert "gst_summary" in report
    assert report["gst_summary"]["period"] == "2026-10"
    assert "total_outward_tax" in report["gst_summary"]
    assert "net_cash_payable" in report["gst_summary"]

    assert "financial_analysis" in report
    assert "net_profit" in report["financial_analysis"]
    assert "total_revenue" in report["financial_analysis"]

    assert "recommendations" in report
    assert len(report["recommendations"]) >= 2

    # 5. Financial safety: Zero unapproved ledger postings
    db_session.expire_all()
    unapproved_entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.tenant_id == tenant_id
    ).all()
    assert len(unapproved_entries) == 0, "Financial safety violated: ledger entries committed without approval"


# ==============================================================================
# Scenario 3: Conditional Routing
# ==============================================================================
def test_conditional_routing():
    """
    Verifies that the LangGraph supervisor router functions accurately direct
    workflow state to the appropriate agent nodes based on intent and lifecycle status.
    """
    # 1. Supervisor Router
    assert supervisor_router({"intent": "VOICE_TRANSACTION", "status": "RUNNING"}) == "classification_agent"
    assert supervisor_router({"intent": "CLOSE_ACCOUNTS", "status": "RUNNING"}) == "document_agent"
    assert supervisor_router({"intent": "DOCUMENT_INGESTION", "status": "RUNNING"}) == "document_agent"
    assert supervisor_router({"intent": "RECONCILE", "status": "RUNNING"}) == "document_agent"
    assert supervisor_router({"intent": "AUDIT_CHECK", "status": "RUNNING"}) == "audit_agent"
    assert supervisor_router({"intent": "GST_RETURN", "status": "RUNNING"}) == "gst_agent"
    assert supervisor_router({"intent": "FINANCIAL_ANALYSIS", "status": "RUNNING"}) == "financial_analysis_agent"
    assert supervisor_router({"intent": "GENERAL_QUERY", "status": "RUNNING"}) == "general_query_agent"

    # Router halts when already waiting for approval
    assert supervisor_router({"intent": "CLOSE_ACCOUNTS", "status": "WAITING_APPROVAL"}) == "__end__"

    # 2. Accounting Router
    assert accounting_router({"intent": "VOICE_TRANSACTION"}) == "audit_agent"
    assert accounting_router({"intent": "DOCUMENT_INGESTION"}) == "approval_checkpoint"
    assert accounting_router({"intent": "CLOSE_ACCOUNTS"}) == "reconciliation_agent"

    # 3. Reconciliation Router
    assert reconciliation_router({"intent": "RECONCILE"}) == "approval_checkpoint"
    assert reconciliation_router({"intent": "CLOSE_ACCOUNTS"}) == "audit_agent"

    # 4. Audit Router
    assert audit_router({"intent": "AUDIT_CHECK"}) == "__end__"
    assert audit_router({"intent": "VOICE_TRANSACTION"}) == "approval_checkpoint"
    assert audit_router({"intent": "CLOSE_ACCOUNTS"}) == "gst_agent"

    # 5. GST Router
    assert gst_router({"intent": "GST_RETURN"}) == "__end__"
    assert gst_router({"intent": "CLOSE_ACCOUNTS"}) == "financial_analysis_agent"

    # 6. Financial Analysis Router
    assert financial_analysis_router({"intent": "FINANCIAL_ANALYSIS"}) == "__end__"
    assert financial_analysis_router({"intent": "CLOSE_ACCOUNTS"}) == "approval_checkpoint"


# ==============================================================================
# Scenario 4: Failed Agent Recovery and Retry Limits
# ==============================================================================
def test_failed_agent_recovery_and_retry_limits(client: TestClient, db_session: Session):
    """
    Simulates an agent-level failure (e.g. malformed document attachment)
    and verifies that the error is recorded, retry count tracked,
    and the workflow continues gracefully without an unhandled server crash.
    """
    headers, tenant_id = get_auth_headers_and_tenant(
        client, db_session, "retry.failure@kirana.in", "Recovery Mart", "27CCCCC3003C1Z3"
    )

    # Attach corrupted data simulating unparseable statement
    corrupt_bytes = b"BINARY_GARBAGE\x00\x01\x02NOT_A_VALID_CSV_HEADER\xff\xfe"
    files = [
        ("files", ("corrupt_statement.csv", io.BytesIO(corrupt_bytes), "text/csv"))
    ]
    data = {
        "instruction": "Process attached bank statement and close accounts",
        "language": "en",
        "financial_period": "2026-10"
    }

    res = client.post("/api/v1/command/execute-upload", data=data, files=files, headers=headers)
    assert res.status_code == 200, res.text
    res_data = res.json()

    # The pipeline should survive the corrupt file and record the error
    assert res_data["status"] in ("WAITING_APPROVAL", "COMPLETED")
    errors = res_data.get("errors", [])
    retry_counts = res_data.get("retry_counts", {})

    assert len(errors) >= 1 or retry_counts.get("document_agent", 0) >= 1
    # Check that retry tracking exists in state
    assert isinstance(retry_counts, dict)


# ==============================================================================
# Scenario 5: Ambiguous Requests and Clarification
# ==============================================================================
def test_ambiguous_requests_and_clarification(client: TestClient, db_session: Session):
    """
    Tests an ambiguous or incomplete voice/text request ('Payment kiya').
    Verifies that the supervisor halts at a clarification checkpoint,
    identifies the missing fields, and returns a clarification question.
    """
    headers, tenant_id = get_auth_headers_and_tenant(
        client, db_session, "ambiguous.user@kirana.in", "Ambiguous Kirana", "27DDDDD4004D1Z4"
    )

    payload = {
        "instruction": "Payment kiya",
        "language": "hi",
        "financial_period": "2026-10"
    }

    res = client.post("/api/v1/command/execute", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["intent"] == "VOICE_TRANSACTION"
    assert data["status"] == "WAITING_APPROVAL"
    assert data["requires_approval"] is True

    # Validate missing information detection
    missing = data.get("missing_information", [])
    assert len(missing) >= 1
    assert any(f in missing for f in ["amount", "counterparty_name"])

    # Validate clarification question
    clarification_q = data.get("clarification_question")
    assert clarification_q is not None
    assert len(clarification_q) > 5

    # Verify execution plan stopped at Clarification Checkpoint
    plan = data.get("execution_plan", [])
    checkpoint_step = next((s for s in plan if "Clarification" in s["title"]), None)
    assert checkpoint_step is not None
    assert checkpoint_step["status"] == "WAITING_APPROVAL"


# ==============================================================================
# Scenario 6: Approval-Required Operations Financial Safety
# ==============================================================================
def test_approval_required_operations_financial_safety(client: TestClient, db_session: Session):
    """
    Verifies the zero-trust financial safety barrier:
    Even when a complete, valid transaction is proposed, exactly 0 rows are
    committed to the general ledger or confirmed transactions before explicit approval.
    """
    headers, tenant_id = get_auth_headers_and_tenant(
        client, db_session, "safety.guard@kirana.in", "Safe Accounts Store", "27EEEEE5005E1Z5"
    )

    payload = {
        "instruction": "Kal Sharma Paper Mills ko 12,500 rupees UPI payment kiya",
        "language": "hi",
        "financial_period": "2026-10"
    }

    res = client.post("/api/v1/command/execute", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["status"] == "WAITING_APPROVAL"
    assert data["requires_approval"] is True
    assert len(data.get("proposed_transactions", [])) == 1

    # Verify in DB: 0 confirmed transactions with this amount
    db_session.expire_all()
    committed_txs = db_session.query(Transaction).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.amount == Decimal("12500.00"),
        Transaction.status == "CONFIRMED"
    ).all()
    assert len(committed_txs) == 0, "Unapproved transaction found in DB!"

    # Verify in DB: 0 ledger entries committed
    committed_entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.tenant_id == tenant_id
    ).all()
    assert len(committed_entries) == 0, "Unapproved ledger entries found in DB!"


# ==============================================================================
# Scenario 7: Workflow Resumption and Idempotency
# ==============================================================================
def test_workflow_resumption_and_idempotency(client: TestClient, db_session: Session):
    """
    Tests resumption from checkpoint via /approve:
    1. Resumes execution and commits balanced double-entry vouchers to ledger.
    2. Logs an audit trail.
    3. Re-submitting the exact same approval is fully idempotent (no double-posting).
    """
    headers, tenant_id = get_auth_headers_and_tenant(
        client, db_session, "idempotent.flow@kirana.in", "Idempotent Stores", "27FFFFF6006F1Z6"
    )

    # 1. Propose transaction
    payload = {
        "instruction": "Paid 7500 rupees to Modern Packaging via Bank",
        "language": "en",
        "financial_period": "2026-10"
    }
    exec_res = client.post("/api/v1/command/execute", json=payload, headers=headers)
    assert exec_res.status_code == 200, exec_res.text
    run_id = exec_res.json()["run_id"]

    # 2. Approve transaction
    approve_payload = {"run_id": run_id, "approved": True}
    appr_res = client.post("/api/v1/command/approve", json=approve_payload, headers=headers)
    assert appr_res.status_code == 200, appr_res.text
    appr_data = appr_res.json()

    assert appr_data["status"] == "COMPLETED"
    exec_results = appr_data.get("execution_results", {})
    assert exec_results.get("committed_transactions") == 1
    assert exec_results.get("ledger_entries_created", 0) >= 2

    # Verify ledger entries in DB
    db_session.expire_all()
    txs = db_session.query(Transaction).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.amount == Decimal("7500.00")
    ).all()
    assert len(txs) == 1
    tx_id = txs[0].id

    entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.tenant_id == tenant_id,
        LedgerEntry.transaction_id == tx_id
    ).all()
    assert len(entries) >= 2

    # Check Total Dr == Total Cr
    total_dr = sum(e.debit for e in entries)
    total_cr = sum(e.credit for e in entries)
    assert total_dr == total_cr == Decimal("7500.00"), f"Double-entry imbalance: Dr={total_dr}, Cr={total_cr}"

    # Verify AuditLog created
    audit = db_session.query(AuditLog).filter(
        AuditLog.tenant_id == tenant_id,
        AuditLog.entity_id == run_id,
        AuditLog.action == "APPROVE_WORKFLOW"
    ).first()
    assert audit is not None, "AuditLog entry missing for approved workflow run"

    # 3. Idempotency test: approve again with the exact same run_id
    second_appr_res = client.post("/api/v1/command/approve", json=approve_payload, headers=headers)
    assert second_appr_res.status_code == 200, second_appr_res.text
    second_data = second_appr_res.json()
    assert second_data["status"] == "COMPLETED"
    assert "idempotent" in second_data.get("message", "").lower()

    # Verify database was NOT double-posted
    db_session.expire_all()
    tx_count_after = db_session.query(Transaction).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.amount == Decimal("7500.00")
    ).count()
    assert tx_count_after == 1, "Idempotency violated: duplicate transaction created on second approval!"

    entry_count_after = db_session.query(LedgerEntry).filter(
        LedgerEntry.tenant_id == tenant_id,
        LedgerEntry.transaction_id == tx_id
    ).count()
    assert entry_count_after == len(entries), "Idempotency violated: duplicate ledger entries created!"


# ==============================================================================
# Scenario 8: Strict Tenant Isolation
# ==============================================================================
def test_strict_tenant_isolation(client: TestClient, db_session: Session):
    """
    Verifies that multi-agent workflow runs and approval mechanisms are strictly
    isolated across tenants:
    1. Tenant A initiates a workflow run.
    2. Tenant B cannot view Tenant A's run by ID (HTTP 404).
    3. Tenant B cannot approve Tenant A's run (HTTP 404).
    4. Tenant B's run history does not include Tenant A's run.
    5. Tenant B's financial ledger remains completely untainted.
    """
    headers_a, tenant_a_id = get_auth_headers_and_tenant(
        client, db_session, "tenant.alpha@kirana.in", "Tenant Alpha Traders", "27GGGGG7007G1Z7"
    )
    headers_b, tenant_b_id = get_auth_headers_and_tenant(
        client, db_session, "tenant.beta@kirana.in", "Tenant Beta Supermarket", "27HHHHH8008H1Z8"
    )

    # 1. Tenant A starts a command run
    payload = {
        "instruction": "Paid 20000 rupees to Alpha Wholesale Vendor",
        "language": "en",
        "financial_period": "2026-10"
    }
    res_a = client.post("/api/v1/command/execute", json=payload, headers=headers_a)
    assert res_a.status_code == 200, res_a.text
    run_a_id = res_a.json()["run_id"]

    # 2. Tenant B attempts to fetch Tenant A's run -> 404 NOT FOUND
    get_res = client.get(f"/api/v1/command/runs/{run_a_id}", headers=headers_b)
    assert get_res.status_code == 404, f"Expected 404, got {get_res.status_code}: {get_res.text}"

    # 3. Tenant B attempts to approve Tenant A's run -> 404 NOT FOUND
    approve_res = client.post(
        "/api/v1/command/approve",
        json={"run_id": run_a_id, "approved": True},
        headers=headers_b
    )
    assert approve_res.status_code == 404, f"Expected 404, got {approve_res.status_code}: {approve_res.text}"

    # 4. Tenant B lists runs -> Tenant A's run must NOT be present
    list_res = client.get("/api/v1/command/runs", headers=headers_b)
    assert list_res.status_code == 200
    runs_b = list_res.json()
    run_ids_b = [r["run_id"] for r in runs_b]
    assert run_a_id not in run_ids_b, "Tenant isolation leak: Tenant A run visible in Tenant B run list"

    # 5. Confirm Tenant B's ledger is completely clean
    db_session.expire_all()
    entries_b = db_session.query(LedgerEntry).filter(LedgerEntry.tenant_id == tenant_b_id).all()
    assert len(entries_b) == 0, "Tenant isolation leak: entries posted to Tenant B ledger"
