import os
import json
from pathlib import Path
from backend.app.services.synthetic_data import (
    generate_reproducible_msme_dataset,
    bank_statement_to_csv_string,
    bank_statement_to_excel_bytes
)

def export_msme_dataset():
    out_dir = Path("synthetic_data")
    out_dir.mkdir(exist_ok=True)

    data = generate_reproducible_msme_dataset()
    transactions = data["transactions"]
    invoices = data["invoices"]
    profile = data["business_profile"]

    # 1. Export CSV
    csv_str = bank_statement_to_csv_string(transactions)
    csv_path = out_dir / "shree_krishna_bank_statement.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_str)
    print(f"[EXPORT] CSV Bank Statement written to {csv_path} ({len(transactions)} records)")

    # 2. Export Excel (.xlsx)
    xlsx_bytes = bank_statement_to_excel_bytes(transactions)
    xlsx_path = out_dir / "shree_krishna_bank_statement.xlsx"
    with open(xlsx_path, "wb") as f:
        f.write(xlsx_bytes)
    print(f"[EXPORT] Excel Bank Statement written to {xlsx_path} ({len(transactions)} records)")

    # 3. Export Invoices & Metadata JSON
    json_path = out_dir / "shree_krishna_dataset.json"
    serializable_data = {
        "business_profile": profile,
        "invoices": invoices,
        "transactions_count": len(transactions),
        "vendors_count": len(data["vendors"]),
        "customers_count": len(data["customers"])
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(serializable_data, f, indent=2)
    print(f"[EXPORT] MSME Invoices & Profile JSON written to {json_path}")

if __name__ == "__main__":
    export_msme_dataset()

