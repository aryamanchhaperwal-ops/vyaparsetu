import pytest
import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.user import Tenant, User, Membership
from backend.app.models.transaction import Transaction
from backend.app.models.ledger import LedgerAccount
from backend.app.services.rag_service import classify_assistant_intent, answer_conversational_assistant

client = TestClient(app)

@pytest.fixture
def test_tenant_context():
    db = SessionLocal()
    tenant = db.query(Tenant).filter(Tenant.simulated_gstin == "27TESTCONV0001Z5").first()
    if not tenant:
        tenant = Tenant(
            name="Test Mercantile Enterprises",
            trade_name="Test Mercantile",
            simulated_gstin="27TESTCONV0001Z5",
            state_code="27",
            currency_symbol="₹"
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

    # Seed an account and transaction
    cash_acc = db.query(LedgerAccount).filter(
        LedgerAccount.tenant_id == tenant.id,
        LedgerAccount.code == "1010"
    ).first()
    if not cash_acc:
        cash_acc = LedgerAccount(
            tenant_id=tenant.id,
            code="1010",
            name="Cash in Hand",
            account_type="ASSET",
            balance=Decimal("50000.00")
        )
        db.add(cash_acc)

    tx = db.query(Transaction).filter(
        Transaction.tenant_id == tenant.id,
        Transaction.reference_number == "REF_TEST_CONV_01"
    ).first()
    if not tx:
        tx = Transaction(
            tenant_id=tenant.id,
            transaction_date=datetime.date(2026, 11, 1),
            description="Cement Purchase from Sharma",
            raw_narration="Sharma ji ko cement ke liye cash diya",
            amount=Decimal("15000.00"),
            type="DEBIT",
            channel="CASH",
            category="Raw Materials",
            reference_number="REF_TEST_CONV_01",
            counterparty_name="Sharma ji"
        )
        db.add(tx)

    db.commit()
    yield db, tenant
    db.close()

def test_intent_classification():
    # 1. Greetings
    assert classify_assistant_intent("Hi") == "CONVERSATION"
    assert classify_assistant_intent("Hello!") == "CONVERSATION"
    assert classify_assistant_intent("Namaste, how can you help me?") == "CONVERSATION"
    assert classify_assistant_intent("Good morning") == "CONVERSATION"

    # 2. Business Queries
    assert classify_assistant_intent("What is my total spend?") == "BUSINESS_QUERY"
    assert classify_assistant_intent("Who are my top vendors?") == "BUSINESS_QUERY"
    assert classify_assistant_intent("What is my current bank balance?") == "BUSINESS_QUERY"

    # 3. Accounting Guidance
    assert classify_assistant_intent("Explain the golden rules of double entry") == "ACCOUNTING_GUIDANCE"
    assert classify_assistant_intent("What is a trial balance and why does it balance?") == "ACCOUNTING_GUIDANCE"

    # 4. Analytics
    assert classify_assistant_intent("How is my cash flow runway looking?") == "ANALYTICS_INSIGHTS"

    # 5. GST RAG
    assert classify_assistant_intent("What are the Section 16(2) ITC conditions?") == "GST_RAG"
    assert classify_assistant_intent("Can I claim ITC on motor cars under Section 17(5)?") == "GST_RAG"

@pytest.mark.asyncio
async def test_greeting_never_triggers_gst_statutes(test_tenant_context):
    db, tenant = test_tenant_context
    resp = await answer_conversational_assistant("Hi, good morning!", db, tenant)

    assert resp["intent"] == "CONVERSATION"
    assert resp["citations"] == []
    assert "Section 16" not in resp["answer"]
    assert "Namaste" in resp["answer"]
    assert tenant.name in resp["answer"]

@pytest.mark.asyncio
async def test_business_data_query_deterministic(test_tenant_context):
    db, tenant = test_tenant_context
    resp = await answer_conversational_assistant("What is my total spend and cash balance?", db, tenant)

    assert resp["intent"] == "BUSINESS_QUERY"
    assert resp["citations"] == []
    assert "Total Outflows / Spend" in resp["answer"]
    assert "Cash in Hand [1010]" in resp["answer"]
    assert resp["tenant_data"]["total_debit"] >= 15000.0

@pytest.mark.asyncio
async def test_accounting_guidance(test_tenant_context):
    db, tenant = test_tenant_context
    resp = await answer_conversational_assistant("Explain the three golden rules of double entry", db, tenant)

    assert resp["intent"] == "ACCOUNTING_GUIDANCE"
    assert "Golden Rules of Accounting" in resp["answer"]
    assert "Debit what comes in" in resp["answer"]
