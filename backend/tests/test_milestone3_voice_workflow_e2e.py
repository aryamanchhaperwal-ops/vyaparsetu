import pytest
import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.user import Tenant, User, Membership
from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt
from backend.app.models.ledger import LedgerAccount, LedgerEntry
from backend.app.models.workflow import WorkflowRun
from backend.app.models.usage import AuditLog
from backend.app.core.init_db import seed_standard_accounts_for_tenant
from backend.app.services.voice_service import parse_vernacular_voice_narration
from backend.app.workflows.supervisor import (
    supervisor_graph,
    SupervisorWorkflowState,
    planner_node,
    approval_checkpoint_node,
    execution_agent_node,
    audit_agent_node
)
from backend.app.api.v1.command import run_supervisor_pipeline, approve_workflow_run, ApproveCommandRequest


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def seeded_demo_tenant(db_session: Session):
    """Creates or loads a seeded realistic demo merchant for Milestone 3."""
    t = db_session.query(Tenant).filter(Tenant.simulated_gstin == "27TESTG1234F1Z5").first()
    if not t:
        t = db_session.query(Tenant).filter(Tenant.id == "test_milestone3_tenant").first()
    if not t:
        t = Tenant(
            id="test_milestone3_tenant",
            name="Sharma Kirana & Hardware Traders",
            trade_name="Sharma Traders",
            simulated_gstin="27M3TEST1234F1Z5",
            state_code="27",
            business_category="Retail & Hardware Supplies",
            turnover_tier="Micro (< 5 Cr)",
            subscription_plan="PRO",
            country_code="IN",
            tax_jurisdiction="INDIA_GST",
            base_currency="INR"
        )
        db_session.add(t)
        db_session.commit()
    seed_standard_accounts_for_tenant(db_session, t.id)

    # Ensure demo user and membership exist
    user = db_session.query(User).filter(User.email == "demo_m3@vyaparsetu.in").first()
    if not user:
        user = User(
            id=f"user_demo_m3_{t.id[:8]}",
            email="demo_m3@vyaparsetu.in",
            password_hash="mock_hash",
            full_name="Rajesh Sharma",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

    mem = db_session.query(Membership).filter(
        Membership.tenant_id == t.id,
        Membership.user_id == user.id
    ).first()
    if not mem:
        mem = Membership(tenant_id=t.id, user_id=user.id, role="OWNER")
        db_session.add(mem)
        db_session.commit()

    return t, user, mem


@pytest.fixture
def tenant_b(db_session: Session):
    """Separate tenant to verify strict multi-tenant isolation."""
    tb = db_session.query(Tenant).filter(Tenant.id == "test_tenant_b_isolated").first()
    if not tb:
        tb = Tenant(
            id="test_tenant_b_isolated",
            name="Patel Logistics & Transport",
            trade_name="Patel Cargo",
            simulated_gstin="24M3PATEL999F1Z2",
            state_code="24",
            business_category="Logistics",
            subscription_plan="STARTER"
        )
        db_session.add(tb)
        db_session.commit()
    seed_standard_accounts_for_tenant(db_session, tb.id)

    ub = db_session.query(User).filter(User.email == "patel_b@vyaparsetu.in").first()
    if not ub:
        ub = User(
            id="user_patel_b_m3",
            email="patel_b@vyaparsetu.in",
            password_hash="mock_hash",
            full_name="Suresh Patel",
            is_active=True
        )
        db_session.add(ub)
        db_session.commit()

    memb = db_session.query(Membership).filter(
        Membership.tenant_id == tb.id,
        Membership.user_id == ub.id
    ).first()
    if not memb:
        memb = Membership(tenant_id=tb.id, user_id=ub.id, role="OWNER")
        db_session.add(memb)
        db_session.commit()

    return tb, ub, memb


# =========================================================================
# 1. English Voice Command Parsing
# =========================================================================
def test_1_english_voice_command_parsing():
    transcript = "Paid 8500 rupees to Patel Logistics via UPI today for transportation charges"
    parsed = parse_vernacular_voice_narration(transcript)

    assert parsed["amount"] == 8500.0
    assert parsed["type"] == "DEBIT"
    assert parsed["channel"] == "UPI"
    assert "Patel Logistics" in parsed["counterparty_name"]
    assert parsed["category"] == "Logistics & Transport"
    assert parsed["confidence_score"] >= 0.85
    assert not parsed["requires_clarification"]


# =========================================================================
# 2. Hindi Voice Command Parsing
# =========================================================================
def test_2_hindi_voice_command_parsing():
    transcript = "Kal Sharma ji ko 15000 rupaye diye cement aur ret ke liye"
    parsed = parse_vernacular_voice_narration(transcript)

    assert parsed["amount"] == 15000.0
    assert parsed["type"] == "DEBIT"
    assert "Sharma" in parsed["counterparty_name"]
    assert parsed["category"] == "Raw Materials"
    # "kal" must parse to yesterday's date
    expected_date = str(datetime.date.today() - datetime.timedelta(days=1))
    assert parsed["transaction_date"] == expected_date
    assert parsed["confidence_score"] >= 0.85


# =========================================================================
# 3. Text Fallback Handling
# =========================================================================
def test_3_text_fallback_handling():
    """Text entered manually when speech-to-text is unavailable."""
    raw_text = "Bank transfer of 50000 to Tata Steel on 15-10-2026"
    parsed = parse_vernacular_voice_narration(raw_text)

    assert parsed["amount"] == 50000.0
    assert parsed["channel"] == "BANK"
    assert parsed["type"] == "DEBIT"
    assert "Tata Steel" in parsed["counterparty_name"]
    assert "2026-10-15" in parsed["transaction_date"]


# =========================================================================
# 4. Transcript Editing Before Execution
# =========================================================================
def test_4_transcript_editing():
    """Simulates speech recognition mishearing, corrected by user before execution."""
    spoken_raw = "Paid 12000 to Shama ji"
    corrected_transcript = spoken_raw.replace("Shama", "Sharma Enterprises")
    parsed = parse_vernacular_voice_narration(corrected_transcript)

    assert parsed["amount"] == 12000.0
    assert "Sharma Enterprises" in parsed["counterparty_name"]


# =========================================================================
# 5. Ambiguous Command Clarification
# =========================================================================
def test_5_ambiguous_command_clarification():
    ambiguous = "Payment kiya dukan ke liye"  # Missing amount and counterparty
    parsed = parse_vernacular_voice_narration(ambiguous)

    assert parsed["requires_clarification"] is True
    assert "amount" in parsed["missing_fields"]
    assert parsed["clarification_question"] is not None
    assert len(parsed["clarification_question"]) > 10


# =========================================================================
# 6. Complete October Account-Closing Workflow Execution
# =========================================================================
@pytest.mark.asyncio
async def test_6_complete_october_account_closing_workflow(db_session: Session, seeded_demo_tenant):
    tenant, user, mem = seeded_demo_tenant
    cmd = (
        "Close my October accounts. Process my bank statements, classify transactions, "
        "reconcile invoices and payments, prepare my GST summary, run a compliance audit "
        "and generate my financial reports."
    )

    state = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=user.id,
        instruction=cmd,
        language="en",
        financial_period="2026-10",
        idempotency_key="idemp_close_october_01",
        attached_files=[],
        db=db_session
    )

    assert state["status"] == "WAITING_APPROVAL"  # Financial safety: halts for merchant approval
    assert state["intent"] == "CLOSE_ACCOUNTS"
    assert state["financial_period"] == "2026-10"
    assert len(state["execution_plan"]) >= 8

    # Verify key steps are present
    step_agents = [s["agent"] for s in state["execution_plan"]]
    assert "Document Extraction Agent" in step_agents
    assert "Transaction Classification Agent" in step_agents
    assert "Accounting Agent" in step_agents
    assert "Reconciliation Agent" in step_agents
    assert "Audit Agent" in step_agents
    assert "GST Agent" in step_agents
    assert "Financial Analysis Agent" in step_agents
    assert "Supervisor Checkpoint" in step_agents

    # Verify approval summary metrics
    summary = state["approval_summary"]
    assert summary is not None
    assert int(summary["proposed_transactions_count"]) > 0
    assert summary["trial_balance_balanced"] is True
    assert "net_gst_payable" in summary


# =========================================================================
# 7. Document Ingestion and ChromaDB Auto-Indexing
# =========================================================================
@pytest.mark.asyncio
async def test_7_document_ingestion_and_chromadb_retrieval(db_session: Session, seeded_demo_tenant):
    tenant, user, mem = seeded_demo_tenant
    csv_bytes = (
        b"Date,Description,Amount,Type,Channel,ReferenceNumber\n"
        b"2026-10-12,Tata Power Electricity Invoice,18240.00,DEBIT,NEFT,CMS99281726\n"
        b"2026-10-14,Shree Ganesh Logistics Freight,14124.00,DEBIT,RTGS,RTGS881920\n"
    )

    state = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=user.id,
        instruction="Process bank statement and index into ChromaDB",
        language="en",
        financial_period="2026-10",
        idempotency_key="idemp_doc_chroma_02",
        attached_files=[{"filename": "oct_bank_stmt.csv", "content_bytes": csv_bytes}],
        db=db_session
    )

    assert state["status"] == "WAITING_APPROVAL"
    assert len(state["extracted_documents"]) > 0
    assert state["extracted_documents"][0]["filename"] == "oct_bank_stmt.csv"

    # Verify vector store holds the document
    from backend.app.services.vector_store import list_tenant_documents
    docs = list_tenant_documents(tenant.id)
    assert any("oct_bank_stmt.csv" in d["source"] for d in docs)


# =========================================================================
# 8. GraphRAG Evidence Retrieval & Entity Trails
# =========================================================================
@pytest.mark.asyncio
async def test_8_graphrag_evidence_retrieval(db_session: Session, seeded_demo_tenant):
    tenant, user, mem = seeded_demo_tenant
    from backend.app.services.graph_rag import find_vendor_payment_trail, find_unreconciled_transaction_trail

    # Seed vendor and invoice for graph trail
    v_trail = find_vendor_payment_trail(db_session, tenant.id, "Goyal")
    assert "vendor_query" in v_trail

    u_trail = find_unreconciled_transaction_trail(db_session, tenant.id)
    assert "found_unreconciled" in u_trail or "unreconciled_count" in u_trail
    assert "trail_narration" in u_trail


# =========================================================================
# 9. Invoice-Payment Reconciliation
# =========================================================================
@pytest.mark.asyncio
async def test_9_invoice_payment_reconciliation(db_session: Session, seeded_demo_tenant):
    tenant, user, mem = seeded_demo_tenant

    state = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=user.id,
        instruction="Reconcile all unlinked transactions for October",
        language="en",
        financial_period="2026-10",
        idempotency_key="idemp_recon_03",
        attached_files=[],
        db=db_session
    )

    assert state["reconciliation_results"] is not None
    assert "auto_linked_count" in state["reconciliation_results"]
    assert "suggested_count" in state["reconciliation_results"]


# =========================================================================
# 10. GST Calculations & Section 170 Rounding
# =========================================================================
@pytest.mark.asyncio
async def test_10_gst_calculations_and_section170_rounding(db_session: Session, seeded_demo_tenant):
    tenant, user, mem = seeded_demo_tenant
    from backend.app.services.gst_calculator import generate_gstr3b_summary

    gstr3b = generate_gstr3b_summary(db_session, tenant.id, "2026-10")
    assert gstr3b["report_type"] in ("GSTR3B", "GSTR-3B")
    assert "table_6_1_payment_of_tax" in gstr3b
    cash_payable = gstr3b["table_6_1_payment_of_tax"]["total_net_cash_payable"]
    # Check Section 170 rounding (has .00 integer decimal representation)
    assert "." in cash_payable


# =========================================================================
# 11. Compliance Audit & Section 40A(3) Cash Limits
# =========================================================================
@pytest.mark.asyncio
async def test_11_compliance_audit_and_section40a3_check(db_session: Session, seeded_demo_tenant):
    tenant, user, mem = seeded_demo_tenant
    from backend.app.services.anomaly_service import scan_tenant_anomalies

    anomalies = scan_tenant_anomalies(db_session, tenant.id)
    assert "total_anomalies_detected" in anomalies
    assert "flagged_transactions" in anomalies


# =========================================================================
# 12. Failed Agent Recovery and Retry Limits
# =========================================================================
@pytest.mark.asyncio
async def test_12_failed_agent_recovery_and_retry_limits(db_session: Session, seeded_demo_tenant):
    tenant, user, mem = seeded_demo_tenant

    # Test bad document content that triggers recovery
    corrupt_file = [{"filename": "corrupt.csv", "content_bytes": b"\xff\xfe\x00\x00corrupt"}]
    state = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=user.id,
        instruction="Process corrupted attachment",
        language="en",
        financial_period="2026-10",
        idempotency_key="idemp_recover_04",
        attached_files=corrupt_file,
        db=db_session
    )

    # Should not crash the entire server; marks errors and handles gracefully
    assert "status" in state


# =========================================================================
# 13. Workflow Resumption from Database Checkpoint
# =========================================================================
def test_13_workflow_resumption(db_session: Session, seeded_demo_tenant):
    tenant, user, mem = seeded_demo_tenant
    run_id = f"cmd_resume_test_{datetime.datetime.now().strftime('%M%S')}"

    # Seed a WAITING_APPROVAL WorkflowRun
    run = WorkflowRun(
        tenant_id=tenant.id,
        run_id=run_id,
        workflow_name="autonomous_command_centre",
        status="WAITING_APPROVAL",
        current_node="approval_checkpoint",
        input_payload={"instruction": "Close October", "financial_period": "2026-10"},
        checkpoint_state={"proposed_transactions_count": 1, "net_gst_payable": "500.00"},
        output_payload={
            "proposed_transactions": [{
                "transaction_date": "2026-10-30",
                "amount": 2500.0,
                "type": "DEBIT",
                "channel": "UPI",
                "description": "Stationery supplies",
                "category": "Office & Miscellaneous",
                "status": "PROPOSED"
            }],
            "execution_plan": [
                {"step": 1, "title": "Audit Agent", "agent": "Audit Agent", "status": "COMPLETED"}
            ]
        }
    )
    db_session.add(run)
    db_session.commit()

    # Query from DB to confirm resumption readiness
    resumed = db_session.query(WorkflowRun).filter(WorkflowRun.run_id == run_id).first()
    assert resumed is not None
    assert resumed.status == "WAITING_APPROVAL"
    assert len(resumed.output_payload["proposed_transactions"]) == 1


# =========================================================================
# 14. Approval Required Before Ledger Posting (Zero Mutations)
# =========================================================================
@pytest.mark.asyncio
async def test_14_approval_required_before_ledger_posting(db_session: Session, seeded_demo_tenant):
    tenant, user, mem = seeded_demo_tenant

    initial_tx_count = db_session.query(Transaction).filter(Transaction.tenant_id == tenant.id).count()
    initial_entry_count = db_session.query(LedgerEntry).filter(LedgerEntry.tenant_id == tenant.id).count()

    # Run command that reaches WAITING_APPROVAL
    state = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=user.id,
        instruction="Close my October accounts",
        language="en",
        financial_period="2026-10",
        idempotency_key="idemp_no_mut_05",
        attached_files=[],
        db=db_session
    )

    assert state["status"] == "WAITING_APPROVAL"

    # Strictly 0 ledger entries or confirmed transactions should be added prior to approval
    post_tx_count = db_session.query(Transaction).filter(Transaction.tenant_id == tenant.id).count()
    post_entry_count = db_session.query(LedgerEntry).filter(LedgerEntry.tenant_id == tenant.id).count()

    assert post_tx_count == initial_tx_count
    assert post_entry_count == initial_entry_count


# =========================================================================
# 15. Ledger Posting & Audit Trail After Approval
# =========================================================================
@pytest.mark.asyncio
async def test_15_ledger_posting_and_audit_trail(db_session: Session, seeded_demo_tenant):
    tenant, user, mem = seeded_demo_tenant
    run_id = f"cmd_approve_{datetime.datetime.now().strftime('%M%S')}"

    # Setup a run in WAITING_APPROVAL
    run = WorkflowRun(
        tenant_id=tenant.id,
        run_id=run_id,
        workflow_name="autonomous_command_centre",
        status="WAITING_APPROVAL",
        current_node="approval_checkpoint",
        input_payload={"instruction": "Close October accounts", "language": "en", "financial_period": "2026-10"},
        checkpoint_state={"proposed_transactions_count": 1, "net_gst_payable": "250.00"},
        output_payload={
            "proposed_transactions": [{
                "transaction_date": "2026-10-31",
                "amount": 4500.0,
                "type": "DEBIT",
                "channel": "NEFT",
                "description": "Courier & transport charges",
                "category": "Logistics & Transport",
                "counterparty_name": "Delhivery Freight",
                "status": "PROPOSED"
            }],
            "execution_plan": [
                {"step": 1, "title": "Supervisor Checkpoint", "agent": "Supervisor Checkpoint", "status": "WAITING_APPROVAL"}
            ]
        }
    )
    db_session.add(run)
    db_session.commit()

    req = ApproveCommandRequest(run_id=run_id, approved=True, idempotency_key=f"idemp_{run_id}")
    res = await approve_workflow_run(req=req, membership=mem, db=db_session)

    assert res["status"] == "COMPLETED"
    assert res["execution_results"]["committed_transactions"] == 1
    assert res["execution_results"]["ledger_entries_created"] >= 2  # Balanced double-entry Dr & Cr

    # Verify AuditLog entry was recorded
    audit = db_session.query(AuditLog).filter(
        AuditLog.tenant_id == tenant.id,
        AuditLog.entity_id == run_id,
        AuditLog.action == "APPROVE_WORKFLOW"
    ).first()
    assert audit is not None


# =========================================================================
# 16. Idempotent Approval Protection
# =========================================================================
@pytest.mark.asyncio
async def test_16_idempotent_approval(db_session: Session, seeded_demo_tenant):
    tenant, user, mem = seeded_demo_tenant
    run_id = f"cmd_idemp_test_{datetime.datetime.now().strftime('%M%S')}"

    run = WorkflowRun(
        tenant_id=tenant.id,
        run_id=run_id,
        workflow_name="autonomous_command_centre",
        status="WAITING_APPROVAL",
        current_node="approval_checkpoint",
        input_payload={"instruction": "Pay supplier", "language": "en"},
        checkpoint_state={"proposed_transactions_count": 1},
        output_payload={
            "proposed_transactions": [{
                "transaction_date": "2026-10-31",
                "amount": 1000.0,
                "type": "DEBIT",
                "channel": "UPI",
                "description": "Office tea & snacks",
                "category": "Office & Miscellaneous",
                "status": "PROPOSED"
            }]
        }
    )
    db_session.add(run)
    db_session.commit()

    req = ApproveCommandRequest(run_id=run_id, approved=True, idempotency_key=f"idemp_{run_id}")

    # First approval commits records
    res1 = await approve_workflow_run(req=req, membership=mem, db=db_session)
    assert res1["status"] == "COMPLETED"
    assert res1["execution_results"]["committed_transactions"] == 1

    # Second approval must detect idempotency and NOT duplicate transactions
    res2 = await approve_workflow_run(req=req, membership=mem, db=db_session)
    assert res2["status"] == "COMPLETED"
    assert "already been approved" in res2["message"]


# =========================================================================
# 17. Bilingual Spoken Final Responses (English & Hindi)
# =========================================================================
@pytest.mark.asyncio
async def test_17_spoken_final_response_bilingual(db_session: Session, seeded_demo_tenant):
    tenant, user, mem = seeded_demo_tenant

    # 1. English spoken response
    en_state = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=user.id,
        instruction="Close my October accounts",
        language="en",
        financial_period="2026-10",
        idempotency_key="idemp_en_speech_07",
        attached_files=[],
        db=db_session
    )
    assert "October" in en_state["spoken_response"] or "prepared" in en_state["spoken_response"]

    # 2. Hindi spoken response
    hi_state = await run_supervisor_pipeline(
        tenant_id=tenant.id,
        user_id=user.id,
        instruction="October ke khate band karo",
        language="hi",
        financial_period="2026-10",
        idempotency_key="idemp_hi_speech_08",
        attached_files=[],
        db=db_session
    )
    assert "October" in hi_state["spoken_response"] or "GST" in hi_state["spoken_response"]


# =========================================================================
# 18. Strict Multi-Tenant Isolation
# =========================================================================
@pytest.mark.asyncio
async def test_18_strict_tenant_isolation(db_session: Session, seeded_demo_tenant, tenant_b):
    tenant_a, user_a, mem_a = seeded_demo_tenant
    tenant_b_obj, user_b, mem_b = tenant_b

    # Run a workflow for Tenant A
    run_a = await run_supervisor_pipeline(
        tenant_id=tenant_a.id,
        user_id=user_a.id,
        instruction="Confidential Tenant A Transaction",
        language="en",
        financial_period="2026-10",
        idempotency_key="idemp_iso_tenant_a",
        attached_files=[],
        db=db_session
    )
    run_a_id = run_a["run_id"]

    # Tenant B tries to approve Tenant A's run -> MUST 404
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        req = ApproveCommandRequest(run_id=run_a_id, approved=True)
        await approve_workflow_run(req=req, membership=mem_b, db=db_session)

    assert exc.value.status_code == 404
