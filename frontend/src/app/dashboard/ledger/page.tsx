"use client";

import React, { useState, useEffect } from "react";
import {
  BookOpen,
  Scale,
  CheckCircle2,
  AlertCircle,
  Layers,
  ArrowRightLeft,
  Search,
  RefreshCw,
  FolderTree,
  FileText
} from "lucide-react";
import { api } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

interface AccountItem {
  id: string;
  code: string;
  name: string;
  account_type: string;
  balance: string;
}

interface TrialBalanceRow {
  account_code: string;
  account_name: string;
  account_type: string;
  debit: string;
  credit: string;
}

interface TrialBalanceData {
  tenant_id: string;
  is_balanced: boolean;
  total_debit: string;
  total_credit: string;
  accounts: TrialBalanceRow[];
}

interface LedgerEntryItem {
  id: string;
  entry_date: string;
  debit: string;
  credit: string;
  narration: string;
  account_id: string;
}

export default function LedgerPage() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<"trial_balance" | "chart_of_accounts" | "journal_entries">("trial_balance");

  const [trialBalance, setTrialBalance] = useState<TrialBalanceData | null>(null);
  const [accounts, setAccounts] = useState<AccountItem[]>([]);
  const [entries, setEntries] = useState<LedgerEntryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [tb, accs, ents] = await Promise.all([
        api.getTrialBalance(),
        api.getAccounts(),
        api.getLedgerEntries(),
      ]);
      setTrialBalance(tb);
      setAccounts(accs || []);
      setEntries(ents || []);
    } catch (err: any) {
      console.error("Failed to load ledger data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredAccounts = accounts.filter(
    (a) =>
      a.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.code.includes(searchTerm) ||
      a.account_type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredTbRows = (trialBalance?.accounts || []).filter(
    (r) =>
      r.account_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.account_code.includes(searchTerm) ||
      r.account_type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BookOpen className="w-7 h-7 text-emerald-600" />
            {t("ledger")} &amp; Double-Entry Accounting
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Deterministic general ledger engine strictly enforcing the fundamental accounting equation: Assets = Liabilities + Equity.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-lg shadow-sm transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {/* Trial Balance Audit Banner */}
      {trialBalance && (
        <div
          className={`p-5 rounded-2xl border flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm ${
            trialBalance.is_balanced
              ? "bg-emerald-50/80 border-emerald-300 text-emerald-950"
              : "bg-rose-50 border-rose-300 text-rose-950"
          }`}
        >
          <div className="flex items-center gap-3">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                trialBalance.is_balanced ? "bg-emerald-600 text-white" : "bg-rose-600 text-white"
              }`}
            >
              <Scale className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-base">
                  {trialBalance.is_balanced
                    ? "Trial Balance Verified: Exactly Balanced (Σ Dr = Σ Cr)"
                    : "Trial Balance Imbalance Detected!"}
                </h3>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
                    trialBalance.is_balanced ? "bg-emerald-200 text-emerald-900" : "bg-rose-200 text-rose-900"
                  }`}
                >
                  {trialBalance.is_balanced ? "Balanced" : "Discrepancy"}
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                Every transaction posted by LangGraph or manual entry creates equal and opposite debit/credit entries.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div>
              <span className="text-xs text-slate-500 uppercase tracking-wider block">Total Debits</span>
              <span className="font-mono font-bold text-lg text-slate-900">₹{trialBalance.total_debit}</span>
            </div>
            <div className="h-8 w-px bg-slate-300" />
            <div>
              <span className="text-xs text-slate-500 uppercase tracking-wider block">Total Credits</span>
              <span className="font-mono font-bold text-lg text-slate-900">₹{trialBalance.total_credit}</span>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 gap-4 text-sm font-medium">
        <button
          onClick={() => setActiveTab("trial_balance")}
          className={`pb-3 px-1 border-b-2 transition flex items-center gap-2 ${
            activeTab === "trial_balance"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Scale className="w-4 h-4" />
          <span>Trial Balance</span>
        </button>

        <button
          onClick={() => setActiveTab("chart_of_accounts")}
          className={`pb-3 px-1 border-b-2 transition flex items-center gap-2 ${
            activeTab === "chart_of_accounts"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <FolderTree className="w-4 h-4" />
          <span>Chart of Accounts ({accounts.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("journal_entries")}
          className={`pb-3 px-1 border-b-2 transition flex items-center gap-2 ${
            activeTab === "journal_entries"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Journal Vouchers ({entries.length})</span>
        </button>
      </div>

      {/* Tab 1: Trial Balance */}
      {activeTab === "trial_balance" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-semibold text-slate-800 text-sm">Account Balances &amp; Tax Offsets</h3>
            <div className="relative w-64">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Filter by account..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3">Code</th>
                  <th className="px-5 py-3">Account Name</th>
                  <th className="px-5 py-3">Classification</th>
                  <th className="px-5 py-3 text-right">Debit Balance (₹)</th>
                  <th className="px-5 py-3 text-right">Credit Balance (₹)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredTbRows.map((r) => (
                  <tr key={r.account_code} className="hover:bg-slate-50 transition">
                    <td className="px-5 py-3 font-mono text-xs font-semibold text-slate-700">
                      {r.account_code}
                    </td>
                    <td className="px-5 py-3 font-medium text-slate-800">{r.account_name}</td>
                    <td className="px-5 py-3">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                          r.account_type === "ASSET"
                            ? "bg-blue-100 text-blue-800"
                            : r.account_type === "LIABILITY"
                            ? "bg-amber-100 text-amber-800"
                            : r.account_type === "EQUITY"
                            ? "bg-purple-100 text-purple-800"
                            : r.account_type === "REVENUE"
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-rose-100 text-rose-800"
                        }`}
                      >
                        {r.account_type}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right font-mono font-medium text-slate-800">
                      {parseFloat(r.debit) > 0 ? `₹${r.debit}` : "—"}
                    </td>
                    <td className="px-5 py-3 text-right font-mono font-medium text-slate-800">
                      {parseFloat(r.credit) > 0 ? `₹${r.credit}` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-slate-100 font-bold border-t-2 border-slate-300 text-slate-900">
                <tr>
                  <td colSpan={3} className="px-5 py-3 text-right uppercase text-xs">
                    Grand Total
                  </td>
                  <td className="px-5 py-3 text-right font-mono text-emerald-700">
                    ₹{trialBalance?.total_debit || "0.00"}
                  </td>
                  <td className="px-5 py-3 text-right font-mono text-emerald-700">
                    ₹{trialBalance?.total_credit || "0.00"}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Chart of Accounts */}
      {activeTab === "chart_of_accounts" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-semibold text-slate-800 text-sm">
              Standard Indian MSME Chart of Accounts
            </h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3">Code</th>
                  <th className="px-5 py-3">Account Name</th>
                  <th className="px-5 py-3">Type</th>
                  <th className="px-5 py-3 text-right">Net Running Balance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredAccounts.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50 transition">
                    <td className="px-5 py-3 font-mono text-xs font-semibold text-slate-700">
                      {a.code}
                    </td>
                    <td className="px-5 py-3 font-medium text-slate-800">{a.name}</td>
                    <td className="px-5 py-3">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 uppercase">
                        {a.account_type}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right font-mono font-bold text-slate-900">
                      ₹{a.balance}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Journal Entries */}
      {activeTab === "journal_entries" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-semibold text-slate-800 text-sm">Journal Vouchers &amp; Audit Trail</h3>
          </div>

          {entries.length === 0 ? (
            <div className="p-12 text-center text-slate-400 text-sm">
              No journal vouchers generated yet. Ingest transactions or run the LangGraph agent to generate balanced vouchers.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500 text-xs uppercase border-b border-slate-200">
                  <tr>
                    <th className="px-5 py-3">Date</th>
                    <th className="px-5 py-3">Narration / Voucher Description</th>
                    <th className="px-5 py-3 text-right">Debit (₹)</th>
                    <th className="px-5 py-3 text-right">Credit (₹)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {entries.slice(0, 50).map((e) => (
                    <tr key={e.id} className="hover:bg-slate-50 transition">
                      <td className="px-5 py-3 text-xs text-slate-500">{e.entry_date}</td>
                      <td className="px-5 py-3 font-medium text-slate-800">{e.narration}</td>
                      <td className="px-5 py-3 text-right font-mono text-emerald-700 font-medium">
                        {parseFloat(e.debit) > 0 ? `₹${e.debit}` : "—"}
                      </td>
                      <td className="px-5 py-3 text-right font-mono text-rose-700 font-medium">
                        {parseFloat(e.credit) > 0 ? `₹${e.credit}` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

