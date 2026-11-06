import pytest

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["project"] == "VyaparSetu"
    assert data["llm_provider"] == "BharatCode Hosted API"

def test_user_registration_and_automatic_tenant_creation(client):
    payload = {
        "email": "ramesh.patel@kirana.in",
        "password": "SecurePassword@123",
        "full_name": "Ramesh Patel",
        "phone_number": "+919811223344",
        "business_name": "Patel Provisions & General Store",
        "state_code": "24"  # Gujarat
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "ramesh.patel@kirana.in"

    # Verify workspace listing
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ws_res = client.get("/api/v1/auth/workspaces", headers=headers)
    assert ws_res.status_code == 200
    workspaces = ws_res.json()
    assert len(workspaces) == 1
    assert workspaces[0]["role"] == "OWNER"
    tenant = workspaces[0]["tenant"]
    assert tenant["name"] == "Patel Provisions & General Store"
    assert tenant["state_code"] == "24"
    assert tenant["simulated_gstin"].startswith("24")

def test_user_login(client):
    login_data = {
        "username": "ramesh.patel@kirana.in",
        "password": "SecurePassword@123"
    }
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["full_name"] == "Ramesh Patel"

def test_create_multiple_workspaces(client):
    # Login first
    login_data = {
        "username": "ramesh.patel@kirana.in",
        "password": "SecurePassword@123"
    }
    login_res = client.post("/api/v1/auth/login", data=login_data)
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a second business workspace (e.g. wholesale branch)
    ws_payload = {
        "name": "Patel Wholesale Depot",
        "trade_name": "Patel Wholesale",
        "state_code": "27",  # Maharashtra branch
        "business_category": "Wholesale FMCG",
        "turnover_tier": "Small (5-10 Cr)"
    }
    create_res = client.post("/api/v1/auth/workspaces", json=ws_payload, headers=headers)
    assert create_res.status_code == 201
    new_tenant = create_res.json()
    assert new_tenant["name"] == "Patel Wholesale Depot"
    assert new_tenant["state_code"] == "27"

    # List all workspaces
    ws_res = client.get("/api/v1/auth/workspaces", headers=headers)
    assert ws_res.status_code == 200
    workspaces = ws_res.json()
    assert len(workspaces) == 2

def test_tenant_context_isolation(client):
    # Register second user
    u2_payload = {
        "email": "vijay.kumar@tech.in",
        "password": "SecurePassword@456",
        "full_name": "Vijay Kumar",
        "business_name": "Kumar Electronics",
        "state_code": "29"  # Karnataka
    }
    u2_res = client.post("/api/v1/auth/register", json=u2_payload)
    u2_token = u2_res.json()["access_token"]
    u2_headers = {"Authorization": f"Bearer {u2_token}"}

    # Fetch Vijay's workspace
    u2_ws = client.get("/api/v1/auth/workspaces", headers=u2_headers).json()
    vijay_tenant_id = u2_ws[0]["tenant"]["id"]

    # Login as Ramesh
    login_data = {
        "username": "ramesh.patel@kirana.in",
        "password": "SecurePassword@123"
    }
    ramesh_token = client.post("/api/v1/auth/login", data=login_data).json()["access_token"]
    
    # Ramesh tries to access Vijay's tenant
    ramesh_bad_headers = {
        "Authorization": f"Bearer {ramesh_token}",
        "X-Tenant-ID": vijay_tenant_id
    }
    forbidden_res = client.get("/api/v1/tenants/current", headers=ramesh_bad_headers)
    assert forbidden_res.status_code == 403
    assert "Access forbidden" in forbidden_res.json()["detail"]
