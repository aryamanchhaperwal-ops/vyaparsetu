import re
from typing import Dict, Any, List, Set, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.user import Tenant
from backend.app.models.transaction import Transaction
from backend.app.models.receipt import Receipt
from backend.app.models.ledger import LedgerAccount, LedgerEntry
from backend.app.services.knowledge_graph import build_financial_knowledge_graph, slugify


def search_graph_entities(
    db: Session,
    tenant_id: str,
    entity_query: str,
    entity_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Searches the tenant's financial knowledge graph for entities matching the query.
    Matches vendors, customers, invoices, transactions, ledger accounts, and GST records.
    Strictly tenant isolated.
    """
    graph = build_financial_knowledge_graph(db, tenant_id)
    nodes = graph["nodes"]
    q_terms = [t.lower() for t in re.findall(r"\w+", entity_query) if len(t) > 1]
    if not q_terms:
        return []

    matched_nodes = []
    for node in nodes:
        if entity_types and node["type"] not in entity_types:
            continue

        label = node.get("label", "").lower()
        node_id = node.get("id", "").lower()
        meta_str = " ".join(str(v).lower() for v in node.get("metadata", {}).values())
        searchable_text = f"{label} {node_id} {meta_str}"

        # Score relevance
        score = 0
        for term in q_terms:
            if term in label:
                score += 4
            elif term in searchable_text:
                score += 2

        if score > 0:
            matched_nodes.append((score, node))

    matched_nodes.sort(key=lambda x: x[0], reverse=True)
    return [node for _, node in matched_nodes[:10]]


def expand_graph_neighbors(
    db: Session,
    tenant_id: str,
    node_id: str,
    max_hops: int = 2
) -> Dict[str, Any]:
    """
    Expands a graph node up to max_hops (1 or 2) across edges, returning the
    connected subgraph of entities and relationships.
    """
    graph = build_financial_knowledge_graph(db, tenant_id)
    all_nodes = {n["id"]: n for n in graph["nodes"]}
    all_edges = graph["edges"]

    subgraph_node_ids: Set[str] = {node_id}
    subgraph_edges: List[Dict[str, Any]] = []

    # Hop 1
    current_frontier = {node_id}
    for hop in range(max_hops):
        next_frontier: Set[str] = set()
        for edge in all_edges:
            src = edge["source"]
            tgt = edge["target"]

            if src in current_frontier and tgt not in subgraph_node_ids:
                subgraph_node_ids.add(tgt)
                next_frontier.add(tgt)
                subgraph_edges.append(edge)
            elif tgt in current_frontier and src not in subgraph_node_ids:
                subgraph_node_ids.add(src)
                next_frontier.add(src)
                subgraph_edges.append(edge)
            elif src in subgraph_node_ids and tgt in subgraph_node_ids and edge not in subgraph_edges:
                subgraph_edges.append(edge)

        current_frontier = next_frontier
        if not current_frontier:
            break

    subgraph_nodes = [all_nodes[nid] for nid in subgraph_node_ids if nid in all_nodes]

    return {
        "root_node_id": node_id,
        "nodes": subgraph_nodes,
        "edges": subgraph_edges,
        "total_nodes": len(subgraph_nodes),
        "total_edges": len(subgraph_edges)
    }


def find_vendor_payment_trail(
    db: Session,
    tenant_id: str,
    vendor_query: str
) -> Dict[str, Any]:
    """
    Traverses the full financial chain for a vendor:
    Business -> Vendor -> Invoices -> Payments -> Ledger Entries -> Tax Impact.
    """
    matched_vendors = search_graph_entities(db, tenant_id, vendor_query, entity_types=["VENDOR"])
    if not matched_vendors:
        # Fallback to general counterparty search in transactions
        matched_vendors = search_graph_entities(db, tenant_id, vendor_query)
        if not matched_vendors:
            return {
                "vendor_query": vendor_query,
                "found": False,
                "trail": [],
                "summary": f"No vendor or records matching '{vendor_query}' found in tenant financial graph."
            }

    vendor_node = matched_vendors[0]
    vendor_id = vendor_node["id"]
    vendor_name = vendor_node.get("metadata", {}).get("vendor_name") or vendor_node["label"]

    expansion = expand_graph_neighbors(db, tenant_id, vendor_id, max_hops=2)
    nodes = expansion["nodes"]
    edges = expansion["edges"]

    invoices = [n for n in nodes if n["type"] == "INVOICE"]
    transactions = [n for n in nodes if n["type"] == "TRANSACTION"]
    entries = [n for n in nodes if n["type"] == "LEDGER_ENTRY"]
    gst_records = [n for n in nodes if n["type"] == "GST_RECORD"]

    # Factual narration lines
    trail_steps = []
    trail_steps.append(f"Vendor Entity: **{vendor_name}** (Node ID: `{vendor_id}`, GSTIN: {vendor_node.get('metadata', {}).get('gstin', 'Unregistered')})")

    total_invoiced = sum(float(inv.get("metadata", {}).get("total_amount", 0)) for inv in invoices)
    total_paid = sum(float(tx.get("metadata", {}).get("amount", 0)) for tx in transactions)

    if invoices:
        trail_steps.append(f"• **Invoices Issued ({len(invoices)}):** Total ₹{total_invoiced:,.2f}")
        for inv in invoices[:5]:
            meta = inv.get("metadata", {})
            trail_steps.append(f"   - Invoice #{meta.get('invoice_number', 'N/A')}: ₹{meta.get('total_amount', 0):,.2f} on {meta.get('invoice_date', 'N/A')} (Taxable: ₹{meta.get('taxable_amount', 0):,.2f}, CGST: ₹{meta.get('cgst', 0):,.2f}, SGST: ₹{meta.get('sgst', 0):,.2f})")

    if transactions:
        trail_steps.append(f"• **Payments / Settlements ({len(transactions)}):** Total ₹{total_paid:,.2f}")
        for tx in transactions[:5]:
            meta = tx.get("metadata", {})
            trail_steps.append(f"   - {meta.get('type')}: ₹{meta.get('amount', 0):,.2f} on {meta.get('date', 'N/A')} via {meta.get('channel', 'BANK')} (Ref: {meta.get('reference_number', 'N/A')}, Reconciled: {meta.get('is_reconciled')})")

    if entries:
        trail_steps.append(f"• **Balanced Ledger Vouchers ({len(entries)}):** Posted to double-entry general ledger.")

    if gst_records:
        gst_forms = list(set(g.get("metadata", {}).get("form", "GSTR-3B") for g in gst_records))
        trail_steps.append(f"• **Tax Linkage:** Linked to {', '.join(gst_forms)} for statutory Input Tax Credit (ITC).")

    return {
        "vendor_query": vendor_query,
        "found": True,
        "vendor": vendor_node,
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "invoices_count": len(invoices),
        "transactions_count": len(transactions),
        "ledger_entries_count": len(entries),
        "trail_narration": "\n".join(trail_steps),
        "subgraph": expansion
    }


def find_unreconciled_transaction_trail(
    db: Session,
    tenant_id: str,
    transaction_query: Optional[str] = None
) -> Dict[str, Any]:
    """
    Investigates unlinked bank transactions and explains why they remain unreconciled
    using the financial knowledge graph and receipt correlation.
    """
    tx_query = db.query(Transaction).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.is_reconciled == False
    )

    if transaction_query:
        # Search for specific narration, reference, or amount
        tx_query = tx_query.filter(
            (Transaction.description.ilike(f"%{transaction_query}%")) |
            (Transaction.raw_narration.ilike(f"%{transaction_query}%")) |
            (Transaction.reference_number.ilike(f"%{transaction_query}%"))
        )

    unreconciled_txs = tx_query.order_by(Transaction.transaction_date.desc()).limit(5).all()

    if not unreconciled_txs:
        return {
            "found_unreconciled": False,
            "message": "All transactions for this period are fully reconciled, or no matching unlinked transaction found."
        }

    reports = []
    for tx in unreconciled_txs:
        # Check potential candidates in receipts
        candidates = db.query(Receipt).filter(
            Receipt.tenant_id == tenant_id,
            Receipt.transaction_id == None
        ).all()

        reasons = []
        # Check if amount matches any receipt
        exact_amt_match = [r for r in candidates if r.total_amount == tx.amount]
        if not exact_amt_match:
            reasons.append(f"No receipt/invoice found with exact matching amount of ₹{tx.amount:,.2f}.")
        else:
            reasons.append(f"Found {len(exact_amt_match)} receipt(s) with matching amount (e.g. #{exact_amt_match[0].invoice_number}), but reference number or date window requires manual verification.")

        if not tx.counterparty_name or tx.counterparty_name in ("Supplier / Counterparty", "Uncategorized"):
            reasons.append("Bank narration lacks clear counterparty / supplier name to verify invoice issuer.")

        reports.append({
            "transaction_id": tx.id,
            "date": str(tx.transaction_date),
            "amount": float(tx.amount),
            "type": tx.type,
            "description": tx.description,
            "channel": tx.channel,
            "reference_number": tx.reference_number,
            "reasons": reasons
        })

    narration_lines = [f"Found {len(reports)} unreconciled bank item(s) in financial graph:\n"]
    for r in reports:
        narration_lines.append(f"• **`{r['date']}` {r['type']} ₹{r['amount']:,.2f}** ({r['description']})")
        narration_lines.append(f"   - **Reason for non-reconciliation:** {'; '.join(r['reasons'])}")

    return {
        "found_unreconciled": True,
        "unreconciled_items": reports,
        "trail_narration": "\n".join(narration_lines)
    }


def build_relationship_aware_context(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]]
) -> str:
    """
    Transforms graph entities and relationships into structured factual context
    with explicit relational provenance (never hallucinated).
    """
    if not nodes:
        return "No relevant financial graph entities found."

    lines = ["### Financial Knowledge Graph Relational Context:"]

    # Entities summary
    entity_by_type: Dict[str, List[str]] = {}
    for n in nodes:
        t = n.get("type", "UNKNOWN")
        lbl = n.get("label", n.get("id"))
        entity_by_type.setdefault(t, []).append(lbl)

    for etype, labels in entity_by_type.items():
        lines.append(f"• **{etype} Entities ({len(labels)}):** {', '.join(labels[:5])}")

    # Top relationships
    if edges:
        lines.append("\n**Verified Entity Relationships:**")
        for e in edges[:10]:
            src = e.get("source", "")
            tgt = e.get("target", "")
            rel = e.get("relation", "CONNECTED_TO")
            lines.append(f"  - `{src}` ---[{rel}]---> `{tgt}`")

    return "\n".join(lines)

