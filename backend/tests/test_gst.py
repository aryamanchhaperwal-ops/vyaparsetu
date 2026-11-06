import pytest
from decimal import Decimal
from backend.app.services.gst_calculator import (
    calculate_transaction_gst,
    is_interstate_supply,
    is_itc_blocked_under_section_17_5,
    round_to_rupee
)

def get_auth_header(client, email="gst.test@kirana.in"):
    login_data = {
        "username": email,
        "password": "SecurePassword@123"
    }
    res = client.post("/api/v1/auth/login", data=login_data)
    if res.status_code != 200:
        reg_payload = {
            "email": email,
            "password": "SecurePassword@123",
            "full_name": "GST Merchant",
            "business_name": "GST Enterprises",
            "state_code": "27"  # Maharashtra
        }
        res = client.post("/api/v1/auth/register", json=reg_payload)
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_place_of_supply_evaluation():
    # Same state (Intra-state)
    assert not is_interstate_supply("27", "27")
    # Different state (Inter-state)
    assert is_interstate_supply("27", "24")
    assert is_interstate_supply("29", "07")

def test_blocked_itc_under_section_17_5():
    # Food and pantry is blocked
    assert is_itc_blocked_under_section_17_5("Office & Miscellaneous", "Staff Tea & Coffee Pantry")
    assert is_itc_blocked_under_section_17_5("Restaurant Food Bill", None)
    # Raw materials and rent are NOT blocked
    assert not is_itc_blocked_under_section_17_5("Raw Materials", "Cement and Steel")
    assert not is_itc_blocked_under_section_17_5("Rent & Utilities", "Shop Rent")

def test_section_170_statutory_rounding():
    # Half-up rounding to nearest rupee
    assert round_to_rupee(Decimal("145.49")) == Decimal("145")
    assert round_to_rupee(Decimal("145.50")) == Decimal("146")
    assert round_to_rupee(Decimal("145.51")) == Decimal("146")

def test_gst_compute_api_endpoint(client):
    res = client.post("/api/v1/gst/compute", json={
        "amount": 10000.0,
        "rate_percent": 18.0,
        "is_interstate": False,
        "is_inclusive": False
    })
    assert res.status_code == 200
    data = res.json()
    assert data["taxable_value"] == "10000.00"
    assert data["cgst"] == "900.00"
    assert data["sgst"] == "900.00"
    assert data["igst"] == "0.00"
    assert data["total_tax"] == "1800.00"

def test_simulated_gstr1_and_gstr3b_reports(client):
    headers = get_auth_header(client)

    # Ingest synthetic bank data
    client.post("/api/v1/ingestion/synthetic?count=10", headers=headers)

    # 1. Fetch GSTR-1
    period = "2026-11"
    gstr1_res = client.get(f"/api/v1/gst/gstr1/{period}", headers=headers)
    assert gstr1_res.status_code == 200
    gstr1 = gstr1_res.json()
    assert gstr1["report_type"] == "GSTR1"
    assert "table_4_b2b" in gstr1
    assert "table_7_b2c" in gstr1
    assert "table_12_hsn" in gstr1
    assert "SIMULATED GSTR-1 REPORT" in gstr1["compliance_notice"]

    # 2. Fetch GSTR-3B
    gstr3b_res = client.get(f"/api/v1/gst/gstr3b/{period}", headers=headers)
    assert gstr3b_res.status_code == 200
    gstr3b = gstr3b_res.json()
    assert gstr3b["report_type"] == "GSTR3B"
    assert "table_3_1_outward_supplies" in gstr3b
    assert "table_4_eligible_itc" in gstr3b
    assert "table_6_1_payment_of_tax" in gstr3b

    # 3. Simulate return filing
    file_res = client.post("/api/v1/gst/simulate-filing", json={
        "period": period,
        "report_type": "GSTR3B"
    }, headers=headers)
    assert file_res.status_code == 200
    file_data = file_res.json()
    assert file_data["status"] == "SIMULATED_FILED"
    assert "arn" in file_data
    assert "TEST SANDBOX ONLY" in file_data["notice"]

