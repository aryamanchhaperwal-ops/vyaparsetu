import pytest

def register_and_get_auth(client, email: str, business_name: str, country_code: str = "IN", base_currency: str = "INR"):
    payload = {
        "email": email,
        "password": "SecurePassword@123",
        "full_name": email.split("@")[0].title(),
        "business_name": business_name,
        "state_code": "27"
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    token = data["access_token"]
    
    # Fetch tenant ID
    headers = {"Authorization": f"Bearer {token}"}
    ws = client.get("/api/v1/auth/workspaces", headers=headers).json()
    tenant_id = ws[0]["tenant"]["id"]
    return token, tenant_id, headers

def test_workspace_creation_with_global_settings(client):
    token, tenant_id, headers = register_and_get_auth(
        client,
        email="global.founder@saas.com",
        business_name="Global Exports LLC",
        country_code="US",
        base_currency="USD"
    )

    # 1. Update settings to global US parameters
    patch_payload = {
        "country_code": "US",
        "tax_jurisdiction": "US_SALES_TAX",
        "base_currency": "USD",
        "currency_symbol": "$",
        "financial_year_start_month": 1,
        "timezone": "America/New_York"
    }
    patch_res = client.patch(
        "/api/v1/tenants/current/settings",
        json=patch_payload,
        headers={**headers, "X-Tenant-ID": tenant_id}
    )
    assert patch_res.status_code == 200
    t = patch_res.json()
    assert t["country_code"] == "US"
    assert t["base_currency"] == "USD"
    assert t["currency_symbol"] == "$"
    assert t["financial_year_start_month"] == 1
    assert t["timezone"] == "America/New_York"

def test_multi_business_accountant_workflow(client):
    # Business 1 (Owner 1)
    _, t1_id, o1_headers = register_and_get_auth(
        client, "owner1@kirana.in", "Dukaan 1 - Retail"
    )
    # Business 2 (Owner 2)
    _, t2_id, o2_headers = register_and_get_auth(
        client, "owner2@hardware.in", "Hardware 2 - Wholesale"
    )

    # Both businesses invite the same CA / Accountant
    accountant_email = "ca.mukesh@finadvisors.in"
    inv1 = client.post(
        f"/api/v1/tenants/{t1_id}/invite",
        json={"email": accountant_email, "role": "ACCOUNTANT"},
        headers={**o1_headers, "X-Tenant-ID": t1_id}
    )
    assert inv1.status_code == 201

    inv2 = client.post(
        f"/api/v1/tenants/{t2_id}/invite",
        json={"email": accountant_email, "role": "ACCOUNTANT"},
        headers={**o2_headers, "X-Tenant-ID": t2_id}
    )
    assert inv2.status_code == 201

    # Login as Accountant
    ca_login = client.post("/api/v1/auth/login", data={
        "username": accountant_email,
        "password": "VyaparSetu@Invite2026"
    })
    assert ca_login.status_code == 200
    ca_token = ca_login.json()["access_token"]
    ca_headers = {"Authorization": f"Bearer {ca_token}"}

    # Accountant sees both client businesses in their workspace selector
    workspaces = client.get("/api/v1/auth/workspaces", headers=ca_headers).json()
    assert len(workspaces) >= 2
    assert any(w["tenant"]["id"] == t1_id and w["role"] == "ACCOUNTANT" for w in workspaces)
    assert any(w["tenant"]["id"] == t2_id and w["role"] == "ACCOUNTANT" for w in workspaces)

def test_role_based_access_control_rbac(client):
    _, tenant_id, owner_headers = register_and_get_auth(
        client, "retail.owner@kirana.in", "Apex Mart"
    )

    # Owner invites Employee
    emp_email = "staff.karan@kirana.in"
    inv_emp = client.post(
        f"/api/v1/tenants/{tenant_id}/invite",
        json={"email": emp_email, "role": "EMPLOYEE"},
        headers={**owner_headers, "X-Tenant-ID": tenant_id}
    )
    assert inv_emp.status_code == 201

    # Login as Employee
    emp_login = client.post("/api/v1/auth/login", data={
        "username": emp_email,
        "password": "VyaparSetu@Invite2026"
    })
    emp_token = emp_login.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}", "X-Tenant-ID": tenant_id}

    # 1. Employee CAN view transactions
    emp_tx = client.get("/api/v1/transactions", headers=emp_headers)
    assert emp_tx.status_code == 200

    # 2. Employee CANNOT file simulated GST return (Requires OWNER, ADMIN or ACCOUNTANT)
    emp_gst_file = client.post("/api/v1/gst/simulate-filing", json={
        "period": "2026-11",
        "report_type": "GSTR3B"
    }, headers=emp_headers)
    assert emp_gst_file.status_code == 403
    assert "Permission denied" in emp_gst_file.json()["detail"]

    # 3. Employee CANNOT upgrade subscription plan (Requires OWNER or ADMIN)
    emp_upgrade = client.post("/api/v1/subscription/upgrade", json={
        "plan": "ENTERPRISE"
    }, headers=emp_headers)
    assert emp_upgrade.status_code == 403
    assert "Permission denied" in emp_upgrade.json()["detail"]

    # 4. Employee CANNOT invite new members
    emp_invite = client.post(f"/api/v1/tenants/{tenant_id}/invite", json={
        "email": "hacker@evil.com",
        "role": "ADMIN"
    }, headers=emp_headers)
    assert emp_invite.status_code == 403

def test_strict_cross_tenant_data_isolation(client):
    # Setup Tenant A with confidential transaction
    _, tenant_a_id, a_headers = register_and_get_auth(
        client, "founder.a@co.in", "Company Alpha"
    )
    a_tx = client.post("/api/v1/transactions", json={
        "transaction_date": "2026-11-04",
        "description": "Confidential Alpha Patent Acquisition",
        "raw_narration": "Transfer for patent",
        "amount": 250000.00,
        "type": "DEBIT",
        "channel": "RTGS",
        "category": "Capital Asset"
    }, headers={**a_headers, "X-Tenant-ID": tenant_a_id}).json()
    a_tx_id = a_tx["id"]

    # Setup Tenant B
    _, tenant_b_id, b_headers = register_and_get_auth(
        client, "competitor.b@co.in", "Company Beta Competitor"
    )

    # 1. Tenant B tries to pass Tenant A's ID in header -> 403 Forbidden
    b_snoop_header = {**b_headers, "X-Tenant-ID": tenant_a_id}
    res_forbidden = client.get("/api/v1/transactions", headers=b_snoop_header)
    assert res_forbidden.status_code == 403
    assert "Access forbidden" in res_forbidden.json()["detail"]

    # 2. Tenant B tries to fetch Tenant A's transaction directly by ID -> 404 Not Found
    b_normal_header = {**b_headers, "X-Tenant-ID": tenant_b_id}
    res_direct_tx = client.get(f"/api/v1/transactions/{a_tx_id}", headers=b_normal_header)
    assert res_direct_tx.status_code == 404

    # 3. Tenant B's transaction list does NOT contain Tenant A's transactions
    b_list = client.get("/api/v1/transactions", headers=b_normal_header).json()
    assert not any(t["id"] == a_tx_id for t in b_list)

