# VyaparSetu (व्यापारसेतु)
### AI-Powered Multilingual Bookkeeping, Financial Intelligence & GST Platform for Indian MSMEs
**Developed for the BharatCode Hackathon 2026**

[![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.7-orange.svg)](https://langchain.com)
[![LLM Provider](https://img.shields.io/badge/LLM-BharatCode%20Hosted%20API-emerald.svg)](#)
[![Next.js](https://img.shields.io/badge/Next.js-14.2%20(App%20Router)-black.svg)](https://nextjs.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38bdf8.svg)](https://tailwindcss.com)
[![Tests](https://img.shields.io/badge/Tests-31%2F31%20Passing-brightgreen.svg)](#)
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20BharatCode-purple.svg)](#)

---

## 📌 Problem Statement

Over **63 million micro, small, and medium enterprises (MSMEs)** power 30% of India's GDP, yet they face severe structural hurdles:
1. **Linguistic Complexity & Vernacular Bookkeeping:** Indian shopkeepers and merchants think in mixed Hindi, Hinglish, and local dialects (*"Sharma ji ko cement ke liye 25000 diya"*, *"kiraya"*, *"udhari chukta kiya"*). Conventional accounting software forces rigid, English-first double-entry inputs.
2. **GST Compliance Burden & Cost:** MSMEs struggle to distinguish between intra-state (CGST/SGST) and inter-state (IGST) supplies, miscalculate Section 170 statutory rounding, and inadvertently claim ineligible Input Tax Credit (ITC) blocked under Section 17(5).
3. **Credit Gap & Working Capital Blindness:** Traditional banks demand formal audited financial statements, denying credit to creditworthy micro-merchants whose cash flow is buried in disjointed UPI statements and cash slips.

---

## 💡 The VyaparSetu Solution

**VyaparSetu** bridges the vernacular mercantile reality of Indian MSMEs with enterprise-grade double-entry accounting and statutory tax compliance:

- 🤖 **BharatCode Hosted API as Sole LLM:** Interprets natural mercantile vernacular (*Hinglish*, *Hindi*, *English*) and powers statutory legal RAG grounded in the Central Goods and Services Tax Act, 2017.
- 🔄 **LangGraph Multi-Agent Orchestration:** Autonomous financial state machine routing transactions through validation, SHA-256 deduplication, Indic classification, and confidence-gated ledger posting.
- 🛡️ **Human-in-the-Loop (HITL) Checkpoint:** Low-confidence ($\text{confidence} < 0.85$) or ambiguous transactions halt in a merchant approval queue before ledger commitment.
- 📐 **100% Deterministic Financial Arithmetic:** Financial calculations and double-entry balancing are **never** delegated to LLM hallucination. Built with pure Python `Decimal` enforcing $\sum \text{Debits} == \sum \text{Credits}$ down to the paisa.
- ⚖️ **Statutory GST Engine:** Enforces Section 7/8 Place of Supply, Section 17(5) blocked credit detection, and Section 170 `ROUND_HALF_UP` statutory rounding. Generates simulated GSTR-1 and GSTR-3B tax offset waterfalls.
- 🏢 **Multi-Tenant SaaS Foundation:** Strict tenant data isolation with Role-Based Access Control (`OWNER`, `ADMIN`, `ACCOUNTANT`, `EMPLOYEE`), multi-business accountant access, and global currency/timezone settings.

---

## 🏛️ System Architecture

```
[ Merchant Input / Ingestion ]
   ├─ Multilingual Narration ("Sharma ji ko cement ke liye 25000 cash diya")
   ├─ Bank Statements (CSV / PDF — HDFC, SBI, ICICI)
   └─ Document OCR (Vendor Receipts, Invoices with 15-char GSTINs)
                 │
                 ▼
[ LangGraph Multi-Agent State Machine ]
   ├─ Node 1: Ingestion & Schema Normalization
   ├─ Node 2: SHA-256 Hash Fingerprint Deduplication
   ├─ Node 3: BharatCode Hosted LLM (Sole Indic Model Provider)
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
[ Compliance & Business Intelligence ]
   ├─ Regional GST Engine (Sec 170 Rounding, Sec 17(5) Blocked ITC, GSTR-1 / 3B)
   ├─ BharatCode RAG Assistant (Grounded in CGST & IGST Statutes)
   └─ MSME Working Capital & Credit Health Scoring (0–100 Explainable Rating)
```

---

## ⚡ Quickstart & Local Installation

### Prerequisites
- **Python 3.11+**
- **Node.js 18+ & npm 9+**
- **Git**

### 1. Clone & Set Up Backend
```powershell
# Navigate to project directory
cd c:\Users\karma\Downloads\vyparsetu

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate    # Linux / macOS

# Install backend dependencies
pip install -r requirements.txt

# Configure environment variables
copy .env.example .env
# Edit .env with your BharatCode credentials (BHARATCODE_API_KEY)
```

### 2. Set Up Frontend
```powershell
cd frontend
npm install
cd ..
```

### 3. Launch Services

#### Option A: One-Click Launcher (Windows)
Double-click `start_vyaparsetu.bat` or run:
```powershell
.\start_vyaparsetu.bat
```

#### Option B: Manual Startup

**Terminal 1 — Backend (Port 8000):**
```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend (Port 3000):**
```powershell
cd frontend
npm run dev
```

---

## 🔑 Demo Access & Documentation

- **Frontend App:** [http://localhost:3000](http://localhost:3000)
- **Backend API Docs (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Backend Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Pre-Configured Demo Credentials
| Field | Value |
| :--- | :--- |
| **Email** | `demo@vyaparsetu.in` |
| **Password** | `VyaparSetu@2026` |
| **Workspace** | `Sharma Kirana & Hardware Traders` |
| **Simulated GSTIN** | `27TESTG1234F1Z5` (Maharashtra) |
| **Assigned Role** | `OWNER` |
| **Subscription Plan** | `PRO` (Active) |

*(The login screen also features a 1-click **"Fill Demo"** button for instant access).*

---

## 🧪 Verification & Automated Testing

The complete test suite runs 31 automated tests across 9 test suites verifying the entire system:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

```text
============================= test session starts =============================
collected 31 items

backend/tests/test_auth_and_tenancy.py::test_health_check PASSED         [  3%]
backend/tests/test_auth_and_tenancy.py::test_user_registration_and_automatic_tenant_creation PASSED [  6%]
backend/tests/test_auth_and_tenancy.py::test_user_login PASSED           [  9%]
backend/tests/test_auth_and_tenancy.py::test_create_multiple_workspaces PASSED [ 12%]
backend/tests/test_auth_and_tenancy.py::test_tenant_context_isolation PASSED [ 16%]
backend/tests/test_bharatcode_client.py::test_bharatcode_hinglish_raw_materials_classification PASSED [ 19%]
backend/tests/test_bharatcode_client.py::test_bharatcode_rent_kiraya_classification PASSED [ 22%]
backend/tests/test_bharatcode_client.py::test_bharatcode_salary_classification PASSED [ 25%]
backend/tests/test_bharatcode_client.py::test_bharatcode_ambiguous_low_confidence_classification PASSED [ 29%]
backend/tests/test_bharatcode_client.py::test_bharatcode_gst_statutory_assistant PASSED [ 32%]
backend/tests/test_e2e_full_lifecycle.py::test_full_saas_lifecycle_e2e PASSED [ 35%]
backend/tests/test_financial_engine.py::test_deterministic_gst_split_math PASSED [ 38%]
backend/tests/test_financial_engine.py::test_ledger_posting_and_trial_balance PASSED [ 41%]
backend/tests/test_global_multitenant_and_rbac.py::test_workspace_creation_with_global_settings PASSED [ 45%]
backend/tests/test_global_multitenant_and_rbac.py::test_multi_business_accountant_workflow PASSED [ 48%]
backend/tests/test_global_multitenant_and_rbac.py::test_role_based_access_control_rbac PASSED [ 51%]
backend/tests/test_global_multitenant_and_rbac.py::test_strict_cross_tenant_data_isolation PASSED [ 54%]
backend/tests/test_gst.py::test_place_of_supply_evaluation PASSED        [ 58%]
backend/tests/test_gst.py::test_blocked_itc_under_section_17_5 PASSED    [ 61%]
backend/tests/test_gst.py::test_section_170_statutory_rounding PASSED    [ 64%]
backend/tests/test_gst.py::test_gst_compute_api_endpoint PASSED          [ 67%]
backend/tests/test_gst.py::test_simulated_gstr1_and_gstr3b_reports PASSED [ 70%]
backend/tests/test_ingestion_and_transactions.py::test_generate_and_ingest_synthetic_data PASSED [ 74%]
backend/tests/test_ingestion_and_transactions.py::test_csv_upload_and_deduplication PASSED [ 77%]
backend/tests/test_ingestion_and_transactions.py::test_manual_transaction_creation PASSED [ 80%]
backend/tests/test_rag_analytics_and_saas.py::test_rag_assistant_qa PASSED [ 83%]
backend/tests/test_rag_analytics_and_saas.py::test_cashflow_and_credit_insights PASSED [ 87%]
backend/tests/test_rag_analytics_and_saas.py::test_saas_usage_and_subscription_upgrade PASSED [ 90%]
backend/tests/test_workflow.py::test_langgraph_high_confidence_auto_post PASSED [ 93%]
backend/tests/test_workflow.py::test_langgraph_low_confidence_human_approval_flow PASSED [ 96%]
backend/tests/test_workflow.py::test_duplicate_rejection PASSED          [100%]

============================= 31 passed in 9.56s =============================
```

### Browser E2E Automation (Playwright Headless Chromium)
The automated browser test suite [`verify_browser_e2e.py`](file:///c:/Users/karma/Downloads/vyparsetu/verify_browser_e2e.py) validates all 12 key user flows and captures screenshots saved in [`browser_verification_screenshots/`](file:///c:/Users/karma/Downloads/vyparsetu/browser_verification_screenshots/):
1. `01_landing_page.png` — Marketing overview & language toggle
2. `02_dashboard_executive.png` — Authenticated workspace dashboard
3. `03_transactions_ledger.png` — Multi-channel transaction table
4. `04_invoices_ocr.png` — Entity-extracted receipt document view
5. `05_bookkeeping_agent_run.png` — LangGraph multi-agent execution
6. `06_approvals_queue.png` — Human-in-the-Loop review queue
7. `07_trial_balance_balanced.png` — General ledger trial balance verification
8. `08_reconciliation.png` — Bank vs invoice matching interface
9. `09_financial_statements.png` — Profit & Loss and Balance Sheet
10. `10_gst_workspace.png` — Section 170 calculator and GSTR returns
11. `11_assistant_rag.png` — BharatCode statutory legal citations

---

## 🎤 2-Minute Hackathon Pitch & Presentation Script

### [0:00 - 0:30] The Hook & The Problem
> *"Judges, India has 63 million MSMEs contributing a third of our national GDP. But if you visit a hardware merchant in Kanpur or a kirana store in Jaipur, they don't think in 'debits and credits' or 'harmonized system codes'. They think in Hinglish: 'Sharma ji ko cement ke liye ₹25,000 cash diya'. Because existing software forces rigid English accounting, small merchants end up with bookkeeping backlogs, missed GST ITC claims, and zero credit ratings from banks. Today, we built **VyaparSetu** to solve this once and for all."*

### [0:30 - 1:00] BharatCode AI & LangGraph Multi-Agent Architecture
> *"VyaparSetu is built on a non-negotiable architectural principle: **BharatCode is our sole LLM provider, and mathematical arithmetic is 100% deterministic code**. Watch our LangGraph agent in action: The merchant types natural conversational Hinglish. Node 1 normalizes the data; Node 2 verifies the SHA-256 fingerprint against bank records to stop duplicate charges; Node 3 calls the BharatCode hosted API to map vernacular mercantile terms to standard Indian MSME accounts. If confidence is high, it immediately posts balanced double-entry vouchers. If the entry is ambiguous, our Human-in-the-Loop checkpoint alerts the merchant in their approval queue before anything touches the general ledger."*

### [1:00 - 1:30] Statutory GST Compliance & Ledger Integrity
> *"Look at our double-entry ledger. Every single entry satisfies $\sum \text{Debits} == \sum \text{Credits}$ down to the paisa. In our GST workspace, we strictly implement Section 170 of the CGST Act for half-up rounding, filter blocked credits under Section 17(5), and generate simulated GSTR-1 and GSTR-3B reports with Section 49 priority tax offsets. When a merchant has a tax question, our BharatCode RAG assistant doesn't hallucinate generic internet advice—it cites the exact sub-sections of the Central Goods and Services Tax Act."*

### [1:30 - 2:00] SaaS Scalability & Impact
> *"VyaparSetu is architected from day one as a multi-tenant SaaS product. It supports role-based access control where chartered accountants can manage dozens of client workspaces from a single login, configure international currencies and timezones, and enforce strict tenant-level data isolation. With VyaparSetu, an Indian MSME goes from shoebox receipts and stress to audited books, GST compliance, and bankable creditworthiness. Thank you!"*

---

## 🔒 Security, Compliance & Ethical Standards

- **Exclusivity:** BharatCode is the sole LLM provider; zero external calls or dependencies on OpenAI, Anthropic, or Google Gemini.
- **Data Isolation:** All database tables enforce `tenant_id` foreign keys; cross-tenant query attempts are intercepted and return `HTTP 403 Forbidden`.
- **Credential Safety:** All API secrets and keys reside strictly in server-side `.env` files; zero sensitive tokens exposed in frontend bundles or Git.
- **Statutory Integrity:** Financial arithmetic and tax calculations use deterministic Python `Decimal` with `ROUND_HALF_UP` (Section 170 CGST Act).
- **Transparent Disclosure:** All simulated banking and GST sandbox integrations prominently display compliance warning badges.

---

**Built with pride for the BharatCode Hackathon 2026 🇮🇳**

