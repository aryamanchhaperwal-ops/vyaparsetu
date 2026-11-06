import io
import re
import datetime
from decimal import Decimal
from typing import List, Dict, Any
from pypdf import PdfReader
from backend.app.services.ingestion import parse_indian_date, parse_currency

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extracts raw text streams from digital PDF documents."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n".join(text_parts)

def parse_bank_statement_pdf(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Parses digital Indian bank statement PDFs.
    Looks for line items containing: Date, Description/Narration, Ref/Chq, Debit, Credit.
    """
    full_text = extract_text_from_pdf(pdf_bytes)
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]

    records = []
    # Regex to capture: Date (DD/MM/YYYY, DD-MM-YYYY, DD-Mon-YYYY, YYYY-MM-DD)
    date_pattern = re.compile(
        r"^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4}|\d{1,2}-[A-Za-z]{3}-\d{2,4}|\d{4}-\d{2}-\d{2})"
    )

    for line in lines:
        match = date_pattern.match(line)
        if not match:
            continue

        date_str = match.group(1)

        try:
            tx_date = parse_indian_date(date_str)
            remainder = line[len(date_str):].strip()

            # Find decimal amounts (e.g. 1,50,000.00 or 15000.00 or 150.50)
            amount_matches = re.findall(r"\b\d{1,3}(?:,\d{2,3})*(?:\.\d{2})\b", remainder)
            if not amount_matches:
                # Try finding integer amounts if decimal not explicit
                amount_matches = re.findall(r"\b\d{1,3}(?:,\d{2,3})+\b", remainder)
                if not amount_matches:
                    continue

            # In typical bank statements, the last is Balance, second last is Deposit or Withdrawal
            # E.g. "01/11/2026 UPI/123/Payment to Sharma 15,000.00 1,35,000.00"
            amount_val = parse_currency(amount_matches[-2] if len(amount_matches) >= 2 else amount_matches[-1])
            if amount_val <= 0:
                continue

            line_lower = line.lower()
            if any(w in line_lower for w in ["dr", "withdrawal", "debit", "paid to", "to ", "debiting"]):
                tx_type = "DEBIT"
            elif any(w in line_lower for w in ["cr", "deposit", "credit", "received", "by ", "crediting"]):
                tx_type = "CREDIT"
            else:
                tx_type = "CREDIT" if any(w in line_lower for w in ["sale", "deposit", "inward", "refund", "interest"]) else "DEBIT"

            ref_match = re.search(r"\b(?:UPI|NEFT|RTGS|IMPS|REF|UTR)[/-]?([A-Z0-9]{8,22})\b", line, re.IGNORECASE)
            ref_no = ref_match.group(0) if ref_match else None

            # Clean narration
            narration = remainder
            for amt in amount_matches:
                narration = narration.replace(amt, "")
            narration = re.sub(r"\s+", " ", narration).strip()

            channel = "BANK"
            if "upi" in line_lower:
                channel = "UPI"
            elif "neft" in line_lower:
                channel = "NEFT"
            elif "rtgs" in line_lower:
                channel = "RTGS"
            elif "imps" in line_lower:
                channel = "IMPS"
            elif "cash" in line_lower:
                channel = "CASH"
            elif "chq" in line_lower or "cheque" in line_lower:
                channel = "CHEQUE"
            elif "pos" in line_lower or "card" in line_lower:
                channel = "CARD"

            records.append({
                "transaction_date": tx_date,
                "description": narration[:250] if narration else "Bank Transaction",
                "raw_narration": narration if narration else line,
                "amount": amount_val,
                "type": tx_type,
                "channel": channel,
                "reference_number": ref_no
            })
        except Exception:
            continue

    return records
