import io
import random
import datetime
from decimal import Decimal
from typing import List, Dict, Any, Tuple
import pandas as pd

INDIAN_BANKS = ["HDFC BANK", "STATE BANK OF INDIA", "ICICI BANK", "KOTAK MAHINDRA", "AXIS BANK"]

INDIAN_VENDORS = [
    {"name": "Sharma Cement & Building Materials", "category": "Raw Materials", "gstin_prefix": "27", "hsn": "2523", "rate": 18.0},
    {"name": "Gupta Steel & Hardware Mart", "category": "Raw Materials", "gstin_prefix": "27", "hsn": "7214", "rate": 18.0},
    {"name": "Shree Ganesh Logistics & Transport", "category": "Logistics & Transport", "gstin_prefix": "27", "hsn": "9965", "rate": 5.0},
    {"name": "Patel Property & Warehouse Rentals", "category": "Rent & Utilities", "gstin_prefix": "27", "hsn": "9972", "rate": 18.0},
    {"name": "MahaVitaran State Electricity Board", "category": "Rent & Utilities", "gstin_prefix": "27", "hsn": "9969", "rate": 0.0},
    {"name": "Chai & Snacks Corner (Local Vendor)", "category": "Office & Miscellaneous", "gstin_prefix": None, "hsn": "9963", "rate": 5.0},
    {"name": "Jio Business Internet Services", "category": "Rent & Utilities", "gstin_prefix": "27", "hsn": "9984", "rate": 18.0},
    {"name": "Modern Stationery & Printing Works", "category": "Office & Miscellaneous", "gstin_prefix": "27", "hsn": "4901", "rate": 12.0},
]

INDIAN_CUSTOMERS = [
    "Rahul Verma", "Deepak Joshi", "Sunita Agarwal", "Pooja Mehta",
    "Anand Rao", "Kavita Singh", "Manoj Tiwari", "Vikram Rathore"
]

def generate_synthetic_bank_statement(
    num_records: int = 30,
    start_date: datetime.date = None,
    bank_name: str = "HDFC BANK",
    account_number: str = "50100492817291"
) -> List[Dict[str, Any]]:
    """
    Generates realistic Indian bank statement line items with standard UTR, UPI, NEFT and IMPS references.
    """
    if start_date is None:
        start_date = datetime.date.today() - datetime.timedelta(days=num_records)

    records = []
    current_balance = Decimal("150000.00")
    
    for i in range(num_records):
        tx_date = start_date + datetime.timedelta(days=i)
        is_credit = random.random() < 0.40  # 40% income, 60% expenses
        
        ref_id = f"REF{random.randint(100000000000, 999999999999)}"
        
        if is_credit:
            customer = random.choice(INDIAN_CUSTOMERS)
            channel = random.choice(["UPI", "NEFT", "IMPS", "CASH"])
            amount = Decimal(str(random.randint(500, 45000)))
            
            if channel == "UPI":
                upi_id = f"{customer.lower().replace(' ', '')}@okaxis"
                narration = f"UPI/{ref_id}/CR/{upi_id}/Retail customer bill payment"
            elif channel == "NEFT":
                narration = f"NEFT-CR-{ref_id}-{customer.upper()}-INVOICE PAYMENT"
            elif channel == "IMPS":
                narration = f"IMPS/P2A/{ref_id}/{customer}/Goods advance"
            else:
                narration = f"BY CASH DEPOSIT - BRANCH DUKAN COUNTER SALES"
                
            current_balance += amount
            records.append({
                "Date": tx_date.strftime("%d/%m/%Y"),
                "Narration": narration,
                "Chq/Ref No": ref_id,
                "Value Dt": tx_date.strftime("%d/%m/%Y"),
                "Withdrawal Amt": "",
                "Deposit Amt": f"{amount:.2f}",
                "Closing Balance": f"{current_balance:.2f}",
                "Channel": channel,
                "Type": "CREDIT",
                "Amount": amount
            })
        else:
            vendor = random.choice(INDIAN_VENDORS)
            channel = random.choice(["UPI", "NEFT", "RTGS", "CHEQUE"])
            
            if vendor["category"] == "Raw Materials":
                amount = Decimal(str(random.randint(5000, 75000)))
            elif vendor["category"] == "Rent & Utilities":
                amount = Decimal(str(random.randint(2000, 30000)))
            elif vendor["category"] == "Office & Miscellaneous":
                amount = Decimal(str(random.randint(150, 3500)))
            else:
                amount = Decimal(str(random.randint(1000, 15000)))
                
            if channel == "UPI":
                narration = f"UPI/{ref_id}/DR/merchant@{vendor['name'].split()[0].lower()}/{vendor['name']} payment"
            elif channel == "NEFT":
                narration = f"NEFT-DR-{ref_id}-{vendor['name'][:20]}-PURCHASE"
            elif channel == "RTGS":
                narration = f"RTGS-DR-{ref_id}-{vendor['name'][:20]}-STOCK"
            else:
                narration = f"TO CHEQUE/CHQ-{random.randint(100000, 999999)} - {vendor['name'][:20]}"
                
            current_balance -= amount
            records.append({
                "Date": tx_date.strftime("%d/%m/%Y"),
                "Narration": narration,
                "Chq/Ref No": ref_id,
                "Value Dt": tx_date.strftime("%d/%m/%Y"),
                "Withdrawal Amt": f"{amount:.2f}",
                "Deposit Amt": "",
                "Closing Balance": f"{current_balance:.2f}",
                "Channel": channel,
                "Type": "DEBIT",
                "Amount": amount
            })

    # Add a couple of realistic ambiguous transactions for Human-in-the-Loop review testing
    ambiguous_date = start_date + datetime.timedelta(days=5)
    records.append({
        "Date": ambiguous_date.strftime("%d/%m/%Y"),
        "Narration": "UPI/998877665544/DR/transfer to suresh/personal loan repayment",
        "Chq/Ref No": "998877665544",
        "Value Dt": ambiguous_date.strftime("%d/%m/%Y"),
        "Withdrawal Amt": "7500.00",
        "Deposit Amt": "",
        "Closing Balance": f"{(current_balance - Decimal('7500.00')):.2f}",
        "Channel": "UPI",
        "Type": "DEBIT",
        "Amount": Decimal("7500.00")
    })

    return records

def bank_statement_to_csv_string(records: List[Dict[str, Any]]) -> str:
    """Converts statement records to standard Indian bank CSV format."""
    df = pd.DataFrame(records)
    export_cols = ["Date", "Narration", "Chq/Ref No", "Value Dt", "Withdrawal Amt", "Deposit Amt", "Closing Balance"]
    return df[export_cols].to_csv(index=False)

def bank_statement_to_excel_bytes(records: List[Dict[str, Any]]) -> bytes:
    """Converts statement records to Excel (.xlsx) bytes."""
    df = pd.DataFrame(records)
    export_cols = ["Date", "Narration", "Chq/Ref No", "Value Dt", "Withdrawal Amt", "Deposit Amt", "Closing Balance"]
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df[export_cols].to_excel(writer, index=False, sheet_name="BankStatement")
    return buffer.getvalue()

def generate_reproducible_msme_dataset() -> Dict[str, Any]:
    """
    Creates a deterministic, fully reproducible Indian MSME financial dataset.
    Includes:
    - Business Profile (Shree Krishna Traders, Maharashtra GSTIN: 27AABCU9603R1ZM)
    - 20 Categorized Transactions (Raw materials, rent, utilities, transport, salaries, retail sales)
    - 1 Duplicate Reference Transaction (to verify deduplication engine)
    - 1 Section 40A(3) Cash Outflow Anomaly (cash > ₹10,000)
    - 1 Ambiguous / Low-Confidence Transaction (to verify Human-in-the-Loop review)
    - 5 Matching Vendor Invoices / Receipts with GSTINs and HSN codes
    """
    base_date = datetime.date(2026, 3, 1)

    business_profile = {
        "name": "Shree Krishna Building Supplies & Hardware",
        "gstin": "27AABCU9603R1ZM",
        "state_code": "27",
        "state_name": "Maharashtra",
        "currency": "INR",
        "turnover_tier": "REGULAR_GST_MSME"
    }

    # 1. Vendor & Customer Directory
    vendors = [
        {"name": "UltraTech Cement Limited", "gstin": "27AAACU1234F1Z5", "category": "Raw Materials", "hsn": "2523", "rate": 18.0},
        {"name": "Tata Tiscon Steel Stockists", "gstin": "27AABCT5678G1Z9", "category": "Raw Materials", "hsn": "7214", "rate": 18.0},
        {"name": "Gati KWE Logistics Transporters", "gstin": "27AACCG9012H1Z3", "category": "Logistics & Transport", "hsn": "9965", "rate": 5.0},
        {"name": "Shivaji Commercial Godown Rentals", "gstin": "27AABCS3456J1Z1", "category": "Rent & Utilities", "hsn": "9972", "rate": 18.0},
        {"name": "MSEDCL Maharashtra Electricity Board", "gstin": "27AAECM7890K1Z7", "category": "Rent & Utilities", "hsn": "9969", "rate": 0.0},
        {"name": "Local Chai & Nasta Canteen", "gstin": None, "category": "Office & Miscellaneous", "hsn": "9963", "rate": 5.0}
    ]

    customers = [
        {"name": "Apex Builders & Developers", "gstin": "27AAAFA1111B1Z2", "type": "B2B"},
        {"name": "Rajesh Sharma (Retail Home Builder)", "gstin": None, "type": "B2C"},
        {"name": "Pooja Construction Projects", "gstin": "27AAACP2222C1Z4", "type": "B2B"},
        {"name": "Amit Patel (Retail Cash Customer)", "gstin": None, "type": "B2C"}
    ]

    # 2. Invoices (for automated reconciliation)
    invoices = [
        {
            "invoice_number": "INV/UTC/2026/089",
            "invoice_date": (base_date + datetime.timedelta(days=2)).isoformat(),
            "vendor_name": "UltraTech Cement Limited",
            "vendor_gstin": "27AAACU1234F1Z5",
            "total_amount": 29500.00,
            "taxable_amount": 25000.00,
            "cgst_amount": 2250.00,
            "sgst_amount": 2250.00,
            "igst_amount": 0.00,
            "items": [{"description": "Grade 53 Portland Pozzolana Cement 70 bags", "hsn": "2523", "qty": 70, "rate": 357.14}]
        },
        {
            "invoice_number": "INV/TTS/2026/142",
            "invoice_date": (base_date + datetime.timedelta(days=5)).isoformat(),
            "vendor_name": "Tata Tiscon Steel Stockists",
            "vendor_gstin": "27AABCT5678G1Z9",
            "total_amount": 47200.00,
            "taxable_amount": 40000.00,
            "cgst_amount": 3600.00,
            "sgst_amount": 3600.00,
            "igst_amount": 0.00,
            "items": [{"description": "12mm Fe550D TMT Rebars 1 Metric Ton", "hsn": "7214", "qty": 1, "rate": 40000.00}]
        },
        {
            "invoice_number": "LR/GATI/78912",
            "invoice_date": (base_date + datetime.timedelta(days=6)).isoformat(),
            "vendor_name": "Gati KWE Logistics Transporters",
            "vendor_gstin": "27AACCG9012H1Z3",
            "total_amount": 3675.00,
            "taxable_amount": 3500.00,
            "cgst_amount": 87.50,
            "sgst_amount": 87.50,
            "igst_amount": 0.00,
            "items": [{"description": "Freight & goods transport chhota hathi consignment", "hsn": "9965", "qty": 1, "rate": 3500.00}]
        },
        {
            "invoice_number": "RENT/SHIV/MAR26",
            "invoice_date": (base_date + datetime.timedelta(days=1)).isoformat(),
            "vendor_name": "Shivaji Commercial Godown Rentals",
            "vendor_gstin": "27AABCS3456J1Z1",
            "total_amount": 23600.00,
            "taxable_amount": 20000.00,
            "cgst_amount": 1800.00,
            "sgst_amount": 1800.00,
            "igst_amount": 0.00,
            "items": [{"description": "Commercial Premises Rent for godown No. 4", "hsn": "9972", "qty": 1, "rate": 20000.00}]
        },
        {
            "invoice_number": "INV/UNLINKED/001",
            "invoice_date": (base_date + datetime.timedelta(days=22)).isoformat(),
            "vendor_name": "Hardware Fasteners & Bolts Supplier",
            "vendor_gstin": "27AABCF9999K1Z0",
            "total_amount": 8500.00,
            "taxable_amount": 7203.39,
            "cgst_amount": 648.31,
            "sgst_amount": 648.31,
            "igst_amount": 0.00,
            "items": [{"description": "High tensile hex bolts & washers", "hsn": "7318", "qty": 500, "rate": 14.41}]
        }
    ]

    # 3. Deterministic Bank Statement Transactions
    transactions = [
        # Rent Payment (matches RENT/SHIV/MAR26)
        {
            "Date": (base_date + datetime.timedelta(days=1)).strftime("%d/%m/%Y"),
            "Narration": "NEFT-DR-RENT20260301-SHIVAJI GODOWN RENT MAR26",
            "Chq/Ref No": "NEFT0019283710",
            "Value Dt": (base_date + datetime.timedelta(days=1)).strftime("%d/%m/%Y"),
            "Withdrawal Amt": "23600.00",
            "Deposit Amt": "",
            "Closing Balance": "176400.00",
            "Channel": "NEFT",
            "Type": "DEBIT",
            "Amount": Decimal("23600.00")
        },
        # Cement Payment (matches INV/UTC/2026/089)
        {
            "Date": (base_date + datetime.timedelta(days=3)).strftime("%d/%m/%Y"),
            "Narration": "RTGS-DR-RTGS992817291-ULTRATECH CEMENT LTD INV/UTC/2026/089",
            "Chq/Ref No": "RTGS992817291",
            "Value Dt": (base_date + datetime.timedelta(days=3)).strftime("%d/%m/%Y"),
            "Withdrawal Amt": "29500.00",
            "Deposit Amt": "",
            "Closing Balance": "146900.00",
            "Channel": "RTGS",
            "Type": "DEBIT",
            "Amount": Decimal("29500.00")
        },
        # Steel Payment (matches INV/TTS/2026/142)
        {
            "Date": (base_date + datetime.timedelta(days=5)).strftime("%d/%m/%Y"),
            "Narration": "NEFT-DR-N102938475-TATA TISCON STEEL STOCKISTS",
            "Chq/Ref No": "N102938475",
            "Value Dt": (base_date + datetime.timedelta(days=5)).strftime("%d/%m/%Y"),
            "Withdrawal Amt": "47200.00",
            "Deposit Amt": "",
            "Closing Balance": "99700.00",
            "Channel": "NEFT",
            "Type": "DEBIT",
            "Amount": Decimal("47200.00")
        },
        # Freight Transport (matches LR/GATI/78912)
        {
            "Date": (base_date + datetime.timedelta(days=6)).strftime("%d/%m/%Y"),
            "Narration": "UPI/606512345678/DR/gatikwe@okaxis/chhota hathi tempo bhadha",
            "Chq/Ref No": "606512345678",
            "Value Dt": (base_date + datetime.timedelta(days=6)).strftime("%d/%m/%Y"),
            "Withdrawal Amt": "3675.00",
            "Deposit Amt": "",
            "Closing Balance": "96025.00",
            "Channel": "UPI",
            "Type": "DEBIT",
            "Amount": Decimal("3675.00")
        },
        # B2B Customer Receipt (Sales Inflow)
        {
            "Date": (base_date + datetime.timedelta(days=8)).strftime("%d/%m/%Y"),
            "Narration": "NEFT-CR-N998877665-APEX BUILDERS AND DEVELOPERS INVOICE PAYMENT",
            "Chq/Ref No": "N998877665",
            "Value Dt": (base_date + datetime.timedelta(days=8)).strftime("%d/%m/%Y"),
            "Withdrawal Amt": "",
            "Deposit Amt": "85000.00",
            "Closing Balance": "181025.00",
            "Channel": "NEFT",
            "Type": "CREDIT",
            "Amount": Decimal("85000.00")
        },
        # Electricity Bill
        {
            "Date": (base_date + datetime.timedelta(days=10)).strftime("%d/%m/%Y"),
            "Narration": "UPI/610599887766/DR/mahadiscom@icici/bijli bill dukan feb payment",
            "Chq/Ref No": "610599887766",
            "Value Dt": (base_date + datetime.timedelta(days=10)).strftime("%d/%m/%Y"),
            "Withdrawal Amt": "4850.00",
            "Deposit Amt": "",
            "Closing Balance": "176175.00",
            "Channel": "UPI",
            "Type": "DEBIT",
            "Amount": Decimal("4850.00")
        },
        # Staff Salaries
        {
            "Date": (base_date + datetime.timedelta(days=11)).strftime("%d/%m/%Y"),
            "Narration": "NEFT-DR-N334455667-SALARY MAR26 STAFF RAMESH & SURESH",
            "Chq/Ref No": "N334455667",
            "Value Dt": (base_date + datetime.timedelta(days=11)).strftime("%d/%m/%Y"),
            "Withdrawal Amt": "32000.00",
            "Deposit Amt": "",
            "Closing Balance": "144175.00",
            "Channel": "NEFT",
            "Type": "DEBIT",
            "Amount": Decimal("32000.00")
        },
        # Retail B2C Sales (Daily UPI collection)
        {
            "Date": (base_date + datetime.timedelta(days=12)).strftime("%d/%m/%Y"),
            "Narration": "UPI/612500112233/CR/rajeshsharma@okicici/counter retail cement sale",
            "Chq/Ref No": "612500112233",
            "Value Dt": (base_date + datetime.timedelta(days=12)).strftime("%d/%m/%Y"),
            "Withdrawal Amt": "",
            "Deposit Amt": "14500.00",
            "Closing Balance": "158675.00",
            "Channel": "UPI",
            "Type": "CREDIT",
            "Amount": Decimal("14500.00")
        },
        # Office Pantry & Refreshment
        {
            "Date": (base_date + datetime.timedelta(days=13)).strftime("%d/%m/%Y"),
            "Narration": "UPI/613588776655/DR/canteen@paytm/chai nasta and stationery expenses",
            "Chq/Ref No": "613588776655",
            "Value Dt": (base_date + datetime.timedelta(days=13)).strftime("%d/%m/%Y"),
            "Withdrawal Amt": "680.00",
            "Deposit Amt": "",
            "Closing Balance": "157995.00",
            "Channel": "UPI",
            "Type": "DEBIT",
            "Amount": Decimal("680.00")
        },
        # ANOMALY TEST: Section 40A(3) High-value cash outflow > ₹10,000
        {
            "Date": (base_date + datetime.timedelta(days=14)).strftime("%d/%m/%Y"),
            "Narration": "BY CASH WITHDRAWAL - DUKAN COUNTER RAW MATERIAL CASH SETTLEMENT",
            "Chq/Ref No": "CHQ-445566",
            "Value Dt": (base_date + datetime.timedelta(days=14)).strftime("%d/%m/%Y"),
            "Withdrawal Amt": "18500.00",
            "Deposit Amt": "",
            "Closing Balance": "139495.00",
            "Channel": "CASH",
            "Type": "DEBIT",
            "Amount": Decimal("18500.00")
        },
        # HUMAN APPROVAL TEST: Low confidence ambiguous transfer
        {
            "Date": (base_date + datetime.timedelta(days=15)).strftime("%d/%m/%Y"),
            "Narration": "UPI/615599001122/DR/shrikant@okaxis/paid to shrikant",
            "Chq/Ref No": "615599001122",
            "Value Dt": (base_date + datetime.timedelta(days=15)).strftime("%d/%m/%Y"),
            "Withdrawal Amt": "5000.00",
            "Deposit Amt": "",
            "Closing Balance": "134495.00",
            "Channel": "UPI",
            "Type": "DEBIT",
            "Amount": Decimal("5000.00")
        },
        # DEDUPLICATION TEST: Transaction with duplicate reference number
        {
            "Date": (base_date + datetime.timedelta(days=16)).strftime("%d/%m/%Y"),
            "Narration": "UPI/615599001122/DR/shrikant@okaxis/paid to shrikant duplicate swipe",
            "Chq/Ref No": "615599001122",  # DUPLICATE REF of previous item
            "Value Dt": (base_date + datetime.timedelta(days=16)).strftime("%d/%m/%Y"),
            "Withdrawal Amt": "5000.00",
            "Deposit Amt": "",
            "Closing Balance": "129495.00",
            "Channel": "UPI",
            "Type": "DEBIT",
            "Amount": Decimal("5000.00")
        }
    ]

    return {
        "business_profile": business_profile,
        "vendors": vendors,
        "customers": customers,
        "invoices": invoices,
        "transactions": transactions
    }

