from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_tenant
from backend.app.models.user import Tenant
from backend.app.services.rag_service import answer_conversational_assistant
from backend.app.services.unified_retriever import unified_retrieve, answer_with_unified_retrieval
from backend.app.services.vector_store import (
    ingest_document_to_vector_store,
    list_tenant_documents,
    delete_document_from_vector_store
)
from backend.app.services.graph_rag import find_vendor_payment_trail, find_unreconciled_transaction_trail

router = APIRouter()


class RAGQueryRequest(BaseModel):
    query: str
    language: Optional[str] = "English/Hindi"
    force_strategy: Optional[str] = None


@router.post("/ask")
async def ask_gst_assistant(
    req: RAGQueryRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Multilingual Conversational AI Financial Assistant powered by BharatCode and Unified Retrieval.
    - Routes general greetings politely without invoking GST lectures.
    - Answers tenant database queries (spend, vendors, balances) using deterministic SQL.
    - Grounds statutory GST tax questions in the CGST/IGST statute corpus with exact citations.
    - Uses Unified Hybrid Graph + Vector RAG when detailed evidence retrieval is needed.
    """
    # Use unified retrieval engine for deep questions
    if any(k in req.query.lower() for k in ["find", "invoice", "payment", "which", "why", "section 16", "section 17", "unreconciled"]):
        res = await answer_with_unified_retrieval(
            db=db,
            tenant=tenant,
            query=req.query,
            language=req.language or "en"
        )
        return res

    res = await answer_conversational_assistant(
        user_query=req.query,
        db=db,
        tenant=tenant,
        language_hint=req.language or "English/Hindi"
    )
    return res


@router.post("/query")
async def execute_unified_retrieval(
    req: RAGQueryRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Direct Unified Retrieval Endpoint:
    Dispatches across ChromaDB Vector Search, BM25 Keyword Search, and Knowledge Graph RAG.
    Returns structured provenance, citations, graph entities, and strategy used without LLM generation.
    """
    bundle = await unified_retrieve(
        db=db,
        tenant_id=tenant.id,
        query=req.query,
        force_strategy=req.force_strategy
    )
    return bundle


@router.get("/documents")
def list_indexed_documents(
    tenant: Tenant = Depends(get_current_tenant)
):
    """Lists all documents indexed in the persistent ChromaDB vector store for the active tenant."""
    docs = list_tenant_documents(tenant_id=tenant.id)
    return {
        "tenant_id": tenant.id,
        "total_documents": len(docs),
        "documents": docs
    }


@router.post("/documents/upload")
async def upload_document_to_vector_store(
    file: UploadFile = File(...),
    doc_type: Optional[str] = Form(None),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Uploads and indexes a document (PDF, CSV, Excel, TXT) into ChromaDB persistent storage."""
    content = await file.read()
    res = ingest_document_to_vector_store(
        tenant_id=tenant.id,
        filename=file.filename or "uploaded_doc",
        content_bytes=content,
        doc_type=doc_type
    )
    return res


@router.delete("/documents/{doc_id}")
def delete_indexed_document(
    doc_id: str,
    tenant: Tenant = Depends(get_current_tenant)
):
    """Deletes an indexed document and all its chunks from the persistent vector store."""
    deleted_chunks = delete_document_from_vector_store(tenant_id=tenant.id, doc_id=doc_id)
    return {
        "tenant_id": tenant.id,
        "doc_id": doc_id,
        "deleted_chunks": deleted_chunks,
        "status": "DELETED" if deleted_chunks > 0 else "NOT_FOUND"
    }


@router.get("/graph-trail")
def get_graph_trail(
    query: str,
    trail_type: str = "vendor",  # "vendor" or "reconciliation"
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Retrieves relational graph trails (Vendor payment trail or Unreconciled transaction trail)."""
    if trail_type == "reconciliation":
        return find_unreconciled_transaction_trail(db, tenant.id, transaction_query=query)
    return find_vendor_payment_trail(db, tenant.id, vendor_query=query)
