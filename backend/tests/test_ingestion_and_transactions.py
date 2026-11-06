import io
import pytest

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

def test_generate_and_ingest_synthetic_data(client):
    headers = get_auth_header(client)
    res = client.post("/api/v1/ingestion/synthetic?count=15", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["inserted"] > 0
    assert "SIMULATED TEST DATA" in data["notice"]

    # Verify transactions are in the database
    tx_res = client.get("/api/v1/transactions", headers=headers)
    assert tx_res.status_code == 200
    tx_list = tx_res.json()
    assert len(tx_list) >= data["inserted"]

def test_csv_upload_and_deduplication(client):
    headers = get_auth_header(client)
    sample_csv = """Date,Narration,Chq/Ref No,Value Dt,Withdrawal Amt,Deposit Amt,Closing Balance
01/11/2026,UPI/UTR1122334455/DR/sharma cement/raw materials,UTR1122334455,01/11/2026,18500.00,,131500.00
02/11/2026,UPI/UTR9988776655/CR/retail customer sale,UTR9988776655,02/11/2026,,4500.00,136000.00
"""
    files = {"file": ("hdfc_statement.csv", io.BytesIO(sample_csv.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/v1/ingestion/csv", headers=headers, files=files)
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["inserted"] == 2
    assert upload_data["duplicates_skipped"] == 0

    # Upload exact same CSV again -> should detect 2 duplicates and insert 0
    files_again = {"file": ("hdfc_statement.csv", io.BytesIO(sample_csv.encode("utf-8")), "text/csv")}
    upload_res2 = client.post("/api/v1/ingestion/csv", headers=headers, files=files_again)
    assert upload_res2.status_code == 200
    data2 = upload_res2.json()
    assert data2["inserted"] == 0
    assert data2["duplicates_skipped"] == 2

def test_manual_transaction_creation(client):
    headers = get_auth_header(client)
    tx_payload = {
        "transaction_date": "2026-11-05",
        "description": "Counter Cash Purchase - 100 Packing Cartons",
        "raw_narration": "Paid cash 2400 for packing cartons",
        "amount": 2400.00,
        "type": "DEBIT",
        "channel": "CASH",
        "category": "Office & Miscellaneous",
        "tax_rate": 12.0
    }
    res = client.post("/api/v1/transactions", json=tx_payload, headers=headers)
    assert res.status_code == 201
    tx = res.json()
    assert tx["amount"] == "2400.00"
    assert tx["channel"] == "CASH"
    assert tx["type"] == "DEBIT"
