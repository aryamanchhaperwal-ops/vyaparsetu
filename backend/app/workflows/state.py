from typing import TypedDict, Optional, List, Dict, Any

class TransactionWorkflowState(TypedDict):
    tenant_id: str
    transaction_id: Optional[str]
    raw_narration: str
    amount: float
    direction: str  # DEBIT or CREDIT
    channel: str  # UPI, NEFT, CASH, CHEQUE
    reference_number: Optional[str]
    is_duplicate: bool
    category: str
    sub_category: Optional[str]
    hsn_sac_code: Optional[str]
    gst_rate: float
    counterparty_name: Optional[str]
    counterparty_gstin: Optional[str]
    confidence_score: float
    needs_human_review: bool
    human_approved: bool
    human_feedback: Optional[str]
    reconciled_receipt_id: Optional[str]
    ledger_entries_created: int
    is_interstate: bool
    rationale: str
    error: Optional[str]
