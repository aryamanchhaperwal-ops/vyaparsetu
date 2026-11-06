from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_tenant
from backend.app.models.user import Tenant
from backend.app.models.receipt import Receipt
from backend.app.services.ocr_service import process_and_save_receipt

router = APIRouter()

@router.post("/upload")
async def upload_receipt(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    allowed_exts = (".png", ".jpg", ".jpeg", ".pdf")
    if not any(file.filename.lower().endswith(ext) for ext in allowed_exts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image (.png, .jpg, .jpeg) or .pdf"
        )

    file_bytes = await file.read()
    receipt = process_and_save_receipt(db, tenant.id, file_bytes, file.filename)
    return {
        "status": "success",
        "receipt_id": receipt.id,
        "invoice_number": receipt.invoice_number,
        "vendor_name": receipt.vendor_name,
        "vendor_gstin": receipt.vendor_gstin,
        "total_amount": f"{receipt.total_amount:.2f}",
        "taxable_amount": f"{receipt.taxable_amount:.2f}",
        "cgst": f"{receipt.cgst_amount:.2f}",
        "sgst": f"{receipt.sgst_amount:.2f}",
        "igst": f"{receipt.igst_amount:.2f}",
        "status": receipt.status
    }

@router.get("/receipts")
def list_receipts(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    receipts = db.query(Receipt).filter(
        Receipt.tenant_id == tenant.id
    ).order_by(desc(Receipt.created_at)).all()

    return [
        {
            "id": r.id,
            "invoice_number": r.invoice_number,
            "invoice_date": r.invoice_date.isoformat() if r.invoice_date else None,
            "vendor_name": r.vendor_name,
            "vendor_gstin": r.vendor_gstin,
            "total_amount": f"{r.total_amount:.2f}" if r.total_amount else "0.00",
            "status": r.status,
            "transaction_id": r.transaction_id
        }
        for r in receipts
    ]
