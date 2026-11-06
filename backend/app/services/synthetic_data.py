import random
import datetime
from decimal import Decimal
from typing import List, Dict, Any
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

