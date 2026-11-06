from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_tenant
from backend.app.models.user import Tenant
from backend.app.models.receipt import Receipt
from backend.app.models.transaction import Transaction
from backend.app.services.ocr_service import process_and_save_receipt

router = APIRouter()

class ReconcileReceiptRequest(BaseModel):
    receipt_id: str
    transaction_id: str

class CreateInvoiceRecordRequest(BaseModel):
    invoice_number: str
    invoice_date: str
    vendor_name: str
    vendor_gstin: Optional[str] = None
    total_amount: float
    taxable_amount: float
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0

@router.post("/invoice-record")
def create_invoice_record(
    req: CreateInvoiceRecordRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Directly creates a structured invoice/receipt record in the tenant ledger."""
    import datetime
    from decimal import Decimal
    try:
        inv_date = datetime.date.fromisoformat(req.invoice_date)
    except Exception:
        inv_date = datetime.date.today()

    rcpt = Receipt(
        tenant_id=tenant.id,
        invoice_number=req.invoice_number,
        invoice_date=inv_date,
        vendor_name=req.vendor_name,
        vendor_gstin=req.vendor_gstin,
        total_amount=Decimal(str(req.total_amount)),
        taxable_amount=Decimal(str(req.taxable_amount)),
        cgst_amount=Decimal(str(req.cgst_amount)),
        sgst_amount=Decimal(str(req.sgst_amount)),
        igst_amount=Decimal(str(req.igst_amount)),
        status="EXTRACTED"
    )
    db.add(rcpt)
    db.commit()
    db.refresh(rcpt)

    return {
        "status": "success",
        "receipt_id": rcpt.id,
        "invoice_number": rcpt.invoice_number,
        "vendor_name": rcpt.vendor_name,
        "total_amount": f"{rcpt.total_amount:.2f}"
    }

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

@router.post("/reconcile")
def link_receipt_to_transaction(
    req: ReconcileReceiptRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Manually links an invoice/receipt to a bank transaction and marks both reconciled."""
    rcpt = db.query(Receipt).filter(Receipt.id == req.receipt_id, Receipt.tenant_id == tenant.id).first()
    if not rcpt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    tx = db.query(Transaction).filter(Transaction.id == req.transaction_id, Transaction.tenant_id == tenant.id).first()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    rcpt.transaction_id = tx.id
    rcpt.status = "RECONCILED"
    tx.is_reconciled = True
    db.commit()
    return {
        "status": "success",
        "receipt_id": rcpt.id,
        "transaction_id": tx.id,
        "message": "Receipt successfully matched and reconciled to transaction."
    }

