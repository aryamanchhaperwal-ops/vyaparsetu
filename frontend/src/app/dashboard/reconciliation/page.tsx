"use client";

import React, { useState, useEffect } from "react";
import {
  GitCompare,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  Receipt as ReceiptIcon,
  Link2,
  RefreshCw,
  Search,
  Sparkles,
  ArrowRight,
  ShieldCheck
} from "lucide-react";
import { api, Transaction } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

interface ReceiptItem {
  id: string;
  invoice_number: string | null;
  invoice_date: string | null;
  vendor_name: string | null;
  vendor_gstin: string | null;
  total_amount: string;
  status: string;
  transaction_id: string | null;
}

export default function ReconciliationPage() {
  const { t } = useLanguage();

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [receipts, setReceipts] = useState<ReceiptItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [matching, setMatching] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [txs, rcpts] = await Promise.all([
        api.getTransactions(""),
        api.getReceipts(),
      ]);
      setTransactions(txs || []);
      setReceipts(rcpts || []);
    } catch (err: any) {
      console.error("Failed to load reconciliation data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const unlinkedReceipts = receipts.filter((r) => !r.transaction_id && r.status !== "RECONCILED");
  const unreconciledTxs = transactions.filter((t) => !t.is_reconciled && t.type === "DEBIT");
  const reconciledReceipts = receipts.filter((r) => r.transaction_id || r.status === "RECONCILED");

  const handleMatch = async (receiptId: string, transactionId: string) => {
    setMatching(true);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      await api.reconcileReceipt(receiptId, transactionId);
      setSuccessMsg("Invoice and bank transaction successfully reconciled!");
      await loadData();
    } catch (err: any) {
      setErrorMsg(err.message || "Reconciliation failed.");
    } finally {
      setMatching(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <GitCompare className="w-7 h-7 text-emerald-600" />
            {t("reconciliation")} — Bank vs Invoice Matching
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Pair bank/UPI statement debits with vendor tax invoices to prove legitimate Input Tax Credit (ITC) under Section 16(2).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={async () => {
              setMatching(true);
              try {
                const res = await api.runReconciliation(0.85);
                setSuccessMsg(`Auto-reconciliation complete: ${res.auto_linked_count} invoices linked, ${res.suggested_count} candidates scored.`);
                await loadData();
              } catch (err: any) {
                setErrorMsg("Auto-reconciliation failed: " + err.message);
              } finally {
                setMatching(false);
              }
            }}
            disabled={matching}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg shadow-sm transition"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{matching ? "Matching..." : "Run Auto-Reconciliation"}</span>
          </button>

          <button
            onClick={loadData}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-lg shadow-sm transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-600" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-600" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* KPI Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold block">
            Unreconciled Bank Debits
          </span>
          <p className="text-2xl font-bold text-slate-900 mt-2">{unreconciledTxs.length}</p>
          <span className="text-xs text-amber-600 font-medium">Pending tax invoice verification</span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold block">
            Unlinked Invoices (OCR)
          </span>
          <p className="text-2xl font-bold text-slate-900 mt-2">{unlinkedReceipts.length}</p>
          <span className="text-xs text-blue-600 font-medium">Awaiting bank settlement match</span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold block">
            Fully Reconciled Pairs
          </span>
          <p className="text-2xl font-bold text-emerald-700 mt-2">{reconciledReceipts.length}</p>
          <span className="text-xs text-emerald-600 font-medium flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5" /> ITC Audit Proof Ready
          </span>
        </div>
      </div>

      {/* Side-by-Side Matching Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Unreconciled Bank Outflows */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ReceiptIcon className="w-4 h-4 text-slate-600" />
              <h3 className="font-semibold text-slate-800 text-sm">
                Bank Outflows ({unreconciledTxs.length})
              </h3>
            </div>
            <span className="text-xs text-slate-400">Target for invoice pairing</span>
          </div>

          <div className="p-4 flex-1 space-y-3 overflow-y-auto max-h-[500px]">
            {unreconciledTxs.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                No unreconciled bank debits found.
              </div>
            ) : (
              unreconciledTxs.map((tx) => (
                <div
                  key={tx.id}
                  className="p-3.5 border border-slate-200 rounded-lg hover:border-emerald-400 transition bg-white space-y-1.5"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono text-slate-500">{tx.transaction_date}</span>
                    <span className="font-bold text-slate-900 text-sm">₹{tx.amount}</span>
                  </div>
                  <p className="text-xs font-semibold text-slate-800">{tx.raw_narration}</p>
                  <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                    <span>Channel: {tx.channel}</span>
                    <span className="bg-slate-100 px-2 py-0.5 rounded font-medium">{tx.category}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Unlinked OCR Invoices & 1-Click Match */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
              <h3 className="font-semibold text-slate-800 text-sm">
                OCR Invoices &amp; Auto-Matches ({unlinkedReceipts.length})
              </h3>
            </div>
            <span className="text-xs text-slate-400">Match against bank debits</span>
          </div>

          <div className="p-4 flex-1 space-y-3 overflow-y-auto max-h-[500px]">
            {unlinkedReceipts.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                No unlinked invoices. Upload invoices in Document OCR to reconcile.
              </div>
            ) : (
              unlinkedReceipts.map((rcpt) => {
                // Find potential candidate matching amount within +/- 10 rupees
                const candidate = unreconciledTxs.find((tx) => {
                  const diff = Math.abs(parseFloat(tx.amount) - parseFloat(rcpt.total_amount));
                  return diff <= 10.0;
                });

                return (
                  <div
                    key={rcpt.id}
                    className={`p-3.5 border rounded-lg transition space-y-2 ${
                      candidate
                        ? "border-emerald-300 bg-emerald-50/30"
                        : "border-slate-200 bg-white"
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-900">{rcpt.vendor_name || "Vendor Invoice"}</span>
                      <span className="font-bold text-emerald-700 text-sm">₹{rcpt.total_amount}</span>
                    </div>

                    <div className="text-[11px] text-slate-500 font-mono flex items-center justify-between">
                      <span>GSTIN: {rcpt.vendor_gstin || "Unregistered"}</span>
                      <span>Inv: {rcpt.invoice_number || "—"}</span>
                    </div>

                    {candidate ? (
                      <div className="pt-2 border-t border-emerald-200 flex items-center justify-between">
                        <div className="text-xs text-emerald-800 flex items-center gap-1.5">
                          <Sparkles className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                          <span>
                            Exact Match: <strong>₹{candidate.amount}</strong> ({candidate.raw_narration.slice(0, 25)}...)
                          </span>
                        </div>
                        <button
                          onClick={() => handleMatch(rcpt.id, candidate.id)}
                          disabled={matching}
                          className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded shadow-sm transition flex items-center gap-1"
                        >
                          <Link2 className="w-3.5 h-3.5" />
                          <span>Reconcile</span>
                        </button>
                      </div>
                    ) : (
                      <div className="text-[11px] text-slate-400 italic">
                        No exact amount match found in recent bank statements.
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

