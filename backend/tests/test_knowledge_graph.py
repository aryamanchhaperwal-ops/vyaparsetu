import pytest
import datetime
from decimal import Decimal
from backend.app.core.database import SessionLocal
from backend.app.models.user import Tenant, User, Membership
from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt
from backend.app.models.ledger import LedgerAccount
from backend.app.services.knowledge_graph import build_financial_knowledge_graph

@pytest.fixture
def test_kg_tenant():
    db = SessionLocal()
    tenant = db.query(Tenant).filter(Tenant.simulated_gstin == "27TESTGRAPH001Z9").first()
    if not tenant:
        tenant = Tenant(
            name="Apex Engineering MSME",
            simulated_gstin="27TESTGRAPH001Z9",
            state_code="27",
            currency_symbol="₹"
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

    # Seed User & Membership
    user = db.query(User).filter(User.email == "owner_kg@apex.com").first()
    if not user:
        user = User(
            email="owner_kg@apex.com",
            full_name="Rajesh Patel",
            password_hash="fakehash"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    mem = db.query(Membership).filter(Membership.tenant_id == tenant.id, Membership.user_id == user.id).first()
    if not mem:
        mem = Membership(tenant_id=tenant.id, user_id=user.id, role="OWNER")
        db.add(mem)

    # Seed Ledger Account
    acc = db.query(LedgerAccount).filter(LedgerAccount.tenant_id == tenant.id, LedgerAccount.code == "1020").first()
    if not acc:
        acc = LedgerAccount(tenant_id=tenant.id, code="1020", name="HDFC Current Account", account_type="ASSET", balance=Decimal("150000.00"))
        db.add(acc)

    # Seed Debit Transaction
    tx = db.query(Transaction).filter(Transaction.tenant_id == tenant.id, Transaction.reference_number == "KG_TX_01").first()
    if not tx:
        tx = Transaction(
            tenant_id=tenant.id,
            transaction_date=datetime.date(2026, 11, 1),
            description="Steel plates purchase",
            raw_narration="Payment to Tata Steel",
            amount=Decimal("45000.00"),
            type="DEBIT",
            channel="RTGS",
            category="Raw Materials",
            counterparty_name="Tata Steel",
            reference_number="KG_TX_01"
        )
        db.add(tx)

    # Seed Receipt
    rc = db.query(Receipt).filter(Receipt.tenant_id == tenant.id, Receipt.invoice_number == "INV_KG_999").first()
    if not rc:
        rc = Receipt(
            tenant_id=tenant.id,
            invoice_number="INV_KG_999",
            vendor_name="Tata Steel",
            vendor_gstin="27AAACT2727Q1ZW",
            total_amount=Decimal("45000.00"),
            taxable_amount=Decimal("38135.59"),
            cgst_amount=Decimal("3432.20"),
            sgst_amount=Decimal("3432.20"),
            status="RECONCILED"
        )
        db.add(rc)

    db.commit()
    yield db, tenant
    db.close()

def test_full_knowledge_graph_entities(test_kg_tenant):
    db, tenant = test_kg_tenant
    kg = build_financial_knowledge_graph(db, tenant.id)

    node_types = {n["type"] for n in kg["nodes"]}
    edge_relations = {e["relation"] for e in kg["edges"]}

    # Verify presence of key entity types
    assert "BUSINESS" in node_types
    assert "USER" in node_types
    assert "LEDGER_ACCOUNT" in node_types
    assert "GST_RECORD" in node_types
    assert "TRANSACTION" in node_types
    assert "VENDOR" in node_types
    assert "INVOICE" in node_types

    # Verify key relationship types
    assert "OWNS" in edge_relations
    assert "EMPLOYS" in edge_relations
    assert "CONTRIBUTES_TO_GST" in edge_relations
    assert "ISSUES_INVOICE" in edge_relations
    assert "RECEIVES_INVOICE" in edge_relations

    assert kg["summary"]["total_nodes"] > 5
    assert kg["summary"]["total_edges"] > 5
