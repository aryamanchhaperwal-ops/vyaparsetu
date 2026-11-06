"use client";

import React, { useState, useEffect } from "react";
import {
  CheckSquare,
  AlertTriangle,
  CheckCircle2,
  Edit3,
  X,
  FileCheck2,
  Building,
  ShieldCheck,
  RefreshCw,
  Clock,
  ArrowRight
} from "lucide-react";
import { api } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

interface PendingTx {
  id: string;
  transaction_date: string;
  raw_narration: string;
  amount: string;
  type: string;
  channel: string;
  category: string;
  confidence_score: number;
  status: string;
}

const CATEGORY_OPTIONS = [
  "Raw Materials",
  "Rent & Utilities",
  "Salaries & Wages",
  "Logistics & Transport",
  "Operating Sales",
  "General & Administrative",
  "Office Supplies",
  "Professional Fees",
  "Capital Goods / Machinery",
  "Uncategorized Expense",
];

const GST_RATES = [0, 5, 12, 18, 28];

export default function ApprovalsPage() {
  const { t } = useLanguage();
  const [queue, setQueue] = useState<PendingTx[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTx, setSelectedTx] = useState<PendingTx | null>(null);
  const [category, setCategory] = useState("");
  const [gstRate, setGstRate] = useState(18);
  const [counterpartyName, setCounterpartyName] = useState("");
  const [counterpartyGstin, setCounterpartyGstin] = useState("");
  const [feedback, setFeedback] = useState("");
  const [isInterstate, setIsInterstate] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const loadQueue = async () => {
    try {
      setLoading(true);
      const data = await api.getApprovalQueue();
      setQueue(data || []);
    } catch (err: any) {
      console.error("Failed to load approval queue:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const handleOpenReview = (tx: PendingTx) => {
    setSelectedTx(tx);
    setCategory(tx.category || "General & Administrative");
    setGstRate(18);
    setCounterpartyName("");
    setCounterpartyGstin("");
    setFeedback("");
    setIsInterstate(false);
    setErrorMsg("");
  };

  const handleApprove = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTx) return;

    setSubmitting(true);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      const res = await api.approveTransaction({
        transaction_id: selectedTx.id,
        category,
        gst_rate: gstRate,
        counterparty_name: counterpartyName || undefined,
        counterparty_gstin: counterpartyGstin || undefined,
        human_feedback: feedback || undefined,
        is_interstate: isInterstate,
      });

      setSuccessMsg(`Transaction approved! Created ${res.entries_created} balanced double-entry ledger vouchers.`);
      setSelectedTx(null);
      await loadQueue();
    } catch (err: any) {
      setErrorMsg(err.message || "Approval failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <CheckSquare className="w-7 h-7 text-amber-600" />
            {t("approvals")} (HITL Checkpoint)
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Human-in-the-Loop review for ambiguous, multilingual, or low-confidence transactions before ledger commitment.
          </p>
        </div>

        <button
          onClick={loadQueue}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-lg shadow-sm transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Queue ({queue.length})</span>
        </button>
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-600" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Queue List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-amber-500" />
            <h3 className="font-semibold text-slate-800 text-sm">
              Pending Human Verification ({queue.length})
            </h3>
          </div>
          <span className="text-xs text-slate-400">
            Threshold: Confidence &lt; 85%
          </span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-400 text-sm">Loading pending approval queue...</div>
        ) : queue.length === 0 ? (
          <div className="p-16 text-center">
            <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-3">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h4 className="font-semibold text-slate-800 text-base">Approval Queue is Clear!</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              All transactions have passed the autonomous confidence threshold and have been posted to the double-entry ledger.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {queue.map((tx) => (
              <div
                key={tx.id}
                className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-amber-50/30 transition"
              >
                <div className="space-y-1 max-w-xl">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                        tx.type === "DEBIT" ? "bg-rose-100 text-rose-800" : "bg-emerald-100 text-emerald-800"
                      }`}
                    >
                      {tx.type} • {tx.channel}
                    </span>
                    <span className="text-xs text-slate-400">{tx.transaction_date}</span>
                    <span className="text-xs font-semibold text-amber-700 bg-amber-100 px-2 py-0.5 rounded">
                      AI Confidence: {(tx.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-sm font-semibold text-slate-900">{tx.raw_narration}</p>
                  <p className="text-xs text-slate-500">
                    AI Suggested Category: <span className="font-medium text-slate-700">{tx.category}</span>
                  </p>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <span className="text-xs text-slate-400 block">Amount</span>
                    <span className="font-bold text-slate-900 text-base">₹{tx.amount}</span>
                  </div>

                  <button
                    onClick={() => handleOpenReview(tx)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-medium text-xs rounded-lg shadow-sm transition"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    <span>Review &amp; Approve</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Review & Approve Modal */}
      {selectedTx && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <FileCheck2 className="w-5 h-5 text-amber-600" />
                <h3 className="font-bold text-slate-900">Merchant Review &amp; Ledger Sign-off</h3>
              </div>
              <button
                onClick={() => setSelectedTx(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs space-y-1">
              <div className="text-slate-500">Original Transaction Narration:</div>
              <div className="font-bold text-slate-800 text-sm">{selectedTx.raw_narration}</div>
              <div className="text-slate-600 flex justify-between pt-1">
                <span>Amount: <strong>₹{selectedTx.amount}</strong> ({selectedTx.type})</span>
                <span>Channel: <strong>{selectedTx.channel}</strong></span>
              </div>
            </div>

            <form onSubmit={handleApprove} className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Accounting Category (Chart of Accounts)
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white"
                >
                  {CATEGORY_OPTIONS.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-slate-700 mb-1">GST Tax Rate (%)</label>
                  <select
                    value={gstRate}
                    onChange={(e) => setGstRate(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white"
                  >
                    {GST_RATES.map((r) => (
                      <option key={r} value={r}>
                        {r}% {r === 0 ? "(Exempt/Nil)" : ""}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="pt-5">
                  <label className="inline-flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isInterstate}
                      onChange={(e) => setIsInterstate(e.target.checked)}
                      className="rounded text-amber-600 focus:ring-amber-500"
                    />
                    <span className="font-medium text-slate-700">Inter-State Supply (IGST)</span>
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-slate-700 mb-1">Vendor / Customer Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Acme Corp"
                    value={counterpartyName}
                    onChange={(e) => setCounterpartyName(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500"
                  />
                </div>

                <div>
                  <label className="block font-medium text-slate-700 mb-1">GSTIN (Optional)</label>
                  <input
                    type="text"
                    placeholder="27AAAAA0000A1Z5"
                    value={counterpartyGstin}
                    onChange={(e) => setCounterpartyGstin(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 font-mono uppercase"
                  />
                </div>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Correction Feedback (Optional — Trains Local Agent Memory)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Cement payments should always map to Raw Materials"
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500"
                />
              </div>

              {errorMsg && (
                <div className="p-2.5 bg-red-50 text-red-700 border border-red-200 rounded text-xs">
                  {errorMsg}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setSelectedTx(null)}
                  className="px-4 py-2 border border-slate-300 hover:bg-slate-50 text-slate-700 font-medium rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg shadow-sm transition flex items-center gap-2 disabled:opacity-50"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{submitting ? "Posting to Ledger..." : "Confirm & Post Vouchers"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

