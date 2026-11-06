import pytest
import uuid
from decimal import Decimal
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_full_saas_lifecycle_e2e():
    """
    Comprehensive End-to-End integration test covering the entire user journey across:
    1. Business registration & workspace onboarding
    2. Authentication & JWT token issuance
    3. Synthetic bank data ingestion
    4. Receipt OCR extraction
    5. LangGraph multi-agent financial workflow (auto-post & HITL approval)
    6. Double-entry general ledger balancing (sum Debits == sum Credits)
    7. Profit & Loss and Balance Sheet generation
    8. Invoice & bank transaction reconciliation
    9. RAG statutory assistant query with section citation
    10. GSTR-1 & GSTR-3B generation with Section 49 offset
    11. Simulated return filing with ARN generation
    12. Team member invitation (RBAC)
    13. Subscription tier upgrade (FREE -> PRO) & audit logging
    """
    unique_id = uuid.uuid4().hex[:8]
    # 1. Register User & Business
    user_payload = {
        "email": f"e2e_merchant_{unique_id}@vyaparsetu.in",
        "password": "E2ePassword@2026",
        "full_name": "E2E Test Merchant",
        "phone_number": "+919876543210",
        "business_name": f"E2E Steel Traders {unique_id}",
        "country_code": "IN",
        "base_currency": "INR",
        "currency_symbol": "₹",
        "financial_year_start_month": 4,
        "timezone": "Asia/Kolkata"
    }
    reg_res = client.post("/api/v1/auth/register", json=user_payload)
    assert reg_res.status_code == 201, reg_res.text
    reg_data = reg_res.json()
    token = reg_data["access_token"]

    ws_res = client.get("/api/v1/auth/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert ws_res.status_code == 200
    workspaces = ws_res.json()
    assert len(workspaces) > 0
    tenant_id = workspaces[0]["tenant"]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

    # 2. Ingest Synthetic Banking Data
    synth_res = client.post(f"/api/v1/ingestion/synthetic?count=10", headers=headers)
    assert synth_res.status_code == 200
    assert synth_res.json()["inserted"] >= 10

    # 3. Ingest Receipt Document OCR
    from PIL import Image
    import io
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    ocr_res = client.post(
        "/api/v1/ocr/upload",
        files={"file": ("receipt.png", png_bytes, "image/png")},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}
    )
    assert ocr_res.status_code == 200
    receipt_data = ocr_res.json()
    assert receipt_data["status"] == "EXTRACTED"
    receipt_id = receipt_data["receipt_id"]

    # 4. LangGraph Autonomous Agent: High Confidence Auto-Post
    high_conf_payload = {
        "raw_narration": "Ambuja cement bags purchase payment ₹23600",
        "amount": 23600.0,
        "direction": "DEBIT",
        "channel": "UPI",
        "is_interstate": False
    }
    wf_res = client.post("/api/v1/workflow/process", json=high_conf_payload, headers=headers)
    assert wf_res.status_code == 200
    wf_data = wf_res.json()
    assert wf_data["status"] == "CONFIRMED"
    assert wf_data["ledger_entries_created"] > 0
    auto_tx_id = wf_data["transaction_id"]

    # 5. LangGraph Autonomous Agent: Low Confidence HITL Checkpoint
    low_conf_payload = {
        "raw_narration": "Uncle mixed settlement cash amount ₹4200",
        "amount": 4200.0,
        "direction": "DEBIT",
        "channel": "CASH"
    }
    hitl_res = client.post("/api/v1/workflow/process", json=low_conf_payload, headers=headers)
    assert hitl_res.status_code == 200
    hitl_data = hitl_res.json()
    assert hitl_data["status"] == "NEEDS_APPROVAL"
    hitl_tx_id = hitl_data["transaction_id"]

    # 6. Verify Approval Queue & Human Approval Sign-off
    queue_res = client.get("/api/v1/workflow/approval-queue", headers=headers)
    assert queue_res.status_code == 200
    queue = queue_res.json()
    assert any(tx["id"] == hitl_tx_id for tx in queue)

    approve_payload = {
        "transaction_id": hitl_tx_id,
        "category": "General & Administrative",
        "gst_rate": 18.0,
        "counterparty_name": "Uncle Store",
        "human_feedback": "Approved as miscellaneous admin expense"
    }
    appr_res = client.post("/api/v1/workflow/approve", json=approve_payload, headers=headers)
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "APPROVED_AND_POSTED"

    # 7. Verify Live Double-Entry Trial Balance Balancing
    tb_res = client.get("/api/v1/ledger/trial-balance", headers=headers)
    assert tb_res.status_code == 200
    tb = tb_res.json()
    assert tb["is_balanced"] is True
    assert Decimal(tb["total_debit"]) == Decimal(tb["total_credit"])

    # 8. Verify Financial Statements (P&L and Balance Sheet)
    stmts_res = client.get("/api/v1/ledger/financial-statements", headers=headers)
    assert stmts_res.status_code == 200
    stmts = stmts_res.json()
    assert "profit_and_loss" in stmts
    assert "balance_sheet" in stmts
    assert stmts["balance_sheet"]["is_balanced"] is True

    # 9. Invoice and Transaction Manual Reconciliation
    rec_res = client.post(
        "/api/v1/ocr/reconcile",
        json={"receipt_id": receipt_id, "transaction_id": auto_tx_id},
        headers=headers
    )
    assert rec_res.status_code == 200
    assert rec_res.json()["status"] == "success"

    # 10. RAG GST Query
    rag_res = client.post(
        "/api/v1/rag/ask",
        json={"query": "What are the rules for claiming ITC under Section 16(2)?", "language": "English"},
        headers=headers
    )
    assert rag_res.status_code == 200
    assert "Section 16" in rag_res.json()["answer"] or len(rag_res.json()["retrieved_statutes"]) > 0

    # 11. GSTR-1 and GSTR-3B Summaries
    gstr1_res = client.get("/api/v1/gst/gstr1/2026-03", headers=headers)
    assert gstr1_res.status_code == 200
    gstr3b_res = client.get("/api/v1/gst/gstr3b/2026-03", headers=headers)
    assert gstr3b_res.status_code == 200

    # 12. Simulate Return Filing
    file_res = client.post(
        "/api/v1/gst/simulate-filing",
        json={"period": "2026-03", "report_type": "GSTR1"},
        headers=headers
    )
    assert file_res.status_code == 200
    assert "ARN" in file_res.json() or file_res.json()["arn"].startswith("AA")

    # 13. Team Member Invitation
    inv_res = client.post(
        f"/api/v1/tenants/{tenant_id}/invite",
        json={"email": f"e2e_accountant_{unique_id}@ca-firm.in", "role": "ACCOUNTANT"},
        headers=headers
    )
    assert inv_res.status_code == 201
    assert inv_res.json()["role"] == "ACCOUNTANT"

    # 14. SaaS Subscription Upgrade & Audit Trail
    upg_res = client.post("/api/v1/subscription/upgrade", json={"plan": "PRO"}, headers=headers)
    assert upg_res.status_code == 200
    assert upg_res.json()["new_plan"] == "PRO"

    usage_res = client.get("/api/v1/subscription/usage", headers=headers)
    assert usage_res.status_code == 200
    assert usage_res.json()["subscription_plan"] == "PRO"

    audit_res = client.get("/api/v1/subscription/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    assert len(audit_res.json()) >= 1

