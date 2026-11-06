"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  ShieldCheck,
  CreditCard,
  Clock,
  Sparkles,
  ArrowUpRight,
  ArrowDownLeft,
  FileSpreadsheet,
  Receipt,
  BotMessageSquare,
  RefreshCw,
  AlertTriangle
} from "lucide-react";
import { api, Tenant, Transaction } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

export default function DashboardOverviewPage() {
  const { lang, t } = useLanguage();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [cashFlow, setCashFlow] = useState<any>(null);
  const [creditHealth, setCreditHealth] = useState<any>(null);
  const [recentTransactions, setRecentTransactions] = useState<Transaction[]>([]);
  const [approvalCount, setApprovalCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [tData, cfData, chData, txs, approvals] = await Promise.all([
        api.getCurrentTenant(),
        api.getCashFlow().catch(() => null),
        api.getCreditHealth().catch(() => null),
        api.getTransactions("limit=6").catch(() => []),
        api.getApprovalQueue().catch(() => [])
      ]);
      setTenant(tData);
      setCashFlow(cfData);
      setCreditHealth(chData);
      setRecentTransactions(txs);
      setApprovalCount(approvals.length);
    } catch (err) {
      console.error("Dashboard data load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleGenerateSynthetic = async () => {
    setGenerating(true);
    try {
      await api.generateSyntheticData(15);
      await loadDashboardData();
    } catch (err: any) {
      alert("Failed to generate synthetic data: " + err.message);
    } finally {
      setGenerating(false);
    }
  };

  const symbol = tenant?.currency_symbol || "₹";

  return (
    <div className="space-y-6">
      {/* Top Banner Alert for Pending Approvals */}
      {approvalCount > 0 && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-amber-900">
                {approvalCount} Transaction(s) Need Human Review
              </div>
              <div className="text-xs text-amber-700">
                BharatCode identified low-confidence or ambiguous entries. Review and certify them in the approval queue.
              </div>
            </div>
          </div>
          <Link
            href="/dashboard/approvals"
            className="inline-flex items-center justify-center px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-xl shadow-sm transition-all"
          >
            Review Approvals
          </Link>
        </div>
      )}

      {/* Header and Quick Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">
            {t("welcome")}, {tenant?.name || "Merchant"}
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Real-time financial status &middot; {tenant?.simulated_gstin} &middot; Financial Year {tenant?.financial_year_start_month ? `Starts Month ${tenant.financial_year_start_month}` : "Standard"}
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={handleGenerateSynthetic}
            disabled={generating}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-md shadow-emerald-600/15 disabled:opacity-50 transition-all"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {generating ? "Generating..." : t("generate_synthetic_btn")}
          </button>
          <button
            onClick={loadDashboardData}
            title="Refresh Data"
            className="p-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-600 shadow-sm transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Inflow */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">{t("total_inflow")}</span>
            <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
              <ArrowDownLeft className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900">
            {symbol} {cashFlow?.total_inflows || "0.00"}
          </div>
          <div className="text-[11px] font-medium text-emerald-600 flex items-center gap-1 mt-2">
            <TrendingUp className="w-3.5 h-3.5" /> Verified Inward Commercial Revenue
          </div>
        </div>

        {/* Total Outflow */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">{t("total_outflow")}</span>
            <div className="p-2 rounded-lg bg-rose-50 text-rose-600">
              <ArrowUpRight className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900">
            {symbol} {cashFlow?.total_outflows || "0.00"}
          </div>
          <div className="text-[11px] font-medium text-slate-500 mt-2">
            Operating Purchases & Overheads
          </div>
        </div>

        {/* Net Cash Flow */}
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">{t("net_cashflow")}</span>
            <div className="p-2 rounded-lg bg-teal-50 text-teal-600">
              <Wallet className="w-4 h-4" />
            </div>
          </div>
          <div className={`text-2xl font-black ${
            parseFloat(cashFlow?.net_cash_flow || "0") >= 0 ? "text-emerald-700" : "text-rose-600"
          }`}>
            {symbol} {cashFlow?.net_cash_flow || "0.00"}
          </div>
          <div className="text-[11px] font-medium text-slate-500 mt-2">
            Liquid Balance: {symbol} {cashFlow?.current_liquid_balance || "0.00"}
          </div>
        </div>

        {/* MSME Credit Score */}
        <div className="p-5 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 text-white shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-300 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">{t("credit_score")}</span>
            <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-emerald-400">
              {creditHealth?.indicative_credit_score || "75"}
            </span>
            <span className="text-xs text-slate-400">/ 100</span>
          </div>
          <div className="text-[11px] text-slate-300 mt-2 flex items-center justify-between">
            <span className="font-semibold text-emerald-400">{creditHealth?.credit_grade || "STABLE (A)"}</span>
            <span>Limit: {symbol} {creditHealth?.indicative_working_capital_limit || "0"}</span>
          </div>
        </div>
      </div>

      {/* Analytics & Quick Breakdown Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Expense Category Distribution */}
        <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-4 flex items-center justify-between">
            <span>Operating Expense Breakdown</span>
            <Receipt className="w-4 h-4 text-slate-400" />
          </h2>

          <div className="space-y-3">
            {cashFlow?.expense_category_breakdown?.length > 0 ? (
              cashFlow.expense_category_breakdown.map((item: any, idx: number) => (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold text-slate-700">
                    <span>{item.category}</span>
                    <span>{symbol} {item.amount} ({item.percentage}%)</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-emerald-600 h-2 rounded-full transition-all"
                      style={{ width: `${Math.min(100, item.percentage)}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <div className="text-xs text-slate-400 py-6 text-center">
                No expense records available. Ingest statements to view breakdown.
              </div>
            )}
          </div>
        </div>

        {/* Recent Transactions Mini Ledger */}
        <div className="lg:col-span-2 p-6 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">
                Recent Ledger Activity
              </h2>
              <Link
                href="/dashboard/transactions"
                className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
              >
                View All <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="divide-y divide-slate-100 overflow-x-auto">
              {recentTransactions.length > 0 ? (
                recentTransactions.map((tx) => (
                  <div key={tx.id} className="py-2.5 flex items-center justify-between text-xs gap-3">
                    <div className="flex items-center gap-2.5 truncate">
                      <div
                        className={`h-7 w-7 rounded-lg flex items-center justify-center flex-shrink-0 font-bold ${
                          tx.type === "CREDIT"
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-rose-100 text-rose-700"
                        }`}
                      >
                        {tx.type === "CREDIT" ? "+" : "-"}
                      </div>
                      <div className="truncate">
                        <div className="font-bold text-slate-900 truncate">
                          {tx.raw_narration || tx.description}
                        </div>
                        <div className="text-[10px] text-slate-400 flex items-center gap-2">
                          <span>{tx.transaction_date}</span>
                          <span>&middot;</span>
                          <span className="font-medium text-slate-600">{tx.category}</span>
                          <span>&middot;</span>
                          <span>{tx.channel}</span>
                        </div>
                      </div>
                    </div>

                    <div className="text-right flex-shrink-0">
                      <div className={`font-black ${
                        tx.type === "CREDIT" ? "text-emerald-600" : "text-slate-900"
                      }`}>
                        {tx.type === "CREDIT" ? "+" : "-"}{symbol} {tx.amount}
                      </div>
                      <span
                        className={`inline-block px-1.5 py-0.2 rounded text-[10px] font-bold ${
                          tx.status === "CONFIRMED"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : "bg-amber-50 text-amber-700 border border-amber-200"
                        }`}
                      >
                        {tx.status}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-xs text-slate-400 py-8 text-center">
                  No transactions yet. Click &quot;Generate Synthetic Transactions&quot; above to populate demo data.
                </div>
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 mt-4 flex items-center justify-between text-xs text-slate-500">
            <span>Deterministic Double-Entry Balancing Guard: Active</span>
            <Link href="/dashboard/ledger" className="font-semibold text-emerald-600 hover:underline">
              Open Trial Balance &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

