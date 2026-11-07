import re
from typing import Dict, Any, List, Set, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.user import Tenant, Membership, User
from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt
from backend.app.models.ledger import LedgerAccount, LedgerEntry

def slugify(text: str) -> str:
    """Creates a clean identifier slug."""
    clean = re.sub(r"[^\w\s-]", "", str(text).lower()).strip()
    return re.sub(r"[-\s]+", "_", clean)

def build_financial_knowledge_graph(db: Session, tenant_id: str) -> Dict[str, Any]:
    """
    Constructs the Full Multi-Entity Financial Knowledge Graph for an MSME tenant:
    - 10 Entity Types: BUSINESS, USER, VENDOR, CUSTOMER, INVOICE, TRANSACTION,
                       LEDGER_ACCOUNT, LEDGER_ENTRY, GST_RECORD, RECONCILIATION_MATCH
    - 9 Relationship Types: OWNS, EMPLOYS, ISSUES_INVOICE, RECEIVES_INVOICE, PAYS_INVOICE,
                            CREATES_ENTRY, AFFECTS_ACCOUNT, CONTRIBUTES_TO_GST, MATCHES_RECONCILIATION
    """
    # 1. Fetch Tenant Context
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return {
            "tenant_id": tenant_id,
            "summary": {"total_nodes": 0, "total_edges": 0, "entity_type_counts": {}},
            "nodes": [],
            "edges": []
        }

    memberships = db.query(Membership).filter(Membership.tenant_id == tenant_id).all()
    accounts = db.query(LedgerAccount).filter(LedgerAccount.tenant_id == tenant_id).all()
    txs = db.query(Transaction).filter(Transaction.tenant_id == tenant_id).order_by(Transaction.transaction_date.desc()).all()
    receipts = db.query(Receipt).filter(Receipt.tenant_id == tenant_id).all()
    entries = db.query(LedgerEntry).filter(LedgerEntry.tenant_id == tenant_id).limit(100).all()

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

    def add_edge(source: str, target: str, relation: str, weight: float = 1.0, metadata: Dict[str, Any] = None):
        edges.append({
            "source": source,
            "target": target,
            "relation": relation,
            "weight": weight,
            "metadata": metadata or {}
        })

    # --- ENTITY 1: BUSINESS ---
    biz_id = f"biz_{tenant.id}"
    add_node(biz_id, tenant.name, "BUSINESS", {
        "id": tenant.id,
        "trade_name": tenant.trade_name,
        "gstin": tenant.simulated_gstin,
        "state_code": tenant.state_code,
        "currency": tenant.currency_symbol,
        "turnover_tier": tenant.turnover_tier,
        "plan": tenant.subscription_plan,
        "jurisdiction": tenant.tax_jurisdiction
    })

    # --- ENTITY 2: USER & EMPLOYS ---
    for m in memberships:
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            u_id = f"user_{user.id}"
            add_node(u_id, user.full_name, "USER", {
                "email": user.email,
                "role": m.role,
                "phone": user.phone_number
            })
            add_edge(biz_id, u_id, "EMPLOYS", 1.0, {"role": m.role})

    # --- ENTITY 3: GST_RECORD (Statutory Return Hubs) ---
    gst_nodes = [
        ("gst_gstr1_b2b", "GSTR-1 Table 4 (B2B Taxable Supplies)", "GSTR-1", "Outward Supplies to Registered Persons"),
        ("gst_gstr1_b2c", "GSTR-1 Table 7 (B2C Retail Invoices)", "GSTR-1", "Outward Supplies to Consumers"),
        ("gst_gstr1_hsn", "GSTR-1 Table 12 (HSN/SAC Summary)", "GSTR-1", "HSN Commodity Classification"),
        ("gst_gstr3b_itc", "GSTR-3B Table 4 (Eligible ITC)", "GSTR-3B", "Input Tax Credit Available"),
        ("gst_gstr3b_outward", "GSTR-3B Table 3.1 (Tax on Outward)", "GSTR-3B", "Tax Liability on Inward/Outward"),
    ]
    for gid, glabel, gform, gdesc in gst_nodes:
        add_node(gid, glabel, "GST_RECORD", {
            "form": gform,
            "description": gdesc,
            "jurisdiction": "Central & State GST Acts"
        })
        add_edge(biz_id, gid, "CONTRIBUTES_TO_GST", 1.0)

    # --- ENTITY 4: LEDGER_ACCOUNT & OWNS ---
    acc_map = {}
    for acc in accounts:
        acc_id = f"acc_{acc.code}"
        acc_map[acc.code] = acc_id
        acc_map[acc.id] = acc_id
        add_node(acc_id, f"[{acc.code}] {acc.name}", "LEDGER_ACCOUNT", {
            "code": acc.code,
            "name": acc.name,
            "account_type": acc.account_type,
            "balance": f"{acc.balance:.2f}"
        })
        add_edge(biz_id, acc_id, "OWNS", 1.0)

    # --- ENTITY 5: INVOICE (Receipts / Bills) & ISSUES_INVOICE / RECEIVES_INVOICE ---
    receipt_map = {}
    for r in receipts:
        inv_id = f"inv_{r.id}"
        receipt_map[r.id] = inv_id
        v_name = r.vendor_name or "Vendor Invoice"
        v_slug = slugify(v_name)
        v_id = f"vendor_{v_slug}"

        # Add Vendor Entity
        add_node(v_id, v_name, "VENDOR", {
            "vendor_name": v_name,
            "gstin": r.vendor_gstin,
            "is_registered": bool(r.vendor_gstin)
        })

        add_node(inv_id, f"Invoice #{r.invoice_number or r.id[:8]}", "INVOICE", {
            "invoice_number": r.invoice_number,
            "invoice_date": str(r.invoice_date) if r.invoice_date else None,
            "vendor_name": v_name,
            "vendor_gstin": r.vendor_gstin,
            "total_amount": float(r.total_amount) if r.total_amount else 0.0,
            "taxable_amount": float(r.taxable_amount) if r.taxable_amount else 0.0,
            "cgst": float(r.cgst_amount) if r.cgst_amount else 0.0,
            "sgst": float(r.sgst_amount) if r.sgst_amount else 0.0,
            "status": r.status
        })

        # Relationship: Vendor issues invoice, business receives invoice
        add_edge(v_id, inv_id, "ISSUES_INVOICE", float(r.total_amount or 1.0))
        add_edge(biz_id, inv_id, "RECEIVES_INVOICE", float(r.total_amount or 1.0))

        # Contributes to GST ITC
        add_edge(inv_id, "gst_gstr3b_itc", "CONTRIBUTES_TO_GST", float(r.cgst_amount + r.sgst_amount if r.cgst_amount else 1.0))

    # --- ENTITY 6, 7 & 8: TRANSACTION, VENDOR/CUSTOMER, RECONCILIATION_MATCH ---
    vendor_volumes: Dict[str, Decimal] = {}
    customer_volumes: Dict[str, Decimal] = {}

    for tx in txs[:50]:  # Cap transaction nodes for clean visual rendering
        tx_id = f"tx_{tx.id}"
        amt_float = float(tx.amount)

        add_node(tx_id, f"{tx.type}: {tx.description[:32]}", "TRANSACTION", {
            "amount": amt_float,
            "type": tx.type,
            "channel": tx.channel,
            "category": tx.category,
            "date": str(tx.transaction_date),
            "reference_number": tx.reference_number,
            "confidence_score": tx.confidence_score,
            "is_reconciled": tx.is_reconciled
        })

        # Business owns transactions
        add_edge(biz_id, tx_id, "OWNS", 1.0)

        # Counterparty Handling (Vendor if DEBIT, Customer if CREDIT)
        cp_name = tx.counterparty_name or ("Supplier / Counterparty" if tx.type == "DEBIT" else "Customer / Buyer")
        cp_slug = slugify(cp_name)

        if tx.type == "DEBIT":
            vendor_id = f"vendor_{cp_slug}"
            vendor_volumes[cp_name] = vendor_volumes.get(cp_name, Decimal("0.00")) + tx.amount
            add_node(vendor_id, cp_name, "VENDOR", {
                "name": cp_name,
                "gstin": tx.counterparty_gstin,
                "type": "SUPPLIER"
            })
            add_edge(tx_id, vendor_id, "PAYS_INVOICE", amt_float)
            add_edge(tx_id, "gst_gstr3b_itc", "CONTRIBUTES_TO_GST", amt_float * 0.18)
        else:
            cust_id = f"cust_{cp_slug}"
            customer_volumes[cp_name] = customer_volumes.get(cp_name, Decimal("0.00")) + tx.amount
            add_node(cust_id, cp_name, "CUSTOMER", {
                "name": cp_name,
                "gstin": tx.counterparty_gstin,
                "type": "CLIENT"
            })
            add_edge(cust_id, tx_id, "PAYS_INVOICE", amt_float)
            if tx.counterparty_gstin:
                add_edge(tx_id, "gst_gstr1_b2b", "CONTRIBUTES_TO_GST", amt_float)
            else:
                add_edge(tx_id, "gst_gstr1_b2c", "CONTRIBUTES_TO_GST", amt_float)
            add_edge(tx_id, "gst_gstr3b_outward", "CONTRIBUTES_TO_GST", amt_float)

        # Matched Receipts -> RECONCILIATION_MATCH
        if tx.receipt:
            recon_id = f"recon_{tx.receipt.id}_{tx.id}"
            add_node(recon_id, f"Reconciled Match ({tx.receipt.invoice_number or 'Auto'})", "RECONCILIATION_MATCH", {
                "transaction_id": tx.id,
                "receipt_id": tx.receipt.id,
                "invoice_number": tx.receipt.invoice_number,
                "amount": amt_float,
                "status": "RECONCILED"
            })
            add_edge(tx_id, recon_id, "MATCHES_RECONCILIATION", 1.0)
            if tx.receipt.id in receipt_map:
                add_edge(receipt_map[tx.receipt.id], recon_id, "MATCHES_RECONCILIATION", 1.0)

    # --- ENTITY 9: LEDGER_ENTRY & CREATES_ENTRY / AFFECTS_ACCOUNT ---
    for entry in entries:
        entry_id = f"entry_{entry.id}"
        debit_f = float(entry.debit)
        credit_f = float(entry.credit)
        amt_f = debit_f if debit_f > 0 else credit_f

        add_node(entry_id, f"Voucher ₹{amt_f:.2f}", "LEDGER_ENTRY", {
            "date": str(entry.entry_date),
            "debit": debit_f,
            "credit": credit_f,
            "narration": entry.narration,
            "account_id": entry.account_id
        })

        if entry.transaction_id:
            tx_id = f"tx_{entry.transaction_id}"
            if tx_id in seen_nodes:
                add_edge(tx_id, entry_id, "CREATES_ENTRY", amt_f)

        if entry.account_id in acc_map:
            add_edge(entry_id, acc_map[entry.account_id], "AFFECTS_ACCOUNT", amt_f)

    # Aggregate counts by entity type
    type_counts: Dict[str, int] = {}
    for n in nodes:
        t = n["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "tenant_id": tenant_id,
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entity_type_counts": type_counts,
            "business_count": type_counts.get("BUSINESS", 0),
            "users_count": type_counts.get("USER", 0),
            "vendors_count": type_counts.get("VENDOR", 0),
            "customers_count": type_counts.get("CUSTOMER", 0),
            "invoices_count": type_counts.get("INVOICE", 0),
            "transactions_count": type_counts.get("TRANSACTION", 0),
            "accounts_count": type_counts.get("LEDGER_ACCOUNT", 0),
            "entries_count": type_counts.get("LEDGER_ENTRY", 0),
            "gst_records_count": type_counts.get("GST_RECORD", 0),
            "reconciliations_count": type_counts.get("RECONCILIATION_MATCH", 0),
            "counterparties_count": type_counts.get("VENDOR", 0) + type_counts.get("CUSTOMER", 0),
            "categories_count": len(set(tx.category for tx in txs if tx.category)),
            "hsn_count": len(set(tx.hsn_sac_code for tx in txs if tx.hsn_sac_code)) or 1,
            "top_vendors": [
                {"name": k, "volume": f"{v:.2f}"}
                for k, v in sorted(vendor_volumes.items(), key=lambda x: x[1], reverse=True)[:5]
            ],
            "top_customers": [
                {"name": k, "volume": f"{v:.2f}"}
                for k, v in sorted(customer_volumes.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
        },
        "nodes": nodes,
        "edges": edges
    }
