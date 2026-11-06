from backend.app.core.database import Base, engine, SessionLocal
from backend.app.models import (
    User, Tenant, Membership, Transaction, Receipt,
    LedgerAccount, LedgerEntry, GSTRecord, GSTReport,
    WorkflowRun, UsageRecord, AuditLog
)
from backend.app.core.security import get_password_hash

# Standard Chart of Accounts tailored for Indian MSMEs
STANDARD_CHART_OF_ACCOUNTS = [
    {"code": "1010", "name": "Cash in Hand", "account_type": "ASSET"},
    {"code": "1020", "name": "Bank Account (Current/Savings)", "account_type": "ASSET"},
    {"code": "1030", "name": "Accounts Receivable (Sundry Debtors)", "account_type": "ASSET"},
    {"code": "1040", "name": "Input Tax Credit (CGST Receivable)", "account_type": "ASSET"},
    {"code": "1050", "name": "Input Tax Credit (SGST Receivable)", "account_type": "ASSET"},
    {"code": "1060", "name": "Input Tax Credit (IGST Receivable)", "account_type": "ASSET"},
    {"code": "2010", "name": "Accounts Payable (Sundry Creditors)", "account_type": "LIABILITY"},
    {"code": "2020", "name": "Output GST Payable (CGST Payable)", "account_type": "LIABILITY"},
    {"code": "2030", "name": "Output GST Payable (SGST Payable)", "account_type": "LIABILITY"},
    {"code": "2040", "name": "Output GST Payable (IGST Payable)", "account_type": "LIABILITY"},
    {"code": "3010", "name": "Owner Capital / Equity", "account_type": "EQUITY"},
    {"code": "4010", "name": "Sales Revenue (Goods)", "account_type": "REVENUE"},
    {"code": "4020", "name": "Service Income", "account_type": "REVENUE"},
    {"code": "5010", "name": "Cost of Goods Sold / Raw Materials", "account_type": "EXPENSE"},
    {"code": "5020", "name": "Rent & Utilities", "account_type": "EXPENSE"},
    {"code": "5030", "name": "Salaries & Wages", "account_type": "EXPENSE"},
    {"code": "5040", "name": "Logistics & Transport Expense", "account_type": "EXPENSE"},
    {"code": "5050", "name": "Office & Miscellaneous Expense", "account_type": "EXPENSE"},
]

def init_db(drop_all: bool = False):
    """Initialize database tables and optionally drop old tables."""
    if drop_all:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def seed_standard_accounts_for_tenant(db, tenant_id: str):
    """Ensure every tenant has the standard Indian MSME Chart of Accounts."""
    existing_codes = {
        acc.code for acc in db.query(LedgerAccount).filter(LedgerAccount.tenant_id == tenant_id).all()
    }
    for item in STANDARD_CHART_OF_ACCOUNTS:
        if item["code"] not in existing_codes:
            account = LedgerAccount(
                tenant_id=tenant_id,
                code=item["code"],
                name=item["name"],
                account_type=item["account_type"],
                balance=0.0
            )
            db.add(account)
    db.commit()

def seed_demo_data():
    """Seed initial demo tenant and user for testing."""
    init_db(drop_all=False)
    db = SessionLocal()
    try:
        # Check if demo user exists
        demo_user = db.query(User).filter(User.email == "demo@vyaparsetu.in").first()
        if not demo_user:
            demo_user = User(
                email="demo@vyaparsetu.in",
                password_hash=get_password_hash("VyaparSetu@2026"),
                full_name="Rajesh Sharma (Demo Merchant)",
                phone_number="+919876543210",
                is_active=True
            )
            db.add(demo_user)
            db.flush()

        # Check if demo tenant exists
        demo_tenant = db.query(Tenant).filter(Tenant.simulated_gstin == "27TESTG1234F1Z5").first()
        if not demo_tenant:
            demo_tenant = Tenant(
                name="Sharma Kirana & Hardware Traders",
                trade_name="Sharma Traders",
                simulated_gstin="27TESTG1234F1Z5",
                state_code="27",  # Maharashtra
                business_category="Retail & Hardware Supplies",
                turnover_tier="Micro (< 5 Cr)",
                subscription_plan="PRO"
            )
            db.add(demo_tenant)
            db.flush()

            membership = Membership(
                user_id=demo_user.id,
                tenant_id=demo_tenant.id,
                role="OWNER"
            )
            db.add(membership)
            db.commit()

            # Seed standard MSME Chart of Accounts
            seed_standard_accounts_for_tenant(db, demo_tenant.id)
            print(f"Demo tenant seeded successfully: {demo_tenant.name} (ID: {demo_tenant.id})")
        else:
            print("Demo tenant already exists.")
    finally:
        db.close()

if __name__ == "__main__":
    init_db(drop_all=False)
    seed_demo_data()
    print("Database tables initialized and demo data seeded successfully!")
