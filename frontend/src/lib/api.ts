const API_BASE = ""; // Relative path proxied by Next.js rewrites to http://127.0.0.1:8000

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone_number?: string;
  is_active: boolean;
}

export interface Tenant {
  id: string;
  name: string;
  trade_name?: string;
  simulated_gstin: string;
  state_code: string;
  business_category: string;
  turnover_tier: string;
  subscription_plan: string;
  country_code: string;
  tax_jurisdiction: string;
  base_currency: string;
  currency_symbol: string;
  financial_year_start_month: number;
  timezone: string;
}

export interface Membership {
  id: string;
  role: "OWNER" | "ADMIN" | "ACCOUNTANT" | "EMPLOYEE";
  tenant: Tenant;
}

export interface Transaction {
  id: string;
  transaction_date: string;
  description: string;
  raw_narration: string;
  amount: string;
  currency: string;
  type: "DEBIT" | "CREDIT";
  channel: string;
  reference_number?: string;
  category: string;
  sub_category?: string;
  tax_rate: string;
  confidence_score: number;
  status: "CONFIRMED" | "NEEDS_APPROVAL" | "REJECTED";
  is_reconciled: boolean;
}

// Token and Tenant state management in localStorage
export const getStoredToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("vyaparsetu_token");
};

export const setStoredToken = (token: string) => {
  if (typeof window !== "undefined") localStorage.setItem("vyaparsetu_token", token);
};

export const clearStoredToken = () => {
  if (typeof window !== "undefined") {
    localStorage.removeItem("vyaparsetu_token");
    localStorage.removeItem("vyaparsetu_tenant_id");
  }
};

export const getStoredTenantId = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("vyaparsetu_tenant_id");
};

export const setStoredTenantId = (tenantId: string) => {
  if (typeof window !== "undefined") localStorage.setItem("vyaparsetu_tenant_id", tenantId);
};

async function fetchWithAuth(endpoint: string, options: RequestInit = {}): Promise<any> {
  const token = getStoredToken();
  const tenantId = getStoredTenantId();

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (tenantId) {
    headers["X-Tenant-ID"] = tenantId;
  }

  // If body is not FormData, default to application/json
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    clearStoredToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new Error("Session expired. Please log in again.");
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || `Request failed with status ${res.status}`);
  }

  return res.json();
}

export const api = {
  // Auth
  login: async (formData: FormData) => {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail || "Login failed");
    }
    return res.json();
  },
  register: (data: any) =>
    fetchWithAuth("/api/v1/auth/register", { method: "POST", body: JSON.stringify(data) }),
  getMe: () => fetchWithAuth("/api/v1/auth/me"),
  getWorkspaces: (): Promise<Membership[]> => fetchWithAuth("/api/v1/auth/workspaces"),
  createWorkspace: (data: any): Promise<Tenant> =>
    fetchWithAuth("/api/v1/auth/workspaces", { method: "POST", body: JSON.stringify(data) }),

  // Tenants
  getCurrentTenant: (): Promise<Tenant> => fetchWithAuth("/api/v1/tenants/current"),
  updateTenantSettings: (data: any): Promise<Tenant> =>
    fetchWithAuth("/api/v1/tenants/current/settings", { method: "PATCH", body: JSON.stringify(data) }),
  getMembers: (tenantId: string) => fetchWithAuth(`/api/v1/tenants/${tenantId}/members`),
  inviteMember: (tenantId: string, email: string, role: string) =>
    fetchWithAuth(`/api/v1/tenants/${tenantId}/invite`, {
      method: "POST",
      body: JSON.stringify({ email, role }),
    }),

  // Transactions
  getTransactions: (params: string = ""): Promise<Transaction[]> =>
    fetchWithAuth(`/api/v1/transactions${params ? `?${params}` : ""}`),
  createTransaction: (data: any): Promise<Transaction> =>
    fetchWithAuth("/api/v1/transactions", { method: "POST", body: JSON.stringify(data) }),

  // Ingestion & Mock Data
  generateSyntheticData: (count: number = 20) =>
    fetchWithAuth(`/api/v1/ingestion/synthetic?count=${count}`, { method: "POST" }),
  previewStatement: (file: File, sheetName?: string, delimiter?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (sheetName) fd.append("sheet_name", sheetName);
    if (delimiter) fd.append("delimiter", delimiter);
    return fetchWithAuth("/api/v1/ingestion/preview", { method: "POST", body: fd });
  },
  confirmStatement: (records: any[], skipDuplicates: boolean = true, autoPostLedger: boolean = true) => {
    return fetchWithAuth("/api/v1/ingestion/confirm", {
      method: "POST",
      body: JSON.stringify({
        records,
        skip_duplicates: skipDuplicates,
        auto_post_ledger: autoPostLedger,
      }),
    });
  },
  uploadCSV: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetchWithAuth("/api/v1/ingestion/csv", { method: "POST", body: fd });
  },
  uploadExcel: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetchWithAuth("/api/v1/ingestion/excel", { method: "POST", body: fd });
  },
  uploadStatementAuto: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetchWithAuth("/api/v1/ingestion/statement", { method: "POST", body: fd });
  },
  uploadPDF: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetchWithAuth("/api/v1/ingestion/pdf", { method: "POST", body: fd });
  },

  // Invoices & OCR
  uploadReceipt: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetchWithAuth("/api/v1/ocr/upload", { method: "POST", body: fd });
  },
  getReceipts: () => fetchWithAuth("/api/v1/ocr/receipts"),
  reconcileReceipt: (receiptId: string, transactionId: string) =>
    fetchWithAuth("/api/v1/ocr/reconcile", {
      method: "POST",
      body: JSON.stringify({ receipt_id: receiptId, transaction_id: transactionId }),
    }),

  // LangGraph AI Workflows & Approvals
  parseVoiceNarration: (narration: string) =>
    fetchWithAuth("/api/v1/workflow/parse-voice", { method: "POST", body: JSON.stringify({ narration }) }),
  processWorkflow: (data: any) =>
    fetchWithAuth("/api/v1/workflow/process", { method: "POST", body: JSON.stringify(data) }),
  getApprovalQueue: () => fetchWithAuth("/api/v1/workflow/approval-queue"),
  approveTransaction: (data: any) =>
    fetchWithAuth("/api/v1/workflow/approve", { method: "POST", body: JSON.stringify(data) }),

  // Ledger & Reconciliation
  getAccounts: () => fetchWithAuth("/api/v1/ledger/accounts"),
  getTrialBalance: () => fetchWithAuth("/api/v1/ledger/trial-balance"),
  getFinancialStatements: () => fetchWithAuth("/api/v1/ledger/financial-statements"),
  getLedgerEntries: () => fetchWithAuth("/api/v1/ledger/entries"),
  postToLedger: (txId: string, isInterstate: boolean = false) =>
    fetchWithAuth(`/api/v1/ledger/post/${txId}?is_interstate=${isInterstate}`, { method: "POST" }),
  runReconciliation: (autoLinkThreshold: number = 0.90) =>
    fetchWithAuth(`/api/v1/ledger/reconcile?auto_link_threshold=${autoLinkThreshold}`, { method: "POST" }),
  getReconciliationOverview: () => fetchWithAuth("/api/v1/ledger/reconciliation-status"),

  // GST Engine
  computeGST: (data: any) =>
    fetchWithAuth("/api/v1/gst/compute", { method: "POST", body: JSON.stringify(data) }),
  getGSTR1: (period: string) => fetchWithAuth(`/api/v1/gst/gstr1/${period}`),
  getGSTR3B: (period: string) => fetchWithAuth(`/api/v1/gst/gstr3b/${period}`),
  simulateFiling: (period: string, reportType: string) =>
    fetchWithAuth("/api/v1/gst/simulate-filing", {
      method: "POST",
      body: JSON.stringify({ period, report_type: reportType }),
    }),

  // AI Assistant & Unified RAG
  askAssistant: (query: string, language: string = "Hinglish") =>
    fetchWithAuth("/api/v1/rag/ask", {
      method: "POST",
      body: JSON.stringify({ query, language }),
    }),
  queryRAG: (query: string, language: string = "English", forceStrategy?: string) =>
    fetchWithAuth("/api/v1/rag/query", {
      method: "POST",
      body: JSON.stringify({ query, language, force_strategy: forceStrategy }),
    }),
  getRAGDocuments: () => fetchWithAuth("/api/v1/rag/documents"),
  uploadRAGDocument: (file: File, docType?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (docType) fd.append("doc_type", docType);
    return fetchWithAuth("/api/v1/rag/documents/upload", { method: "POST", body: fd });
  },
  deleteRAGDocument: (docId: string) =>
    fetchWithAuth(`/api/v1/rag/documents/${docId}`, { method: "DELETE" }),
  getGraphTrail: (query: string, trailType: "vendor" | "reconciliation" = "vendor") =>
    fetchWithAuth(`/api/v1/rag/graph-trail?query=${encodeURIComponent(query)}&trail_type=${trailType}`),

  // Analytics & Credit Insights
  getCashFlow: () => fetchWithAuth("/api/v1/analytics/cashflow"),
  getCashFlowForecast: (days: number = 30) => fetchWithAuth(`/api/v1/analytics/forecast?days=${days}`),
  getCreditHealth: () => fetchWithAuth("/api/v1/analytics/credit-health"),
  getKnowledgeGraph: () => fetchWithAuth("/api/v1/analytics/knowledge-graph"),
  getHealth: () => fetch("/health").then((r) => r.json()),

  // Subscription & Audit
  getUsage: () => fetchWithAuth("/api/v1/subscription/usage"),
  upgradePlan: (plan: string) =>
    fetchWithAuth("/api/v1/subscription/upgrade", {
      method: "POST",
      body: JSON.stringify({ plan }),
    }),
  getAuditLogs: () => fetchWithAuth("/api/v1/subscription/audit-logs"),

  // Autonomous Command Centre & Conversational Agent
  executeCommand: (data: { instruction: string; language?: string; financial_period?: string; idempotency_key?: string; conversation_id?: string }) =>
    fetchWithAuth("/api/v1/command/execute", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  executeUploadCommand: (formData: FormData) =>
    fetchWithAuth("/api/v1/command/execute-upload", {
      method: "POST",
      body: formData,
    }),
  approveCommandRun: (data: { run_id: string; approved: boolean; modifications?: any; idempotency_key?: string }) =>
    fetchWithAuth("/api/v1/command/approve", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getCommandRuns: (limit: number = 20) => fetchWithAuth(`/api/v1/command/runs?limit=${limit}`),
  getCommandRun: (runId: string) => fetchWithAuth(`/api/v1/command/runs/${runId}`),
  getConversationHistory: (conversationId: string) =>
    fetchWithAuth(`/api/v1/command/conversation/${conversationId}`),
  clearConversationHistory: (conversationId: string) =>
    fetchWithAuth(`/api/v1/command/conversation/${conversationId}`, { method: "DELETE" }),
  parseVoiceTranscript: (transcript: string, language: string = "en", financial_period?: string) =>
    fetchWithAuth("/api/v1/command/voice-parse", {
      method: "POST",
      body: JSON.stringify({ transcript, language, financial_period }),
    }),
  formatSpokenResponse: (text: string, language: string = "en") =>
    fetchWithAuth("/api/v1/command/speak", {
      method: "POST",
      body: JSON.stringify({ text, language }),
    }),
};
