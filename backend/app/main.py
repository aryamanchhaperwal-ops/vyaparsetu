from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.core.init_db import init_db
from backend.app.api.v1 import auth, tenants, ingestion, transactions, ledger, ocr, workflow, gst, rag, analytics, subscription

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(drop_all=False)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered multilingual bookkeeping, financial intelligence and GST assistance platform for Indian MSMEs.",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware (Frontend Next.js connection)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "ai_mode": getattr(settings, "AI_MODE", "DEV_SIMULATION"),
        "ai_model": settings.BHARATCODE_MODEL_NAME,
        "llm_provider": "BharatCode Hosted API",
        "orchestration": "LangGraph",
        "storage": "Local & Multi-Tenant Partitioned",
        "compliance": "Simulated Indian GST & Banking Sandbox"
    }

# Include API v1 Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication & Workspaces"])
app.include_router(tenants.router, prefix=f"{settings.API_V1_STR}/tenants", tags=["Tenants"])
app.include_router(ingestion.router, prefix=f"{settings.API_V1_STR}/ingestion", tags=["Ingestion & Statement Parser"])
app.include_router(transactions.router, prefix=f"{settings.API_V1_STR}/transactions", tags=["Transactions Ledger"])
app.include_router(ledger.router, prefix=f"{settings.API_V1_STR}/ledger", tags=["Double-Entry Bookkeeping Ledger"])
app.include_router(ocr.router, prefix=f"{settings.API_V1_STR}/ocr", tags=["Receipt & Invoice OCR Ingestion"])
app.include_router(workflow.router, prefix=f"{settings.API_V1_STR}/workflow", tags=["LangGraph Multi-Agent Workflow"])
app.include_router(gst.router, prefix=f"{settings.API_V1_STR}/gst", tags=["Deterministic GST Engine & Simulated Returns"])
app.include_router(rag.router, prefix=f"{settings.API_V1_STR}/rag", tags=["Multilingual RAG GST Assistant"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_STR}/analytics", tags=["Cash Flow & MSME Credit Analytics"])
app.include_router(subscription.router, prefix=f"{settings.API_V1_STR}/subscription", tags=["SaaS Tiers & Audit Trail"])
