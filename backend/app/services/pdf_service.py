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
    # Regex to capture: Date (DD/MM/YYYY or DD-MM-YYYY) followed by Narration and amounts
    date_pattern = re.compile(r"^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})")

    for line in lines:
        match = date_pattern.match(line)
        if not match:
            continue

        parts = line.split()
        if len(parts) < 3:
            continue

        try:
            tx_date = parse_indian_date(parts[0])
            
            # Find decimal amounts from the right side of the line
            amount_matches = re.findall(r"\b\d{1,3}(?:,\d{2,3})*(?:\.\d{2})\b", line)
            if not amount_matches:
                continue

            # In typical bank statements, the last is Balance, second last is Deposit or Withdrawal
            # E.g. "01/11/2026 UPI/123/Payment to Sharma 15,000.00 1,35,000.00"
            amount_val = parse_currency(amount_matches[-2] if len(amount_matches) >= 2 else amount_matches[-1])
            if amount_val <= 0:
                continue

            line_lower = line.lower()
            if any(w in line_lower for w in ["dr", "withdrawal", "debit", "paid to", "to "]):
                tx_type = "DEBIT"
            elif any(w in line_lower for w in ["cr", "deposit", "credit", "received", "by "]):
                tx_type = "CREDIT"
            else:
                # Default based on narration context
                tx_type = "CREDIT" if "sale" in line_lower or "deposit" in line_lower else "DEBIT"

            ref_match = re.search(r"\b(?:UPI|NEFT|RTGS|IMPS|REF|UTR)[/-]?([A-Z0-9]{8,18})\b", line, re.IGNORECASE)
            ref_no = ref_match.group(0) if ref_match else None

            # Narration is the text between date and amounts
            narration = line
            for amt in amount_matches:
                narration = narration.replace(amt, "")
            narration = narration.replace(parts[0], "").strip()

            channel = "UPI" if "upi" in line_lower else ("NEFT" if "neft" in line_lower else ("CASH" if "cash" in line_lower else "BANK"))

            records.append({
                "transaction_date": tx_date,
                "description": narration[:250],
                "raw_narration": narration,
                "amount": amount_val,
                "type": tx_type,
                "channel": channel,
                "reference_number": ref_no
            })
        except Exception:
            continue

    return records

