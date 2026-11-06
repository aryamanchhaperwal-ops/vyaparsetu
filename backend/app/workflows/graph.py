from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from backend.app.workflows.state import TransactionWorkflowState
from backend.app.workflows.nodes import (
    deduplication_node,
    classification_node,
    confidence_router,
    human_review_node,
    reconciliation_node,
    ledger_posting_node
)

def create_transaction_workflow():
    """
    Constructs the LangGraph multi-agent financial pipeline.
    Orchestrates: Ingest -> Dedupe -> BharatCode Classification -> Confidence Router -> [Human Review / Reconcile] -> Ledger.
    """
    workflow = StateGraph(TransactionWorkflowState)

    # 1. Add discrete workflow nodes
    workflow.add_node("deduplicate", deduplication_node)
    workflow.add_node("classify", classification_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("reconcile", reconciliation_node)
    workflow.add_node("ledger_post", ledger_posting_node)

    # 2. Add edges
    workflow.add_edge(START, "deduplicate")
    workflow.add_edge("deduplicate", "classify")

    # 3. Add conditional router based on BharatCode confidence & ambiguity
    workflow.add_conditional_edges(
        "classify",
        confidence_router,
        {
            "human_review": "human_review",
            "reconcile_receipt": "reconcile",
            "end_duplicate": END
        }
    )

    workflow.add_edge("reconcile", "ledger_post")
    workflow.add_edge("ledger_post", END)
    workflow.add_edge("human_review", END)

    # 4. Compile with checkpointer for state persistence
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    return app

transaction_graph = create_transaction_workflow()

