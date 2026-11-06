from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_tenant
from backend.app.models.user import Tenant
from backend.app.services.ingestion import parse_bank_statement_csv, parse_bank_statement_excel, ingest_transactions_to_tenant
from backend.app.services.synthetic_data import generate_synthetic_bank_statement, bank_statement_to_csv_string
from backend.app.services.pdf_service import parse_bank_statement_pdf

router = APIRouter()

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
    if not file.filename.endswith(".csv"):
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
