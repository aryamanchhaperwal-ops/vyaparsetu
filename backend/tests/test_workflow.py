import pytest

def get_auth_header(client, email="workflow.test@kirana.in"):
    login_data = {
        "username": email,
        "password": "SecurePassword@123"
    }
    res = client.post("/api/v1/auth/login", data=login_data)
    if res.status_code != 200:
        reg_payload = {
            "email": email,
            "password": "SecurePassword@123",
            "full_name": "Workflow Merchant",
            "business_name": "Workflow Kirana Store",
            "state_code": "27"
        }
        res = client.post("/api/v1/auth/register", json=reg_payload)
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_langgraph_high_confidence_auto_post(client):
    headers = get_auth_header(client)
    payload = {
        "raw_narration": "Paid 23600 to Sharma cement & hardware for sariya construction",
        "amount": 23600.00,
        "direction": "DEBIT",
        "channel": "UPI",
        "reference_number": "UTR9988112233"
    }
    res = client.post("/api/v1/workflow/process", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "CONFIRMED"
    assert data["category"] == "Raw Materials"
    assert data["confidence_score"] >= 0.85
    assert data["ledger_entries_created"] >= 2

def test_langgraph_low_confidence_human_approval_flow(client):
    headers = get_auth_header(client)
    
    # 1. Ambiguous transaction triggers human-in-the-loop
    payload = {
        "raw_narration": "payment to anil",
        "amount": 4500.00,
        "direction": "DEBIT",
        "channel": "UPI",
        "reference_number": "UTR5544332211"
    }
    res = client.post("/api/v1/workflow/process", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "NEEDS_APPROVAL"
    tx_id = data["transaction_id"]

    # 2. Check that it appears in the approval queue
    queue_res = client.get("/api/v1/workflow/approval-queue", headers=headers)
    assert queue_res.status_code == 200
    queue = queue_res.json()
    assert any(item["id"] == tx_id for item in queue)

    # 3. Merchant provides correction/approval
    approval_payload = {
        "transaction_id": tx_id,
        "category": "Office & Miscellaneous",
        "sub_category": "Staff Welfare & Tea",
        "gst_rate": 5.0,
        "counterparty_name": "Anil Tea Vendor",
        "human_feedback": "Payment was for monthly staff tea and pantry bill"
    }
    approve_res = client.post("/api/v1/workflow/approve", json=approval_payload, headers=headers)
    assert approve_res.status_code == 200
    app_data = approve_res.json()
    assert app_data["status"] == "APPROVED_AND_POSTED"
    assert app_data["category"] == "Office & Miscellaneous"

    # 4. Check that it is removed from the approval queue
    queue_res2 = client.get("/api/v1/workflow/approval-queue", headers=headers)
    assert not any(item["id"] == tx_id for item in queue_res2.json())

def test_duplicate_rejection(client):
    headers = get_auth_header(client)
    payload = {
        "raw_narration": "Paid 5000 to Sharma cement supplier for cement bags",
        "amount": 5000.00,
        "direction": "DEBIT",
        "channel": "NEFT",
        "reference_number": "DUPLICATE_UTR_123"
    }
    # First time: processes and confirms
    res1 = client.post("/api/v1/workflow/process", json=payload, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "CONFIRMED"

    # Second time with same reference: rejected as duplicate
    res2 = client.post("/api/v1/workflow/process", json=payload, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == "DUPLICATE_REJECTED"
