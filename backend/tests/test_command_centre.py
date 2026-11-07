import io
import pytest
import datetime
from decimal import Decimal
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.user import Tenant, User, Membership
from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt
from backend.app.models.ledger import LedgerAccount, LedgerEntry
from backend.app.models.workflow import WorkflowRun
from backend.app.models.usage import AuditLog

client = TestClient(app)


def get_tenant_auth_header(client: TestClient, email: str, business_name: str, gstin: str):
    """Helper to register/login a merchant and return auth headers with X-Tenant-ID."""
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

    # Fetch user's workspaces
    ws_res = client.get("/api/v1/auth/workspaces", headers=headers)
    assert ws_res.status_code == 200, ws_res.text
    workspaces = ws_res.json()
    tenant_id = workspaces[0]["tenant"]["id"] if workspaces and "tenant" in workspaces[0] else None

    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id

    # Clean tenant records for complete test repeatability
    db = SessionLocal()
    try:
        if tenant_id:
            db.query(LedgerEntry).filter(LedgerEntry.tenant_id == tenant_id).delete()
            db.query(Transaction).filter(Transaction.tenant_id == tenant_id).delete()
            db.query(Receipt).filter(Receipt.tenant_id == tenant_id).delete()
            db.query(WorkflowRun).filter(WorkflowRun.tenant_id == tenant_id).delete()
            db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id).delete()
            db.commit()
    finally:
        db.close()

    return headers, tenant_id


# Test 1: Hindi voice transaction entry
def test_acceptance_1_hindi_voice_transaction_entry():
    headers, tenant_id = get_tenant_auth_header(
        client, "hindi.merchant@kirana.in", "Hindi Kirana Bhandar", "27AAAAA1111A1Z1"
    )
    payload = {
        "instruction": "Kal Sharma Traders ko 15,000 rupees payment kiya",
        "language": "hi",
        "financial_period": "2026-10"
    }
    res = client.post("/api/v1/command/execute", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["intent"] == "VOICE_TRANSACTION"
    assert data["status"] == "WAITING_APPROVAL"
    assert data["requires_approval"] is True

    # Validate extracted entity fields
    proposed = data.get("proposed_transactions", [])
    assert len(proposed) == 1
    p = proposed[0]
    assert p["amount"] == 15000.0
    assert p["type"] == "DEBIT"
    assert "Sharma Traders" in p["counterparty_name"]

    # Verify relative date: yesterday
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    assert p["transaction_date"] == yesterday.isoformat()

    # Verify no ledger entry posted yet without approval
    db = SessionLocal()
    try:
        tx_count = db.query(Transaction).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.amount == Decimal("15000.00"),
            Transaction.raw_narration == payload["instruction"]
        ).count()
        assert tx_count == 0, "Proposed transaction must NOT be posted without merchant approval"
    finally:
        db.close()


# Test 2: English voice transaction entry
def test_acceptance_2_english_voice_transaction_entry():
    headers, tenant_id = get_tenant_auth_header(
        client, "english.merchant@logistics.in", "English Express Cargo", "27BBBBB2222B1Z2"
    )
    payload = {
        "instruction": "Paid 8500 rupees to Patel Logistics via UPI today for transportation",
        "language": "en",
        "financial_period": "2026-10"
    }
    res = client.post("/api/v1/command/execute", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["intent"] == "VOICE_TRANSACTION"
    assert data["status"] == "WAITING_APPROVAL"

    proposed = data.get("proposed_transactions", [])
    assert len(proposed) == 1
    p = proposed[0]
    assert p["amount"] == 8500.0
    assert p["type"] == "DEBIT"
    assert "Patel Logistics" in p["counterparty_name"]
    assert p["channel"] == "UPI"
    assert p["transaction_date"] == datetime.date.today().isoformat()


# Test 3: Text instruction to reconcile transactions
def test_acceptance_3_text_instruction_reconcile():
    headers, tenant_id = get_tenant_auth_header(
        client, "recon.merchant@kirana.in", "Reconciliation Store", "27CCCCC3333C1Z3"
    )
    db = SessionLocal()
    try:
        # Seed an unlinked transaction and matching receipt
        tx = Transaction(
            tenant_id=tenant_id,
            transaction_date=datetime.date(2026, 10, 15),
            description="UPI payment to Super Cement Co",
            raw_narration="UPI payment to Super Cement Co for INV-9901",
            amount=Decimal("11800.00"),
            type="DEBIT",
            channel="UPI",
            reference_number="UTR_RECON_9901",
            is_reconciled=False,
            status="CONFIRMED"
        )
        db.add(tx)

        rcpt = Receipt(
            tenant_id=tenant_id,
            invoice_number="INV-9901",
            invoice_date=datetime.date(2026, 10, 14),
            vendor_name="Super Cement Co",
            vendor_gstin="27XYZAB1234C1Z9",
            total_amount=Decimal("11800.00"),
            taxable_amount=Decimal("10000.00"),
            cgst_amount=Decimal("900.00"),
            sgst_amount=Decimal("900.00"),
            status="EXTRACTED"
        )
        db.add(rcpt)
        db.commit()
    finally:
        db.close()

    payload = {
        "instruction": "Reconcile all unlinked transactions with receipts",
        "language": "en"
    }
    res = client.post("/api/v1/command/execute", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["intent"] == "RECONCILE"
    recon = data.get("reconciliation_results", {})
    assert recon.get("auto_linked_count", 0) >= 1 or len(recon.get("matches", [])) >= 1
    assert any(m.get("invoice_number") == "INV-9901" for m in recon.get("matches", []))


# Test 4: Multi-document upload and processing
def test_acceptance_4_multi_document_upload():
    headers, tenant_id = get_tenant_auth_header(
        client, "multidoc.merchant@kirana.in", "MultiDoc Traders", "27DDDDD4444D1Z4"
    )

    csv_data = (
        "Date,Narration,Ref/Chq,Debit,Credit\n"
        "15/10/2026,HDFC Bank Charges,CHG9921,590.00,\n"
        "16/10/2026,Client Settlement Amit,REF8811,,25000.00\n"
    ).encode("utf-8")

    files = [
        ("files", ("bank_october.csv", io.BytesIO(csv_data), "text/csv"))
    ]
    data = {
        "instruction": "Ingest and process attached bank statements for October",
        "language": "en",
        "financial_period": "2026-10"
    }

    res = client.post("/api/v1/command/execute-upload", data=data, files=files, headers=headers)
    assert res.status_code == 200, res.text
    res_data = res.json()

    assert res_data["intent"] in ("DOCUMENT_INGESTION", "CLOSE_ACCOUNTS")
    assert len(res_data.get("extracted_documents", [])) >= 1
    proposed = res_data.get("proposed_transactions", [])
    assert len(proposed) >= 2


# Test 5: Multi-agent account-closing workflow
def test_acceptance_5_multi_agent_account_closing():
    headers, tenant_id = get_tenant_auth_header(
        client, "close.merchant@kirana.in", "MonthEnd Kirana", "27EEEEE5555E1Z5"
    )

    # Seed an October transaction to give GST and P&L real content
    db = SessionLocal()
    try:
        tx = Transaction(
            tenant_id=tenant_id,
            transaction_date=datetime.date(2026, 10, 20),
            description="October Retail Sales Inflow",
            raw_narration="October Retail Sales Inflow",
            amount=Decimal("59000.00"),
            type="CREDIT",
            channel="BANK",
            reference_number="SALE_OCT_59K",
            category="Sales Revenue",
            tax_rate=Decimal("18.0"),
            status="CONFIRMED"
        )
        db.add(tx)
        db.commit()
    finally:
        db.close()

    payload = {
        "instruction": "Close my October accounts and prepare GST report",
        "language": "en",
        "financial_period": "2026-10"
    }
    res = client.post("/api/v1/command/execute", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["intent"] == "CLOSE_ACCOUNTS"
    assert data["status"] == "WAITING_APPROVAL"
    assert data["requires_approval"] is True

    # Verify execution plan has all specialized agents
    plan = data.get("execution_plan", [])
    agents = [step["agent"] for step in plan]
    assert "Document Extraction Agent" in agents
    assert "Accounting Agent" in agents
    assert "Reconciliation Agent" in agents
    assert "Audit Agent" in agents
    assert "GST Agent" in agents
    assert "Financial Analysis Agent" in agents
    assert "Supervisor Checkpoint" in agents

    # Check GST & Financial reports generated
    gst = data.get("gst_summary", {})
    assert gst.get("period") == "2026-10"
    reports = data.get("financial_reports", {})
    assert "profit_and_loss" in reports
    assert "balance_sheet" in reports

    # Check approval summary contains required audit and liability metrics
    summary = data.get("approval_summary", {})
    assert "net_gst_payable" in summary
    assert "trial_balance_balanced" in summary


# Test 6: Missing-information clarification
def test_acceptance_6_missing_information_clarification():
    headers, tenant_id = get_tenant_auth_header(
        client, "clarify.merchant@kirana.in", "Clarify Store", "27FFFFF6666F1Z6"
    )
    payload = {
        "instruction": "Payment kiya",
        "language": "hi"
    }
    res = client.post("/api/v1/command/execute", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["intent"] == "VOICE_TRANSACTION"
    assert data["status"] == "WAITING_APPROVAL"
    assert "amount" in data.get("missing_information", [])
    assert data.get("clarification_question") is not None
    assert len(data.get("clarification_question", "")) > 10


# Test 7: Approval before ledger posting
def test_acceptance_7_approval_before_ledger_posting():
    headers, tenant_id = get_tenant_auth_header(
        client, "approve.merchant@kirana.in", "Approve Enterprises", "27GGGGG7777G1Z7"
    )

    # 1. Submit voice transaction
    payload = {
        "instruction": "Paid 12000 rupees to Royal Paint Store today via BANK",
        "language": "en"
    }
    exec_res = client.post("/api/v1/command/execute", json=payload, headers=headers)
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    run_id = exec_data["run_id"]
    assert exec_data["status"] == "WAITING_APPROVAL"

    # Verify zero ledger entries committed before approval
    db = SessionLocal()
    try:
        tx_count_pre = db.query(Transaction).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.amount == Decimal("12000.00")
        ).count()
        assert tx_count_pre == 0, "Ledger entries must not be committed before human approval"
    finally:
        db.close()

    # 2. Approve workflow run
    appr_payload = {"run_id": run_id, "approved": True}
    appr_res = client.post("/api/v1/command/approve", json=appr_payload, headers=headers)
    assert appr_res.status_code == 200, appr_res.text
    appr_data = appr_res.json()
    assert appr_data["status"] == "COMPLETED"
    assert appr_data["execution_results"]["committed_transactions"] >= 1

    # 3. Verify committed to DB and balanced
    db = SessionLocal()
    try:
        tx = db.query(Transaction).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.amount == Decimal("12000.00")
        ).first()
        assert tx is not None
        assert tx.status == "CONFIRMED"

        # Check ledger balance
        entries = db.query(LedgerEntry).filter(
            LedgerEntry.tenant_id == tenant_id,
            LedgerEntry.transaction_id == tx.id
        ).all()
        assert len(entries) >= 2
        total_dr = sum(e.debit for e in entries)
        total_cr = sum(e.credit for e in entries)
        assert total_dr == total_cr == Decimal("12000.00")
    finally:
        db.close()


# Test 8: Workflow retry without duplicate entries (Idempotency)
def test_acceptance_8_workflow_retry_idempotency():
    headers, tenant_id = get_tenant_auth_header(
        client, "idemp.merchant@kirana.in", "Idempotent Traders", "27HHHHH8888H1Z8"
    )

    # 1. Execute command
    exec_res = client.post("/api/v1/command/execute", json={
        "instruction": "Paid 4200 rupees to Electricity Board via UPI today",
        "idempotency_key": "IDEMP_KEY_8899"
    }, headers=headers)
    assert exec_res.status_code == 200
    run_id = exec_res.json()["run_id"]

    # 2. Approve first time
    appr1 = client.post("/api/v1/command/approve", json={"run_id": run_id, "approved": True}, headers=headers)
    assert appr1.status_code == 200
    assert appr1.json()["status"] == "COMPLETED"

    db = SessionLocal()
    try:
        count_first = db.query(Transaction).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.amount == Decimal("4200.00")
        ).count()
        assert count_first == 1
    finally:
        db.close()

    # 3. Retry approval with same run_id
    appr2 = client.post("/api/v1/command/approve", json={"run_id": run_id, "approved": True}, headers=headers)
    assert appr2.status_code == 200
    assert appr2.json()["status"] == "COMPLETED"

    # Verify no duplicate transaction was inserted
    db = SessionLocal()
    try:
        count_second = db.query(Transaction).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.amount == Decimal("4200.00")
        ).count()
        assert count_second == 1, "Idempotency violated: duplicate transaction was inserted"
    finally:
        db.close()


# Test 9: Strict tenant isolation
def test_acceptance_9_strict_tenant_isolation():
    # Tenant A
    headers_a, tenant_id_a = get_tenant_auth_header(
        client, "tenant.a@kirana.in", "Tenant A Hardware", "27AAAAA9999A1Z9"
    )
    # Tenant B
    headers_b, tenant_id_b = get_tenant_auth_header(
        client, "tenant.b@kirana.in", "Tenant B Textiles", "27BBBBB9999B1Z9"
    )

    # Tenant A executes a command
    res_a = client.post("/api/v1/command/execute", json={
        "instruction": "Paid 7000 rupees to Steel Supplier today via BANK"
    }, headers=headers_a)
    assert res_a.status_code == 200
    run_id_a = res_a.json()["run_id"]

    # Tenant B attempts to retrieve Tenant A's run
    get_b = client.get(f"/api/v1/command/runs/{run_id_a}", headers=headers_b)
    assert get_b.status_code == 404, "Tenant B should NOT be able to view Tenant A's workflow run"

    # Tenant B attempts to approve Tenant A's run
    appr_b = client.post("/api/v1/command/approve", json={"run_id": run_id_a, "approved": True}, headers=headers_b)
    assert appr_b.status_code == 404, "Tenant B should NOT be able to approve Tenant A's workflow run"

    # Verify Tenant B's ledger is completely empty of Tenant A's transactions
    db = SessionLocal()
    try:
        tx_b = db.query(Transaction).filter(
            Transaction.tenant_id == tenant_id_b,
            Transaction.amount == Decimal("7000.00")
        ).count()
        assert tx_b == 0
    finally:
        db.close()


# Test 10: Recovery from an agent failure
def test_acceptance_10_recovery_from_agent_failure():
    headers, tenant_id = get_tenant_auth_header(
        client, "failure.test@kirana.in", "Resilient Enterprises", "27FFFFF9999F1Z9"
    )

    # Invalid empty or corrupt request should not crash the server
    res = client.post("/api/v1/command/execute", json={
        "instruction": "",
        "language": "en"
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "status" in data

    # Non-existent run approval returns 404 cleanly
    res_fake = client.post("/api/v1/command/approve", json={
        "run_id": "non_existent_run_9999",
        "approved": True
    }, headers=headers)
    assert res_fake.status_code == 404
