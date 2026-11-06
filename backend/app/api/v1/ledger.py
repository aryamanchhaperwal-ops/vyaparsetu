from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_tenant
from backend.app.models.user import Tenant
from backend.app.models.transaction import Transaction
from backend.app.models.ledger import LedgerAccount, LedgerEntry
from backend.app.services.financial_engine import (
    post_transaction_to_ledger,
    generate_trial_balance,
    generate_financial_statements
)
from backend.app.services.reconciliation_service import reconcile_tenant_records

router = APIRouter()

@router.post("/reconcile")
def run_reconciliation(
    auto_link_threshold: float = 0.90,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Executes automated invoice-payment matching and bank statement reconciliation.
    Links matching bank transactions with vendor bills and receipts based on invoice numbers, amounts, and date proximity.
    """
    return reconcile_tenant_records(db, tenant.id, auto_link_threshold=auto_link_threshold)

@router.get("/reconciliation-status")
def get_reconciliation_overview(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Returns reconciliation health metrics, unlinked records, and suggested match candidates."""
    return reconcile_tenant_records(db, tenant.id, auto_link_threshold=1.1)  # Reads without modifying

@router.get("/accounts")
def get_chart_of_accounts(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    accounts = db.query(LedgerAccount).filter(
        LedgerAccount.tenant_id == tenant.id
    ).order_by(LedgerAccount.code).all()
    return [
        {
            "id": a.id,
            "code": a.code,
            "name": a.name,
            "account_type": a.account_type,
            "balance": f"{a.balance:.2f}"
        }
        for a in accounts
    ]

@router.post("/post/{transaction_id}")
def post_transaction(
    transaction_id: str,
    is_interstate: bool = False,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.tenant_id == tenant.id
    ).first()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if tx.is_reconciled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction already posted to ledger")

    entries = post_transaction_to_ledger(db, tx, is_interstate=is_interstate)
    return {
        "status": "success",
        "transaction_id": tx.id,
        "entries_created": len(entries),
        "total_debit": f"{sum(e.debit for e in entries):.2f}",
        "total_credit": f"{sum(e.credit for e in entries):.2f}"
    }

@router.get("/trial-balance")
def get_trial_balance(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    return generate_trial_balance(db, tenant.id)

@router.get("/financial-statements")
def get_financial_statements(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Returns real-time Profit & Loss and Balance Sheet for the business workspace."""
    return generate_financial_statements(db, tenant.id)

@router.get("/entries")
def get_ledger_entries(
    account_code: Optional[str] = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    query = db.query(LedgerEntry).filter(LedgerEntry.tenant_id == tenant.id)
    if account_code:
        acc = db.query(LedgerAccount).filter(
            LedgerAccount.tenant_id == tenant.id,
            LedgerAccount.code == account_code
        ).first()
        if acc:
            query = query.filter(LedgerEntry.account_id == acc.id)
    entries = query.order_by(LedgerEntry.entry_date.desc()).all()
    return [
        {
            "id": e.id,
            "entry_date": e.entry_date.isoformat(),
            "debit": f"{e.debit:.2f}",
            "credit": f"{e.credit:.2f}",
            "narration": e.narration,
            "account_id": e.account_id
        }
        for e in entries
    ]

