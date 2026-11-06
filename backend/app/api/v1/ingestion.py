from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_tenant
from backend.app.models.user import Tenant
from backend.app.services.ingestion import (
    parse_bank_statement_csv,
    parse_bank_statement_excel,
    ingest_transactions_to_tenant,
    preview_bank_statement,
    confirm_statement_ingestion
)
from backend.app.services.synthetic_data import generate_synthetic_bank_statement, bank_statement_to_csv_string
from backend.app.services.pdf_service import parse_bank_statement_pdf

router = APIRouter()

class IngestionConfirmRecord(BaseModel):
    transaction_date: str
    description: Optional[str] = None
    raw_narration: Optional[str] = None
    amount: float
    type: str
    channel: Optional[str] = "BANK"
    reference_number: Optional[str] = None
    category: Optional[str] = "Uncategorized"

class IngestionConfirmRequest(BaseModel):
    records: List[IngestionConfirmRecord]
    skip_duplicates: bool = True
    auto_post_ledger: bool = True

@router.post("/preview")
async def preview_statement_upload(
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None),
    delimiter: Optional[str] = Form(None),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Step 1 of Two-Phase Ingestion:
    Inspects CSV, Excel or PDF statements, detects columns, validates rows,
    flags duplicates against the tenant's database, and returns preview data for user confirmation.
    """
    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    try:
        preview_data = preview_bank_statement(
            file_bytes=content_bytes,
            filename=file.filename,
            db=db,
            tenant_id=tenant.id,
            sheet_name=sheet_name,
            custom_delimiter=delimiter
        )
        return preview_data
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Statement preview analysis failed: {str(e)}"
        )

@router.post("/confirm")
def confirm_statement_upload(
    payload: IngestionConfirmRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Step 2 of Two-Phase Ingestion:
    Persists user-confirmed statement records to the tenant ledger and generates balanced double-entry entries.
    """
    records_dict = [r.dict() for r in payload.records]
    result = confirm_statement_ingestion(
        db=db,
        tenant_id=tenant.id,
        records=records_dict,
        skip_duplicates=payload.skip_duplicates,
        auto_post_ledger=payload.auto_post_ledger
    )
    return result

@router.post("/excel")
async def upload_bank_statement_excel(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Parses bank statement workbooks in Excel (.xlsx or .xls) format."""
    lower_name = file.filename.lower()
    if not (lower_name.endswith(".xlsx") or lower_name.endswith(".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an Excel format (.xlsx or .xls)"
        )
    content_bytes = await file.read()
    try:
        records = parse_bank_statement_excel(content_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse bank statement Excel file: {str(e)}"
        )

    inserted, duplicates = ingest_transactions_to_tenant(db, tenant.id, records)
    return {
        "status": "success",
        "tenant_id": tenant.id,
        "format": "EXCEL",
        "total_parsed": len(records),
        "inserted": inserted,
        "duplicates_skipped": duplicates,
        "filename": file.filename
    }

@router.post("/statement")
async def upload_bank_statement_auto(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Unified multi-format statement ingestion.
    Auto-detects CSV, Excel (.xlsx, .xls), or PDF.
    """
    lower_name = file.filename.lower()
    content_bytes = await file.read()

    try:
        if lower_name.endswith(".csv"):
            fmt = "CSV"
            try:
                text = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = content_bytes.decode("latin-1")
            records = parse_bank_statement_csv(text)
        elif lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
            fmt = "EXCEL"
            records = parse_bank_statement_excel(content_bytes)
        elif lower_name.endswith(".pdf"):
            fmt = "PDF"
            records = parse_bank_statement_pdf(content_bytes)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported format. Please upload .csv, .xlsx, .xls, or .pdf"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse statement: {str(e)}"
        )

    inserted, duplicates = ingest_transactions_to_tenant(db, tenant.id, records)
    return {
        "status": "success",
        "tenant_id": tenant.id,
        "format": fmt,
        "total_parsed": len(records),
        "inserted": inserted,
        "duplicates_skipped": duplicates,
        "filename": file.filename
    }

@router.post("/csv")
async def upload_bank_statement_csv(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a .csv format"
        )
    content_bytes = await file.read()
    try:
        csv_text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        csv_text = content_bytes.decode("latin-1")

    try:
        records = parse_bank_statement_csv(csv_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse bank statement CSV: {str(e)}"
        )

    inserted, duplicates = ingest_transactions_to_tenant(db, tenant.id, records)
    return {
        "status": "success",
        "tenant_id": tenant.id,
        "total_parsed": len(records),
        "inserted": inserted,
        "duplicates_skipped": duplicates,
        "filename": file.filename
    }

@router.post("/pdf")
async def upload_bank_statement_pdf(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a .pdf format"
        )
    content_bytes = await file.read()
    try:
        records = parse_bank_statement_pdf(content_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse bank statement PDF: {str(e)}"
        )

    inserted, duplicates = ingest_transactions_to_tenant(db, tenant.id, records)
    return {
        "status": "success",
        "tenant_id": tenant.id,
        "total_parsed": len(records),
        "inserted": inserted,
        "duplicates_skipped": duplicates,
        "filename": file.filename
    }

@router.post("/synthetic")
def generate_synthetic_transactions(
    count: int = 25,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Generates realistic Indian bank & UPI transactions in the simulated sandbox for this tenant.
    """
    records = generate_synthetic_bank_statement(num_records=count)
    csv_str = bank_statement_to_csv_string(records)
    parsed = parse_bank_statement_csv(csv_str)
    inserted, duplicates = ingest_transactions_to_tenant(db, tenant.id, parsed)

    return {
        "status": "success",
        "message": f"Generated and ingested {inserted} synthetic Indian banking & UPI transactions.",
        "tenant_id": tenant.id,
        "inserted": inserted,
        "duplicates_skipped": duplicates,
        "notice": "SIMULATED TEST DATA — NO REAL BANK/GOVERNMENT CONNECTION"
    }
