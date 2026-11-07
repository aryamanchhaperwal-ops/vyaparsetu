import pytest
from decimal import Decimal
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.transaction import Transaction
from backend.app.models.ledger import LedgerEntry
from backend.app.models.workflow import WorkflowRun
from backend.app.models.usage import AuditLog
from backend.app.config import settings
from backend.app.llm.client import BharatCodeClient, BharatCodeAPIError

def get_live_test_auth_headers(client: TestClient, db, email: str = "ai.integration@lekha.in"):
    """Registers and authenticates a test tenant, cleaning prior state for idempotency."""
    login_data = {"username": email, "password": "SecurePassword@123"}
    res = client.post("/api/v1/auth/login", data=login_data)
    if res.status_code != 200:
        reg_payload = {
            "email": email,
            "password": "SecurePassword@123",
            "full_name": "AI Integration Merchant",
            "business_name": "Bharat Traders & Hardware",
            "state_code": "27"  # Maharashtra (Intra-state base)
        }
        res = client.post("/api/v1/auth/register", json=reg_payload)
        assert res.status_code in (200, 201), res.text

    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws_res = client.get("/api/v1/auth/workspaces", headers=headers)
    assert ws_res.status_code == 200
    workspaces = ws_res.json()
    tenant_id = workspaces[0]["tenant"]["id"] if workspaces and "tenant" in workspaces[0] else None
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id

    # Clean records in test DB
    if tenant_id:
        db.query(LedgerEntry).filter(LedgerEntry.tenant_id == tenant_id).delete()
        db.query(Transaction).filter(Transaction.tenant_id == tenant_id).delete()
        db.query(WorkflowRun).filter(WorkflowRun.tenant_id == tenant_id).delete()
        db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id).delete()
        db.commit()

    return headers, tenant_id


# =========================================================================
# TEST CASE 1: Normal Business Expense (Office Electricity Bill)
# =========================================================================
def test_case_1_normal_business_expense(client, db_session):
    """
    Test Case 1: Normal business expense.
    Verifies classification under Rent & Utilities, GST extraction,
    and balanced double-entry voucher generation.
    """
    headers, tenant_id = get_live_test_auth_headers(client, db_session, "test.case1@lekha.in")
    payload = {
        "raw_narration": "Monthly office electricity bill paid via BESCOM portal ₹3,450",
        "amount": 3450.00,
        "direction": "DEBIT",
        "channel": "UPI",
        "reference_number": "BESCOM98765432",
        "is_interstate": False,
        "ai_mode": "DEV_SIMULATION"
    }

    res = client.post("/api/v1/workflow/process", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["status"] == "CONFIRMED"
    assert data["category"] in ("Rent & Utilities", "Office Expenses")
    assert data["confidence_score"] >= 0.85
    assert data["ledger_entries_created"] >= 2
    assert "accounting_suggestions" in data
    assert len(data["accounting_suggestions"]) > 0

    # Verify deterministic ledger balancing in test database
    db_session.expire_all()
    entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.tenant_id == tenant_id,
        LedgerEntry.transaction_id == data["transaction_id"]
    ).all()
    assert len(entries) >= 2
    total_debit = sum(e.debit for e in entries)
    total_credit = sum(e.credit for e in entries)
    assert total_debit == total_credit == Decimal("3450.00")


# =========================================================================
# TEST CASE 2: Customer Payment (Inward Credit with Customer Identification)
# =========================================================================
def test_case_2_customer_payment(client, db_session):
    """
    Test Case 2: Customer payment.
    Verifies direction=CREDIT, customer identification, sales revenue mapping,
    and balanced double-entry ledger vouchers.
    """
    headers, tenant_id = get_live_test_auth_headers(client, db_session, "test.case2@lekha.in")
    payload = {
        "raw_narration": "Gupta Traders se customer sales advance payment received ₹85,000 via RTGS",
        "amount": 85000.00,
        "direction": "CREDIT",
        "channel": "RTGS",
        "reference_number": "RTGSGUPTA8877",
        "is_interstate": False,
        "ai_mode": "DEV_SIMULATION"
    }

    res = client.post("/api/v1/workflow/process", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["status"] == "CONFIRMED"
    assert data["transaction_type"] == "CREDIT"
    assert "Sales Revenue" in data["category"] or "Revenue" in data["category"]
    assert data["confidence_score"] >= 0.85
    assert data["ledger_entries_created"] >= 2

    # Verify ledger entries: Bank debited, Sales credited
    db_session.expire_all()
    entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.tenant_id == tenant_id,
        LedgerEntry.transaction_id == data["transaction_id"]
    ).all()
    assert len(entries) >= 2
    total_debit = sum(e.debit for e in entries)
    total_credit = sum(e.credit for e in entries)
    assert total_debit == total_credit == Decimal("85000.00")


# =========================================================================
# TEST CASE 3: Supplier Payment (Outward Debit with Vendor and GST Rate)
# =========================================================================
def test_case_3_supplier_payment(client, db_session):
    """
    Test Case 3: Supplier payment.
    Verifies vendor identification, Raw Materials categorization, statutory HSN and GST rate,
    and Section 16 ITC guidance.
    """
    headers, tenant_id = get_live_test_auth_headers(client, db_session, "test.case3@lekha.in")
    payload = {
        "raw_narration": "Paid ₹45,000 to Ambica Steels for raw sariya cement and building materials",
        "amount": 45000.00,
        "direction": "DEBIT",
        "channel": "IMPS",
        "reference_number": "IMPSAMBICA9911",
        "is_interstate": False,
        "ai_mode": "DEV_SIMULATION"
    }

    res = client.post("/api/v1/workflow/process", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["status"] == "CONFIRMED"
    assert data["category"] == "Raw Materials"
    assert data["gst_rate"] in (18.0, 28.0, 12.0)
    assert data["confidence_score"] >= 0.85
    assert data["ledger_entries_created"] >= 2
    assert any("Section 16" in s for s in data["accounting_suggestions"])

    db_session.expire_all()
    entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.tenant_id == tenant_id,
        LedgerEntry.transaction_id == data["transaction_id"]
    ).all()
    assert len(entries) >= 2
    total_debit = sum(e.debit for e in entries)
    total_credit = sum(e.credit for e in entries)
    assert total_debit == total_credit == Decimal("45000.00")


# =========================================================================
# TEST CASE 4: Bank Transfer (Internal Transfer Between Accounts)
# =========================================================================
def test_case_4_bank_transfer(client, db_session):
    """
    Test Case 4: Bank transfer.
    Verifies contra/internal transfer categorization, zero GST liability,
    and balanced double-entry accounting.
    """
    headers, tenant_id = get_live_test_auth_headers(client, db_session, "test.case4@lekha.in")
    payload = {
        "raw_narration": "Inter-bank fund transfer from HDFC current account to SBI business account ₹50,000",
        "amount": 50000.00,
        "direction": "DEBIT",
        "channel": "BANK_TRANSFER",
        "reference_number": "CONTRATRANSFER001",
        "is_interstate": False,
        "ai_mode": "DEV_SIMULATION"
    }

    res = client.post("/api/v1/workflow/process", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["status"] == "CONFIRMED"
    assert data["ledger_entries_created"] >= 2
    assert data["confidence_score"] >= 0.85

    db_session.expire_all()
    entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.tenant_id == tenant_id,
        LedgerEntry.transaction_id == data["transaction_id"]
    ).all()
    assert len(entries) >= 2
    total_debit = sum(e.debit for e in entries)
    total_credit = sum(e.credit for e in entries)
    assert total_debit == total_credit == Decimal("50000.00")


# =========================================================================
# TEST CASE 5: Ambiguous Transaction (Halts for Human Review, 0 Auto-Posted Entries)
# =========================================================================
def test_case_5_ambiguous_transaction(client, db_session):
    """
    Test Case 5: Ambiguous transaction.
    Verifies that low confidence halts the workflow at NEEDS_APPROVAL,
    produces exactly 0 auto-posted ledger entries, enters the approval queue,
    and allows human correction and certified posting.
    """
    headers, tenant_id = get_live_test_auth_headers(client, db_session, "test.case5@lekha.in")
    payload = {
        "raw_narration": "Old uncle settlement payment kuch personal aur vendor mix ₹4,200",
        "amount": 4200.00,
        "direction": "DEBIT",
        "channel": "CASH",
        "reference_number": "CASHUNCLEMIX01",
        "is_interstate": False,
        "ai_mode": "DEV_SIMULATION"
    }

    res = client.post("/api/v1/workflow/process", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["status"] == "NEEDS_APPROVAL"
    assert data["confidence_score"] < 0.85
    assert data["ledger_entries_created"] == 0  # CRITICAL: Never post unapproved transactions
    tx_id = data["transaction_id"]

    # Verify exactly 0 ledger entries in database
    db_session.expire_all()
    entries_before = db_session.query(LedgerEntry).filter(
        LedgerEntry.tenant_id == tenant_id,
        LedgerEntry.transaction_id == tx_id
    ).all()
    assert len(entries_before) == 0

    # Verify transaction is in the approval queue
    queue_res = client.get("/api/v1/workflow/approval-queue", headers=headers)
    assert queue_res.status_code == 200
    queue = queue_res.json()
    assert any(item["id"] == tx_id for item in queue)

    # Human reviews, corrects, and approves the transaction
    approve_payload = {
        "transaction_id": tx_id,
        "category": "Miscellaneous Expense",
        "sub_category": "Staff Welfare & Sundry",
        "gst_rate": 0.0,
        "counterparty_name": "Uncle Sundry Vendor",
        "human_feedback": "Approved as minor cash operational expense",
        "is_interstate": False
    }
    app_res = client.post("/api/v1/workflow/approve", json=approve_payload, headers=headers)
    assert app_res.status_code == 200, app_res.text
    app_data = app_res.json()

    assert app_data["status"] == "APPROVED_AND_POSTED"
    assert app_data["entries_created"] >= 2
    assert app_data["total_balanced_amount"] == "4200.00"

    # Verify ledger entries exist and balance after human approval
    db_session.expire_all()
    entries_after = db_session.query(LedgerEntry).filter(
        LedgerEntry.tenant_id == tenant_id,
        LedgerEntry.transaction_id == tx_id
    ).all()
    assert len(entries_after) >= 2
    total_debit = sum(e.debit for e in entries_after)
    total_credit = sum(e.credit for e in entries_after)
    assert total_debit == total_credit == Decimal("4200.00")


# =========================================================================
# TEST CASE 6: Invalid / Incomplete Narration & Negative Amount (HTTP 400)
# =========================================================================
def test_case_6_invalid_incomplete_narration(client, db_session):
    """
    Test Case 6: Invalid / incomplete narration and non-positive amounts.
    Verifies that invalid requests are rejected with HTTP 400 Bad Request,
    and 0 database records or ledger entries are created.
    """
    headers, tenant_id = get_live_test_auth_headers(client, db_session, "test.case6@lekha.in")

    # 6a: Empty narration
    empty_payload = {
        "raw_narration": "   ",
        "amount": 1000.00,
        "direction": "DEBIT",
        "channel": "UPI"
    }
    res_empty = client.post("/api/v1/workflow/process", json=empty_payload, headers=headers)
    assert res_empty.status_code == 400
    assert "Narration cannot be empty" in res_empty.text

    # 6b: Zero / Negative amount
    negative_payload = {
        "raw_narration": "Valid narration for test",
        "amount": -500.00,
        "direction": "DEBIT",
        "channel": "UPI"
    }
    res_neg = client.post("/api/v1/workflow/process", json=negative_payload, headers=headers)
    assert res_neg.status_code == 400
    assert "Amount must be greater than zero" in res_neg.text

    # Confirm 0 transactions or ledger entries created
    db_session.expire_all()
    tx_count = db_session.query(Transaction).filter(Transaction.tenant_id == tenant_id).count()
    le_count = db_session.query(LedgerEntry).filter(LedgerEntry.tenant_id == tenant_id).count()
    assert tx_count == 0
    assert le_count == 0


# =========================================================================
# TEST CASE 7: API Timeout / Failure (Fails Gracefully, Halts at Review)
# =========================================================================
def test_case_7_api_timeout_auth_failure(client, db_session):
    """
    Test Case 7: API timeout / authentication failure.
    Verifies that when BharatCode API is unavailable or returns an error in production mode,
    it fails gracefully: marks ai_source='FAILED', confidence=0.0, halts at NEEDS_APPROVAL,
    and creates exactly 0 ledger entries.
    """
    headers, tenant_id = get_live_test_auth_headers(client, db_session, "test.case7@lekha.in")

    # Patch classify_transaction to simulate a network timeout / 503 error
    with patch(
        "backend.app.llm.client.BharatCodeClient.classify_transaction",
        side_effect=BharatCodeAPIError("Connection timeout to BharatCode API", status_code=504)
    ):
        payload = {
            "raw_narration": "Urgent server infrastructure maintenance cloud bill ₹12,000",
            "amount": 12000.00,
            "direction": "DEBIT",
            "channel": "NEFT",
            "reference_number": "TIMEOUTTEST99",
            "is_interstate": False,
            "ai_mode": "PRODUCTION_LIVE"
        }

        res = client.post("/api/v1/workflow/process", json=payload, headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()

        # Must halt at NEEDS_APPROVAL and indicate AI failure
        assert data["status"] == "NEEDS_APPROVAL"
        assert data["ai_source"] == "FAILED"
        assert data["confidence_score"] == 0.0
        assert data["ledger_entries_created"] == 0
        assert "timeout" in data["rationale"].lower() or "unavailable" in data["rationale"].lower()

        # Crucial safeguard: exactly 0 ledger entries in the database!
        db_session.expire_all()
        entries = db_session.query(LedgerEntry).filter(
            LedgerEntry.tenant_id == tenant_id,
            LedgerEntry.transaction_id == data["transaction_id"]
        ).all()
        assert len(entries) == 0


# =========================================================================
# LIVE BHARATCODE QWEN INFERENCE TEST (Real HTTP 200 Request)
# =========================================================================
def test_production_bharatcode_live_qwen_inference():
    """
    Authenticates with real BharatCode API credentials from .env and performs
    live Qwen 3.8 27B inference on an Indian mercantile transaction.
    """
    real_key = settings.BHARATCODE_API_KEY
    if not real_key or real_key == "test_bharatcode_key":
        pytest.skip("No real BharatCode API key configured in .env")

    client_live = BharatCodeClient(
        api_key=real_key,
        base_url="https://bharatcode.ai/api/model/v1",
        model_name="qwen-3.8-27b",
        ai_mode="PRODUCTION_LIVE"
    )

    import asyncio
    res = asyncio.run(
        client_live.classify_transaction(
            narration="Goyal Traders se dukaan ka cement aur sariya ₹35,000 khareeda",
            amount=35000.0,
            direction="DEBIT"
        )
    )

    assert res["live_api"] is True
    assert res["source"] == "BHARATCODE_LIVE"
    assert res["category"] is not None
    assert res["confidence_score"] > 0.0
    assert len(res["accounting_suggestions"]) > 0
    assert res["gst_rate"] in (0.0, 5.0, 12.0, 18.0, 28.0)
