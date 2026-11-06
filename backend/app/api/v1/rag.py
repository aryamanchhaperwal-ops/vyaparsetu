from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends

from backend.app.core.dependencies import get_current_tenant
from backend.app.models.user import Tenant
from backend.app.services.rag_service import answer_gst_query_with_rag

router = APIRouter()

class RAGQueryRequest(BaseModel):
    query: str
    language: Optional[str] = "English/Hindi"

@router.post("/ask")
async def ask_gst_assistant(
    req: RAGQueryRequest,
    tenant: Tenant = Depends(get_current_tenant)
):
    """
    Multilingual RAG GST and Accounting Assistant powered exclusively by BharatCode.
    Answers grounded in official CGST/IGST statutes with explicit section citations.
    """
    res = await answer_gst_query_with_rag(
        user_query=req.query,
        language_hint=req.language or "English/Hindi"
    )
    return res
