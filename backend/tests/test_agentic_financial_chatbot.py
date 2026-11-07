import pytest
import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.user import User, Tenant, Membership
from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt
from backend.app.models.ledger import LedgerAccount, LedgerEntry
from backend.app.services.financial_tools import (
    search_transactions_tool,
    get_top_vendors_tool,
    find_unmatched_vendor_payments_tool,
    compare_expenses_tool,
    search_overdue_invoices_tool,
    find_large_and_anomalous_transactions_tool,
    explain_cash_decrease_tool,
    get_gst_itc_status_tool,
    trace_vendor_payment_trail_tool,
    generate_financial_summary_export_tool
)
from backend.app.services.intent_engine import interpret_intent_with_llm
from backend.app.workflows.supervisor import (
    supervisor_graph,
    SupervisorWorkflowState
)
from backend.app.api.v1.command import run_supervisor_pipeline, CONVERSATION_STORE


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Create or fetch test tenant
        tenant = db.query(Tenant).filter(Tenant.simulated_gstin == "27AGENTIC1234F1Z1").first()
        if not tenant:
            tenant = Tenant(
                name="Sharma Kirana & Hardware Traders",
                simulated_gstin="27AGENTIC1234F1Z1",
                state_code="27",
                tax_jurisdiction="INDIA_GST"
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)

        # Seed sample transactions for Sharma Kirana
        # Clear previous test data for this tenant
        db.query(Transaction).filter(Transaction.tenant_id == tenant.id).delete()
        db.query(Receipt).filter(Receipt.tenant_id == tenant.id).delete()

        # Seed transactions
        t1 = Transaction(
            tenant_id=tenant.id,
            transaction_date=datetime.date(2026, 10, 5),
            description="Payment to Sharma Traders for cement",
            raw_narration="UPI/REF1001/DR/merchant@sharmatraders",
            amount=Decimal("35000.00"),
            type="DEBIT",
            channel="UPI",
            reference_number="REF1001",
            category="Raw Materials",
            tax_rate=Decimal("18.0"),
            counterparty_name="Sharma Traders",
            is_reconciled=False,
            status="CONFIRMED"
        )
        t2 = Transaction(
            tenant_id=tenant.id,
            transaction_date=datetime.date(2026, 10, 10),
            description="Second payment to Sharma Traders for steel",
            raw_narration="NEFT-DR-REF1002-SHARMA TRADERS",
            amount=Decimal("50000.00"),
            type="DEBIT",
            channel="NEFT",
            reference_number="REF1002",
            category="Raw Materials",
            tax_rate=Decimal("18.0"),
            counterparty_name="Sharma Traders",
            is_reconciled=False,
            status="CONFIRMED"
        )
        t3 = Transaction(
            tenant_id=tenant.id,
            transaction_date=datetime.date(2026, 10, 12),
            description="Freight charges to Patel Logistics",
            raw_narration="UPI/REF1003/DR/patellogistics",
            amount=Decimal("8500.00"),
            type="DEBIT",
            channel="UPI",
            reference_number="REF1003",
            category="Logistics & Transport",
            tax_rate=Decimal("5.0"),
            counterparty_name="Patel Logistics",
            is_reconciled=True,
            status="CONFIRMED"
        )
        t4 = Transaction(
            tenant_id=tenant.id,
            transaction_date=datetime.date(2026, 10, 15),
            description="Office petty cash disbursement",
            raw_narration="CASH WITHDRAWAL FOR SUNDRY",
            amount=Decimal("12000.00"),  # > 10,000 cash! Sec 40A(3)
            type="DEBIT",
            channel="CASH",
            reference_number="CASH001",
            category="Office & Miscellaneous",
            tax_rate=Decimal("5.0"),
            counterparty_name="Office Pantry",
            is_reconciled=False,
            status="CONFIRMED"
        )
        t5 = Transaction(
            tenant_id=tenant.id,
            transaction_date=datetime.date(2026, 10, 18),
            description="Retail counter sales collection",
            raw_narration="UPI/REF2001/CR/customer@upi/Counter Sales",
            amount=Decimal("82000.00"),
            type="CREDIT",
            channel="UPI",
            reference_number="REF2001",
            category="Sales Revenue",
            tax_rate=Decimal("18.0"),
            counterparty_name="Retail Customers",
            is_reconciled=True,
            status="CONFIRMED"
        )
        # September transactions for expense comparison
        t6 = Transaction(
            tenant_id=tenant.id,
            transaction_date=datetime.date(2026, 9, 10),
            description="September raw materials payment",
            raw_narration="NEFT-DR-SEP01-SHARMA TRADERS",
            amount=Decimal("40000.00"),
            type="DEBIT",
            channel="NEFT",
            reference_number="SEP01",
            category="Raw Materials",
            tax_rate=Decimal("18.0"),
            counterparty_name="Sharma Traders",
            is_reconciled=True,
            status="CONFIRMED"
        )
        t7 = Transaction(
            tenant_id=tenant.id,
            transaction_date=datetime.date(2026, 9, 15),
            description="September warehouse rent",
            raw_narration="NEFT-DR-SEP02-PATEL PROPERTY",
            amount=Decimal("25000.00"),
            type="DEBIT",
            channel="NEFT",
            reference_number="SEP02",
            category="Rent & Utilities",
            tax_rate=Decimal("18.0"),
            counterparty_name="Patel Property",
            is_reconciled=True,
            status="CONFIRMED"
        )

        db.add_all([t1, t2, t3, t4, t5, t6, t7])

        # Overdue invoice receipt
        r1 = Receipt(
            tenant_id=tenant.id,
            invoice_number="INV-2026-089",
            invoice_date=datetime.date(2026, 8, 15),  # > 60 days overdue
            vendor_name="Gupta Steel Mart",
            vendor_gstin="27GUPTA1234F1Z9",
            total_amount=Decimal("45000.00"),
            taxable_amount=Decimal("38135.59"),
            cgst_amount=Decimal("3432.20"),
            sgst_amount=Decimal("3432.20"),
            status="EXTRACTED"  # Unreconciled
        )
        db.add(r1)
        db.commit()

        yield db, tenant
    finally:
        db.close()


# =============================================================================
# 10 ARBITRARY NATURAL LANGUAGE ACCEPTANCE TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_acceptance_1_top_vendors_paid_this_quarter(db_session):
    """1. 'Show me the five vendors I paid the most this quarter.'"""
    db, tenant = db_session
    res = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="Show me the five vendors I paid the most this quarter.",
        language="en",
        financial_period="2026-10",
        idempotency_key=None,
        attached_files=[],
        db=db
    )
    assert res["status"] == "COMPLETED"
    assert res["intent"] == "GET_TOP_VENDORS"
    assert "get_top_vendors" in res.get("selected_tools", [])
    tool_res = res.get("dynamic_tool_results", {}).get("get_top_vendors")
    assert tool_res is not None
    assert len(tool_res["top_vendors"]) > 0
    # Sharma Traders should be the top vendor
    top = tool_res["top_vendors"][0]
    assert "Sharma" in top["vendor_name"]
    assert top["total_paid"] >= 85000.0
    assert "Sharma" in res["spoken_response"]


@pytest.mark.asyncio
async def test_acceptance_2_unmatched_payments_to_vendor(db_session):
    """2. 'Find payments to Sharma Traders that do not have matching invoices.'"""
    db, tenant = db_session
    res = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="Find payments to Sharma Traders that do not have matching invoices.",
        language="en",
        financial_period="2026-10",
        idempotency_key=None,
        attached_files=[],
        db=db
    )
    assert res["status"] == "COMPLETED"
    assert res["intent"] == "FIND_UNMATCHED_PAYMENTS"
    tool_res = res.get("dynamic_tool_results", {}).get("find_unmatched_vendor_payments")
    assert tool_res is not None
    assert tool_res["unmatched_count"] >= 2
    assert tool_res["unmatched_amount"] >= 85000.0
    assert "Sharma Traders" in tool_res["vendor_name"]


@pytest.mark.asyncio
async def test_acceptance_3_compare_october_with_september(db_session):
    """3. 'Compare my October expenses with September.'"""
    db, tenant = db_session
    res = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="Compare my October expenses with September.",
        language="en",
        financial_period="2026-10",
        idempotency_key=None,
        attached_files=[],
        db=db
    )
    assert res["status"] == "COMPLETED"
    assert res["intent"] == "COMPARE_EXPENSES"
    tool_res = res.get("dynamic_tool_results", {}).get("compare_expenses")
    assert tool_res is not None
    assert tool_res["period_a"] == "2026-10"
    assert tool_res["period_b"] == "2026-09"
    assert len(tool_res["categories_breakdown"]) > 0
    assert "Raw Materials" in [c["category"] for c in tool_res["categories_breakdown"]]


@pytest.mark.asyncio
async def test_acceptance_4_overdue_invoices(db_session):
    """4. 'Which customers have overdue invoices?'"""
    db, tenant = db_session
    res = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="Which customers have overdue invoices?",
        language="en",
        financial_period="2026-10",
        idempotency_key=None,
        attached_files=[],
        db=db
    )
    assert res["status"] == "COMPLETED"
    assert res["intent"] == "SEARCH_OVERDUE_INVOICES"
    tool_res = res.get("dynamic_tool_results", {}).get("search_overdue_invoices")
    assert tool_res is not None
    assert tool_res["overdue_count"] >= 1
    assert tool_res["total_overdue_amount"] >= 45000.0


@pytest.mark.asyncio
async def test_acceptance_5_largest_business_expenses(db_session):
    """5. 'Prepare a report of my largest business expenses.'"""
    db, tenant = db_session
    res = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="Prepare a report of my largest business expenses.",
        language="en",
        financial_period="2026-10",
        idempotency_key=None,
        attached_files=[],
        db=db
    )
    assert res["status"] == "COMPLETED"
    tool_res = res.get("dynamic_tool_results", {}).get("get_top_vendors")
    assert tool_res is not None
    assert len(tool_res["top_vendors"]) > 0


@pytest.mark.asyncio
async def test_acceptance_6_transactions_above_25000_anomalies(db_session):
    """6. 'Find all transactions above ₹25,000 and flag unusual entries.'"""
    db, tenant = db_session
    res = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="Find all transactions above ₹25,000 and flag unusual entries.",
        language="en",
        financial_period="2026-10",
        idempotency_key=None,
        attached_files=[],
        db=db
    )
    assert res["status"] == "COMPLETED"
    assert res["intent"] == "FIND_LARGE_TRANSACTIONS"
    tool_res = res.get("dynamic_tool_results", {}).get("find_large_and_anomalous_transactions")
    assert tool_res is not None
    assert tool_res["threshold"] == 25000.0
    assert tool_res["total_count"] >= 2  # 35k and 50k
    assert tool_res["total_amount"] >= 85000.0


@pytest.mark.asyncio
async def test_acceptance_7_explain_cash_decrease(db_session):
    """7. 'Explain why my cash balance decreased this month.'"""
    db, tenant = db_session
    res = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="Explain why my cash balance decreased this month.",
        language="en",
        financial_period="2026-10",
        idempotency_key=None,
        attached_files=[],
        db=db
    )
    assert res["status"] == "COMPLETED"
    assert res["intent"] == "EXPLAIN_CASH_DECREASE"
    tool_res = res.get("dynamic_tool_results", {}).get("explain_cash_decrease")
    assert tool_res is not None
    assert "total_inflows" in tool_res
    assert "total_outflows" in tool_res
    assert len(tool_res["top_outflow_drivers"]) > 0


@pytest.mark.asyncio
async def test_acceptance_8_gst_itc_status(db_session):
    """8. 'Show the GST input tax credit status of my purchases.'"""
    db, tenant = db_session
    res = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="Show the GST input tax credit status of my purchases.",
        language="en",
        financial_period="2026-10",
        idempotency_key=None,
        attached_files=[],
        db=db
    )
    assert res["status"] == "COMPLETED"
    assert res["intent"] == "GET_GST_ITC_STATUS"
    tool_res = res.get("dynamic_tool_results", {}).get("get_gst_itc_status")
    assert tool_res is not None
    assert tool_res["eligible_itc"] > 0.0
    assert len(tool_res["statutory_clauses"]) >= 3


@pytest.mark.asyncio
async def test_acceptance_9_trace_vendor_payment_trail(db_session):
    """9. 'Find all payments to a vendor and trace them to their invoices.'"""
    db, tenant = db_session
    res = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="Find all payments to Sharma Traders and trace them to their invoices.",
        language="en",
        financial_period="2026-10",
        idempotency_key=None,
        attached_files=[],
        db=db
    )
    assert res["status"] == "COMPLETED"
    assert res["intent"] == "TRACE_VENDOR_TRAIL"
    tool_res = res.get("dynamic_tool_results", {}).get("trace_vendor_payment_trail")
    assert tool_res is not None
    assert tool_res.get("found") is True
    assert tool_res.get("total_paid") >= 85000.0


@pytest.mark.asyncio
async def test_acceptance_10_monthly_financial_summary_export(db_session):
    """10. 'Generate a monthly financial summary and export it.'"""
    db, tenant = db_session
    res = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="Generate a monthly financial summary and export it.",
        language="en",
        financial_period="2026-10",
        idempotency_key=None,
        attached_files=[],
        db=db
    )
    assert res["status"] == "COMPLETED"
    assert res["intent"] == "EXPORT_FINANCIAL_SUMMARY"
    tool_res = res.get("dynamic_tool_results", {}).get("generate_financial_summary_export")
    assert tool_res is not None
    assert "report" in tool_res
    report = tool_res["report"]
    assert "profit_and_loss" in report
    assert "export_available_formats" in report
    assert "JSON" in report["export_available_formats"]


# =============================================================================
# ADDITIONAL CRITICAL CAPABILITY TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_unrecognised_out_of_scope_query(db_session):
    """Evaluates scope boundary when user asks non-financial query."""
    db, tenant = db_session
    res = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="What is the capital of France and book a flight?",
        language="en",
        financial_period=None,
        idempotency_key=None,
        attached_files=[],
        db=db
    )
    assert res["status"] == "COMPLETED"
    assert res["intent"] == "UNSUPPORTED"
    assert "financial" in res["spoken_response"].lower() or "accounting" in res["spoken_response"].lower()


@pytest.mark.asyncio
async def test_ambiguous_request_requires_clarification(db_session):
    """Asks clarification question when request is ambiguous without amount or vendor."""
    db, tenant = db_session
    res = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="Process the payment",
        language="en",
        financial_period=None,
        idempotency_key=None,
        attached_files=[],
        db=db
    )
    assert res["status"] == "WAITING_APPROVAL"
    assert res["intent"] == "AMBIGUOUS"
    assert "amount" in res.get("missing_information", [])
    assert res.get("clarification_question") is not None


@pytest.mark.asyncio
async def test_multi_turn_conversational_follow_ups(db_session):
    """Verifies multi-turn memory: Turn 1 -> Turn 2 ('Which of those...') -> Turn 3."""
    db, tenant = db_session
    conv_id = f"test_conv_{tenant.id}"

    # Turn 1
    res1 = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="Find all payments to Sharma Traders last month.",
        language="en",
        financial_period="2026-10",
        idempotency_key=None,
        attached_files=[],
        db=db,
        conversation_id=conv_id
    )
    assert res1["status"] == "COMPLETED"
    assert conv_id in CONVERSATION_STORE[tenant.id]

    # Turn 2: 'Which of those are not reconciled?'
    res2 = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="Which of those are not reconciled?",
        language="en",
        financial_period="2026-10",
        idempotency_key=None,
        attached_files=[],
        db=db,
        conversation_id=conv_id
    )
    assert res2["status"] == "COMPLETED"
    assert res2["intent"] == "FIND_UNMATCHED_PAYMENTS"
    tool_res = res2.get("dynamic_tool_results", {}).get("find_unmatched_vendor_payments")
    assert tool_res is not None
    # Context carried over 'Sharma Traders' from Turn 1!
    assert "Sharma Traders" in tool_res["vendor_name"]
    assert tool_res["unmatched_count"] >= 2


@pytest.mark.asyncio
async def test_hindi_voice_command(db_session):
    """Verifies Hindi spoken financial query and response."""
    db, tenant = db_session
    res = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=None,
        instruction="Maine Sharma ji ko kitna payment kiya pichhle mahine?",
        language="hi",
        financial_period="2026-09",
        idempotency_key=None,
        attached_files=[],
        db=db
    )
    assert res["status"] == "COMPLETED"
    assert res["language"] == "hi"
    assert len(res["spoken_response"]) > 0


@pytest.mark.asyncio
async def test_strict_tenant_isolation(db_session):
    """Verifies Tenant B cannot query Tenant A's transactions or vendors."""
    db, tenant_a = db_session

    # Create Tenant B
    tenant_b = db.query(Tenant).filter(Tenant.simulated_gstin == "27ISOLATE9999F1Z1").first()
    if not tenant_b:
        tenant_b = Tenant(
            name="Isolated Competitor Traders",
            simulated_gstin="27ISOLATE9999F1Z1",
            state_code="27",
            tax_jurisdiction="INDIA_GST"
        )
        db.add(tenant_b)
        db.commit()
        db.refresh(tenant_b)

    # Query top vendors for Tenant B (should be empty, NOT Tenant A's vendors)
    res_b = await run_supervisor_pipeline(
        tenant_id=tenant_b.id,
        user_id=None,
        instruction="Show me the five vendors I paid the most this quarter.",
        language="en",
        financial_period="2026-10",
        idempotency_key=None,
        attached_files=[],
        db=db
    )
    assert res_b["status"] == "COMPLETED"
    tool_res_b = res_b.get("dynamic_tool_results", {}).get("get_top_vendors")
    assert tool_res_b is not None
    # Tenant B has 0 spend
    assert tool_res_b["total_spend"] == 0.0
    assert len(tool_res_b["top_vendors"]) == 0
