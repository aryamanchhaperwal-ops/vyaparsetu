import requests

BASE_URL = "http://127.0.0.1:8000"

def test_two_business_tenant_isolation():
    print("=== TESTING TWO SEPARATE DEMO BUSINESSES FOR STRICT TENANT ISOLATION ===")
    
    # 1. Register Business A
    biz_a_payload = {
        "email": "sharma_biz_a@vyaparsetu.in",
        "password": "Password@2026",
        "full_name": "Rajesh Sharma",
        "phone_number": "+919876543201",
        "business_name": "Sharma Kirana & Hardware",
        "country_code": "IN",
        "base_currency": "INR",
        "currency_symbol": "₹",
        "financial_year_start_month": 4,
        "timezone": "Asia/Kolkata"
    }
    res_a = requests.post(f"{BASE_URL}/api/v1/auth/register", json=biz_a_payload)
    if res_a.status_code == 400: # Already registered
        res_a = requests.post(f"{BASE_URL}/api/v1/auth/login", data={"username": biz_a_payload["email"], "password": biz_a_payload["password"]})
    assert res_a.status_code in (200, 201), res_a.text
    token_a = res_a.json()["access_token"]
    ws_a = requests.get(f"{BASE_URL}/api/v1/auth/workspaces", headers={"Authorization": f"Bearer {token_a}"}).json()
    tenant_a_id = ws_a[0]["tenant"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Tenant-ID": tenant_a_id}
    print(f"  ✓ Business A registered: '{ws_a[0]['tenant']['name']}' (ID: {tenant_a_id})")

    # 2. Register Business B
    biz_b_payload = {
        "email": "patel_biz_b@vyaparsetu.in",
        "password": "Password@2026",
        "full_name": "Suresh Patel",
        "phone_number": "+919876543202",
        "business_name": "Patel Electronics & Mobile Store",
        "country_code": "IN",
        "base_currency": "INR",
        "currency_symbol": "₹",
        "financial_year_start_month": 4,
        "timezone": "Asia/Kolkata"
    }
    res_b = requests.post(f"{BASE_URL}/api/v1/auth/register", json=biz_b_payload)
    if res_b.status_code == 400: # Already registered
        res_b = requests.post(f"{BASE_URL}/api/v1/auth/login", data={"username": biz_b_payload["email"], "password": biz_b_payload["password"]})
    assert res_b.status_code in (200, 201), res_b.text
    token_b = res_b.json()["access_token"]
    ws_b = requests.get(f"{BASE_URL}/api/v1/auth/workspaces", headers={"Authorization": f"Bearer {token_b}"}).json()
    tenant_b_id = ws_b[0]["tenant"]["id"]
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Tenant-ID": tenant_b_id}
    print(f"  ✓ Business B registered: '{ws_b[0]['tenant']['name']}' (ID: {tenant_b_id})")

    # 3. Create a unique transaction in Business A
    tx_a_payload = {
        "transaction_date": "2026-03-01",
        "description": "Sharma exclusive cement procurement",
        "raw_narration": "Exclusive purchase for Sharma Kirana only ₹77,777",
        "amount": 77777.0,
        "type": "DEBIT",
        "channel": "NEFT",
        "category": "Raw Materials",
        "tax_rate": 18.0,
        "reference_number": "SHARMA-REF-777"
    }
    post_tx_a = requests.post(f"{BASE_URL}/api/v1/transactions", json=tx_a_payload, headers=headers_a)
    assert post_tx_a.status_code in (200, 201), post_tx_a.text
    tx_a_id = post_tx_a.json()["id"]
    print(f"  ✓ Created private transaction in Business A (ID: {tx_a_id}, Ref: SHARMA-REF-777)")

    # 4. Verify Business A sees its transaction
    txs_a = requests.get(f"{BASE_URL}/api/v1/transactions", headers=headers_a).json()
    assert any(t["id"] == tx_a_id for t in txs_a), "Business A should see its own transaction"
    print("  ✓ Business A successfully fetched its transaction.")

    # 5. Verify Business B cannot see Business A's transaction in its transaction list
    txs_b = requests.get(f"{BASE_URL}/api/v1/transactions", headers=headers_b).json()
    assert not any(t["id"] == tx_a_id or t.get("reference_number") == "SHARMA-REF-777" for t in txs_b), \
        "SECURITY VIOLATION: Business B must NOT see Business A's transactions!"
    print("  ✓ Proved: Business B's transaction ledger contains 0 records from Business A.")

    # 6. Verify Business B cannot query or spoof Business A's tenant ID
    spoof_headers = {"Authorization": f"Bearer {token_b}", "X-Tenant-ID": tenant_a_id}
    spoof_res = requests.get(f"{BASE_URL}/api/v1/transactions", headers=spoof_headers)
    assert spoof_res.status_code == 403, f"Expected 403 Forbidden for cross-tenant spoofing, got {spoof_res.status_code}"
    print("  ✓ Proved: Cross-tenant spoofing attempt (User B providing X-Tenant-ID: Tenant A) rejected with HTTP 403 Forbidden.")

    print("\n=== STRICT MULTI-TENANT ISOLATION FULLY VERIFIED! ===")

if __name__ == "__main__":
    test_two_business_tenant_isolation()
