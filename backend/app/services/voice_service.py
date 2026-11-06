import re
from decimal import Decimal
from typing import Dict, Any, Optional

def parse_vernacular_voice_narration(text: str) -> Dict[str, Any]:
    """
    Parses Hindi, Hinglish, and Indian English spoken mercantile narration.
    Extracts amount, transaction direction (DEBIT/CREDIT), payment channel,
    counterparty name, expense category, and confidence score.
    """
    clean_text = text.strip()
    lower_text = clean_text.lower()

    # 1. Extract Amount
    amount = Decimal("0.00")
    
    # Check for "k" or "hazar" multiplier (e.g. "25 hazar", "50k", "1.5 lakh")
    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lac|peti)\b", lower_text)
    hazar_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hazar|thousand|k)\b", lower_text)
    
    if lakh_match:
        amount = Decimal(str(float(lakh_match.group(1)) * 100000))
    elif hazar_match:
        amount = Decimal(str(float(hazar_match.group(1)) * 1000))
    else:
        # Standard numeric patterns (e.g. 25000 or 25,000.50 or ₹45000)
        num_matches = re.findall(r"(?:₹|rs\.?|inr)?\s*(\b\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?|\b\d{2,8})\b", lower_text)
        if num_matches:
            # Pick the largest or most prominent number
            candidates = []
            for m in num_matches:
                clean_num = m.replace(",", "").strip()
                try:
                    candidates.append(Decimal(clean_num))
                except Exception:
                    pass
            if candidates:
                amount = max(candidates)

    # 2. Extract Direction (Debit vs Credit)
    debit_keywords = [
        "diye", "diya", "bheja", "transfer kiya", "kharcha", "paid", "gave",
        "debited", "bought", "payment to", "bill", "salary di", "rent diya",
        "spent", "outflow", "chukaaye", "bhugtan kiya"
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
        # Default based on merchant terminology
        direction = "CREDIT" if any(w in lower_text for w in ["customer", "client", "sales"]) else "DEBIT"

    # 3. Extract Payment Channel
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
    elif any(w in lower_text for w in ["net banking", "bank transfer", "account transfer"]):
        channel = "BANK"

    # 4. Extract Counterparty
    counterparty = None
    # Pattern 1: "... [Name] ko ..."
    ko_match = re.search(r"([A-Za-z\s]+?)\s+ko\b", clean_text, re.IGNORECASE)
    # Pattern 2: "... [Name] se ..."
    se_match = re.search(r"([A-Za-z\s]+?)\s+se\b", clean_text, re.IGNORECASE)
    # Pattern 3: "paid to [Name]"
    paid_to_match = re.search(r"paid\s+to\s+([A-Za-z\s]+?)(?:\s+(?:for|via|by|through|rupees|rs|\d)|$)", clean_text, re.IGNORECASE)

    if ko_match and len(ko_match.group(1).split()) <= 4:
        counterparty = ko_match.group(1).strip()
    elif se_match and len(se_match.group(1).split()) <= 4:
        counterparty = se_match.group(1).strip()
    elif paid_to_match:
        counterparty = paid_to_match.group(1).strip()

    # Filter out common stop-words from counterparty
    if counterparty and counterparty.lower() in ["dukaan", "office", "bank", "monthly", "aaj", "kal"]:
        counterparty = None

    # 5. Extract Category
    category = "Raw Materials" if direction == "DEBIT" else "Sales Revenue"
    if any(w in lower_text for w in ["cement", "ret", "material", "raw", "steel", "loha", "stock", "goods", "mal"]):
        category = "Raw Materials" if direction == "DEBIT" else "Sales Revenue"
    elif any(w in lower_text for w in ["rent", "kiraya", "godown", "dukaan ka rent"]):
        category = "Rent & Utilities"
    elif any(w in lower_text for w in ["salary", "tankhwah", "wages", "mazdoori", "staff"]):
        category = "Salaries & Wages"
    elif any(w in lower_text for w in ["transport", "tempo", "freight", "gaadi", "logistics", "courier"]):
        category = "Logistics & Transport"
    elif any(w in lower_text for w in ["tea", "chai", "nasta", "snacks", "petty", "stationery"]):
        category = "Office & Miscellaneous"

    # 6. Confidence Scoring
    confidence = 0.50
    if amount > 0:
        confidence += 0.25
    if counterparty:
        confidence += 0.15
    if category:
        confidence += 0.05
    if has_debit or has_credit:
        confidence += 0.05

    # Suggested Description
    if counterparty:
        suggested = f"{'Payment to' if direction == 'DEBIT' else 'Receipt from'} {counterparty} for {category} ({channel})"
    else:
        suggested = f"{direction.capitalize()} of ₹{amount:,.2f} for {category} via {channel}"

    return {
        "raw_narration": clean_text,
        "amount": float(amount),
        "direction": direction,
        "channel": channel,
        "counterparty_name": counterparty,
        "category": category,
        "confidence_score": round(min(confidence, 0.98), 2),
        "suggested_description": suggested
    }
