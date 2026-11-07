import io
import pytest
import datetime
from decimal import Decimal
import pandas as pd
from backend.app.core.database import SessionLocal
from backend.app.models.user import Tenant
from backend.app.models.transaction import Transaction
from backend.app.services.ingestion import preview_bank_statement, confirm_statement_ingestion

@pytest.fixture
def test_ingestion_tenant():
    db = SessionLocal()
    tenant = db.query(Tenant).filter(Tenant.simulated_gstin == "27TESTINGEST01Z8").first()
    if not tenant:
        tenant = Tenant(
            name="Test Ingestion Enterprises",
            simulated_gstin="27TESTINGEST01Z8",
            state_code="27",
            currency_symbol="₹"
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

    # Clean up any leftover transactions from previous test runs to ensure idempotency
    db.query(Transaction).filter(Transaction.tenant_id == tenant.id).delete()
    db.commit()

    # Seed an existing reference to test duplicate detection
    existing_tx = Transaction(
        tenant_id=tenant.id,
        transaction_date=datetime.date(2026, 11, 1),
        description="Existing Bank Outflow",
        raw_narration="UPI/UTR_EXISTING_999/Old supplier",
        amount=Decimal("5000.00"),
        type="DEBIT",
        channel="UPI",
        reference_number="UTR_EXISTING_999"
    )
    db.add(existing_tx)
    db.commit()

    yield db, tenant
    db.close()

def test_preview_csv_with_dirty_headers_and_duplicates(test_ingestion_tenant):
    db, tenant = test_ingestion_tenant

    # CSV with bank branch metadata rows on top
    csv_content = """State Bank of India - Account Statement
Account Number: 1234567890
Branch: Pune Main
Date,Narration,Ref/Chq,Debit,Credit,Balance
01/11/2026,UPI/111/Cement Supplier,UTR_FRESH_001,12000.00,,88000.00
02/11/2026,UPI/999/Old Supplier,UTR_EXISTING_999,5000.00,,83000.00
03/11/2026,Customer Payment Inward,UTR_FRESH_002,,25000.00,108000.00
"""
    preview = preview_bank_statement(
        file_bytes=csv_content.encode("utf-8"),
        filename="sbi_statement.csv",
        db=db,
        tenant_id=tenant.id
    )

    assert preview["file_type"] == "CSV"
    assert preview["total_rows"] == 3
    assert preview["duplicates_count"] == 1  # UTR_EXISTING_999 flagged
    assert preview["valid_rows"] == 2  # 2 fresh valid records

    # Confirm ingestion skipping duplicates
    valid_candidates = [r for r in preview["preview_rows"] if not r["is_duplicate"]]
    result = confirm_statement_ingestion(
        db=db,
        tenant_id=tenant.id,
        records=valid_candidates,
        skip_duplicates=True,
        auto_post_ledger=True
    )

    assert result["inserted"] == 2
    assert result["status"] == "success"

def test_preview_excel_workbook(test_ingestion_tenant):
    db, tenant = test_ingestion_tenant

    df = pd.DataFrame([
        {"Date": "04/11/2026", "Particulars": "Office Rent NEFT", "Reference": "NEFT_RENT_88", "Withdrawal": 18000.00, "Deposit": None},
        {"Date": "05/11/2026", "Particulars": "Retail Sales Inflow", "Reference": "UPI_SALES_99", "Withdrawal": None, "Deposit": 32000.00},
    ])

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="AccountTransactions", index=False)

    excel_bytes = buf.getvalue()

    preview = preview_bank_statement(
        file_bytes=excel_bytes,
        filename="hdfc_statement.xlsx",
        db=db,
        tenant_id=tenant.id,
        sheet_name="AccountTransactions"
    )

    assert preview["file_type"] == "EXCEL"
    assert preview["total_rows"] == 2
    assert preview["active_sheet"] == "AccountTransactions"
    assert "AccountTransactions" in preview["sheet_names"]
    assert preview["valid_rows"] == 2
