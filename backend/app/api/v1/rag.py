from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_tenant
from backend.app.models.user import Tenant
from backend.app.services.rag_service import answer_conversational_assistant, answer_gst_query_with_rag

router = APIRouter()

class RAGQueryRequest(BaseModel):
    query: str
    language: Optional[str] = "English/Hindi"

@router.post("/ask")
async def ask_gst_assistant(
    req: RAGQueryRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Multilingual Conversational AI Financial Assistant powered by BharatCode.
    - Routes general greetings politely without invoking GST lectures.
    - Answers tenant database queries (spend, vendors, balances) using deterministic SQL.
    - Answers accounting questions with Indian double-entry principles.
    - Grounds statutory GST tax questions in the CGST/IGST statute corpus with exact citations.
    """
    res = await answer_conversational_assistant(
        user_query=req.query,
        db=db,
        tenant=tenant,
        language_hint=req.language or "English/Hindi"
    )
    return res
