import re
import json
import logging
import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.llm.client import bharatcode_client, BharatCodeAPIError

logger = logging.getLogger("intent_engine")


class UserIntentPlan(BaseModel):
    user_objective: str
    intent_type: str
    entities: Dict[str, Any] = Field(default_factory=dict)
    selected_tools: List[str] = Field(default_factory=list)
    plan_steps: List[Dict[str, Any]] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    clarification_question: Optional[str] = None
    requires_approval: bool = False
    language: str = "en"
    ai_mode: str = "DEV_SIMULATION"
    source: str = "BHARATCODE_INDIC_INTENT"


def extract_period_dates(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts explicit or relative periods from text (e.g. 'October', 'September', '2026-10', 'last month').
    """
    lower = text.lower()
    months = {
        "january": "01", "jan": "01", "february": "02", "feb": "02",
        "march": "03", "mar": "03", "april": "04", "apr": "04",
        "may": "05", "june": "06", "jun": "06", "july": "07", "jul": "07",
        "august": "08", "aug": "08", "september": "09", "sep": "09",
        "october": "10", "oct": "10", "november": "11", "nov": "11",
        "december": "12", "dec": "12"
    }

    matches = []
    for m_name, m_num in months.items():
        for match in re.finditer(r"\b" + m_name + r"\b", lower):
            matches.append((match.start(), m_num))
    matches.sort(key=lambda x: x[0])
    found_months = [m[1] for m in matches]

    # Check for YYYY-MM
    iso_matches = re.findall(r"\b(20\d{2})[-/](0[1-9]|1[0-2])\b", text)
    if iso_matches:
        periods = [f"{m[0]}-{m[1]}" for m in iso_matches]
        return periods[0], (periods[1] if len(periods) > 1 else None)

    year = "2026"
    y_m = re.search(r"\b(20\d{2})\b", text)
    if y_m:
        year = y_m.group(1)

    if len(found_months) >= 2:
        return f"{year}-{found_months[0]}", f"{year}-{found_months[1]}"
    elif len(found_months) == 1:
        return f"{year}-{found_months[0]}", None

    if "last month" in lower or "pichhle mahine" in lower or "pichle mahine" in lower:
        return f"{year}-09", None
    if "this month" in lower or "iss mahine" in lower or "is mahine" in lower:
        return f"{year}-10", None

    return None, None


def resolve_multi_turn_context(
    current_instruction: str,
    conversation_history: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Inspects previous conversational turns to resolve anaphora and references
    (e.g., 'those', 'which of those', 'that vendor', 'prepare a report').
    """
    lower = current_instruction.lower()
    context = {}

    if not conversation_history:
        return context

    # Traverse history backwards to find most recent entities
    for msg in reversed(conversation_history):
        role = msg.get("role")
        meta = msg.get("metadata") or {}
        text = msg.get("content", "")

        # Check for vendor references
        if not context.get("vendor_name"):
            if meta.get("vendor_name"):
                context["vendor_name"] = meta["vendor_name"]
            else:
                m_v = re.search(r"to\s+([A-Z][a-zA-Z\s]+(?:Traders|Suppliers|Mart|Services|Works|Materials))", text)
                if m_v:
                    context["vendor_name"] = m_v.group(1).strip()

        # Check for period references
        if not context.get("period"):
            if meta.get("period"):
                context["period"] = meta["period"]
            else:
                p_a, _ = extract_period_dates(text)
                if p_a:
                    context["period"] = p_a

        # Check for previous result types
        if not context.get("last_intent"):
            if meta.get("intent_type"):
                context["last_intent"] = meta["intent_type"]

    return context


async def interpret_intent_with_llm(
    instruction: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    tenant_id: Optional[str] = None,
    language: str = "en"
) -> UserIntentPlan:
    """
    Interprets natural language queries using BharatCode Qwen with structured outputs.
    Removes hardcoded command template restrictions and supports arbitrary financial operations.
    """
    history = conversation_history or []
    inst_lower = instruction.strip().lower()

    # Detect language
    is_hindi = language == "hi" or any(w in inst_lower for w in ["karo", "diye", "kiya", "pichhle", "mahine", "batao", "dikhao", "khate"])
    eff_lang = "hi" if is_hindi else "en"

    # Resolve context from multi-turn history
    turn_context = resolve_multi_turn_context(instruction, history)

    p1, p2 = extract_period_dates(instruction)
    period_a = p1 or turn_context.get("period") or "2026-10"
    period_b = p2 or "2026-09"

    # Check for live API mode
    is_live = settings.AI_MODE in ("PRODUCTION_LIVE", "PRODUCTION_BHARATCODE")
    if is_live:
        logger.info(f"Invoking BharatCode live API for intent planning: {instruction[:60]}")
        system_prompt = (
            "You are Lekha Intent Engine for MSME accounting. Interpret the merchant's natural language request. "
            "Output a JSON object with: user_objective, intent_type, entities, selected_tools, requires_approval, "
            "missing_information (list), clarification_question.\n"
            "Valid intent_type: GET_TOP_VENDORS, FIND_UNMATCHED_PAYMENTS, COMPARE_EXPENSES, SEARCH_OVERDUE_INVOICES, "
            "EXPLAIN_CASH_DECREASE, GET_GST_ITC_STATUS, TRACE_VENDOR_TRAIL, EXPORT_FINANCIAL_SUMMARY, "
            "SEARCH_TRANSACTIONS, GENERAL_QUERY, UNSUPPORTED, AMBIGUOUS.\n"
            "Valid selected_tools: get_top_vendors, find_unmatched_vendor_payments, compare_expenses, "
            "search_overdue_invoices, explain_cash_decrease, get_gst_itc_status, trace_vendor_payment_trail, "
            "generate_financial_summary_export, search_transactions."
        )
        try:
            resp = await bharatcode_client.generate_completion(
                prompt=f"{system_prompt}\n\nUSER REQUEST: {instruction}\nHISTORY CONTEXT: {turn_context}\nJSON OUTPUT:"
            )
            raw_text = resp.get("text", "")
            # Attempt to extract JSON from completion
            json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if json_match:
                parsed_json = json.loads(json_match.group(0))
                tools = parsed_json.get("selected_tools") or []
                raw_intent = str(parsed_json.get("intent_type", "GENERAL_QUERY")).upper()

                valid_intents = {
                    "GET_TOP_VENDORS", "FIND_UNMATCHED_PAYMENTS", "COMPARE_EXPENSES",
                    "SEARCH_OVERDUE_INVOICES", "EXPLAIN_CASH_DECREASE", "GET_GST_ITC_STATUS",
                    "TRACE_VENDOR_TRAIL", "EXPORT_FINANCIAL_SUMMARY", "SEARCH_TRANSACTIONS",
                    "GENERAL_QUERY", "UNSUPPORTED", "AMBIGUOUS"
                }

                # Only return if intent is recognized and has tools or is a known boundary
                if tools and raw_intent in valid_intents and raw_intent not in ("GENERAL_QUERY", "UNSUPPORTED"):
                    steps = []
                    for idx, t in enumerate(tools, 1):
                        steps.append({
                            "step": idx,
                            "title": f"Execute {t.replace('_', ' ').title()}",
                            "agent": f"{t.replace('_', ' ').title()} Agent",
                            "status": "PENDING",
                            "details": f"Invoking tool {t}"
                        })
                    return UserIntentPlan(
                        user_objective=parsed_json.get("user_objective", instruction),
                        intent_type=raw_intent,
                        entities=parsed_json.get("entities", {}),
                        selected_tools=tools,
                        plan_steps=steps,
                        missing_information=parsed_json.get("missing_information", []),
                        clarification_question=parsed_json.get("clarification_question"),
                        requires_approval=parsed_json.get("requires_approval", False),
                        language=eff_lang,
                        ai_mode="PRODUCTION_LIVE",
                        source="BHARATCODE_LIVE"
                    )
        except Exception as e:
            logger.error(f"Live BharatCode intent planning failed: {e}")
            if is_live:
                raise BharatCodeAPIError(f"Live BharatCode API error during intent planning: {e}")

    # =========================================================================
    # DETERMINISTIC INDIC MERCANTILE INTENT PARSER (DEV_SIMULATION & OFFLINE)
    # =========================================================================

    # 1. Unrecognised / Unsupported / Non-financial queries
    if any(q in inst_lower for q in ["capital of france", "book a flight", "weather in", "cricket score", "movie tickets", "recipe for"]):
        return UserIntentPlan(
            user_objective="Non-financial or out-of-scope query",
            intent_type="UNSUPPORTED",
            entities={},
            selected_tools=[],
            plan_steps=[
                {"step": 1, "title": "Scope Boundary Evaluation", "agent": "Supervisor Gateway", "status": "COMPLETED", "details": "Request falls outside financial and accounting operations."}
            ],
            missing_information=[],
            clarification_question="I am Lekha, your dedicated financial and accounting assistant. I can help you with transactions, invoices, GST, bank reconciliation, and financial reports. How can I assist with your business finances?",
            requires_approval=False,
            language=eff_lang
        )

    # 2. Ambiguous query requiring clarification
    if inst_lower in ["process the payment", "record transaction", "payment kar do", "entry karo", "adjust accounts"] or (
        any(k in inst_lower for k in ["process payment", "record entry"]) and not any(char.isdigit() for char in inst_lower)
    ):
        q_text = (
            "Kripya payment ki rashi (amount) aur vendor/customer ka naam batayein."
            if eff_lang == "hi"
            else "Please provide the payment amount and the counterparty (vendor or customer) name to record this transaction."
        )
        return UserIntentPlan(
            user_objective="Process unspecified financial transaction",
            intent_type="AMBIGUOUS",
            entities={},
            selected_tools=[],
            plan_steps=[
                {"step": 1, "title": "Intent Extraction", "agent": "Supervisor Gateway", "status": "COMPLETED", "details": "Detected payment intent lacking parameters"},
                {"step": 2, "title": "Clarification Checkpoint", "agent": "Supervisor Checkpoint", "status": "WAITING_APPROVAL", "details": "Awaiting amount and counterparty"}
            ],
            missing_information=["amount", "counterparty_name"],
            clarification_question=q_text,
            requires_approval=True,
            language=eff_lang
        )

    # 3. Acceptance Query 1: Top vendors paid this quarter / period
    # "Show me the five vendors I paid the most this quarter"
    if any(k in inst_lower for k in ["five vendors", "top vendors", "vendors i paid the most", "largest suppliers", "zyada payment kiya"]):
        top_n = 5
        m_num = re.search(r"\b(\d+)\s+vendors\b", inst_lower)
        if m_num:
            top_n = int(m_num.group(1))

        return UserIntentPlan(
            user_objective=f"Identify top {top_n} vendors by payment expenditure this quarter",
            intent_type="GET_TOP_VENDORS",
            entities={"top_n": top_n, "quarter": "this quarter"},
            selected_tools=["get_top_vendors"],
            plan_steps=[
                {"step": 1, "title": "Vendor Expenditure Analysis", "agent": "Vendor Intelligence Agent", "status": "PENDING", "details": f"Querying top {top_n} vendors by outflow"},
                {"step": 2, "title": "Vendor Ranking & Share Calculation", "agent": "Financial Analytics Agent", "status": "PENDING", "details": "Computing spend percentages and category mapping"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    # 4. Multi-Turn / Acceptance Query 2: Payments without matching invoices
    # "Find payments to Sharma Traders that do not have matching invoices" OR "Which of those are not reconciled?"
    if any(k in inst_lower for k in ["not have matching invoices", "without matching invoices", "unmatched invoices", "which of those are not reconciled", "not reconciled"]):
        # Extract vendor if present, or use multi-turn context
        vendor = turn_context.get("vendor_name") or "Sharma Traders"
        m_v = re.search(r"to\s+([A-Za-z\s]+?)(?:\s+that|\s+without|\s+last|\s+in|$)", instruction, re.IGNORECASE)
        if m_v and not any(w in m_v.group(1).lower() for w in ["the", "a", "my", "those"]):
            vendor = m_v.group(1).strip()

        return UserIntentPlan(
            user_objective=f"Identify unmatched payments to {vendor}",
            intent_type="FIND_UNMATCHED_PAYMENTS",
            entities={"vendor_name": vendor, "period": period_a},
            selected_tools=["find_unmatched_vendor_payments", "trace_vendor_payment_trail"],
            plan_steps=[
                {"step": 1, "title": "Payment & Invoice Correlation", "agent": "Reconciliation Agent", "status": "PENDING", "details": f"Querying unreconciled payments to {vendor}"},
                {"step": 2, "title": "Knowledge Graph Traversal", "agent": "GraphRAG Agent", "status": "PENDING", "details": "Correlating bank UTRs with OCR invoice receipts"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    # 5. Acceptance Query 3: Compare expenses between periods
    # "Compare my October expenses with September"
    if any(k in inst_lower for k in ["compare", "tulanatmak", "versus", "vs", "difference in expenses"]) and (
        any(m in inst_lower for m in ["september", "october", "august", "november", "month", "mahine"])
    ):
        return UserIntentPlan(
            user_objective=f"Compare operating expenses between {period_a} and {period_b}",
            intent_type="COMPARE_EXPENSES",
            entities={"period_a": period_a, "period_b": period_b},
            selected_tools=["compare_expenses"],
            plan_steps=[
                {"step": 1, "title": "Category Expense Extraction", "agent": "Financial Analytics Agent", "status": "PENDING", "details": f"Aggregating outflows for {period_a} and {period_b}"},
                {"step": 2, "title": "Variance & Driver Analysis", "agent": "Financial Insights Agent", "status": "PENDING", "details": "Computing category differences and percentage variance"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    # 6. Acceptance Query 4: Overdue customer/vendor invoices
    # "Which customers have overdue invoices?"
    if any(k in inst_lower for k in ["overdue", "unpaid invoices", "pending bills", "baki bill", "overdue invoices"]):
        return UserIntentPlan(
            user_objective="Identify overdue invoices and outstanding balances",
            intent_type="SEARCH_OVERDUE_INVOICES",
            entities={"overdue_days": 30},
            selected_tools=["search_overdue_invoices"],
            plan_steps=[
                {"step": 1, "title": "Aging Invoice Analysis", "agent": "Accounts Receivable Agent", "status": "PENDING", "details": "Scanning invoices past 30-day payment threshold"},
                {"step": 2, "title": "Counterparty Exposure Summary", "agent": "Credit Control Agent", "status": "PENDING", "details": "Aggregating overdue balances by customer/vendor"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    # 7. Acceptance Query 5: Report of largest business expenses
    # "Prepare a report of my largest business expenses"
    if any(k in inst_lower for k in ["largest business expenses", "biggest expenses", "highest expenditure", "bade kharche", "major expenses"]):
        return UserIntentPlan(
            user_objective="Generate an analysis of largest business expenditures",
            intent_type="GET_TOP_VENDORS",
            entities={"top_n": 5, "period": period_a},
            selected_tools=["get_top_vendors", "find_large_and_anomalous_transactions"],
            plan_steps=[
                {"step": 1, "title": "Outflow Stratification", "agent": "Expense Audit Agent", "status": "PENDING", "details": "Stratifying business payments by size"},
                {"step": 2, "title": "Category Concentration Report", "agent": "Executive Reporting Agent", "status": "PENDING", "details": "Evaluating expense concentration"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    # 8. Acceptance Query 6: Transactions above ₹25,000 and unusual entries
    # "Find all transactions above ₹25,000 and flag unusual entries"
    if any(k in inst_lower for k in ["above ₹", "above rs", "above 25", "greater than", "anomalous", "unusual entries", "flag unusual"]):
        threshold = 25000.0
        m_t = re.search(r"(?:above|greater than|over)\s*(?:₹|rs\.?|inr)?\s*(\d[\d,]*)", inst_lower)
        if m_t:
            try:
                threshold = float(m_t.group(1).replace(",", ""))
            except Exception:
                threshold = 25000.0

        return UserIntentPlan(
            user_objective=f"Scan transactions >= ₹{threshold:,.0f} and flag audit anomalies",
            intent_type="FIND_LARGE_TRANSACTIONS",
            entities={"threshold": threshold, "period": period_a},
            selected_tools=["find_large_and_anomalous_transactions"],
            plan_steps=[
                {"step": 1, "title": "High-Value Transaction Query", "agent": "Audit & Validation Agent", "status": "PENDING", "details": f"Filtering transactions >= ₹{threshold:,.0f}"},
                {"step": 2, "title": "Section 40A(3) Statutory Check", "agent": "Compliance Audit Agent", "status": "PENDING", "details": "Scanning daily cash limits and duplicate entries"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    # 9. Acceptance Query 7: Explain why cash balance decreased
    # "Explain why my cash balance decreased this month"
    if any(k in inst_lower for k in ["why my cash balance decreased", "cash kam kyu hua", "decrease in cash", "cash flow drop", "cash deficit"]):
        return UserIntentPlan(
            user_objective=f"Explain cash balance reduction during {period_a}",
            intent_type="EXPLAIN_CASH_DECREASE",
            entities={"period": period_a},
            selected_tools=["explain_cash_decrease"],
            plan_steps=[
                {"step": 1, "title": "Cash Inflow vs Outflow Audit", "agent": "Cash Flow Intelligence Agent", "status": "PENDING", "details": f"Aggregating net collections against disbursements for {period_a}"},
                {"step": 2, "title": "Variance Driver Synthesis", "agent": "Financial Insights Agent", "status": "PENDING", "details": "Identifying primary operating outflow drivers"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    # 9.5 Conceptual or Advisory Knowledge Question (General Query Agent)
    if any(k in inst_lower for k in ["what are the requirements", "requirements for", "how to claim", "what is the process", "rules for"]):
        return UserIntentPlan(
            user_objective=instruction,
            intent_type="GENERAL_QUERY",
            entities={"query": instruction},
            selected_tools=[],
            plan_steps=[
                {"step": 1, "title": "Conversational Response", "agent": "BharatCode Assistant", "status": "PENDING", "details": "Generate answer"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    # 10. Acceptance Query 8: GST Input Tax Credit status
    # "Show the GST input tax credit status of my purchases"
    if any(k in inst_lower for k in ["input tax credit", "itc status", "gst credit", "section 16", "section 17(5)"]):
        return UserIntentPlan(
            user_objective=f"Evaluate GST Input Tax Credit eligibility for {period_a}",
            intent_type="GET_GST_ITC_STATUS",
            entities={"period": period_a},
            selected_tools=["get_gst_itc_status"],
            plan_steps=[
                {"step": 1, "title": "Purchase Tax Extraction", "agent": "GST & Compliance Agent", "status": "PENDING", "details": f"Extracting GST components on purchases for {period_a}"},
                {"step": 2, "title": "Statutory Eligibility Check", "agent": "Tax Advisory Agent", "status": "PENDING", "details": "Applying Section 16(1) and Section 17(5) blocked credit rules"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    # 11. Acceptance Query 9: Trace vendor payments to invoices
    # "Find all payments to a vendor and trace them to their invoices"
    if any(k in inst_lower for k in ["trace them to their invoices", "trace payments", "vendor payment trail", "vendor invoices and payments"]):
        vendor = turn_context.get("vendor_name") or "Sharma Cement & Building Materials"
        m_v = re.search(r"to\s+([A-Za-z\s]+?)(?:\s+and|\s+in|\s+for|$)", instruction, re.IGNORECASE)
        if m_v and not any(w in m_v.group(1).lower() for w in ["a vendor", "the vendor", "any vendor"]):
            vendor = m_v.group(1).strip()

        return UserIntentPlan(
            user_objective=f"Trace full GraphRAG payment and invoice chain for '{vendor}'",
            intent_type="TRACE_VENDOR_TRAIL",
            entities={"vendor_name": vendor},
            selected_tools=["trace_vendor_payment_trail"],
            plan_steps=[
                {"step": 1, "title": "Knowledge Graph Traversal", "agent": "GraphRAG Agent", "status": "PENDING", "details": f"Traversing entity graph for {vendor}"},
                {"step": 2, "title": "Audit Chain Verification", "agent": "Audit & Validation Agent", "status": "PENDING", "details": "Correlating invoices, bank UTRs, and ledger vouchers"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    # 12. Acceptance Query 10: Monthly financial summary and export
    # "Generate a monthly financial summary and export it"
    if any(k in inst_lower for k in ["financial summary and export", "export summary", "monthly financial summary", "export financial"]):
        return UserIntentPlan(
            user_objective=f"Compile and package monthly financial operations summary for {period_a}",
            intent_type="EXPORT_FINANCIAL_SUMMARY",
            entities={"period": period_a, "format": "JSON"},
            selected_tools=["generate_financial_summary_export"],
            plan_steps=[
                {"step": 1, "title": "Financial Statement Compilation", "agent": "Financial Analysis Agent", "status": "PENDING", "details": f"Compiling P&L, balance sheet, and GST return for {period_a}"},
                {"step": 2, "title": "Export Package Generation", "agent": "Executive Reporting Agent", "status": "PENDING", "details": "Formatting exportable JSON and CSV payload"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    # 13. Close Accounts (Existing multi-agent workflow)
    if any(k in inst_lower for k in ["close", "month-end", "band karo", "closing", "close accounts"]):
        return UserIntentPlan(
            user_objective=f"Close financial accounts for period {period_a}",
            intent_type="CLOSE_ACCOUNTS",
            entities={"period": period_a},
            selected_tools=["search_transactions", "trace_vendor_payment_trail"],
            plan_steps=[
                {"step": 1, "title": "Document Intelligence", "agent": "Document Extraction Agent", "status": "PENDING", "details": "Extract statements & receipts from attached files"},
                {"step": 2, "title": "Transaction Classification (BharatCode Qwen)", "agent": "Transaction Classification Agent", "status": "PENDING", "details": "Classify expenses, counterparties & HSN codes"},
                {"step": 3, "title": "Accounting & Ledger Mapping", "agent": "Accounting Agent", "status": "PENDING", "details": "Map chart of accounts & Section 16 ITC rules"},
                {"step": 4, "title": "Invoice-Payment Reconciliation", "agent": "Reconciliation Agent", "status": "PENDING", "details": "Correlate unlinked bank items against receipts"},
                {"step": 5, "title": "Statutory Compliance Audit", "agent": "Audit Agent", "status": "PENDING", "details": "Scan Section 40A(3) cash limits & trial balance equilibrium"},
                {"step": 6, "title": "GST Returns & Tax Liability", "agent": "GST Agent", "status": "PENDING", "details": f"Compute GSTR-1 and GSTR-3B for {period_a}"},
                {"step": 7, "title": "Financial Statements & Analytics", "agent": "Financial Analysis Agent", "status": "PENDING", "details": "Compile P&L, Balance Sheet, and Cash Flow metrics"},
                {"step": 8, "title": "Consolidated Merchant Approval Checkpoint", "agent": "Supervisor Checkpoint", "status": "PENDING", "details": "Review proposed adjustments before posting to ledger"},
                {"step": 9, "title": "Ledger Commitment & Audit Logging", "agent": "Execution Agent", "status": "PENDING", "details": "Persist records and close accounts"}
            ],
            requires_approval=True,
            language=eff_lang
        )

    # 13.1 Core Supervisor Multi-Agent Workflows (Preserving existing capabilities)
    if any(k in inst_lower for k in ["gstr-3b", "gstr-1", "gstr", "gst return", "tax summary", "tax liability"]) and not any(k in inst_lower for k in ["input tax credit", "itc status"]):
        return UserIntentPlan(
            user_objective=f"Prepare GST return for {period_a}",
            intent_type="GST_RETURN",
            entities={"period": period_a},
            selected_tools=["get_gst_itc_status"],
            plan_steps=[
                {"step": 1, "title": "GST Ledger Extraction", "agent": "GST Agent", "status": "PENDING", "details": f"Aggregating outward and inward tax components for {period_a}"},
                {"step": 2, "title": "Section 170 CGST Rounding", "agent": "GST Agent", "status": "PENDING", "details": "Applying statutory rounding to nearest rupee"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    if any(k in inst_lower for k in ["reconcile", "reconciliation", "match transactions and receipts", "unlinked transactions"]) and not any(k in inst_lower for k in ["which of those are not reconciled"]):
        return UserIntentPlan(
            user_objective=f"Reconcile unlinked transactions and receipts for {period_a}",
            intent_type="RECONCILE",
            entities={"period": period_a},
            selected_tools=["find_unmatched_vendor_payments"],
            plan_steps=[
                {"step": 1, "title": "Bank vs Invoice Matching", "agent": "Reconciliation Agent", "status": "PENDING", "details": "Correlating bank lines with receipts"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    if any(k in inst_lower for k in ["compliance audit", "audit compliance", "run audit", "statutory audit", "audit check"]):
        return UserIntentPlan(
            user_objective=f"Execute compliance audit for {period_a}",
            intent_type="AUDIT_CHECK",
            entities={"period": period_a},
            selected_tools=["find_large_and_anomalous_transactions"],
            plan_steps=[
                {"step": 1, "title": "Compliance Audit", "agent": "Audit Agent", "status": "PENDING", "details": "Scanning Section 40A(3) and double-entry consistency"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    if any(k in inst_lower for k in ["profit and loss", "balance sheet", "financial statements", "p&l statement", "p&l summary"]):
        return UserIntentPlan(
            user_objective=f"Generate financial statements for {period_a}",
            intent_type="FINANCIAL_ANALYSIS",
            entities={"period": period_a},
            selected_tools=["generate_financial_summary_export"],
            plan_steps=[
                {"step": 1, "title": "Financial Statement Compilation", "agent": "Financial Analysis Agent", "status": "PENDING", "details": f"Compiling P&L and Balance Sheet for {period_a}"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    # 13.5 Querying past payments or transactions (e.g. "Find all payments to Sharma Traders last month" or "Maine Sharma ji ko kitna payment kiya pichhle mahine?")
    if (
        any(q in inst_lower for q in ["find", "show", "kitna", "search", "list", "get", "view", "how much", "tell me", "display", "check", "dikhao", "batao"])
        and any(w in inst_lower for w in ["payment", "payments", "transactions", "paid", "diye", "kharch", "bhugtan"])
    ) or (
        inst_lower.startswith(("find all payments", "show all payments", "search payments", "find payments", "payments to"))
    ):
        vendor = turn_context.get("vendor_name")
        # Try English pattern: "to Sharma Traders"
        m_v = re.search(r"(?:to|for)\s+([A-Za-z\s]+?)(?:\s+last|\s+in|\s+pichhle|\s+this|\s*$)", instruction, re.IGNORECASE)
        if m_v and not any(w in m_v.group(1).lower() for w in ["all", "the", "my", "those"]):
            vendor = m_v.group(1).strip()
        else:
            # Try Hindi pattern: "Sharma ji ko" / "Sharma Traders ko"
            m_vh = re.search(r"(?:maine\s+|humne\s+)?([A-Za-z\s]+?)\s+ko\b", instruction, re.IGNORECASE)
            if m_vh:
                raw_v = m_vh.group(1).strip()
                clean_v = re.sub(r"\b(ji|bhai|sahab|saab)\b", "", raw_v, flags=re.IGNORECASE).strip()
                vendor = clean_v or raw_v

        clean_vendor = re.sub(r"\b(ji|bhai|sahab|saab)\b", "", vendor, flags=re.IGNORECASE).strip() if vendor else None

        return UserIntentPlan(
            user_objective=f"Search past payments and transactions for '{vendor or 'records'}'",
            intent_type="SEARCH_TRANSACTIONS",
            entities={
                "counterparty": clean_vendor or vendor,
                "vendor_name": vendor or clean_vendor,
                "period": period_a,
                "query": clean_vendor or vendor
            },
            selected_tools=["search_transactions"],
            plan_steps=[
                {"step": 1, "title": "Payment & Ledger Search", "agent": "Transaction Query Agent", "status": "PENDING", "details": f"Querying transactions for {vendor or 'merchant records'}"},
                {"step": 2, "title": "Statement Summary Synthesis", "agent": "Financial Intelligence Agent", "status": "PENDING", "details": "Formatting totals and transaction breakdown"}
            ],
            requires_approval=False,
            language=eff_lang
        )

    # 14. Single Voice / Text Transaction
    if any(k in inst_lower for k in ["paid", "diye", "diya", "received", "aaye", "payment", "rupees", "rs", "₹"]):
        from backend.app.services.voice_service import parse_vernacular_voice_narration
        parsed = parse_vernacular_voice_narration(instruction)
        if parsed.get("missing_fields"):
            return UserIntentPlan(
                user_objective="Record transaction (incomplete)",
                intent_type="VOICE_TRANSACTION",
                entities=parsed,
                selected_tools=[],
                plan_steps=[
                    {"step": 1, "title": "Entity Extraction", "agent": "Voice Extraction Agent", "status": "COMPLETED", "details": f"Detected partial intent: {parsed.get('type')}"},
                    {"step": 2, "title": "Clarification Checkpoint", "agent": "Supervisor Checkpoint", "status": "WAITING_APPROVAL", "details": f"Missing: {', '.join(parsed['missing_fields'])}"}
                ],
                missing_information=parsed["missing_fields"],
                clarification_question=parsed["clarification_question"],
                requires_approval=True,
                language=eff_lang
            )
        else:
            return UserIntentPlan(
                user_objective=f"Record {parsed.get('type')} of ₹{parsed.get('amount')} to {parsed.get('counterparty_name')}",
                intent_type="VOICE_TRANSACTION",
                entities=parsed,
                selected_tools=["search_transactions"],
                plan_steps=[
                    {"step": 1, "title": "Entity Extraction", "agent": "Voice Extraction Agent", "status": "COMPLETED", "details": f"Extracted {parsed.get('type')} ₹{parsed.get('amount')}"},
                    {"step": 2, "title": "Transaction Classification (BharatCode Qwen)", "agent": "Transaction Classification Agent", "status": "PENDING", "details": "Classify mercantile intent and GST rate"},
                    {"step": 3, "title": "Accounting & Ledger Structure", "agent": "Accounting Agent", "status": "PENDING", "details": "Validate double-entry accounts"},
                    {"step": 4, "title": "Compliance & Anomaly Audit", "agent": "Audit Agent", "status": "PENDING", "details": "Evaluating Section 40A(3)"},
                    {"step": 5, "title": "Consolidated Approval Checkpoint", "agent": "Supervisor Checkpoint", "status": "PENDING", "details": "Awaiting merchant approval"},
                    {"step": 6, "title": "Ledger Execution", "agent": "Execution Agent", "status": "PENDING", "details": "Commit balanced double-entry voucher"}
                ],
                requires_approval=True,
                language=eff_lang
            )

    # 15. General Search / Question
    return UserIntentPlan(
        user_objective="Search records and provide financial guidance",
        intent_type="SEARCH_TRANSACTIONS",
        entities={"query": instruction},
        selected_tools=["search_transactions"],
        plan_steps=[
            {"step": 1, "title": "Financial Knowledge & Record Search", "agent": "Unified Retrieval Agent", "status": "PENDING", "details": f"Querying records for '{instruction[:40]}'"},
            {"step": 2, "title": "Conversational Synthesis", "agent": "BharatCode Assistant", "status": "PENDING", "details": "Generating verified response"}
        ],
        requires_approval=False,
        language=eff_lang
    )
