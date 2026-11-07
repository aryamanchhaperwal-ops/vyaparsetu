import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from backend.app.config import settings
from backend.app.llm.prompts import (
    SYSTEM_TRANSACTION_CLASSIFIER,
    PROMPT_CLASSIFY_TRANSACTION,
    SYSTEM_GST_ASSISTANT
)

logger = logging.getLogger("bharatcode_client")

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import httpx
from backend.app.config import settings
from backend.app.llm.prompts import (
    SYSTEM_TRANSACTION_CLASSIFIER,
    PROMPT_CLASSIFY_TRANSACTION,
    SYSTEM_GST_ASSISTANT
)

logger = logging.getLogger("bharatcode_client")

VALID_GST_RATES = {0.0, 0.1, 0.25, 1.5, 3.0, 5.0, 12.0, 18.0, 28.0}

def validate_and_normalize_gst_rate(rate: Any) -> Tuple[float, Optional[str]]:
    """
    Validates GST rate against authoritative Indian GST tax slabs under CGST Act, 2017.
    If non-standard, snaps to the closest legal statutory slab and provides an advisory warning.
    """
    try:
        r = float(rate)
    except (ValueError, TypeError):
        return 18.0, "Invalid GST rate specified; normalized to standard 18% slab."

    if r in VALID_GST_RATES:
        return r, None

    closest = min(VALID_GST_RATES, key=lambda x: abs(x - r))
    return closest, f"Non-statutory GST rate {r}% normalized to closest legal slab {closest}%."

def validate_hsn_sac(code: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Validates format of HSN (Goods: 2, 4, 6, 8 digits) or SAC (Services: 99xxxx) code.
    """
    if not code:
        return None, None
    cleaned = re.sub(r"[^\d]", "", str(code)).strip()
    if not cleaned:
        return None, "HSN/SAC format invalid."
    if len(cleaned) in (2, 4, 6, 8):
        return cleaned, None
    if len(cleaned) > 8:
        return cleaned[:8], f"HSN code truncated to standard 8 digits ({cleaned[:8]})."
    return cleaned, None

def generate_accounting_suggestions(category: str, direction: str, gst_rate: float) -> List[str]:
    """Generates authoritative double-entry bookkeeping and GST ITC suggestions."""
    suggestions = []
    if direction == "DEBIT":
        acc_map = {
            "Raw Materials": "Debit: 5010 (Cost of Goods Sold / Raw Materials)",
            "Logistics & Transport": "Debit: 5030 (Logistics & Freight - check RCM under Sec 9(3))",
            "Rent & Utilities": "Debit: 5020 (Commercial Property Rent / Utilities)",
            "Salaries & Wages": "Debit: 5040 (Salaries & Wages - exempt under Sched III)",
            "Office & Miscellaneous": "Debit: 5090 (Office & Sundry Operating Expense)",
            "Capital Asset": "Debit: 1050 (Plant, Machinery & Office Equipment)",
            "Tax Payment": "Debit: 2010 (GST Liability Cash Ledger Offset)",
        }
        suggestions.append(acc_map.get(category, "Debit: 5090 (General Business Expense)"))
        suggestions.append("Credit: 1020 (Bank Account) or 1010 (Cash in Hand)")
        if category == "Salaries & Wages":
            suggestions.append("Schedule III: Employee remuneration out of scope of GST.")
        elif gst_rate > 0:
            suggestions.append("ITC eligible under Section 16(1) CGST Act subject to supplier GSTR-2B reflection.")
    else:
        suggestions.append("Debit: 1020 (Bank Account) or 1010 (Cash in Hand)")
        suggestions.append("Credit: 4010 (Sales Revenue / Outward Taxable Supply)")
        if gst_rate > 0:
            suggestions.append(f"Credit: Output GST Liability ({gst_rate}%) under Section 9 CGST Act.")
    return suggestions

class BharatCodeAPIError(Exception):
    """Raised when BharatCode API is unavailable or returns an error in production mode."""
    def __init__(self, message: str, status_code: int = 503, response_body: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

class BharatCodeClient:
    """
    Dedicated client for BharatCode Hosted LLM API.
    Adheres strictly to the constraint of using BharatCode as the sole LLM provider.
    Supports explicitly separated PRODUCTION_LIVE / PRODUCTION_BHARATCODE and DEV_SIMULATION modes.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        ai_mode: Optional[str] = None,
        timeout: float = 90.0
    ):
        self.api_key = api_key or settings.BHARATCODE_API_KEY
        self.base_url = (base_url or settings.BHARATCODE_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.BHARATCODE_MODEL_NAME
        self.ai_mode = ai_mode or getattr(settings, "AI_MODE", "DEV_SIMULATION")
        self.timeout = timeout

    @property
    def is_live(self) -> bool:
        mode = (self.ai_mode or getattr(settings, "AI_MODE", "DEV_SIMULATION")).upper()
        return mode in ("PRODUCTION_LIVE", "PRODUCTION_BHARATCODE")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        response_format: Optional[Dict[str, str]] = None,
        max_tokens: int = 2500,
        ai_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an asynchronous chat completion request.
        - In PRODUCTION_LIVE / PRODUCTION_BHARATCODE mode: calls real BharatCode endpoint; fails explicitly if unavailable.
        - In DEV_SIMULATION mode: runs local deterministic Indic engine with explicit labels.
        """
        effective_mode = (ai_mode or self.ai_mode or getattr(settings, "AI_MODE", "DEV_SIMULATION")).upper()
        is_live_call = effective_mode in ("PRODUCTION_LIVE", "PRODUCTION_BHARATCODE")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if response_format:
            payload["response_format"] = response_format

        # 1. LIVE PRODUCTION BHARATCODE MODE
        if is_live_call:
            masked_key = f"{self.api_key[:4]}...{self.api_key[-4:]}" if len(self.api_key) > 8 else "***"
            logger.info(f"Dispatching live request to BharatCode API: {self.base_url} (Model: {self.model_name})")
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=headers
                    )
                    if response.status_code == 200:
                        data = response.json()
                        choices = data.get("choices", [])
                        msg = choices[0].get("message", {}) if choices else {}
                        content = msg.get("content") or msg.get("reasoning_content") or ""
                        return {
                            "content": content,
                            "raw": data,
                            "live_api": True,
                            "source": "BHARATCODE_LIVE",
                            "ai_mode": effective_mode,
                            "model": self.model_name
                        }

                    # Production mode must NOT silently fall back
                    error_text = response.text
                    logger.error(f"BharatCode API rejected request with HTTP {response.status_code}: {error_text}")
                    raise BharatCodeAPIError(
                        f"BharatCode API returned HTTP {response.status_code}: {error_text}",
                        status_code=response.status_code,
                        response_body=error_text
                    )
            except httpx.RequestError as e:
                logger.error(f"BharatCode network error: {e}")
                raise BharatCodeAPIError(
                    f"Failed to connect to BharatCode API at {self.base_url}: {str(e)}",
                    status_code=503
                )

        # 2. DEV SIMULATION MODE (explicitly labelled)
        logger.info("Executing transaction intelligence in DEV_SIMULATION mode.")
        sim_result = self._simulate_indic_llm_response(messages)
        sim_result["live_api"] = False
        sim_result["source"] = "DEV_SIMULATION"
        sim_result["ai_mode"] = "DEV_SIMULATION"
        sim_result["model"] = "dev-indic-simulator-v1"
        sim_result["notice"] = "DEVELOPMENT SIMULATION — Deterministic Indic simulation (Not a live BharatCode inference response)."
        return sim_result

    async def generate_completion(self, prompt: str, max_tokens: int = 500, temperature: float = 0.2) -> Dict[str, Any]:
        """Generates text completion using chat_completion under the hood."""
        messages = [{"role": "user", "content": prompt}]
        res = await self.chat_completion(messages, temperature=temperature, max_tokens=max_tokens)
        return {
            "text": res.get("content", ""),
            "raw": res.get("raw"),
            "live_api": res.get("live_api", False),
            "source": res.get("source", "DEV_SIMULATION"),
            "ai_mode": res.get("ai_mode", "DEV_SIMULATION")
        }

    def _simulate_indic_llm_response(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Simulates BharatCode Indic LLM response for local testing and deterministic validation.
        Understands Hindi, Hinglish, UPI narrations, and Indian mercantile phrasing.
        """
        user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        user_lower = user_msg.lower()

        # 1. Classification Query
        if "narration:" in user_lower or "analyze the following indian merchant transaction" in user_lower:
            import re
            narration_match = re.search(r'narration:\s*"([^"]+)"', user_msg, re.IGNORECASE)
            extracted_narration = narration_match.group(1) if narration_match else user_msg
            return {"content": self._simulate_transaction_classification(extracted_narration), "raw": {"model": self.model_name}}

        # 2. GST RAG / Statutory Query
        if "gst" in user_lower or "itc" in user_lower or "gstr" in user_lower:
            return {"content": self._simulate_gst_statutory_response(user_lower), "raw": {"model": self.model_name}}

        # Default response
        return {
            "content": "BharatCode Indic Assistant: Transaction acknowledged and processed according to MSME guidelines.",
            "raw": {"model": self.model_name}
        }

    def _simulate_transaction_classification(self, prompt_text: str) -> str:
        """Rule-based Indic merchant classifier simulating BharatCode's inference."""
        p = prompt_text.lower()

        # Determine category & details based on Indian keywords
        if any(w in p for w in ["cement", "sariya", "loha", "brick", "raw material", "kaccha mal", "inventory", "stock"]):
            res = {
                "category": "Raw Materials",
                "sub_category": "Building & Hardware Supplies",
                "counterparty_name": "Supplier",
                "is_business_expense": True,
                "suggested_hsn_sac": "2523",
                "gst_rate": 18.0,
                "confidence_score": 0.94,
                "rationale": "Narration references raw building materials/supplies (cement/iron), classified under Section 16 ITC eligible."
            }
        elif any(w in p for w in ["kiraya", "rent", "dukaan kiraya", "shop rent", "godown"]):
            res = {
                "category": "Rent & Utilities",
                "sub_category": "Commercial Property Rent",
                "counterparty_name": "Landlord",
                "is_business_expense": True,
                "suggested_hsn_sac": "9972",
                "gst_rate": 18.0,
                "confidence_score": 0.92,
                "rationale": "Narration indicates commercial premises rental expense."
            }
        elif any(w in p for w in ["bijli", "electricity", "bill payment", "bescom", "mahadiscom", "tneb", "water", "pani"]):
            res = {
                "category": "Rent & Utilities",
                "sub_category": "Electricity & Power",
                "counterparty_name": "Utility Board",
                "is_business_expense": True,
                "suggested_hsn_sac": "9969",
                "gst_rate": 0.0,
                "confidence_score": 0.96,
                "rationale": "Electricity distribution is an exempt utility expense under GST Notification No. 12/2017."
            }
        elif any(w in p for w in ["salary", "vetan", "tankhwah", "wages", "staff", "karamchari"]):
            res = {
                "category": "Salaries & Wages",
                "sub_category": "Employee Compensation",
                "counterparty_name": "Staff Member",
                "is_business_expense": True,
                "suggested_hsn_sac": None,
                "gst_rate": 0.0,
                "confidence_score": 0.95,
                "rationale": "Employee services are excluded from the scope of GST under Schedule III of the CGST Act."
            }
        elif any(w in p for w in ["transport", "chhota hathi", "freight", "bhadha", "tempo", "courier", "delivery"]):
            res = {
                "category": "Logistics & Transport",
                "sub_category": "Goods Transport Agency (GTA)",
                "counterparty_name": "Transporter",
                "is_business_expense": True,
                "suggested_hsn_sac": "9965",
                "gst_rate": 5.0,
                "confidence_score": 0.90,
                "rationale": "Freight and goods transport agency charges, subject to Reverse Charge Mechanism (RCM) or 5%."
            }
        elif any(w in p for w in ["chai", "nasta", "tea", "coffee", "stationery", "pen", "paper", "cleaning", "pooja"]):
            res = {
                "category": "Office & Miscellaneous",
                "sub_category": "Office Pantry & Sundry",
                "counterparty_name": "Local Vendor",
                "is_business_expense": True,
                "suggested_hsn_sac": "9963",
                "gst_rate": 5.0,
                "confidence_score": 0.88,
                "rationale": "Day-to-day office pantry and maintenance expense. Note: food ITC may be blocked under Sec 17(5)."
            }
        elif any(w in p for w in ["customer payment", "sale", "jama", "upi received", "bill no", "invoice payment", "bikri"]):
            res = {
                "category": "Sales Revenue",
                "sub_category": "Direct Retail/Wholesale Sales",
                "counterparty_name": "Retail Customer",
                "is_business_expense": False,
                "suggested_hsn_sac": "9988",
                "gst_rate": 18.0,
                "confidence_score": 0.93,
                "rationale": "Inward payment for goods or services delivered, taxable outward supply."
            }
        elif any(w in p for w in ["payment to", "transfer to", "paid to", "sent to"]) and len(p.split()) <= 4:
            res = {
                "category": "Uncategorized",
                "sub_category": "Generic Transfer",
                "counterparty_name": "Individual",
                "is_business_expense": False,
                "suggested_hsn_sac": None,
                "gst_rate": 0.0,
                "confidence_score": 0.55,
                "rationale": "Narration contains insufficient business context. Requires merchant manual confirmation."
            }
        else:
            res = {
                "category": "Office & Miscellaneous",
                "sub_category": "General Operating Expense",
                "counterparty_name": "Merchant Vendor",
                "is_business_expense": True,
                "suggested_hsn_sac": None,
                "gst_rate": 18.0,
                "confidence_score": 0.75,
                "rationale": "Standard business operating outflow."
            }

        return json.dumps(res, indent=2)

    def _simulate_gst_statutory_response(self, prompt_text: str) -> str:
        """Simulates statutory GST responses with specific Section citations."""
        p = prompt_text.lower()
        if "itc" in p or "input tax credit" in p:
            return (
                "Under **Section 16 of the CGST Act, 2017**, a registered person is entitled to take Input Tax Credit (ITC) "
                "subject to four fundamental conditions:\n"
                "1. Possession of a tax invoice or debit note issued by the supplier (Section 16(2)(a)).\n"
                "2. The details of the invoice have been furnished by the supplier in GSTR-1 and reflected in your GSTR-2B (Section 16(2)(aa)).\n"
                "3. The goods or services have been received (Section 16(2)(b)).\n"
                "4. Tax charged in respect of such supply has been actually paid to the Government (Section 16(2)(c)).\n\n"
                "⚠️ **Blocked Credits (Section 17(5)):** ITC cannot be claimed on motor vehicles (<13 passengers), food and beverages, "
                "outdoor catering, and goods lost, stolen or destroyed."
            )
        elif "gstr-1" in p or "gstr 1" in p:
            return (
                "**GSTR-1 Statutory Rules (Rule 59 of CGST Rules):**\n"
                "- GSTR-1 is the monthly or quarterly return for reporting outward supplies of goods and services.\n"
                "- **Filing Due Date:** 11th of the succeeding month for monthly filers; 13th of the month succeeding the quarter under the QRMP scheme.\n"
                "- **Key Tables:** Table 4 (B2B Taxable Supplies), Table 5 (Inter-state B2C large supplies > ₹2.5 Lakh), "
                "Table 7 (B2C Others / Small retail sales), Table 12 (HSN-wise summary of outward supplies)."
            )
        elif "gstr-3b" in p or "gstr 3b" in p:
            return (
                "**GSTR-3B Statutory Summary Return (Section 39):**\n"
                "- GSTR-3B is a monthly self-assessed summary return of outward supplies, input tax credit claimed, and tax liability paid.\n"
                "- **Filing Due Date:** 20th of the following month for regular taxpayers.\n"
                "- **Formula:** Net Cash Tax Payable = Total Output Tax (CGST + SGST + IGST) - Eligible Input Tax Credit (ITC)."
            )
        else:
            return (
                "According to the **Central Goods and Services Tax (CGST) Act, 2017**, transactions must be classified by "
                "nature of supply: Intra-state supplies attract CGST + SGST (Section 9), while Inter-state supplies attract IGST (Section 5 of IGST Act). "
                "All financial amounts must be rounded to the nearest rupee pursuant to Section 170."
            )

    async def classify_transaction(
        self,
        narration: str,
        amount: float,
        direction: str = "DEBIT",
        counterparty_hint: str = "",
        ai_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convenience method to classify an Indian MSME transaction."""
        effective_mode = (ai_mode or self.ai_mode or getattr(settings, "AI_MODE", "DEV_SIMULATION")).upper()
        is_live_call = effective_mode in ("PRODUCTION_LIVE", "PRODUCTION_BHARATCODE")

        if not narration or not narration.strip():
            return {
                "category": "Uncategorized",
                "sub_category": None,
                "counterparty_name": None,
                "is_business_expense": False,
                "suggested_hsn_sac": None,
                "gst_rate": 0.0,
                "confidence_score": 0.0,
                "rationale": "Empty transaction narration provided",
                "source": "VALIDATION_FAILED",
                "ai_mode": effective_mode,
                "live_api": False,
                "accounting_suggestions": []
            }

        user_prompt = PROMPT_CLASSIFY_TRANSACTION.format(
            narration=narration.strip(),
            amount=amount,
            direction=direction,
            counterparty_hint=counterparty_hint
        )
        messages = [
            {"role": "system", "content": SYSTEM_TRANSACTION_CLASSIFIER},
            {"role": "user", "content": user_prompt}
        ]

        # Call chat_completion (raises BharatCodeAPIError if live inference fails)
        result = await self.chat_completion(messages, temperature=0.1, ai_mode=effective_mode)

        raw_text = (result.get("content") or "").strip()
        if not raw_text and "raw" in result:
            raw_choices = result["raw"].get("choices", [])
            raw_msg = raw_choices[0].get("message", {}) if raw_choices else {}
            raw_text = (raw_msg.get("content") or raw_msg.get("reasoning_content") or "").strip()

        clean_json_str = raw_text
        if "```" in clean_json_str:
            m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_json_str)
            if m:
                clean_json_str = m.group(1).strip()
        if not (clean_json_str.startswith("{") and clean_json_str.endswith("}")):
            m_obj = re.search(r"\{[\s\S]*\}", clean_json_str)
            if m_obj:
                clean_json_str = m_obj.group(0)

        try:
            parsed = json.loads(clean_json_str)
        except Exception as e:
            logger.error(f"Failed to parse LLM output as JSON: {e}")
            if is_live_call:
                raise BharatCodeAPIError(f"Model output could not be parsed as valid JSON: {raw_text[:200]}", status_code=502)
            parsed = {
                "category": "Uncategorized",
                "sub_category": None,
                "counterparty_name": None,
                "is_business_expense": True,
                "suggested_hsn_sac": None,
                "gst_rate": 0.0,
                "confidence_score": 0.5,
                "rationale": "Fallback parsing due to non-JSON output"
            }

        # Authoritative GST Rate Validation
        raw_gst = parsed.get("gst_rate", 18.0)
        norm_gst, gst_warning = validate_and_normalize_gst_rate(raw_gst)
        parsed["gst_rate"] = norm_gst
        if gst_warning:
            parsed["gst_advisory"] = gst_warning

        # Authoritative HSN/SAC Validation
        raw_hsn = parsed.get("suggested_hsn_sac")
        norm_hsn, hsn_warning = validate_hsn_sac(raw_hsn)
        parsed["suggested_hsn_sac"] = norm_hsn
        if hsn_warning:
            parsed["hsn_advisory"] = hsn_warning

        # Generate Authoritative Accounting Suggestions
        cat = parsed.get("category", "General Expense")
        suggestions = generate_accounting_suggestions(cat, direction, norm_gst)
        parsed["accounting_suggestions"] = suggestions

        # Explicitly tag whether inference was live BharatCode or dev simulation
        parsed["source"] = result.get("source", "DEV_SIMULATION")
        parsed["ai_mode"] = result.get("ai_mode", "DEV_SIMULATION")
        parsed["live_api"] = result.get("live_api", False)
        parsed["notice"] = result.get("notice", "")
        return parsed

bharatcode_client = BharatCodeClient()
