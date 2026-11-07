# VyaparSetu (व्यापारसेतु) — Final Repository-Wide LLM Provider Audit Report

**Project Name:** VyaparSetu (Lekha)  
**Hackathon:** BharatCode Build League 2026  
**Audit Scope:** Repository-Wide LLM Provider Exclusivity, LangGraph Orchestration, and Security Audit  
**Sole Runtime LLM Provider:** BharatCode Hosted API  
**Designated Model:** `qwen-3.8-27b`  
**Official Endpoint:** `https://bharatcode.ai/api/model/v1/chat/completions`  
**Audit Result:** ✅ **100% PASS — FULL COMPLIANCE VERIFIED**  

---

## 1. Executive Summary

This repository-wide audit confirms that **VyaparSetu** exclusively and unconditionally uses **BharatCode Hosted API (`qwen-3.8-27b`)** as its sole runtime Large Language Model provider.

A rigorous, exhaustive scan of all source files across the frontend and backend confirms that:
1. **Zero third-party LLMs exist:** No SDKs, imports, or API calls to OpenAI, Anthropic, Google Gemini, Groq, Cohere, Mistral, or Ollama are used.
2. **All AI workflows are unified under BharatCode:** The LangGraph supervisor, transaction classification node, agentic command centre, GST statutory RAG, and hybrid knowledge retrieval all invoke `BharatCodeClient`.
3. **Embeddings & deterministic logic are strictly segregated:** Dense vector retrieval utilizes local ChromaDB (`all-MiniLM-L6-v2` ONNX) without delegating embeddings to third-party APIs. Accounting calculations, double-entry voucher balance checks, and Section 170 CGST Act statutory rounding use pure Python `Decimal` arithmetic.
4. **No silent fallbacks in production:** In `PRODUCTION_BHARATCODE` mode, failures raise explicit `BharatCodeAPIError` exceptions and route unclassified items to the human approval queue; the system never substitutes fake responses.
5. **Credential protection:** BharatCode credentials reside exclusively in server-side `.env` files; zero secrets are exposed in the frontend or Git history.

---

## 2. Comprehensive Compliance & Verification Matrix

| # | Requirement | Status | Verification Evidence |
| :-: | :--- | :---: | :--- |
| **1** | **Search entire repository for LLM providers & SDKs** | **PASS** | Repository-wide regex/AST search over all `.py`, `.ts`, `.tsx`, `.js`, `.json`, `.env`, and documentation files found **zero third-party LLMs**. The only occurrences are compliance assertions in test suites and README exclusivity declarations. |
| **2** | **Verify all runtime LLM operations use BharatCode exclusively** | **PASS** | All LLM calls route through [`BharatCodeClient`](file:///c:/Users/karma/Downloads/vyparsetu/backend/app/llm/client.py) targeting `https://bharatcode.ai/api/model/v1/chat/completions` with model `qwen-3.8-27b`. |
| **3** | **Remove/disable alternative runtime LLM integrations** | **PASS** | Confirmed zero alternative runtime LLMs existed in code; no removals needed. Exclusivity is complete. |
| **4** | **Verify LangGraph supervisor, agents, Command Centre, & RAG use BharatCode** | **PASS** | Verified that: <br>• `nodes.py:79` (`classification_node`) invokes `classify_transaction`<br>• `supervisor.py:752` (`classification_agent_node`) invokes `classify_transaction`<br>• `supervisor.py:1533` (`general_query_agent_node`) invokes `generate_completion`<br>• `intent_engine.py:155` (`interpret_intent_with_llm`) invokes `generate_completion`<br>• `rag_service.py:322` (`answer_conversational_assistant`) invokes `chat_completion`<br>• `unified_retriever.py:206` (`answer_with_unified_retrieval`) invokes `generate_completion` |
| **5** | **Distinguish embeddings & deterministic logic from LLM inference** | **PASS** | Embeddings: ChromaDB with local ONNX `all-MiniLM-L6-v2` / deterministic Indic hash (zero LLM token consumption).<br>Deterministic math: Double-entry vouchers balance $\sum \text{Debits} == \sum \text{Credits}$ via pure Python `Decimal`, Section 170 CGST `ROUND_HALF_UP`, Section 17(5) blocked credits, and Place of Supply rules. |
| **6** | **Verify no silent fallback/mock in production mode** | **PASS** | In `PRODUCTION_BHARATCODE` mode, `BharatCodeAPIError` is raised on network or API failures. Transactions route to human review with `confidence_score = 0.0`; zero transactions are auto-posted on error. |
| **7** | **Run live end-to-end application request with evidence** | **PASS** | Executed real HTTP request to FastAPI `/api/v1/workflow/process`. Received genuine `qwen-3.8-27b` inference (`Sales Revenue`, 18% GST, Indic Hindi rationale, Section 9 CGST citation). |
| **8** | **Confirm BharatCode credentials remain backend-only** | **PASS** | `.env` ignored by `.gitignore` (line 9: `*.env`). Git history deep log scan confirmed zero real keys committed. Next.js frontend code contains zero references to `BHARATCODE_API_KEY`. |
| **9** | **Overall Compliance Verdict** | **PASS** | **100% Compliant with BharatCode Build League 2026 Rules.** |

---

## 3. Detailed Audit Findings by Requirement

### Requirement 1 & 2: Repository-Wide LLM Provider Scan
An automated AST and regex scan was performed across every source file in the repository (excluding `.git`, `.venv`, and `node_modules`):
- Prohibited tokens scanned: `openai`, `anthropic`, `google.generativeai`, `gemini`, `groq`, `ollama`, `cohere`, `mistral`, `ChatOpenAI`, `ChatAnthropic`, `api.openai.com`.
- **Scan Result:**
  - `backend/app/` source code: **0 occurrences**
  - `frontend/` source code: **0 occurrences**
  - Occurrences detected were restricted to:
    1. `test_bharatcode_official_api.py:58`: Unit test verifying that forbidden providers do not exist in client code.
    2. `BharatCode.txt` & `README.md`: Architectural documentation declaring exclusivity.

### Requirement 3: Removal / Disabling of Alternative Integrations
- No alternative runtime providers were present in active code paths.
- The backend configuration ([`backend/app/config.py`](file:///c:/Users/karma/Downloads/vyparsetu/backend/app/config.py)) exposes exclusively `BHARATCODE_API_KEY`, `BHARATCODE_BASE_URL`, and `BHARATCODE_MODEL_NAME`.

### Requirement 4: AI Workflows and LangGraph Verification
Every AI-powered component in the application was traced to its caller:
1. **LangGraph Transaction Workflow:**
   - File: [`backend/app/workflows/nodes.py`](file:///c:/Users/karma/Downloads/vyparsetu/backend/app/workflows/nodes.py)
   - Function: `classification_node` (Line 79)
   - Invocation: `await bharatcode_client.classify_transaction(...)`
2. **LangGraph Multi-Agent Supervisor:**
   - File: [`backend/app/workflows/supervisor.py`](file:///c:/Users/karma/Downloads/vyparsetu/backend/app/workflows/supervisor.py)
   - Function: `classification_agent_node` (Line 752) & `general_query_agent_node` (Line 1533)
   - Invocation: `await bharatcode_client.classify_transaction(...)` & `await bharatcode_client.generate_completion(...)`
3. **Command Centre Intent Engine:**
   - File: [`backend/app/services/intent_engine.py`](file:///c:/Users/karma/Downloads/vyparsetu/backend/app/services/intent_engine.py)
   - Function: `interpret_intent_with_llm` (Line 155)
   - Invocation: `await bharatcode_client.generate_completion(...)`
4. **GST Statutory Legal RAG:**
   - File: [`backend/app/services/rag_service.py`](file:///c:/Users/karma/Downloads/vyparsetu/backend/app/services/rag_service.py)
   - Function: `answer_conversational_assistant` (Line 322)
   - Invocation: `await bharatcode_client.chat_completion(...)`
5. **Unified Hybrid RAG & GraphRAG:**
   - File: [`backend/app/services/unified_retriever.py`](file:///c:/Users/karma/Downloads/vyparsetu/backend/app/services/unified_retriever.py)
   - Function: `answer_with_unified_retrieval` (Line 206)
   - Invocation: `await bharatcode_client.generate_completion(...)`

### Requirement 5: Embeddings & Deterministic Engine Segregation
- **Dense Vector Embeddings:** Generated locally using ChromaDB's embedded ONNX runtime (`all-MiniLM-L6-v2`) or deterministic feature-hashing (`DeterministicIndicEmbeddingFunction`). Vector operations are completely decoupled from external LLM API quotas.
- **Deterministic Financial Engine:**
  - Bookkeeping entries are balanced down to the paisa using Python `Decimal`.
  - Automatic double-entry equation check: $\sum \text{Debits} == \sum \text{Credits}$.
  - Place of Supply rules (Section 7 and Section 8 IGST Act) determine CGST+SGST vs IGST deterministically based on merchant and supplier GSTIN state prefixes.
  - Section 17(5) blocked credit filters prevent illegitimate ITC claims deterministically.
  - Section 170 CGST Act `ROUND_HALF_UP` rounding is applied to all tax components.

### Requirement 6: Strict Production Fail-Safe (No Silent Fallback)
In [`backend/app/llm/client.py`](file:///c:/Users/karma/Downloads/vyparsetu/backend/app/llm/client.py):
```python
if is_live_call:
    # Live HTTP streaming with SSE heartbeats
    if response.status_code != 200:
        raise BharatCodeAPIError(...)
```
When running in `PRODUCTION_BHARATCODE` mode:
- If the BharatCode endpoint is unreachable or returns an error, the system raises `BharatCodeAPIError`.
- The transaction state machine assigns `confidence_score = 0.0` and flags the transaction for Human-in-the-Loop review.
- **Zero transactions are auto-posted on AI failure.**
- Offline simulation is restricted strictly to explicit `DEV_SIMULATION` mode and prominently tagged with `"source": "DEV_SIMULATION"`.

### Requirement 7: Live End-to-End Inference Evidence

#### Test 1: Direct BharatCode API Verification (qwen-3.8-27b)
- **Target URL:** `https://bharatcode.ai/api/model/v1/chat/completions`
- **Model Returned:** `qwen-3.8-27b`
- **HTTP Status:** `200 OK`
- **Test Prompt:** *"Classify this transaction: Received ₹5,000 from a customer for an invoice. Return a short JSON classification."*
- **Live Output Sample:**
  ```json
  {
    "category": "Sales Revenue",
    "sub_category": "Customer invoice payment",
    "gst_rate": 18.0,
    "confidence_score": 0.8,
    "rationale": "Customer ne invoice ke liye payment kiya hai, isliye yeh Sales Revenue / income hai. HSN/SAC clear nahi hai, isliye common 18% GST suggested hai.",
    "accounting_suggestions": [
      "Debit: 1020 (Bank Account) or 1010 (Cash in Hand)",
      "Credit: 4010 (Sales Revenue / Outward Taxable Supply)",
      "Credit: Output GST Liability (18.0%) under Section 9 CGST Act."
    ],
    "source": "BHARATCODE_LIVE",
    "live_api": true
  }
  ```

#### Test 2: Full End-to-End Application Stack Request (LangGraph + FastAPI + BharatCode)
- **Endpoint Called:** `POST http://127.0.0.1:8000/api/v1/workflow/process`
- **Tenant Context:** `Sharma Kirana & Hardware Traders` (`d434eaae-238d-448b-bc14-edd041359e1f`)
- **Payload:**
  ```json
  {
    "raw_narration": "Received ₹25,000 via NEFT from Ramesh Construction for concrete supplies invoice",
    "amount": 25000.0,
    "direction": "CREDIT",
    "channel": "NEFT",
    "reference_number": "NEFT-E2E-AUDIT-9921",
    "is_interstate": false
  }
  ```
- **HTTP Response Status:** `200 OK`
- **Application Execution Pipeline:**
  1. API endpoint receives authenticated request with Bearer JWT token.
  2. LangGraph state machine initializes and executes `validate_node` and `deduplication_node`.
  3. LangGraph dispatches `classification_node` to live BharatCode endpoint `https://bharatcode.ai/api/model/v1/chat/completions`.
  4. BharatCode `qwen-3.8-27b` generates authentic vernacular reasoning and classification.
  5. Deterministic financial engine verifies double-entry balance and GST rules.
  6. High confidence ($\ge 0.85$) completes ledger posting.
- **Full End-to-End Response Received:**
  ```json
  {
    "status": "CONFIRMED",
    "category": "Sales Revenue",
    "sub_category": "Concrete Supplies Sales - Invoice Receipt",
    "gst_rate": 18.0,
    "confidence_score": 0.95,
    "ai_source": "BHARATCODE_LIVE",
    "live_api": true,
    "rationale": "Yeh credit entry hai - Ramesh Construction se NEFT ke through ₹25,000 aaya hai concrete supplies invoice ke against. Yeh hamari sales revenue hai, customer ka payment received hua hai. Concrete/ready-mix material supply karte hain toh goods sale hai, GST 18% applicable (HSN 3824 ya 2523 ready-mix concrete). Business expense nahi, balki income hai.",
    "accounting_suggestions": [
      "Debit: 1020 (Bank Account) or 1010 (Cash in Hand)",
      "Credit: 4010 (Sales Revenue / Outward Taxable Supply)",
      "Credit: Output GST Liability (18.0%) under Section 9 CGST Act."
    ]
  }
  ```

### Requirement 8: Credential Isolation & Git Security
- `.env` is completely excluded via `.gitignore` (`*.env` at line 9).
- Git repository history deep scan (`git log -p -S "bc_l" --all`) returned zero committed secrets.
- The Next.js frontend code has zero references to `BHARATCODE_API_KEY`. All LLM communication occurs through secure backend API endpoints.

---

## 4. Final Verdict

| Check | Verdict | Notes |
| :--- | :---: | :--- |
| **Sole Provider** | **PASS** | Only BharatCode (`qwen-3.8-27b`) is used |
| **Architecture** | **PASS** | All agents & RAG workflows route to BharatCode |
| **Determinism** | **PASS** | Math and legal rules decoupled from LLM |
| **Fail-Safe** | **PASS** | No silent mock substitution in production |
| **Security** | **PASS** | Zero credentials exposed in frontend or Git |
| **Submission** | **PASS** | **Ready for BharatCode Build League 2026** |
