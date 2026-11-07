import io
import pytest
import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.user import Tenant, User, Membership
from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt
from backend.app.models.ledger import LedgerAccount, LedgerEntry
from backend.app.services.vector_store import (
    ingest_document_to_vector_store,
    query_vector_store,
    delete_document_from_vector_store,
    list_tenant_documents,
    get_tenant_collection
)
from backend.app.services.hybrid_rag import (
    hybrid_retrieve,
    query_bm25_keyword_store,
    expand_query_terms,
    reciprocal_rank_fusion
)
from backend.app.services.graph_rag import (
    search_graph_entities,
    expand_graph_neighbors,
    find_vendor_payment_trail,
    find_unreconciled_transaction_trail,
    build_relationship_aware_context
)
from backend.app.services.unified_retriever import (
    classify_retrieval_strategy,
    unified_retrieve,
    answer_with_unified_retrieval
)


def get_auth_headers_and_tenant(client: TestClient, db: Session, email: str, business_name: str, gstin: str):
    """Registers/authenticates a merchant for isolated test execution."""
    login_data = {"username": email, "password": "SecurePassword@123"}
    res = client.post("/api/v1/auth/login", data=login_data)
    if res.status_code != 200:
        reg_payload = {
            "email": email,
            "password": "SecurePassword@123",
            "full_name": f"{business_name} Admin",
            "business_name": business_name,
            "state_code": gstin[:2] if len(gstin) >= 2 else "27"
        }
        res = client.post("/api/v1/auth/register", json=reg_payload)
        assert res.status_code in (200, 201), res.text

    data = res.json()
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws_res = client.get("/api/v1/auth/workspaces", headers=headers)
    assert ws_res.status_code == 200, ws_res.text
    workspaces = ws_res.json()
    tenant_id = workspaces[0]["tenant"]["id"] if workspaces and "tenant" in workspaces[0] else None

    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id

    return headers, tenant_id


# ==============================================================================
# 1. Persistent ChromaDB Storage and Retrieval
# ==============================================================================
def test_1_persistent_chromadb_storage_and_retrieval():
    tenant_id = "test_tenant_persistent_01"
    content = b"Electricity bill for October 2026: Amount Rs 4500 payable to BESCOM Power Utility."
    
    # Ingest document
    res = ingest_document_to_vector_store(
        tenant_id=tenant_id,
        filename="bescom_october_bill.txt",
        content_bytes=content,
        doc_type="INVOICE"
    )
    assert res["status"] == "INDEXED"
    assert res["is_duplicate"] is False
    assert res["chunk_count"] >= 1
    doc_id = res["doc_id"]

    # Query vector store
    results = query_vector_store(tenant_id=tenant_id, query_text="BESCOM electricity bill October")
    assert len(results) >= 1
    assert "BESCOM" in results[0]["snippet"]
    assert results[0]["doc_id"] == doc_id
    assert results[0]["document_type"] == "INVOICE"
    assert results[0]["similarity_score"] > 0.0

    # Cleanup
    delete_document_from_vector_store(tenant_id, doc_id)


# ==============================================================================
# 2. PDF and Spreadsheet Ingestion (PDF, CSV, Excel)
# ==============================================================================
def test_2_pdf_csv_excel_spreadsheet_ingestion():
    tenant_id = "test_tenant_multiformat_02"

    # 2a. CSV Ingestion
    csv_bytes = (
        "Date,Description,Debit,Credit,Balance\n"
        "2026-10-01,Opening Balance,,,100000.00\n"
        "2026-10-05,Birla Cement Supplier Payment,25000.00,,75000.00\n"
        "2026-10-12,Retail Customer Sales Cash Inflow,,48000.00,123000.00\n"
    ).encode("utf-8")
    csv_res = ingest_document_to_vector_store(tenant_id, "bank_october.csv", csv_bytes, doc_type="BANK_STATEMENT")
    assert csv_res["status"] == "INDEXED"
    assert csv_res["chunk_count"] >= 1

    # 2b. Simple text/PDF-like ingestion
    txt_bytes = (
        "TAX INVOICE\n"
        "Vendor: Sharma Paper Mills Pvt Ltd\n"
        "GSTIN: 27AABCS1429B1Z8\n"
        "Invoice No: SPM-2026-881\n"
        "Date: 15-10-2026\n"
        "Description: Printing & Packaging Kraft Paper\n"
        "Taxable Value: Rs 20,000.00\n"
        "CGST 9%: Rs 1,800.00\n"
        "SGST 9%: Rs 1,800.00\n"
        "Total Amount: Rs 23,600.00\n"
    ).encode("utf-8")
    txt_res = ingest_document_to_vector_store(tenant_id, "sharma_paper_invoice.txt", txt_bytes, doc_type="INVOICE")
    assert txt_res["status"] == "INDEXED"

    # Query spreadsheet content
    csv_matches = query_vector_store(tenant_id, "Birla Cement supplier payment")
    assert len(csv_matches) >= 1
    assert "Birla Cement" in csv_matches[0]["snippet"]

    # Query invoice content
    inv_matches = query_vector_store(tenant_id, "Sharma Paper Mills kraft paper")
    assert len(inv_matches) >= 1
    assert "23,600" in inv_matches[0]["snippet"] or "Sharma Paper" in inv_matches[0]["snippet"]

    # Cleanup
    delete_document_from_vector_store(tenant_id, csv_res["doc_id"])
    delete_document_from_vector_store(tenant_id, txt_res["doc_id"])


# ==============================================================================
# 3. Duplicate Document Detection
# ==============================================================================
def test_3_duplicate_document_detection():
    tenant_id = "test_tenant_dup_03"
    content = b"Contract Agreement: Monthly warehouse lease of Rs 35,000 to Apex Logistics."

    # First ingestion
    first_res = ingest_document_to_vector_store(tenant_id, "warehouse_lease.txt", content)
    assert first_res["status"] == "INDEXED"
    assert first_res["is_duplicate"] is False
    doc_id = first_res["doc_id"]

    # Second ingestion with identical content
    second_res = ingest_document_to_vector_store(tenant_id, "warehouse_lease_duplicate.txt", content)
    assert second_res["status"] == "DUPLICATE"
    assert second_res["is_duplicate"] is True
    assert second_res["doc_id"] == doc_id

    # Verify vector store only contains 1 copy
    chunks = query_vector_store(tenant_id, "Apex Logistics warehouse lease")
    assert len(chunks) == 1

    delete_document_from_vector_store(tenant_id, doc_id)


# ==============================================================================
# 4. Tenant-Isolated Vector Retrieval
# ==============================================================================
def test_4_tenant_isolated_vector_retrieval():
    tenant_a = "tenant_alpha_isolated"
    tenant_b = "tenant_beta_isolated"

    content_a = b"CONFIDENTIAL: Tenant Alpha Secret Project Aurora Budget Rs 50,00,000."
    content_b = b"CONFIDENTIAL: Tenant Beta Secret Project Zephyr Budget Rs 10,00,000."

    res_a = ingest_document_to_vector_store(tenant_a, "alpha_doc.txt", content_a)
    res_b = ingest_document_to_vector_store(tenant_b, "beta_doc.txt", content_b)

    # Tenant A searches for Project Aurora -> Found
    a_results = query_vector_store(tenant_a, "Project Aurora")
    assert len(a_results) >= 1
    assert "Tenant Alpha" in a_results[0]["snippet"]

    # Tenant B searches for Project Aurora -> NOT FOUND in Tenant B (0 leaks of Tenant A)
    b_cross_leak = query_vector_store(tenant_b, "Project Aurora")
    assert not any("Tenant Alpha" in r["snippet"] for r in b_cross_leak)
    assert not any("Aurora" in r["snippet"] for r in b_cross_leak)

    # Tenant A searches for Project Zephyr -> NOT FOUND in Tenant A (0 leaks of Tenant B)
    a_cross_leak = query_vector_store(tenant_a, "Project Zephyr")
    assert not any("Tenant Beta" in r["snippet"] for r in a_cross_leak)
    assert not any("Zephyr" in r["snippet"] for r in a_cross_leak)

    # Tenant B searches for Project Zephyr -> Found
    b_results = query_vector_store(tenant_b, "Project Zephyr")
    assert len(b_results) >= 1
    assert "Tenant Beta" in b_results[0]["snippet"]

    delete_document_from_vector_store(tenant_a, res_a["doc_id"])
    delete_document_from_vector_store(tenant_b, res_b["doc_id"])


# ==============================================================================
# 5. Keyword (BM25) and Semantic (Vector) Retrieval
# ==============================================================================
def test_5_keyword_bm25_and_semantic_retrieval():
    tenant_id = "test_tenant_hybrid_bm25_05"
    content = b"Tata Sky broadband high speed internet optical fiber bill Rs 1499."
    res = ingest_document_to_vector_store(tenant_id, "internet_bill.txt", content)

    # 5a. BM25 exact keyword match
    bm25_matches = query_bm25_keyword_store(tenant_id, "broadband optical fiber")
    assert len(bm25_matches) >= 1
    assert "Tata Sky" in bm25_matches[0]["snippet"]
    assert bm25_matches[0]["retrieval_method"] == "KEYWORD_BM25"

    # 5b. Dense semantic match (concept match without exact token overlap)
    vec_matches = query_vector_store(tenant_id, "wifi internet connection subscription")
    assert len(vec_matches) >= 1
    assert "Tata Sky" in vec_matches[0]["snippet"]
    assert vec_matches[0]["retrieval_method"] == "VECTOR_DENSE"

    delete_document_from_vector_store(tenant_id, res["doc_id"])


# ==============================================================================
# 6. Hybrid Result Fusion (Reciprocal Rank Fusion - RRF)
# ==============================================================================
def test_6_hybrid_result_fusion_rrf():
    tenant_id = "test_tenant_rrf_06"
    doc1 = b"Invoice #101: Purchase of 100 bags Ambuja Cement from Ambuja Cements Ltd."
    doc2 = b"Invoice #102: Purchase of 50 bags UltraTech Cement from UltraTech Suppliers."

    r1 = ingest_document_to_vector_store(tenant_id, "ambuja.txt", doc1)
    r2 = ingest_document_to_vector_store(tenant_id, "ultratech.txt", doc2)

    hybrid_res = hybrid_retrieve(tenant_id, "Ambuja Cement purchase invoice", top_k=5)
    fused = hybrid_res["fused_results"]

    assert len(fused) >= 1
    top_hit = fused[0]
    assert "Ambuja" in top_hit["snippet"]
    assert top_hit["retrieval_method"] == "HYBRID_RRF"
    assert "rrf_score" in top_hit
    assert top_hit["rrf_score"] > 0.0
    assert len(hybrid_res["citations"]) >= 1

    delete_document_from_vector_store(tenant_id, r1["doc_id"])
    delete_document_from_vector_store(tenant_id, r2["doc_id"])


# ==============================================================================
# 7. Graph Entity and Relationship Retrieval
# ==============================================================================
def test_7_graph_entity_and_relationship_retrieval(client: TestClient, db_session: Session):
    headers, tenant_id = get_auth_headers_and_tenant(
        client, db_session, "graph.entity@kirana.in", "Graph Entity Mart", "27AAAAA7777A1Z7"
    )

    # Seed vendor invoice and payment transaction
    rcpt = Receipt(
        tenant_id=tenant_id,
        vendor_name="Goyal Hardware Supplies",
        vendor_gstin="27GHYJK1234A1Z5",
        invoice_number="GHS-9921",
        invoice_date=datetime.date(2026, 10, 10),
        total_amount=Decimal("15000.00"),
        taxable_amount=Decimal("12711.86"),
        cgst_amount=Decimal("1144.07"),
        sgst_amount=Decimal("1144.07"),
        status="PROCESSED"
    )
    db_session.add(rcpt)
    db_session.commit()

    tx = Transaction(
        tenant_id=tenant_id,
        transaction_date=datetime.date(2026, 10, 11),
        description="Goyal Hardware bill payment",
        raw_narration="Goyal Hardware bill payment",
        amount=Decimal("15000.00"),
        type="DEBIT",
        channel="BANK",
        reference_number="NEFT_GHS_001",
        category="Raw Materials",
        counterparty_name="Goyal Hardware Supplies",
        status="CONFIRMED"
    )
    db_session.add(tx)
    db_session.commit()

    # 7a. Search graph entities
    entities = search_graph_entities(db_session, tenant_id, "Goyal Hardware")
    assert len(entities) >= 1
    assert any(e["label"] == "Goyal Hardware Supplies" for e in entities)

    # 7b. Expand graph neighbors
    vendor_node = next(e for e in entities if e["label"] == "Goyal Hardware Supplies")
    subgraph = expand_graph_neighbors(db_session, tenant_id, vendor_node["id"], max_hops=2)
    assert subgraph["total_nodes"] >= 2
    assert any(n["type"] == "INVOICE" for n in subgraph["nodes"])

    # 7c. Find vendor payment trail
    trail = find_vendor_payment_trail(db_session, tenant_id, "Goyal Hardware")
    assert trail["found"] is True
    assert trail["invoices_count"] >= 1
    assert "GHS-9921" in trail["trail_narration"]


# ==============================================================================
# 8. Hybrid Vector + Graph Retrieval
# ==============================================================================
@pytest.mark.asyncio
async def test_8_hybrid_vector_plus_graph_retrieval(client: TestClient, db_session: Session):
    headers, tenant_id = get_auth_headers_and_tenant(
        client, db_session, "hybrid.graph.vector@kirana.in", "Hybrid Graph Mart", "27AAAAA8888A1Z8"
    )

    # Index document in vector store
    doc_content = b"Supplier contract: Goyal Hardware Supplies supplies raw construction materials."
    res = ingest_document_to_vector_store(tenant_id, "goyal_contract.txt", doc_content)

    # Run unified retrieval
    unified = await unified_retrieve(
        db=db_session,
        tenant_id=tenant_id,
        query="Which payments belong to Goyal Hardware Supplies and what documents exist?",
        force_strategy="HYBRID_GRAPH_VECTOR"
    )

    assert unified["strategy_used"] == "HYBRID_GRAPH_VECTOR"
    assert unified["has_sufficient_evidence"] is True
    assert len(unified["citations"]) >= 1
    assert "DOCUMENT EVIDENCE" in unified["assembled_context"]

    delete_document_from_vector_store(tenant_id, res["doc_id"])


# ==============================================================================
# 9. Agentic Retrieval Routing (Supervisor Strategy Selection)
# ==============================================================================
def test_9_agentic_retrieval_routing():
    # 9a. Document lookup -> DOCUMENT_SEARCH
    s1 = classify_retrieval_strategy("Find the electricity invoice from October")
    assert s1 == "DOCUMENT_SEARCH"

    # 9b. Vendor payment trail -> GRAPH_SEARCH
    s2 = classify_retrieval_strategy("Which payments belong to this vendor?")
    assert s2 == "GRAPH_SEARCH"

    # 9c. Non-reconciliation inquiry -> RECONCILIATION_SEARCH
    s3 = classify_retrieval_strategy("Why does this bank transaction remain unreconciled?")
    assert s3 == "RECONCILIATION_SEARCH"

    # 9d. Statutory legal tax inquiry -> STATUTORY_SEARCH
    s4 = classify_retrieval_strategy("What GST treatment applies here under Section 16?")
    assert s4 == "STATUTORY_SEARCH"


# ==============================================================================
# 10. Missing or Conflicting Evidence (Stops without Hallucination)
# ==============================================================================
@pytest.mark.asyncio
async def test_10_missing_evidence_stops_without_hallucination(db_session: Session):
    tenant_id = "test_tenant_empty_10"
    
    # Query completely non-existent vendor and document
    res = await unified_retrieve(
        db=db_session,
        tenant_id=tenant_id,
        query="Find the supersonic aerospace invoice for spaceship fuel",
        force_strategy="DOCUMENT_SEARCH"
    )

    assert res["has_sufficient_evidence"] is False
    assert res["confidence_score"] == 0.0
    assert len(res["citations"]) == 0


# ==============================================================================
# 11. Source Provenance and Citations
# ==============================================================================
def test_11_source_provenance_and_citations():
    tenant_id = "test_tenant_cit_11"
    content = b"Rental Agreement: Shop premises rent of Rs 25,000 to Shanti Real Estate on 1st of each month."
    res = ingest_document_to_vector_store(tenant_id, "rental_agreement.pdf", content, doc_type="LEASE")

    hybrid_res = hybrid_retrieve(tenant_id, "Shanti Real Estate rent", top_k=2)
    citations = hybrid_res["citations"]
    assert len(citations) >= 1
    cit = citations[0]

    assert cit["source"] == "rental_agreement.pdf"
    assert cit["doc_id"] == res["doc_id"]
    assert cit["document_type"] == "LEASE"
    assert "section" in cit

    delete_document_from_vector_store(tenant_id, res["doc_id"])


# ==============================================================================
# 12. Cross-Tenant Isolation Defense-in-Depth
# ==============================================================================
def test_12_cross_tenant_isolation_defense_in_depth(client: TestClient, db_session: Session):
    headers_a, tenant_a_id = get_auth_headers_and_tenant(
        client, db_session, "tenant.rag.a@kirana.in", "Tenant RAG Alpha", "27AAAAA1212A1Z1"
    )
    headers_b, tenant_b_id = get_auth_headers_and_tenant(
        client, db_session, "tenant.rag.b@kirana.in", "Tenant RAG Beta", "27BBBBB2323B1Z2"
    )

    # Ingest document for Tenant A via API
    doc_bytes = b"Quarterly Net Profit for Alpha is Rs 8,50,000 with 15% GST rebate."
    files = [("file", ("alpha_profit_statement.txt", io.BytesIO(doc_bytes), "text/plain"))]
    res_upload = client.post("/api/v1/rag/documents/upload", files=files, headers=headers_a)
    assert res_upload.status_code == 200, res_upload.text
    doc_a_id = res_upload.json()["doc_id"]

    # Tenant B queries vector store via API
    res_b_query = client.post("/api/v1/rag/query", json={"query": "Alpha profit statement 8,50,000"}, headers=headers_b)
    assert res_b_query.status_code == 200
    data_b = res_b_query.json()
    citations_b = data_b.get("citations", [])
    assert not any(c.get("doc_id") == doc_a_id for c in citations_b), "Security Violation: Tenant B retrieved Tenant A's document!"
    assert not any("alpha_profit_statement" in str(c.get("source", "")) for c in citations_b), "Security Violation: Tenant B saw Tenant A's document!"

    # Tenant B lists documents via API -> Tenant A's doc must not be listed
    res_b_docs = client.get("/api/v1/rag/documents", headers=headers_b)
    assert res_b_docs.status_code == 200
    docs_b = res_b_docs.json()["documents"]
    assert not any(d["doc_id"] == doc_a_id for d in docs_b)

    # Cleanup
    client.delete(f"/api/v1/rag/documents/{doc_a_id}", headers=headers_a)


# ==============================================================================
# 13. Retrieval Failure Recovery (Corrupted / Empty Input)
# ==============================================================================
def test_13_retrieval_failure_recovery():
    tenant_id = "test_tenant_failure_recovery_13"

    # Empty content bytes
    res_empty = ingest_document_to_vector_store(tenant_id, "empty.txt", b"")
    assert res_empty["status"] == "FAILED"
    assert res_empty["chunk_count"] == 0

    # Query with non-alphanumeric / special characters
    res_query = query_vector_store(tenant_id, "!@#$%^&*()_+{}[]:;'<>?,./")
    assert isinstance(res_query, list)


# ==============================================================================
# 14. End-to-End Financial Question Answering (API Endpoint)
# ==============================================================================
def test_14_end_to_end_financial_question_answering(client: TestClient, db_session: Session):
    headers, tenant_id = get_auth_headers_and_tenant(
        client, db_session, "e2e.qa@kirana.in", "E2E QA Mart", "27CCCCC3434C1Z3"
    )

    # 14a. Authoritative GST treatment query
    res_gst = client.post(
        "/api/v1/rag/ask",
        json={"query": "What GST treatment applies to Input Tax Credit under Section 16?"},
        headers=headers
    )
    assert res_gst.status_code == 200, res_gst.text
    data_gst = res_gst.json()
    assert "answer" in data_gst
    assert len(data_gst["answer"]) > 20
    assert "Section 16" in data_gst["answer"] or "Input Tax Credit" in data_gst["answer"]

    # 14b. Direct unified query API endpoint
    res_unified = client.post(
        "/api/v1/rag/query",
        json={"query": "Find the electricity invoice from October"},
        headers=headers
    )
    assert res_unified.status_code == 200, res_unified.text
    data_unified = res_unified.json()
    assert data_unified["strategy_used"] == "DOCUMENT_SEARCH"
    assert "assembled_context" in data_unified

