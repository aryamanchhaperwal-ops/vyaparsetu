import io
import csv
import re
import datetime
from decimal import Decimal
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
from sqlalchemy.orm import Session
from backend.app.models.transaction import Transaction
from backend.app.services.financial_engine import post_transaction_to_ledger

def parse_indian_date(date_val: Any) -> datetime.date:
    """Parses various Indian date formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, Excel datetime, timestamps)."""
    if isinstance(date_val, (datetime.date, datetime.datetime)):
        return date_val.date() if isinstance(date_val, datetime.datetime) else date_val

    clean_str = str(date_val).strip().split(" ")[0].split("T")[0]
    for fmt in (
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y",
        "%d-%b-%Y", "%d-%B-%Y", "%d %b %Y", "%d %B %Y", "%Y/%m/%d"
    ):
        try:
            return datetime.datetime.strptime(clean_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date: {date_val}")

def parse_currency(amount_str: Any) -> Decimal:
    """Parses Indian currency strings like '1,25,000.50' or '₹ 15,000' to Decimal."""
    if not amount_str or pd.isna(amount_str):
        return Decimal("0.00")
    s = str(amount_str).replace("₹", "").replace("Rs.", "").replace("Rs", "").replace(",", "").replace(" ", "").strip()
    if not s or s == "-":
        return Decimal("0.00")
    try:
        return Decimal(s)
    except Exception:
        return Decimal("0.00")

def find_header_row_and_clean_df(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Detects if top rows contain bank account/branch metadata.
    Finds the row containing standard bank transaction headers, slices the DataFrame,
    and returns a cleaned DataFrame.
    """
    if df_raw.empty:
        return df_raw

    keywords = {"date", "txn", "txndate", "narration", "particulars", "description", "withdrawal", "deposit", "credit", "debit", "balance", "amount", "chq", "ref", "utr"}
    
    # Check if first row is already a good header
    existing_cols = [str(c).lower().strip() for c in df_raw.columns]
    match_count = sum(1 for c in existing_cols if any(k in c for k in keywords))
    if match_count >= 2:
        return df_raw

    # Scan top 25 rows for header keywords
    header_idx = None
    for idx in range(min(25, len(df_raw))):
        row_vals = [str(v).lower().strip() for v in df_raw.iloc[idx].values if pd.notna(v)]
        row_matches = sum(1 for v in row_vals if any(k in v for k in keywords))
        if row_matches >= 2:
            header_idx = idx
            break

    if header_idx is not None:
        new_cols = [str(v).strip() for v in df_raw.iloc[header_idx].values]
        cleaned_df = df_raw.iloc[header_idx + 1:].copy()
        cleaned_df.columns = new_cols
        cleaned_df.reset_index(drop=True, inplace=True)
        return cleaned_df

    return df_raw

def detect_column_mapping(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Detects standard column roles from DataFrame column names."""
    cols = [str(c).strip() for c in df.columns]
    cols_lower = [c.lower() for c in cols]

    mapping: Dict[str, Optional[str]] = {
        "date": None,
        "narration": None,
        "reference": None,
        "withdrawal": None,
        "deposit": None,
        "amount": None,
        "type": None,
    }

    for original, lower in zip(cols, cols_lower):
        if not mapping["date"] and any(k in lower for k in ["date", "txn dt", "txndate", "value date"]):
            mapping["date"] = original
        elif not mapping["narration"] and any(k in lower for k in ["narration", "description", "particulars", "remarks", "details"]):
            mapping["narration"] = original
        elif not mapping["reference"] and any(k in lower for k in ["chq", "ref", "utr", "cheque", "reference", "txn id"]):
            mapping["reference"] = original
        elif not mapping["withdrawal"] and any(k in lower for k in ["withdrawal", "debit", "dr", "paid out", "outflow"]):
            mapping["withdrawal"] = original
        elif not mapping["deposit"] and any(k in lower for k in ["deposit", "credit", "cr", "paid in", "inflow"]):
            mapping["deposit"] = original
        elif not mapping["amount"] and lower in ["amount", "txn amount", "net amount", "total amount"]:
            mapping["amount"] = original
        elif not mapping["type"] and any(k in lower for k in ["type", "dr/cr", "cr/dr", "direction", "cr_dr"]):
            mapping["type"] = original

    return mapping

def _parse_statement_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Core normalisation engine for bank statements across CSV and Excel formats.
    Normalizes columns to: date, narration, reference_number, type, amount, channel.
    """
    df = find_header_row_and_clean_df(df)
    mapping = detect_column_mapping(df)

    date_col = mapping["date"]
    narration_col = mapping["narration"]
    ref_col = mapping["reference"]
    withdrawal_col = mapping["withdrawal"]
    deposit_col = mapping["deposit"]
    amount_col = mapping["amount"]
    type_col = mapping["type"]

    if not date_col or not narration_col:
        raise ValueError("Statement missing required columns (Date and Narration/Particulars)")

    parsed_records = []
    for _, row in df.iterrows():
        try:
            raw_date = row[date_col]
            if pd.isna(raw_date):
                continue
            tx_date = parse_indian_date(raw_date)
            narration = str(row[narration_col]).strip()
            if not narration or narration.lower() in ["nan", "none"]:
                continue

            ref_no = str(row[ref_col]).strip() if ref_col and pd.notna(row[ref_col]) else None
            if ref_no and ref_no.lower() in ["nan", "none", "-"]:
                ref_no = None

            # Determine amount and direction
            debit_amt = parse_currency(row[withdrawal_col]) if withdrawal_col and pd.notna(row[withdrawal_col]) else Decimal("0.00")
            credit_amt = parse_currency(row[deposit_col]) if deposit_col and pd.notna(row[deposit_col]) else Decimal("0.00")

            if debit_amt > 0:
                tx_type = "DEBIT"
                amount = debit_amt
            elif credit_amt > 0:
                tx_type = "CREDIT"
                amount = credit_amt
            elif amount_col and pd.notna(row[amount_col]):
                amt = parse_currency(row[amount_col])
                if amt <= 0:
                    continue
                direction_hint = str(row[type_col]).upper() if type_col and pd.notna(row[type_col]) else ""
                if "CR" in direction_hint or "CREDIT" in direction_hint or "IN" in direction_hint:
                    tx_type = "CREDIT"
                else:
                    tx_type = "DEBIT"
                amount = amt
            else:
                continue

            # Detect Indian payment channel
            channel = "BANK"
            narr_lower = narration.lower()
            if "upi" in narr_lower or (ref_no and len(ref_no) == 12 and ref_no.isdigit()):
                channel = "UPI"
            elif "neft" in narr_lower:
                channel = "NEFT"
            elif "rtgs" in narr_lower:
                channel = "RTGS"
            elif "imps" in narr_lower:
                channel = "IMPS"
            elif "cash" in narr_lower:
                channel = "CASH"
            elif "chq" in narr_lower or "cheque" in narr_lower:
                channel = "CHEQUE"
            elif "pos" in narr_lower or "card" in narr_lower or "ecom" in narr_lower:
                channel = "CARD"

            parsed_records.append({
                "transaction_date": tx_date,
                "description": narration[:250],
                "raw_narration": narration,
                "amount": amount,
                "type": tx_type,
                "channel": channel,
                "reference_number": ref_no,
            })
        except Exception:
            continue

    return parsed_records

def clean_csv_text_before_pandas(text: str) -> str:
    """
    Finds the header row index in CSV text and strips preceding metadata lines
    so that pandas does not encounter field count mismatch errors.
    """
    lines = [l for l in text.splitlines() if l.strip()]
    keywords = {"date", "txn", "txndate", "narration", "particulars", "description", "withdrawal", "deposit", "credit", "debit", "balance", "amount", "chq", "ref", "utr"}
    for idx, line in enumerate(lines[:35]):
        tokens = [t.lower().strip() for t in re.split(r"[,;\t|]", line)]
        if sum(1 for tok in tokens if any(k in tok for k in keywords)) >= 2:
            return "\n".join(lines[idx:])
    return text

def parse_bank_statement_csv(csv_content: str, delimiter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Parses arbitrary Indian bank statement CSVs (HDFC, SBI, ICICI, Axis, Kotak).
    Detects delimiter automatically if not provided.
    """
    cleaned_csv = clean_csv_text_before_pandas(csv_content)
    if not delimiter:
        try:
            sample = "\n".join(cleaned_csv.splitlines()[:15])
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample, delimiters=",\t;|").delimiter
        except Exception:
            delimiter = ","

    df = pd.read_csv(io.StringIO(cleaned_csv), sep=delimiter)
    return _parse_statement_dataframe(df)

def parse_bank_statement_excel(excel_bytes: bytes, sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Parses arbitrary Indian bank statement Excel workbooks (.xlsx or .xls).
    """
    if sheet_name:
        df = pd.read_excel(io.BytesIO(excel_bytes), sheet_name=sheet_name)
    else:
        df = pd.read_excel(io.BytesIO(excel_bytes))
    return _parse_statement_dataframe(df)

def preview_bank_statement(
    file_bytes: bytes,
    filename: str,
    db: Session,
    tenant_id: str,
    sheet_name: Optional[str] = None,
    custom_delimiter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Two-Phase Ingestion Step 1:
    Extracts preview rows, headers, column mappings, worksheet options, row-level validation errors,
    and flags duplicates against the tenant's transaction ledger without persisting to DB.
    """
    from backend.app.services.pdf_service import parse_bank_statement_pdf

    lower_name = filename.lower()
    sheet_names: List[str] = []
    active_sheet: Optional[str] = None
    detected_headers: List[str] = []
    detected_mapping: Dict[str, Optional[str]] = {}
    candidate_records: List[Dict[str, Any]] = []

    # 1. Parse into raw candidate records depending on format
    if lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
        file_type = "EXCEL"
        excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
        sheet_names = excel_file.sheet_names
        active_sheet = sheet_name if sheet_name in sheet_names else sheet_names[0]
        raw_df = pd.read_excel(excel_file, sheet_name=active_sheet)
        cleaned_df = find_header_row_and_clean_df(raw_df)
        detected_headers = [str(c) for c in cleaned_df.columns]
        detected_mapping = detect_column_mapping(cleaned_df)
        candidate_records = _parse_statement_dataframe(raw_df)

    elif lower_name.endswith(".csv"):
        file_type = "CSV"
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except Exception:
                text = file_bytes.decode("cp1252", errors="ignore")

        cleaned_text = clean_csv_text_before_pandas(text)
        delimiter = custom_delimiter
        if not delimiter:
            try:
                sample = "\n".join(cleaned_text.splitlines()[:15])
                delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
            except Exception:
                delimiter = ","

        raw_df = pd.read_csv(io.StringIO(cleaned_text), sep=delimiter)
        cleaned_df = find_header_row_and_clean_df(raw_df)
        detected_headers = [str(c) for c in cleaned_df.columns]
        detected_mapping = detect_column_mapping(cleaned_df)
        candidate_records = _parse_statement_dataframe(raw_df)

    elif lower_name.endswith(".pdf"):
        file_type = "PDF"
        detected_headers = ["Date", "Narration", "Ref/Chq", "Debit", "Credit"]
        detected_mapping = {
            "date": "Date",
            "narration": "Narration",
            "reference": "Ref/Chq",
            "withdrawal": "Debit",
            "deposit": "Credit"
        }
        candidate_records = parse_bank_statement_pdf(file_bytes)

    else:
        raise ValueError("Unsupported format. Please upload .csv, .xlsx, .xls, or .pdf")

    # 2. Row-level validation and duplicate detection against tenant database
    existing_refs = {
        r[0] for r in db.query(Transaction.reference_number).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.reference_number.isnot(None)
        ).all() if r[0]
    }

    seen_batch_refs = set()
    preview_rows: List[Dict[str, Any]] = []
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")
    valid_count = 0
    duplicate_count = 0
    error_count = 0

    for idx, r in enumerate(candidate_records, start=1):
        errors: List[str] = []
        is_duplicate = False

        ref = r.get("reference_number")
        if ref:
            if ref in existing_refs:
                is_duplicate = True
                duplicate_count += 1
                errors.append(f"Duplicate reference ({ref}) already exists in database")
            elif ref in seen_batch_refs:
                is_duplicate = True
                duplicate_count += 1
                errors.append(f"Duplicate reference ({ref}) appears multiple times in file")
            seen_batch_refs.add(ref)

        amt = r.get("amount", Decimal("0.00"))
        if amt <= 0:
            errors.append("Invalid or zero transaction amount")
            error_count += 1

        if not r.get("transaction_date"):
            errors.append("Missing transaction date")
            error_count += 1

        if not r.get("raw_narration"):
            errors.append("Missing narration")
            error_count += 1

        is_valid = len(errors) == 0 or (len(errors) == 1 and is_duplicate)
        if is_valid and not is_duplicate:
            valid_count += 1

        if r.get("type") == "DEBIT":
            total_debit += amt
        else:
            total_credit += amt

        preview_rows.append({
            "row_index": idx,
            "transaction_date": str(r["transaction_date"]),
            "description": r["description"],
            "raw_narration": r["raw_narration"],
            "amount": float(amt),
            "type": r["type"],
            "channel": r["channel"],
            "reference_number": ref,
            "is_duplicate": is_duplicate,
            "is_valid": is_valid,
            "errors": errors
        })

    return {
        "file_type": file_type,
        "filename": filename,
        "sheet_names": sheet_names,
        "active_sheet": active_sheet,
        "detected_headers": detected_headers,
        "detected_mapping": detected_mapping,
        "total_rows": len(preview_rows),
        "valid_rows": valid_count,
        "duplicates_count": duplicate_count,
        "invalid_rows": error_count,
        "total_credit_volume": f"{total_credit:.2f}",
        "total_debit_volume": f"{total_debit:.2f}",
        "preview_rows": preview_rows
    }

def confirm_statement_ingestion(
    db: Session,
    tenant_id: str,
    records: List[Dict[str, Any]],
    skip_duplicates: bool = True,
    auto_post_ledger: bool = True
) -> Dict[str, Any]:
    """
    Two-Phase Ingestion Step 2:
    Takes user-reviewed candidate records, persists confirmed rows to the tenant ledger,
    and optionally generates balanced double-entry vouchers automatically.
    """
    inserted = 0
    duplicates_skipped = 0
    ledger_entries_created = 0

    existing_refs = {
        r[0] for r in db.query(Transaction.reference_number).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.reference_number.isnot(None)
        ).all() if r[0]
    }

    for r in records:
        ref_no = r.get("reference_number")
        if ref_no and ref_no in existing_refs:
            if skip_duplicates:
                duplicates_skipped += 1
                continue

        try:
            tx_date = parse_indian_date(r["transaction_date"])
            amt = Decimal(str(r["amount"]))
        except Exception:
            continue

        category = r.get("category", "Uncategorized")
        tx = Transaction(
            tenant_id=tenant_id,
            transaction_date=tx_date,
            description=r.get("description", r.get("raw_narration", "Bank Transaction"))[:250],
            raw_narration=r.get("raw_narration", r.get("description", "Bank Transaction")),
            amount=amt,
            type=r.get("type", "DEBIT"),
            channel=r.get("channel", "BANK"),
            reference_number=ref_no,
            category=category,
            confidence_score=0.85 if category != "Uncategorized" else 0.5,
            status="CONFIRMED"
        )
        db.add(tx)
        db.flush()

        if ref_no:
            existing_refs.add(ref_no)
        inserted += 1

        if auto_post_ledger:
            try:
                entries = post_transaction_to_ledger(db, tx)
                ledger_entries_created += len(entries)
            except Exception:
                pass

    db.commit()

    return {
        "status": "success",
        "tenant_id": tenant_id,
        "total_submitted": len(records),
        "inserted": inserted,
        "duplicates_skipped": duplicates_skipped,
        "ledger_entries_created": ledger_entries_created
    }

def ingest_transactions_to_tenant(
    db: Session,
    tenant_id: str,
    records: List[Dict[str, Any]]
) -> Tuple[int, int]:
    """
    Inserts normalized transactions into the tenant's transaction ledger.
    Skips exact duplicate reference numbers for the tenant.
    Returns (num_inserted, num_duplicates_skipped).
    """
    res = confirm_statement_ingestion(db, tenant_id, records, skip_duplicates=True, auto_post_ledger=True)
    return res["inserted"], res["duplicates_skipped"]
