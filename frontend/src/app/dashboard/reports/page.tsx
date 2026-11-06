"use client";

import React, { useState, useEffect } from "react";
import {
  BarChart3,
  TrendingUp,
  Scale,
  DollarSign,
  PieChart,
  RefreshCw,
  Download,
  ShieldCheck,
  CheckCircle2,
  FileText,
  Network,
  CalendarDays,
  AlertTriangle
} from "lucide-react";
import { api } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";
import InteractiveKnowledgeGraph from "@/components/InteractiveKnowledgeGraph";

interface FinancialStatementsData {
  tenant_id: string;
  profit_and_loss: {
    revenues: { code: string; name: string; amount: string }[];
    total_revenue: string;
    expenses: { code: string; name: string; amount: string }[];
    total_expenses: string;
    net_profit: string;
  };
  balance_sheet: {
    assets: { code: string; name: string; amount: string }[];
    total_assets: string;
    liabilities: { code: string; name: string; amount: string }[];
    total_liabilities: string;
    equity: { code: string; name: string; amount: string }[];
    total_equity: string;
    is_balanced: boolean;
  };
}

interface CashFlowData {
  total_inflows: string;
  total_outflows: string;
  net_cash_flow: string;
  current_liquid_balance: string;
  estimated_monthly_burn: string;
  cash_runway_months: number;
  expense_category_breakdown: { category: string; amount: string; percentage: number }[];
}

export default function ReportsPage() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<"p_and_l" | "balance_sheet" | "cash_flow" | "forecast" | "knowledge_graph">("p_and_l");
  const [statements, setStatements] = useState<FinancialStatementsData | null>(null);
  const [cashFlow, setCashFlow] = useState<CashFlowData | null>(null);
  const [forecast, setForecast] = useState<any>(null);
  const [knowledgeGraph, setKnowledgeGraph] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const [stmts, cf, fc, kg] = await Promise.all([
        api.getFinancialStatements(),
        api.getCashFlow(),
        api.getCashFlowForecast(),
        api.getKnowledgeGraph(),
      ]);
      setStatements(stmts);
      setCashFlow(cf);
      setForecast(fc);
      setKnowledgeGraph(kg);
    } catch (err: any) {
      console.error("Failed to load financial statements:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const pnl = statements?.profit_and_loss;
  const bs = statements?.balance_sheet;
  const isNetProfitPositive = parseFloat(pnl?.net_profit || "0") >= 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BarChart3 className="w-7 h-7 text-emerald-600" />
            {t("reports")} — Financial Statements
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time Profit &amp; Loss, Balance Sheet, and Working Capital analytics computed deterministically from the general ledger.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-lg shadow-sm transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Statements</span>
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 gap-4 text-sm font-medium">
        <button
          onClick={() => setActiveTab("p_and_l")}
          className={`pb-3 px-1 border-b-2 transition flex items-center gap-2 ${
            activeTab === "p_and_l"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          <span>Profit &amp; Loss (P&amp;L)</span>
        </button>

        <button
          onClick={() => setActiveTab("balance_sheet")}
          className={`pb-3 px-1 border-b-2 transition flex items-center gap-2 ${
            activeTab === "balance_sheet"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Scale className="w-4 h-4" />
          <span>Balance Sheet</span>
        </button>

        <button
          onClick={() => setActiveTab("cash_flow")}
          className={`pb-3 px-1 border-b-2 transition flex items-center gap-2 ${
            activeTab === "cash_flow"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <PieChart className="w-4 h-4" />
          <span>Cash Flow</span>
        </button>

        <button
          onClick={() => setActiveTab("forecast")}
          className={`pb-3 px-1 border-b-2 transition flex items-center gap-2 ${
            activeTab === "forecast"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <CalendarDays className="w-4 h-4" />
          <span>30-Day Forecast</span>
        </button>

        <button
          onClick={() => setActiveTab("knowledge_graph")}
          className={`pb-3 px-1 border-b-2 transition flex items-center gap-2 ${
            activeTab === "knowledge_graph"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Network className="w-4 h-4" />
          <span>Knowledge Graph</span>
        </button>
      </div>

      {/* Tab 1: Profit & Loss Statement */}
      {activeTab === "p_and_l" && (
        <div className="space-y-6">
          {/* Top KPI Card */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold block">
                Total Operating Revenue
              </span>
              <p className="text-2xl font-bold text-slate-900 mt-2">₹{pnl?.total_revenue || "0.00"}</p>
              <span className="text-xs text-emerald-600 font-medium">Invoiced sales &amp; merchant credits</span>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold block">
                Total Operating Expenses
              </span>
              <p className="text-2xl font-bold text-slate-900 mt-2">₹{pnl?.total_expenses || "0.00"}</p>
              <span className="text-xs text-slate-500">Materials, rent, payroll, freight</span>
            </div>

            <div
              className={`p-5 rounded-xl border shadow-sm ${
                isNetProfitPositive ? "bg-emerald-50 border-emerald-300" : "bg-rose-50 border-rose-300"
              }`}
            >
              <span className="text-xs text-slate-600 uppercase tracking-wider font-semibold block">
                Net Operating Profit / (Loss)
              </span>
              <p
                className={`text-2xl font-bold mt-2 ${
                  isNetProfitPositive ? "text-emerald-800" : "text-rose-800"
                }`}
              >
                ₹{pnl?.net_profit || "0.00"}
              </p>
              <span className="text-xs font-semibold">
                {isNetProfitPositive ? "Net Profitable Performance" : "Operating Deficit"}
              </span>
            </div>
          </div>

          {/* Detailed P&L Breakdown Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-slate-100 bg-slate-50">
              <h3 className="font-semibold text-slate-800 text-sm">Income &amp; Expense Schedule</h3>
            </div>

            <div className="p-5 space-y-6">
              {/* Revenue Section */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                  Operating Incomes &amp; Sales (Credit)
                </h4>
                <div className="divide-y divide-slate-100">
                  {pnl?.revenues.map((r) => (
                    <div key={r.code} className="py-2.5 flex items-center justify-between text-sm">
                      <span className="text-slate-800">
                        <span className="font-mono text-xs text-slate-400 mr-2">{r.code}</span>
                        {r.name}
                      </span>
                      <span className="font-mono font-medium text-slate-900">₹{r.amount}</span>
                    </div>
                  ))}
                  <div className="py-2.5 flex items-center justify-between text-sm font-bold bg-slate-50 px-2 rounded">
                    <span>Total Operating Revenue</span>
                    <span className="font-mono text-emerald-700">₹{pnl?.total_revenue || "0.00"}</span>
                  </div>
                </div>
              </div>

              {/* Expense Section */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                  Operating Expenses (Debit)
                </h4>
                <div className="divide-y divide-slate-100">
                  {pnl?.expenses.map((e) => (
                    <div key={e.code} className="py-2.5 flex items-center justify-between text-sm">
                      <span className="text-slate-800">
                        <span className="font-mono text-xs text-slate-400 mr-2">{e.code}</span>
                        {e.name}
                      </span>
                      <span className="font-mono font-medium text-slate-900">₹{e.amount}</span>
                    </div>
                  ))}
                  <div className="py-2.5 flex items-center justify-between text-sm font-bold bg-slate-50 px-2 rounded">
                    <span>Total Operating Expenses</span>
                    <span className="font-mono text-rose-700">₹{pnl?.total_expenses || "0.00"}</span>
                  </div>
                </div>
              </div>

              {/* Net Profit Summary */}
              <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 flex items-center justify-between">
                <div>
                  <h4 className="font-bold text-slate-900 text-base">Net Operating Profit for Period</h4>
                  <p className="text-xs text-slate-500">Carried forward to Balance Sheet Equity as Retained Earnings</p>
                </div>
                <span className="text-xl font-bold font-mono text-emerald-800">
                  ₹{pnl?.net_profit || "0.00"}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Balance Sheet */}
      {activeTab === "balance_sheet" && (
        <div className="space-y-6">
          {/* Balance Sheet Verification Banner */}
          {bs && (
            <div
              className={`p-4 rounded-xl border flex items-center justify-between ${
                bs.is_balanced ? "bg-emerald-50 border-emerald-300 text-emerald-900" : "bg-amber-50 border-amber-300 text-amber-900"
              }`}
            >
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                <span className="font-bold text-sm">
                  {bs.is_balanced
                    ? "Balance Sheet Condition Verified: Total Assets == Total Liabilities + Equity"
                    : "Accounting Equation Variance Detected"}
                </span>
              </div>
              <span className="text-xs font-mono font-bold bg-white/70 px-2.5 py-1 rounded">
                Assets: ₹{bs.total_assets} | Liab+Eq: ₹{bs.total_liabilities} + ₹{bs.total_equity}
              </span>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Assets Column */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-4 border-b border-slate-100 bg-blue-50/50 flex items-center justify-between">
                <h3 className="font-bold text-blue-900 text-sm">Assets (Applications of Funds)</h3>
                <span className="font-mono font-bold text-blue-900">₹{bs?.total_assets}</span>
              </div>

              <div className="p-4 divide-y divide-slate-100">
                {bs?.assets.map((a) => (
                  <div key={a.code} className="py-2.5 flex items-center justify-between text-sm">
                    <span className="text-slate-800">
                      <span className="font-mono text-xs text-slate-400 mr-2">{a.code}</span>
                      {a.name}
                    </span>
                    <span className="font-mono font-medium text-slate-900">₹{a.amount}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Liabilities & Equity Column */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-4 border-b border-slate-100 bg-amber-50/50 flex items-center justify-between">
                <h3 className="font-bold text-amber-900 text-sm">Liabilities &amp; Owner's Equity</h3>
                <span className="font-mono font-bold text-amber-900">
                  ₹{(parseFloat(bs?.total_liabilities || "0") + parseFloat(bs?.total_equity || "0")).toFixed(2)}
                </span>
              </div>

              <div className="p-4 space-y-4">
                <div>
                  <h4 className="text-xs font-bold uppercase text-slate-500 mb-2">Liabilities</h4>
                  <div className="divide-y divide-slate-100">
                    {bs?.liabilities.map((l) => (
                      <div key={l.code} className="py-2 flex items-center justify-between text-sm">
                        <span className="text-slate-800">
                          <span className="font-mono text-xs text-slate-400 mr-2">{l.code}</span>
                          {l.name}
                        </span>
                        <span className="font-mono font-medium text-slate-900">₹{l.amount}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-200">
                  <h4 className="text-xs font-bold uppercase text-slate-500 mb-2">Equity &amp; Retained Earnings</h4>
                  <div className="divide-y divide-slate-100">
                    {bs?.equity.map((eq) => (
                      <div key={eq.code} className="py-2 flex items-center justify-between text-sm">
                        <span className="text-slate-800">
                          <span className="font-mono text-xs text-slate-400 mr-2">{eq.code}</span>
                          {eq.name}
                        </span>
                        <span className="font-mono font-bold text-slate-900">₹{eq.amount}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Cash Flow & Runway */}
      {activeTab === "cash_flow" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">Total Inflow</span>
              <p className="text-2xl font-bold text-emerald-700 mt-2">₹{cashFlow?.total_inflows || "0.00"}</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">Total Outflow</span>
              <p className="text-2xl font-bold text-rose-700 mt-2">₹{cashFlow?.total_outflows || "0.00"}</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">Net Cash Flow</span>
              <p className="text-2xl font-bold text-slate-900 mt-2">₹{cashFlow?.net_cash_flow || "0.00"}</p>
            </div>
            <div className="bg-emerald-50 p-5 rounded-xl border border-emerald-300 shadow-sm">
              <span className="text-xs text-emerald-800 uppercase font-semibold">Estimated Runway</span>
              <p className="text-2xl font-bold text-emerald-900 mt-2">
                {cashFlow?.cash_runway_months || 0} Months
              </p>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-800 text-sm mb-4">Expense Outflow Concentration</h3>
            <div className="space-y-3">
              {(cashFlow?.expense_category_breakdown || []).map((c) => (
                <div key={c.category} className="space-y-1">
                  <div className="flex justify-between text-xs font-medium text-slate-700">
                    <span>{c.category}</span>
                    <span>₹{c.amount} ({c.percentage}%)</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2">
                    <div
                      className="bg-emerald-600 h-2 rounded-full"
                      style={{ width: `${Math.min(100, c.percentage)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: 30-Day Forward Cash Forecast */}
      {activeTab === "forecast" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">Starting Liquidity</span>
              <p className="text-2xl font-bold text-slate-900 mt-2">₹{forecast?.starting_liquidity || "0.00"}</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">Daily Run Rate (In / Out)</span>
              <p className="text-base font-bold text-slate-800 mt-2">
                +₹{forecast?.daily_average_inflow || "0"} / -₹{forecast?.daily_average_outflow || "0"}
              </p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">30-Day Projected Balance</span>
              <p className={`text-2xl font-bold mt-2 ${parseFloat(forecast?.projected_closing_balance_30d || "0") >= 0 ? "text-emerald-700" : "text-rose-600"}`}>
                ₹{forecast?.projected_closing_balance_30d || "0.00"}
              </p>
            </div>
            <div className={`p-5 rounded-xl border shadow-sm ${forecast?.shortfall_risk_level === "HIGH" ? "bg-rose-50 border-rose-300" : "bg-emerald-50 border-emerald-300"}`}>
              <span className="text-xs uppercase font-semibold text-slate-700">Shortfall Risk</span>
              <p className={`text-2xl font-bold mt-2 ${forecast?.shortfall_risk_level === "HIGH" ? "text-rose-700" : "text-emerald-800"}`}>
                {forecast?.shortfall_risk_level || "LOW"}
              </p>
            </div>
          </div>

          {forecast?.statutory_buffer_advice && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-xs flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
              <span><strong>Statutory Tax Buffer:</strong> {forecast.statutory_buffer_advice}</span>
            </div>
          )}

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-800 text-sm mb-4">Forward Liquidity Milestones</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="pb-2">Milestone</th>
                    <th className="pb-2">Target Date</th>
                    <th className="pb-2">Projected Balance</th>
                    <th className="pb-2">Net Shift</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(forecast?.milestones || []).map((m: any) => (
                    <tr key={m.day} className="hover:bg-slate-50">
                      <td className="py-2.5 font-bold text-slate-800">Day +{m.day}</td>
                      <td className="py-2.5 text-slate-600">{m.date}</td>
                      <td className="py-2.5 font-semibold text-slate-900">₹{m.projected_balance}</td>
                      <td className={`py-2.5 font-bold ${parseFloat(m.net_change) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                        {parseFloat(m.net_change) >= 0 ? "+" : ""}₹{m.net_change}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: Financial Knowledge Graph */}
      {activeTab === "knowledge_graph" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">Graph Entities</span>
              <p className="text-2xl font-bold text-slate-900 mt-1">{knowledgeGraph?.summary?.total_nodes || 0}</p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">Relationships</span>
              <p className="text-2xl font-bold text-emerald-700 mt-1">{knowledgeGraph?.summary?.total_edges || 0}</p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">Vendors / Suppliers</span>
              <p className="text-2xl font-bold text-rose-700 mt-1">{knowledgeGraph?.summary?.vendors_count || 0}</p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">Customers / Buyers</span>
              <p className="text-2xl font-bold text-blue-700 mt-1">{knowledgeGraph?.summary?.customers_count || 0}</p>
            </div>
          </div>

          {/* Interactive Visualizer Canvas with Pan, Zoom, Search, Filtering & Node Inspector Drawer */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div>
                <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                  <Network className="w-4 h-4 text-emerald-600" />
                  Interactive Multi-Entity Financial Knowledge Graph
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Visualizes interconnected entities (Businesses, Members, Vendors, Customers, Invoices, Transactions, Accounts, Vouchers, GST Records, Reconciliation Matches)
                </p>
              </div>
            </div>

            <InteractiveKnowledgeGraph data={knowledgeGraph} />
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-800 text-sm mb-3">Top Counterparty Volume Hubs</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {(knowledgeGraph?.summary?.top_vendors || []).map((cp: any) => (
                <div key={cp.name} className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">VENDOR</span>
                    <span className="font-semibold text-xs text-slate-800">{cp.name}</span>
                  </div>
                  <span className="font-bold text-xs text-rose-700">₹{cp.volume}</span>
                </div>
              ))}
              {(knowledgeGraph?.summary?.top_customers || []).map((cp: any) => (
                <div key={cp.name} className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">CUSTOMER</span>
                    <span className="font-semibold text-xs text-slate-800">{cp.name}</span>
                  </div>
                  <span className="font-bold text-xs text-emerald-700">₹{cp.volume}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

