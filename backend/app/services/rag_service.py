import re
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.knowledge_base.gst_statutes import GST_STATUTORY_CORPUS
from backend.app.llm.client import bharatcode_client
from backend.app.llm.prompts import SYSTEM_GST_ASSISTANT
from backend.app.models.user import Tenant
from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt
from backend.app.models.ledger import LedgerAccount
from backend.app.services.analytics_service import compute_cash_flow_analytics, compute_cash_flow_forecast
from backend.app.services.anomaly_service import scan_tenant_anomalies

def retrieve_relevant_statutes(query: str, top_k: int = 3) -> List[Dict[str, str]]:
    """
    Lightweight, deterministic lexical and semantic retriever over the Indian GST statute corpus.
    Calculates relevance score without external cloud vector database latency.
    """
    query_terms = set(re.findall(r"\w+", query.lower()))
    scored_items = []

    for item in GST_STATUTORY_CORPUS:
        score = 0
        text_corpus = f"{item['title']} {item['content']} {item['keywords']}".lower()

        for term in query_terms:
            if len(term) <= 2:
                continue
            if term in text_corpus:
                score += 2
            if term in item["keywords"]:
                score += 3
            if term in item["title"].lower():
                score += 4

        if score > 0:
            scored_items.append((score, item))

    scored_items.sort(key=lambda x: x[0], reverse=True)
    if not scored_items:
        return []
    return [item for _, item in scored_items[:top_k]]

def classify_assistant_intent(query: str) -> str:
    """
    Classifies the user's mercantile request into one of 5 precise categories:
    1. CONVERSATION: Greetings, introductions, general help
    2. BUSINESS_QUERY: Deterministic tenant database questions (spend, vendors, balances)
    3. ANALYTICS_INSIGHTS: Cash flow, runway, forward liquidity, anomalies
    4. ACCOUNTING_GUIDANCE: General double-entry principles, rules of debit/credit
    5. GST_RAG: Statutory tax laws, ITC conditions, rates, GST sections
    """
    q = query.lower().strip()

    # 1. Greetings & Small Talk
    greeting_patterns = [
        r"^(hi|hello|hey|namaste|pranam|ram ram|sasriyakaal|vanakkam|good morning|good afternoon|good evening)\b",
        r"^(who are you|what can you do|how can you help|tell me about yourself|help me|kya kar sakte ho)\b",
        r"^(thanks|thank you|shukriya|dhanyawad|bye|goodbye|see you)\b"
    ]
    if any(re.search(pat, q) for pat in greeting_patterns) or q in ["hi", "hello", "hey", "namaste", "help"]:
        return "CONVERSATION"

    # 2. Business Data Queries against Tenant DB
    biz_keywords = [
        "my spend", "total spend", "how much did i spend", "kharcha", "expenditure",
        "top vendor", "top supplier", "who did i pay", "top customer", "top client",
        "bank balance", "cash balance", "kitna balance", "account balance", "current balance",
        "recent transaction", "last transaction", "pichle transaction", "latest transactions",
        "unpaid invoice", "pending bill", "total revenue", "my revenue", "total sales", "how much did i earn"
    ]
    if any(k in q for k in biz_keywords):
        return "BUSINESS_QUERY"

    # 3. Analytics & Insights
    analytics_keywords = [
        "cash flow", "runway", "forecast", "projection", "anomaly", "anomalies",
        "suspicious", "fraud", "liquidity", "shortfall", "risk"
    ]
    if any(k in q for k in analytics_keywords):
        return "ANALYTICS_INSIGHTS"

    # 4. Accounting Principles
    acct_keywords = [
        "double entry", "golden rule", "debit and credit", "what is debit", "what is credit",
        "trial balance", "balance sheet", "p&l", "profit and loss", "depreciation", "journal entry",
        "ledger account", "contra entry", "accrual"
    ]
    if any(k in q for k in acct_keywords) and not any(k in q for k in ["gst", "itc", "section 16", "section 17", "cgst", "igst"]):
        return "ACCOUNTING_GUIDANCE"

    # 5. Default to GST RAG
    return "GST_RAG"

async def answer_conversational_assistant(
    user_query: str,
    db: Session,
    tenant: Tenant,
    language_hint: str = "English/Hindi"
) -> Dict[str, Any]:
    """
    Conversational Financial Intelligence Engine with intent routing.
    - Prevents greeting queries from triggering GST statutes.
    - Executes deterministic SQL aggregations for tenant business queries.
    - Uses BharatCode Qwen 3.8 27B for semantic and statutory RAG generation.
    """
    intent = classify_assistant_intent(user_query)
    symbol = tenant.currency_symbol or "₹"

    # -------------------------------------------------------------
    # INTENT 1: CONVERSATION (Greetings, Small Talk, Capabilities)
    # -------------------------------------------------------------
    if intent == "CONVERSATION":
        answer = (
            f"Namaste! I am your AI Financial Assistant for **{tenant.name}**, powered by BharatCode Qwen 3.8 27B.\n\n"
            f"Here is what I can assist your business with:\n"
            f"• **Business Intelligence**: Ask *'What is my total spend?'*, *'Who are my top vendors?'*, or *'What is my current bank balance?'*\n"
            f"• **Statutory GST Inquiries**: Ask *'What are the Input Tax Credit (ITC) conditions?'*, *'Is GST blocked on motor vehicles?'*, or *'How does statutory rounding work?'*\n"
            f"• **Bookkeeping & Accounting**: Ask *'Explain double-entry rules'* or *'How to record a contra voucher?'*\n"
            f"• **Cash Flow & Forward Projections**: Ask *'What is my 30-day forward cash flow?'* or *'Are there any duplicate payment anomalies?'*\n\n"
            f"How can I help {tenant.name} right now?"
        )
        return {
            "query": user_query,
            "intent": "CONVERSATION",
            "intent_label": "General Conversation",
            "answer": answer,
            "citations": [],
            "llm_provider": "BharatCode Hosted API",
            "ai_mode": "DEV_SIMULATION",
            "live_api": False,
            "grounded": True
        }

    # -------------------------------------------------------------
    # INTENT 2: BUSINESS_QUERY (Deterministic SQL on Tenant Database)
    # -------------------------------------------------------------
    if intent == "BUSINESS_QUERY":
        q_lower = user_query.lower()
        data_summary = {}

        # 1. Total Spend / Expense
        total_debit = db.query(func.sum(Transaction.amount)).filter(
            Transaction.tenant_id == tenant.id,
            Transaction.type == "DEBIT"
        ).scalar() or Decimal("0.00")

        # 2. Total Inflow / Revenue
        total_credit = db.query(func.sum(Transaction.amount)).filter(
            Transaction.tenant_id == tenant.id,
            Transaction.type == "CREDIT"
        ).scalar() or Decimal("0.00")

        # 3. Cash and Bank Balances
        cash_acc = db.query(LedgerAccount).filter(
            LedgerAccount.tenant_id == tenant.id,
            LedgerAccount.code == "1010"
        ).first()
        bank_acc = db.query(LedgerAccount).filter(
            LedgerAccount.tenant_id == tenant.id,
            LedgerAccount.code == "1020"
        ).first()

        cash_bal = cash_acc.balance if cash_acc else Decimal("0.00")
        bank_bal = bank_acc.balance if bank_acc else Decimal("0.00")

        # 4. Top Vendors
        top_vendors = db.query(
            Transaction.counterparty_name,
            func.sum(Transaction.amount).label("vol")
        ).filter(
            Transaction.tenant_id == tenant.id,
            Transaction.type == "DEBIT",
            Transaction.counterparty_name.isnot(None)
        ).group_by(Transaction.counterparty_name).order_by(func.sum(Transaction.amount).desc()).limit(5).all()

        # Construct deterministic response
        lines = [f"Here is the verified financial data for **{tenant.name}** directly from your general ledger:\n"]

        if any(w in q_lower for w in ["spend", "expense", "kharcha", "paid", "outflow"]):
            lines.append(f"• **Total Outflows / Spend:** {symbol}{total_debit:,.2f}")
        if any(w in q_lower for w in ["revenue", "sales", "inflow", "earn", "income"]):
            lines.append(f"• **Total Revenue / Inflows:** {symbol}{total_credit:,.2f}")
        if any(w in q_lower for w in ["balance", "bank", "cash", "account"]):
            lines.append(f"• **Cash in Hand [1010]:** {symbol}{cash_bal:,.2f}")
            lines.append(f"• **Bank Balance [1020]:** {symbol}{bank_bal:,.2f}")
            lines.append(f"• **Total Current Liquidity:** {symbol}{(cash_bal + bank_bal):,.2f}")

        if any(w in q_lower for w in ["vendor", "supplier", "payee", "who did i pay"]):
            lines.append("\n**Top Suppliers / Outflow Counterparties:**")
            if top_vendors:
                for v_name, vol in top_vendors:
                    lines.append(f"  - **{v_name}**: {symbol}{vol:,.2f}")
            else:
                lines.append("  *(No vendor counterparties recorded yet)*")

        if any(w in q_lower for w in ["recent", "latest", "pichle", "transaction"]):
            recent_txs = db.query(Transaction).filter(
                Transaction.tenant_id == tenant.id
            ).order_by(Transaction.transaction_date.desc()).limit(5).all()

            lines.append("\n**Latest 5 Recorded Transactions:**")
            for t in recent_txs:
                sign = "+" if t.type == "CREDIT" else "-"
                lines.append(f"  - `{t.transaction_date}`: {t.description[:35]} — **{sign}{symbol}{t.amount:,.2f}** ({t.channel})")

        # If user asked a generic question, show executive dashboard summary
        if len(lines) == 1:
            lines.append(f"• **Total Inflows:** {symbol}{total_credit:,.2f}")
            lines.append(f"• **Total Outflows:** {symbol}{total_debit:,.2f}")
            lines.append(f"• **Net Position:** {symbol}{(total_credit - total_debit):,.2f}")
            lines.append(f"• **Bank Liquidity [1020]:** {symbol}{bank_bal:,.2f}")

        return {
            "query": user_query,
            "intent": "BUSINESS_QUERY",
            "intent_label": "Business Workspace Data",
            "answer": "\n".join(lines),
            "citations": [],
            "tenant_data": {
                "total_debit": float(total_debit),
                "total_credit": float(total_credit),
                "bank_balance": float(bank_bal),
                "cash_balance": float(cash_bal)
            },
            "llm_provider": "Deterministic Tenant Database Engine",
            "ai_mode": "DEV_SIMULATION",
            "live_api": False,
            "grounded": True
        }

    # -------------------------------------------------------------
    # INTENT 3: ANALYTICS_INSIGHTS (Cash Flow, Runway, Anomaly Check)
    # -------------------------------------------------------------
    if intent == "ANALYTICS_INSIGHTS":
        cf = compute_cash_flow_analytics(db, tenant.id)
        fc = compute_cash_flow_forecast(db, tenant.id)
        anomalies = scan_tenant_anomalies(db, tenant.id)

        answer = (
            f"### Financial Health & Liquidity Analytics for {tenant.name}\n\n"
            f"• **Starting Liquidity:** {symbol}{fc.get('starting_liquidity', '0.00')}\n"
            f"• **30-Day Forward Closing Balance:** {symbol}{fc.get('projected_closing_balance_30d', '0.00')} *(Risk Level: **{fc.get('shortfall_risk_level', 'LOW')}**)*\n"
            f"• **Estimated Cash Runway:** **{cf.get('cash_runway_months', 0)} Months**\n"
            f"• **Net Cash Flow (Recent Period):** {symbol}{cf.get('net_cash_flow', '0.00')}\n"
            f"• **Statutory Tax Buffer Recommendation:** {fc.get('statutory_buffer_advice', 'Adequate buffer')}\n"
            f"• **Detected Anomalies / Duplicates:** **{anomalies.get('total_anomalies_detected', 0)} flagged items**\n"
        )
        return {
            "query": user_query,
            "intent": "ANALYTICS_INSIGHTS",
            "intent_label": "Financial Analytics & Insights",
            "answer": answer,
            "citations": [],
            "llm_provider": "VyaparSetu Financial Analytics Engine",
            "ai_mode": "DEV_SIMULATION",
            "live_api": False,
            "grounded": True
        }

    # -------------------------------------------------------------
    # INTENT 4: ACCOUNTING_GUIDANCE (Educational Double-Entry Principles)
    # -------------------------------------------------------------
    if intent == "ACCOUNTING_GUIDANCE":
        answer = (
            f"### Indian Mercantile Double-Entry Principles\n\n"
            f"VyaparSetu enforces strict dual-aspect accounting for Indian MSMEs:\n\n"
            f"1. **The Three Golden Rules of Accounting:**\n"
            f"   • **Real Accounts** (Cash, Machinery, Building): *Debit what comes in, Credit what goes out.*\n"
            f"   • **Personal Accounts** (Vendors, Debtors, Banks): *Debit the receiver, Credit the giver.*\n"
            f"   • **Nominal Accounts** (Expenses, Sales, Rent): *Debit all expenses and losses, Credit all incomes and gains.*\n\n"
            f"2. **The Fundamental Accounting Equation:**\n"
            f"   $$\\text{{Assets}} = \\text{{Liabilities}} + \\text{{Owner's Equity}}$$\n"
            f"   Every single bank debit or credit voucher creates balanced debit and credit entries down to the exact paisa (Section 170 compliance).\n\n"
            f"3. **MSME Chart of Accounts in Lekha:**\n"
            f"   • `1010`: Cash in Hand | `1020`: Bank Account\n"
            f"   • `2010`: Accounts Payable | `2020`: Output GST Payable\n"
            f"   • `1030`: Input Tax Credit (ITC) Receivable\n"
            f"   • `4010`: Sales & Operating Revenue | `5010`: Raw Materials Expense"
        )
        return {
            "query": user_query,
            "intent": "ACCOUNTING_GUIDANCE",
            "intent_label": "Accounting Principles",
            "answer": answer,
            "citations": [],
            "llm_provider": "VyaparSetu Accounting Principles Knowledge Base",
            "ai_mode": "DEV_SIMULATION",
            "live_api": False,
            "grounded": True
        }

    # -------------------------------------------------------------
    # INTENT 5: GST_RAG (Statutory Corpus Grounding with BharatCode)
    # -------------------------------------------------------------
    retrieved_statutes = retrieve_relevant_statutes(user_query, top_k=3)
    if not retrieved_statutes:
        # Fallback to key fundamental sections
        retrieved_statutes = GST_STATUTORY_CORPUS[:2]

    context_str = "\n\n".join(
        f"--- Source: {doc['citation']} ---\n{doc['content']}"
        for doc in retrieved_statutes
    )

    prompt = (
        f"Statutory GST Legal Context:\n{context_str}\n\n"
        f"Merchant Query: {user_query}\n"
        f"Preferred Language: {language_hint}\n\n"
        f"Provide a clear, legally sound, and concise explanation for the Indian MSME business owner. "
        f"You MUST cite the relevant Section(s) and circulars from the provided context."
    )

    messages = [
        {"role": "system", "content": SYSTEM_GST_ASSISTANT},
        {"role": "user", "content": prompt}
    ]

    llm_resp = await bharatcode_client.chat_completion(messages, temperature=0.1)

    citations = [
        {"title": doc["title"], "citation": doc["citation"], "id": doc["id"]}
        for doc in retrieved_statutes
    ]

    return {
        "query": user_query,
        "intent": "GST_RAG",
        "intent_label": "GST Statutory RAG",
        "answer": llm_resp["content"],
        "citations": citations,
        "llm_provider": "BharatCode Qwen 3.8 27B" if llm_resp.get("live_api") else "Dev Indic Statutory Assistant (Simulated)",
        "ai_mode": llm_resp.get("ai_mode", "DEV_SIMULATION"),
        "source": llm_resp.get("source", "DEV_SIMULATION"),
        "live_api": llm_resp.get("live_api", False),
        "notice": llm_resp.get("notice", ""),
        "grounded": True
    }

# Backward compatible helper
async def answer_gst_query_with_rag(user_query: str, language_hint: str = "English/Hindi") -> Dict[str, Any]:
    from backend.app.core.database import SessionLocal
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).first()
        if not tenant:
            # Synthetic placeholder if no tenant
            tenant = Tenant(name="Demo MSME", simulated_gstin="27AABCU9603R1ZM")
        return await answer_conversational_assistant(user_query, db, tenant, language_hint)
    finally:
        db.close()
