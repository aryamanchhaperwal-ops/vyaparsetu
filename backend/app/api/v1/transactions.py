from typing import List, Optional
import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_tenant
from backend.app.models.user import Tenant
from backend.app.models.transaction import Transaction
from backend.app.schemas.transaction import TransactionCreate, TransactionOut

router = APIRouter()

@router.get("", response_model=List[TransactionOut])
def list_transactions(
    tenant: Tenant = Depends(get_current_tenant),
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    status: Optional[str] = None,
    tx_type: Optional[str] = Query(None, alias="type"),
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(Transaction).filter(Transaction.tenant_id == tenant.id)

    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)
    if status:
        query = query.filter(Transaction.status == status)
    if tx_type:
        query = query.filter(Transaction.type == tx_type)
    if category:
        query = query.filter(Transaction.category == category)

    return query.order_by(desc(Transaction.transaction_date), desc(Transaction.created_at)).offset(skip).limit(limit).all()

@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_manual_transaction(
    tx_in: TransactionCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    tx = Transaction(
        tenant_id=tenant.id,
        transaction_date=tx_in.transaction_date,
        description=tx_in.description,
        raw_narration=tx_in.raw_narration,
        amount=tx_in.amount,
        type=tx_in.type,
        channel=tx_in.channel,
        reference_number=tx_in.reference_number,
        category=tx_in.category,
        sub_category=tx_in.sub_category,
        hsn_sac_code=tx_in.hsn_sac_code,
        tax_rate=tx_in.tax_rate,
        counterparty_name=tx_in.counterparty_name,
        counterparty_gstin=tx_in.counterparty_gstin,
        confidence_score=1.0,
        status="CONFIRMED",
        is_reconciled=False
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx

@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.tenant_id == tenant.id
    ).first()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return tx
