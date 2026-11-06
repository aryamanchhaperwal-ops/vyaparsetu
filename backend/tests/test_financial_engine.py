from decimal import Decimal
import pytest
from backend.app.services.financial_engine import compute_gst_split, round_paisa

def get_auth_header(client, email="ramesh.patel@kirana.in"):
    login_data = {
        "username": email,
        "password": "SecurePassword@123"
    }
    res = client.post("/api/v1/auth/login", data=login_data)
    if res.status_code != 200:
        reg_payload = {
            "email": email,
            "password": "SecurePassword@123",
            "full_name": "Ramesh Patel",
            "business_name": "Patel General Store",
            "state_code": "24"
        }
        res = client.post("/api/v1/auth/register", json=reg_payload)
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_deterministic_gst_split_math():
    # 1. 18% GST inclusive on 11800 -> taxable: 10000, cgst: 900, sgst: 900
    res = compute_gst_split(Decimal("11800.00"), Decimal("18.0"), is_interstate=False)
    assert res["taxable_value"] == Decimal("10000.00")
    assert res["cgst"] == Decimal("900.00")
    assert res["sgst"] == Decimal("900.00")
    assert res["igst"] == Decimal("0.00")
    assert res["taxable_value"] + res["cgst"] + res["sgst"] == Decimal("11800.00")

    # 2. 18% GST inclusive on 11800 Inter-state -> taxable: 10000, igst: 1800
    res_inter = compute_gst_split(Decimal("11800.00"), Decimal("18.0"), is_interstate=True)
    assert res_inter["taxable_value"] == Decimal("10000.00")
    assert res_inter["igst"] == Decimal("1800.00")
    assert res_inter["cgst"] == Decimal("0.00")
    assert res_inter["sgst"] == Decimal("0.00")
    assert res_inter["taxable_value"] + res_inter["igst"] == Decimal("11800.00")

    # 3. Odd amount with fractional paisa: 1253.77 @ 18%
    res_odd = compute_gst_split(Decimal("1253.77"), Decimal("18.0"), is_interstate=False)
    assert res_odd["taxable_value"] + res_odd["cgst"] + res_odd["sgst"] == Decimal("1253.77")

def test_ledger_posting_and_trial_balance(client):
    headers = get_auth_header(client, email="ledger.test@kirana.in")

    # 1. Create a Sales Revenue Transaction (Credit ₹59,000 with 18% GST)
    sale_tx = client.post("/api/v1/transactions", json={
        "transaction_date": "2026-11-01",
        "description": "Sale of 100 bags fertilizer to Farmer Cooperative",
        "raw_narration": "NEFT received from Farmer Cooperative",
        "amount": 59000.00,
        "type": "CREDIT",
        "channel": "NEFT",
        "category": "Sales Revenue",
        "tax_rate": 18.0
    }, headers=headers).json()

    # Post Sale to Ledger
    post_sale = client.post(f"/api/v1/ledger/post/{sale_tx['id']}?is_interstate=false", headers=headers)
    assert post_sale.status_code == 200
    sale_data = post_sale.json()
    assert sale_data["total_debit"] == sale_data["total_credit"] == "59000.00"

    # 2. Create an Expense Transaction (Debit ₹23,600 with 18% GST for Cement Purchase)
    expense_tx = client.post("/api/v1/transactions", json={
        "transaction_date": "2026-11-02",
        "description": "Purchase of cement bags from Sharma Cement Mart",
        "raw_narration": "UPI to Sharma Cement Mart",
        "amount": 23600.00,
        "type": "DEBIT",
        "channel": "UPI",
        "category": "Raw Materials",
        "tax_rate": 18.0
    }, headers=headers).json()

    # Post Expense to Ledger
    post_exp = client.post(f"/api/v1/ledger/post/{expense_tx['id']}?is_interstate=false", headers=headers)
    assert post_exp.status_code == 200
    exp_data = post_exp.json()
    assert exp_data["total_debit"] == exp_data["total_credit"] == "23600.00"

    # 3. Check Trial Balance
    tb_res = client.get("/api/v1/ledger/trial-balance", headers=headers)
    assert tb_res.status_code == 200
    tb = tb_res.json()
    assert tb["is_balanced"] is True
    assert tb["total_debit"] == tb["total_credit"]
