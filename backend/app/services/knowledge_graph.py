from typing import Dict, Any, List, Set
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt
from backend.app.models.ledger import LedgerAccount, LedgerEntry

def build_financial_knowledge_graph(db: Session, tenant_id: str) -> Dict[str, Any]:
    """
    Constructs the Financial Knowledge Graph for an MSME tenant:
    Vendors/Counterparties -> Categories -> HSN/SAC Codes -> Ledger Accounts -> GST Return Tables.
    """
    txs = db.query(Transaction).filter(Transaction.tenant_id == tenant_id).all()
    accounts = db.query(LedgerAccount).filter(LedgerAccount.tenant_id == tenant_id).all()
    receipts = db.query(Receipt).filter(Receipt.tenant_id == tenant_id).all()

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    seen_nodes: Set[str] = set()

    def add_node(node_id: str, label: str, node_type: str, metadata: Dict[str, Any] = None):
        if node_id not in seen_nodes:
            seen_nodes.add(node_id)
            nodes.append({
                "id": node_id,
                "label": label,
                "type": node_type,
                "metadata": metadata or {}
            })

    def add_edge(source: str, target: str, relation: str, weight: float = 1.0):
        edges.append({
            "source": source,
            "target": target,
            "relation": relation,
            "weight": weight
        })

    # 1. Base GST Return Table Nodes
    add_node("gst_gstr1_b2b", "GSTR-1 Table 4 (B2B Invoices)", "GST_RETURN_TABLE", {"return": "GSTR-1"})
    add_node("gst_gstr1_b2c", "GSTR-1 Table 7 (B2C Retail)", "GST_RETURN_TABLE", {"return": "GSTR-1"})
    add_node("gst_gstr1_hsn", "GSTR-1 Table 12 (HSN Summary)", "GST_RETURN_TABLE", {"return": "GSTR-1"})
    add_node("gst_gstr3b_itc", "GSTR-3B Table 4 (Eligible ITC)", "GST_RETURN_TABLE", {"return": "GSTR-3B"})
    add_node("gst_gstr3b_outward", "GSTR-3B Table 3.1 (Outward Tax)", "GST_RETURN_TABLE", {"return": "GSTR-3B"})

    # 2. Ledger Account Nodes
    acc_map = {}
    for acc in accounts:
        node_id = f"acc_{acc.code}"
        acc_map[acc.code] = node_id
        add_node(node_id, f"[{acc.code}] {acc.name}", "LEDGER_ACCOUNT", {
            "code": acc.code,
            "account_type": acc.account_type,
            "balance": f"{acc.balance:.2f}"
        })

    # 3. Process Transactions & Connect Entities
    category_totals: Dict[str, Decimal] = {}
    hsn_totals: Dict[str, Decimal] = {}
    vendor_totals: Dict[str, Decimal] = {}

    for tx in txs:
        cat = tx.category or "Uncategorized"
        cat_id = f"cat_{cat.replace(' ', '_').lower()}"
        category_totals[cat] = category_totals.get(cat, Decimal("0.00")) + tx.amount

        add_node(cat_id, cat, "CATEGORY", {"type": "Expense" if tx.type == "DEBIT" else "Revenue"})

        # HSN / SAC Node
        hsn = tx.hsn_sac_code or ("9988" if tx.type == "CREDIT" else "9969")
        hsn_id = f"hsn_{hsn}"
        hsn_totals[hsn] = hsn_totals.get(hsn, Decimal("0.00")) + tx.amount
        add_node(hsn_id, f"HSN {hsn} ({tx.tax_rate}%)", "HSN_SAC", {
            "code": hsn,
            "tax_rate": float(tx.tax_rate)
        })

        add_edge(cat_id, hsn_id, "TAXED_UNDER_HSN", float(tx.amount))
        add_edge(hsn_id, "gst_gstr1_hsn", "REPORTED_IN_HSN_SUMMARY", 1.0)

        # Counterparty / Vendor Node
        cp_name = tx.counterparty_name or ("Local Counterparty" if tx.type == "DEBIT" else "Retail Customer")
        cp_id = f"cp_{cp_name.replace(' ', '_').lower()}"
        vendor_totals[cp_name] = vendor_totals.get(cp_name, Decimal("0.00")) + tx.amount
        add_node(cp_id, cp_name, "COUNTERPARTY", {
            "gstin": tx.counterparty_gstin,
            "is_b2b": bool(tx.counterparty_gstin)
        })

        add_edge(cp_id, cat_id, "SUPPLIES_IN_CATEGORY" if tx.type == "DEBIT" else "PURCHASES_FROM", float(tx.amount))

        # Connect to Ledger Accounts
        if tx.type == "DEBIT":
            # Connected to Expense account and Input ITC
            exp_code = "5010" if cat == "Raw Materials" else "5020" if cat == "Rent & Utilities" else "5050"
            if exp_code in acc_map:
                add_edge(cat_id, acc_map[exp_code], "DEBITED_TO_EXPENSE", float(tx.amount))
            add_edge(cat_id, "gst_gstr3b_itc", "CLAIMS_INPUT_TAX_CREDIT", float(tx.amount))
        else:
            if "4010" in acc_map:
                add_edge(cat_id, acc_map["4010"], "CREDITED_TO_REVENUE", float(tx.amount))
            add_edge(cat_id, "gst_gstr3b_outward", "CREATES_TAX_LIABILITY", float(tx.amount))
            if tx.counterparty_gstin:
                add_edge(cp_id, "gst_gstr1_b2b", "REPORTED_IN_B2B", float(tx.amount))
            else:
                add_edge(cp_id, "gst_gstr1_b2c", "REPORTED_IN_B2C", float(tx.amount))

    return {
        "tenant_id": tenant_id,
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "counterparties_count": len([n for n in nodes if n["type"] == "COUNTERPARTY"]),
            "categories_count": len([n for n in nodes if n["type"] == "CATEGORY"]),
            "hsn_count": len([n for n in nodes if n["type"] == "HSN_SAC"]),
            "accounts_count": len([n for n in nodes if n["type"] == "LEDGER_ACCOUNT"]),
            "top_counterparties": [
                {"name": k, "volume": f"{v:.2f}"} for k, v in sorted(vendor_totals.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
        },
        "nodes": nodes,
        "edges": edges
    }
