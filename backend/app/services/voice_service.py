import re
import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List

def parse_relative_date(text: str, reference_date: Optional[datetime.date] = None) -> datetime.date:
    """
    Parses relative dates in Hindi, Hinglish, and English:
    'kal' / 'yesterday' -> reference_date - 1 day
    'parson' / 'day before yesterday' -> reference_date - 2 days
    'aaj' / 'today' -> reference_date
    Explicit dates: '15 oct', '15 october', '01-11-2026', '2026-10-15'
    """
    ref = reference_date or datetime.date.today()
    lower = text.lower()

    if "parson" in lower or "day before yesterday" in lower:
        return ref - datetime.timedelta(days=2)
    elif "kal" in lower or "yesterday" in lower:
        return ref - datetime.timedelta(days=1)
    elif "aaj" in lower or "today" in lower:
        return ref

    # Check for DD/MM/YYYY or YYYY-MM-DD
    iso_match = re.search(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", text)
    if iso_match:
        try:
            return datetime.date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            pass

    dmy_match = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})\b", text)
    if dmy_match:
        try:
            year = int(dmy_match.group(3))
            if year < 100:
                year += 2000
            return datetime.date(year, int(dmy_match.group(2)), int(dmy_match.group(1)))
        except ValueError:
            pass

    # Check for "15 Oct" or "15 October"
    month_names = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
        "nov": 11, "november": 11, "dec": 12, "december": 12
    }
    date_word_match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(\d{4}))?\b", text)
    if date_word_match:
        day = int(date_word_match.group(1))
        m_str = date_word_match.group(2).lower()
        year = int(date_word_match.group(3)) if date_word_match.group(3) else ref.year
        if m_str in month_names:
            try:
                return datetime.date(year, month_names[m_str], day)
            except ValueError:
                pass

    return ref

def parse_vernacular_voice_narration(text: str, reference_date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    Parses Hindi, Hinglish, and Indian English spoken mercantile narration.
    Extracts date, counterparty, amount, currency, transaction type, payment method,
    category, description, missing information flags, and confidence score.
    """
    clean_text = text.strip()
    lower_text = clean_text.lower()
    ref_date = reference_date or datetime.date.today()

    # 1. Date Extraction
    tx_date = parse_relative_date(lower_text, ref_date)

    # 2. Amount Extraction
    amount = Decimal("0.00")
    
    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lac|peti)\b", lower_text)
    hazar_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hazar|thousand|k)\b", lower_text)
    
    if lakh_match:
        amount = Decimal(str(float(lakh_match.group(1)) * 100000))
    elif hazar_match:
        amount = Decimal(str(float(hazar_match.group(1)) * 1000))
    else:
        num_matches = re.findall(r"(?:₹|rs\.?|inr|rupees?|rupaye?)?\s*(\b\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?|\b\d{2,8})\b", lower_text)
        if num_matches:
            candidates = []
            for m in num_matches:
                clean_num = m.replace(",", "").strip()
                try:
                    candidates.append(Decimal(clean_num))
                except Exception:
                    pass
            if candidates:
                amount = max(candidates)

    # 3. Transaction Direction (DEBIT vs CREDIT)
    debit_keywords = [
        "diye", "diya", "bheja", "transfer kiya", "kharcha", "paid", "gave",
        "debited", "bought", "payment to", "bill", "salary di", "rent diya",
        "spent", "outflow", "chukaaye", "bhugtan kiya", "payment kiya"
    ]
    credit_keywords = [
        "mila", "mile", "aaye", "aaya", "received", "credited", "got", "sale",
        "sold", "jama", "inward", "aaye hain", "payment from", "advance mila",
        "collected", "vasooli"
    ]

    has_debit = any(k in lower_text for k in debit_keywords)
    has_credit = any(k in lower_text for k in credit_keywords)

    if has_credit and not has_debit:
        direction = "CREDIT"
    elif has_debit:
        direction = "DEBIT"
    else:
        direction = "CREDIT" if any(w in lower_text for w in ["customer", "client", "sales", "buyer"]) else "DEBIT"

    # 4. Payment Method / Channel
    channel = "UPI"
    if any(w in lower_text for w in ["cash", "nagad", "rokhad"]):
        channel = "CASH"
    elif any(w in lower_text for w in ["cheque", "check", "chq"]):
        channel = "CHEQUE"
    elif "rtgs" in lower_text:
        channel = "RTGS"
    elif "neft" in lower_text:
        channel = "NEFT"
    elif "imps" in lower_text:
        channel = "IMPS"
    elif any(w in lower_text for w in ["card", "pos", "credit card", "debit card"]):
        channel = "CARD"
    elif any(w in lower_text for w in ["upi", "gpay", "google pay", "phonepe", "paytm", "qr"]):
        channel = "UPI"
    elif any(w in lower_text for w in ["net banking", "bank transfer", "account transfer", "bank"]):
        channel = "BANK"

    # 5. Counterparty Extraction
    counterparty = None
    # Pattern 1: "... [Name] ko ..."
    ko_match = re.search(r"([A-Za-z0-9\s&.-]+?)\s+ko\b", clean_text, re.IGNORECASE)
    # Pattern 2: "... [Name] se ..."
    se_match = re.search(r"([A-Za-z0-9\s&.-]+?)\s+se\b", clean_text, re.IGNORECASE)
    # Pattern 3: "to [Name]" (e.g. "Paid 8500 rupees to Patel Logistics via UPI")
    to_match = re.search(r"\bto\s+([A-Za-z0-9\s&.-]+?)(?:\s+(?:via|for|by|through|today|aaj|kal|yesterday|rupees|rs|\d)|$)", clean_text, re.IGNORECASE)
    # Pattern 4: "from [Name]" (e.g. "Received 5000 from Amit Sharma")
    from_match = re.search(r"\bfrom\s+([A-Za-z0-9\s&.-]+?)(?:\s+(?:via|for|by|through|today|aaj|kal|yesterday|rupees|rs|\d)|$)", clean_text, re.IGNORECASE)

    if ko_match and len(ko_match.group(1).split()) <= 4:
        counterparty = ko_match.group(1).strip()
    elif se_match and len(se_match.group(1).split()) <= 4:
        counterparty = se_match.group(1).strip()
    elif to_match and len(to_match.group(1).split()) <= 5:
        counterparty = to_match.group(1).strip()
    elif from_match and len(from_match.group(1).split()) <= 5:
        counterparty = from_match.group(1).strip()

    # Clean leading relative words from counterparty
    if counterparty:
        counterparty = re.sub(r"^(?:kal|aaj|parson|yesterday|today)\s+", "", counterparty, flags=re.IGNORECASE).strip()
        if counterparty.lower() in ["dukaan", "office", "bank", "monthly", "aaj", "kal", "parson", "store"]:
            counterparty = None

    # 6. Category Extraction
    category = "Raw Materials" if direction == "DEBIT" else "Sales Revenue"
    if any(w in lower_text for w in ["cement", "ret", "material", "raw", "steel", "loha", "stock", "goods", "mal", "hardware"]):
        category = "Raw Materials" if direction == "DEBIT" else "Sales Revenue"
    elif any(w in lower_text for w in ["rent", "kiraya", "godown", "dukaan ka rent"]):
        category = "Rent & Utilities"
    elif any(w in lower_text for w in ["salary", "tankhwah", "wages", "mazdoori", "staff"]):
        category = "Salaries & Wages"
    elif any(w in lower_text for w in ["transport", "tempo", "freight", "gaadi", "logistics", "courier"]):
        category = "Logistics & Transport"
    elif any(w in lower_text for w in ["tea", "chai", "nasta", "snacks", "petty", "stationery"]):
        category = "Office & Miscellaneous"

    # 7. Missing Information Detection
    missing_fields: List[str] = []
    if amount <= 0:
        missing_fields.append("amount")
    if not counterparty:
        missing_fields.append("counterparty")

    clarification_question = None
    if missing_fields:
        if "amount" in missing_fields and "counterparty" in missing_fields:
            clarification_question = "Kripya transaction ki rashi (amount) aur counterparty ka naam batayein. (Please specify the transaction amount and counterparty name.)"
        elif "amount" in missing_fields:
            clarification_question = f"{counterparty or 'Counterparty'} ke liye kitni rashi (amount) thi? (What was the amount for {counterparty or 'this counterparty'}?)"
        elif "counterparty" in missing_fields:
            clarification_question = f"₹{amount:,.2f} ka bhugtan kisse kiya/mila tha? (Who was this payment of ₹{amount:,.2f} made to or received from?)"

    # 8. Confidence Scoring
    confidence = 0.50
    if amount > 0:
        confidence += 0.25
    if counterparty:
        confidence += 0.15
    if category:
        confidence += 0.05
    if has_debit or has_credit:
        confidence += 0.05

    # 9. Structured Description
    if counterparty:
        suggested = f"{'Payment to' if direction == 'DEBIT' else 'Receipt from'} {counterparty} for {category} ({channel})"
    else:
        suggested = f"{direction.capitalize()} of ₹{amount:,.2f} for {category} via {channel}"

    return {
        "raw_narration": clean_text,
        "transaction_date": str(tx_date),
        "amount": float(amount),
        "currency": "INR",
        "direction": direction,
        "type": direction,
        "channel": channel,
        "payment_method": channel,
        "counterparty_name": counterparty,
        "counterparty": counterparty,
        "category": category,
        "description": suggested,
        "suggested_description": suggested,
        "confidence_score": round(min(confidence, 0.98), 2),
        "missing_fields": missing_fields,
        "requires_clarification": len(missing_fields) > 0,
        "clarification_question": clarification_question
    }
