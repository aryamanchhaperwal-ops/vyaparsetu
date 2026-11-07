# VyaparSetu (व्यापारसेतु)
### AI-Powered Multilingual Bookkeeping, Financial Intelligence & GST Platform for Indian MSMEs
**Developed for the BharatCode Build League Hackathon 2026**

[![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.7-orange.svg)](https://langchain.com)
[![LLM Provider](https://img.shields.io/badge/LLM-BharatCode%20Qwen%203.8%2027B-emerald.svg)](https://bharatcode.ai)
[![Next.js](https://img.shields.io/badge/Next.js-14.2%20(App%20Router)-black.svg)](https://nextjs.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38bdf8.svg)](https://tailwindcss.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Store-purple.svg)](https://trychroma.com)
[![Tests](https://img.shields.io/badge/Tests-118%20Passing-brightgreen.svg)](#)
[![Compliance](https://img.shields.io/badge/BharatCode%20Compliance-100%25%20Verified-blue.svg)](#)

---

## 📌 Problem Statement

Over **63 million micro, small, and medium enterprises (MSMEs)** power 30% of India's GDP, yet they face severe structural hurdles:
1. **Linguistic Complexity & Vernacular Bookkeeping:** Indian shopkeepers and merchants think in mixed Hindi, Hinglish, and local dialects (*"Sharma ji ko cement ke liye 25000 diya"*, *"kiraya"*, *"udhari chukta kiya"*). Conventional accounting software forces rigid, English-first double-entry inputs.
2. **GST Compliance Burden & Cost:** MSMEs struggle to distinguish between intra-state (CGST/SGST) and inter-state (IGST) supplies, miscalculate Section 170 statutory rounding, and inadvertently claim ineligible Input Tax Credit (ITC) blocked under Section 17(5).
3. **Credit Gap & Working Capital Blindness:** Traditional banks demand formal audited financial statements, denying credit to creditworthy micro-merchants whose cash flow is buried in disjointed UPI statements and cash slips.

---

## 💡 The VyaparSetu Solution

**VyaparSetu** bridges the vernacular mercantile reality of Indian MSMEs with enterprise-grade double-entry accounting and statutory tax compliance:

- 🤖 **BharatCode (`qwen-3.8-27b`) as Sole Runtime LLM:** Interprets natural mercantile vernacular (*Hinglish*, *Hindi*, *English*) and powers statutory legal RAG grounded in the Central Goods and Services Tax Act, 2017.
- 🔄 **LangGraph Multi-Agent Orchestration:** Autonomous financial supervisor coordinating specialized agents across validation, deduplication, Indic classification, and confidence-gated ledger posting.
- 🛡️ **Human-in-the-Loop (HITL) Checkpoint:** Low-confidence ($\text{confidence} < 0.85$) or ambiguous transactions halt in a merchant approval queue before ledger commitment (0 auto-posted entries without explicit sign-off).
- 📐 **100% Deterministic Financial Arithmetic:** Financial calculations and double-entry balancing are **never** delegated to LLM hallucination. Built with pure Python `Decimal` enforcing $\sum \text{Debits} == \sum \text{Credits}$ down to the paisa.
- ⚖️ **Statutory GST Engine:** Enforces Section 7/8 Place of Supply, Section 17(5) blocked credit detection, and Section 170 `ROUND_HALF_UP` statutory rounding. Generates simulated GSTR-1 and GSTR-3B tax offset waterfalls.
- 🏢 **Multi-Tenant SaaS Foundation:** Strict tenant data isolation with Role-Based Access Control (`OWNER`, `ADMIN`, `ACCOUNTANT`, `EMPLOYEE`), multi-business accountant access, and global currency/timezone settings.

---

## 🚀 Key Modules & Capabilities

### 1. Unified Command Centre & Agentic Financial Chatbot
- **Natural Language Financial Operations:** Direct query dispatching using BharatCode intent classification without rigid command templates.
- **Multimodal Inputs:** Spoken audio, live microphone transcription, text queries, and multi-file attachments.
- **Dynamic Execution Streams:** Interactive visual result cards for vendor spend rankings, reconciliation discrepancies, cash flow runways, and monthly closes.

### 2. Multi-Agent LangGraph Supervisor Architecture
- **Central Supervisor Node:** Evaluates incoming mercantile requests and dynamically delegates to 7 specialized domain agents:
  1. `Classification Agent`: Maps raw narrations and UPI handles to Indian Chart of Accounts.
  2. `Reconciliation Agent`: Matches bank outflows to supplier invoices within threshold tolerances.
  3. `GST Compliance Agent`: Validates tax rates, HSN/SAC codes, and Section 17(5) blocked credits.
  4. `Ledger & Journal Agent`: Posts balanced double-entry vouchers down to the paisa.
  5. `Analytics & Anomaly Agent`: Monitors cash burn, Section 40A(3) cash ceilings, and duplicates.
  6. `Audit & Closing Agent`: Coordinates end-of-period closing checklists and review halts.
  7. `Statutory Advisory Agent`: Grounds responses in official CGST/IGST statutes.

### 3. Persistent ChromaDB + Advanced Hybrid RAG & GraphRAG
- **ChromaDB Vector Store:** Embedded tenant isolation with persistent local disk storage.
- **Reciprocal Rank Fusion (RRF):** Blends semantic vector search with BM25 lexical keyword matching.
- **Interactive Multi-Entity Knowledge Graph:** 10 tenant-scoped entities (`BUSINESS`, `VENDOR`, `CUSTOMER`, `INVOICE`, `TRANSACTION`, `LEDGER_ACCOUNT`, etc.) connected by 9 verified relationship types on an interactive canvas.

### 4. Robust Document Ingestion Pipeline
- **Two-Phase Ingestion Workflow:** Step 1 performs non-destructive parsing and row-level validation (`POST /api/v1/ingestion/preview`); Step 2 commits confirmed rows and automatically posts balanced ledger vouchers (`POST /api/v1/ingestion/confirm`).
- **Multi-Format Support:** Ingests CSV, multi-sheet Excel workbooks (`.xlsx`), and PDF bank statements with leading header cleanup.

### 5. Multilingual & Vernacular Voice Interface
- **Browser-Native Web Speech Integration:** Speech recognition and speech synthesis (`hi-IN`, `en-IN`, `en-US`) with editable transcripts and progress feedback.
- **Voice Bookkeeping Workbench:** Spoken mercantile narration (e.g. *"Goyal Traders ko cement ke liye 35000 rupaye cash me diye"*) parsed into structured vouchers.

---

## 🏛️ System Architecture

```
[ Merchant Input / Ingestion ]
   ├─ Multilingual Narration ("Sharma ji ko cement ke liye 25000 cash diya")
   ├─ Bank Statements (CSV / Excel / PDF — SBI, HDFC, ICICI)
   └─ Document OCR (Vendor Receipts, Invoices with 15-char GSTINs)
                 │
                 ▼
[ Next.js Frontend (BFF Architecture) ]
   ├─ Port 3000 / Relative Proxy to /api/v1/*
   └─ Zero Client-Side Secret Exposure (No API Keys in Browser)
                 │
                 ▼
[ LangGraph Multi-Agent Supervisor (FastAPI Backend) ]
   ├─ Node 1: Ingestion & Schema Normalization
   ├─ Node 2: SHA-256 Hash Fingerprint Deduplication
   ├─ Node 3: BharatCode Hosted API (Sole Indic LLM: qwen-3.8-27b)
   │           └─ Multilingual Mercantile Taxonomy Mapping
   ├─ Node 4: Confidence Router
   │           ├─ Score ≥ 0.85  ──► Auto-Approve & Post to Ledger
   │           └─ Score < 0.85  ──► [ Human-in-the-Loop (HITL) Approval Queue ]
   │                                     │ (Merchant Sign-off / Correction)
   │                                     └──► Post to Ledger
   └─ Node 5: Reconciliation Engine
               └─ Matches Outflows with Unlinked Invoices (within ±₹10)
                 │
                 ▼
[ Deterministic Double-Entry Ledger Engine ]
   ├─ 18 Standard Indian MSME Accounts (Assets, Liabilities, Equity, Revenue, Expense)
   ├─ Strict Mathematical Balance: Σ Debits == Σ Credits
   ├─ Real-Time Trial Balance Generator
   └─ Financial Statements (Profit & Loss + Balance Sheet)
                 │
                 ▼
[ Hybrid RAG & Knowledge Graph Engine ]
   ├─ Persistent ChromaDB Vector Store
   ├─ Reciprocal Rank Fusion (BM25 + Semantic Search)
   └─ Multi-Entity Graph RAG & Visualizer
```

---

## 🛠️ Quickstart & Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/<owner>/vyaparsetu.git
cd vyaparsetu
```

### 2. Configure Environment Variables
Copy the template configuration file:
```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:
```env
# Application Settings
PROJECT_NAME="VyaparSetu"
ENVIRONMENT="development"
DEBUG=true
API_V1_STR="/api/v1"

# Database Configuration
DATABASE_URL="sqlite:///./vyaparsetu.db"

# JWT Authentication
SECRET_KEY="your-random-jwt-secret-key-change-in-production"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# BharatCode Hosted LLM Configuration (Sole Runtime LLM Provider)
BHARATCODE_API_KEY="your_actual_bharatcode_api_key_here"
BHARATCODE_BASE_URL="https://bharatcode.ai/api/model/v1"
BHARATCODE_MODEL_NAME="qwen-3.8-27b"

# AI Mode: PRODUCTION_BHARATCODE or DEV_SIMULATION
AI_MODE="PRODUCTION_BHARATCODE"

# Storage
STORAGE_DIR="./storage"
```

### 3. Backend Setup
```bash
# Create and activate Python virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend will be available at `http://127.0.0.1:8000` with interactive Swagger docs at `http://127.0.0.1:8000/docs`.

### 4. Frontend Setup
In a new terminal:
```bash
cd frontend
npm install
npm run build
npm start
```
The frontend will be available at `http://localhost:3000`.

---

## 🧪 Automated Test Suite

Run the full automated test suite (118+ tests):

```bash
# Run all backend tests
pytest backend/tests/ -v

# Run official BharatCode compliance tests specifically
pytest backend/tests/test_bharatcode_official_api.py -v
```

### Verified Test Categories:
- `test_bharatcode_official_api.py`: Official endpoint, live Qwen 3.8 27B inference, zero alternative LLMs.
- `test_supervisor_orchestration.py`: LangGraph supervisor routing across all 7 specialized agents.
- `test_advanced_rag_and_graph.py`: ChromaDB vector search, BM25, and GraphRAG.
- `test_agentic_financial_chatbot.py`: Natural language command center & multi-turn intent handling.
- `test_milestone3_voice_workflow_e2e.py`: Speech recognition and vernacular audio parsing.
- `test_auth_and_tenancy.py`: Tenant isolation and RBAC.
- `test_gst.py`: Place of supply, Section 17(5) blocked credits, and Section 170 rounding.

---

## 🔒 Security, Compliance & Ethical Standards

- **Exclusivity:** BharatCode API (`https://bharatcode.ai/api/model/v1/chat/completions`) using model `qwen-3.8-27b` is the **sole runtime LLM provider**. Zero dependencies on OpenAI, Anthropic, Gemini, Ollama, or local models.
- **Zero Credential Exposure:** All secret tokens and keys reside strictly in server-side `.env` files. The frontend client bundle contains zero API keys.
- **Fail-Safe Policy:** When live inference is unavailable, the system explicitly raises `BharatCodeAPIError` and routes transactions to human review with 0 auto-posted entries. It never silently substitutes mock data or alternate models in production mode.
- **Deterministic Arithmetic:** All bookkeeping vouchers and tax calculations use Python `Decimal` with Section 170 `ROUND_HALF_UP` statutory compliance.

---

**Built with pride for the BharatCode Build League Hackathon 2026 🇮🇳**
