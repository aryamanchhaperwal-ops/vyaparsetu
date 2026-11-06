import pytest

def get_auth_header(client, email="saas.test@kirana.in"):
    login_data = {
        "username": email,
        "password": "SecurePassword@123"
    }
    res = client.post("/api/v1/auth/login", data=login_data)
    if res.status_code != 200:
        reg_payload = {
            "email": email,
            "password": "SecurePassword@123",
            "full_name": "SaaS Test Merchant",
            "business_name": "SaaS Kirana Mart",
            "state_code": "27"
        }
        res = client.post("/api/v1/auth/register", json=reg_payload)
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_rag_assistant_qa(client):
    headers = get_auth_header(client)
    res = client.post("/api/v1/rag/ask", json={
        "query": "What are the rules and blocked credits under Section 17(5)?",
        "language": "Hinglish"
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "Section 17(5)" in data["answer"]
    assert len(data["citations"]) > 0
    assert data["grounded"] is True
    assert data["llm_provider"] == "BharatCode Hosted API"

def test_cashflow_and_credit_insights(client):
    headers = get_auth_header(client)
    
    # Ingest synthetic bank data first
    client.post("/api/v1/ingestion/synthetic?count=15", headers=headers)

    # 1. Cash flow analytics
    cf_res = client.get("/api/v1/analytics/cashflow", headers=headers)
    assert cf_res.status_code == 200
    cf = cf_res.json()
    assert "total_inflows" in cf
    assert "total_outflows" in cf
    assert "net_cash_flow" in cf
    assert "cash_runway_months" in cf

    # 2. Credit health
    credit_res = client.get("/api/v1/analytics/credit-health", headers=headers)
    assert credit_res.status_code == 200
    credit = credit_res.json()
    assert credit["indicative_credit_score"] > 0
    assert "credit_grade" in credit
    assert "indicative_working_capital_limit" in credit
    assert "score_factors" in credit

def test_saas_usage_and_subscription_upgrade(client):
    headers = get_auth_header(client)

    # 1. Fetch current usage
    usage_res = client.get("/api/v1/subscription/usage", headers=headers)
    assert usage_res.status_code == 200
    usage = usage_res.json()
    assert usage["subscription_plan"] in ("FREE", "PRO")

    # 2. Upgrade plan to PRO
    up_res = client.post("/api/v1/subscription/upgrade", json={"plan": "PRO"}, headers=headers)
    assert up_res.status_code == 200
    assert up_res.json()["new_plan"] == "PRO"

    # 3. Verify audit log was recorded
    audit_res = client.get("/api/v1/subscription/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert any(l["action"] == "UPGRADE_SUBSCRIPTION_PLAN" for l in logs)
