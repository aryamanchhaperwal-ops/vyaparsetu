"use client";

import React, { useState, useEffect } from "react";
import {
  Landmark,
  Calculator,
  FileCheck2,
  AlertTriangle,
  CheckCircle2,
  ShieldCheck,
  Send,
  HelpCircle,
  RefreshCw,
  Clock,
  ArrowRight,
  Scale
} from "lucide-react";
import { api } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

export default function GSTPage() {
  const { t } = useLanguage();

  const [period, setPeriod] = useState("2026-03");
  const [activeTab, setActiveTab] = useState<"gstr1" | "gstr3b" | "calculator">("gstr1");

  // Calculator State
  const [calcAmount, setCalcAmount] = useState("10000");
  const [calcRate, setCalcRate] = useState(18);
  const [calcInterstate, setCalcInterstate] = useState(false);
  const [calcInclusive, setCalcInclusive] = useState(true);
  const [calcResult, setCalcResult] = useState<any>(null);

  // Return Summaries
  const [gstr1, setGstr1] = useState<any>(null);
  const [gstr3b, setGstr3b] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [filing, setFiling] = useState(false);
  const [filingResult, setFilingResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const loadGSTData = async () => {
    try {
      setLoading(true);
      setErrorMsg("");
      const [r1, r3b] = await Promise.all([
        api.getGSTR1(period),
        api.getGSTR3B(period),
      ]);
      setGstr1(r1);
      setGstr3b(r3b);
    } catch (err: any) {
      console.error("Failed to load GST reports:", err);
      setErrorMsg(err.message || "Failed to load GST summaries.");
    } finally {
      setLoading(false);
    }
  };

  const handleComputeGST = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    try {
      const res = await api.computeGST({
        amount: parseFloat(calcAmount),
        rate_percent: calcRate,
        is_interstate: calcInterstate,
        is_inclusive: calcInclusive,
      });
      setCalcResult(res);
    } catch (err: any) {
      console.error("GST calc error:", err);
    }
  };

  useEffect(() => {
    loadGSTData();
    handleComputeGST();
  }, [period]);

  const handleSimulateFiling = async (reportType: "GSTR1" | "GSTR3B") => {
    setFiling(true);
    setFilingResult(null);
    setErrorMsg("");

    try {
      const res = await api.simulateFiling(period, reportType);
      setFilingResult(res);
      await loadGSTData();
    } catch (err: any) {
      setErrorMsg(err.message || "Simulated filing failed.");
    } finally {
      setFiling(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Landmark className="w-7 h-7 text-emerald-600" />
            {t("gst")} — Regional Compliance Sandbox
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Simulated GSTR-1, GSTR-3B tax offset engine with Section 170 statutory rounding and Section 17(5) blocked credit filters.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-slate-600">Tax Period:</label>
          <input
            type="month"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="px-3 py-1.5 text-xs font-bold bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          <button
            onClick={loadGSTData}
            disabled={loading}
            className="px-3 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-lg shadow-sm transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Non-Negotiable Constraint Disclosure Banner */}
      <div className="bg-amber-500/10 border-2 border-amber-500/40 rounded-xl p-4 flex items-center justify-between text-xs text-amber-900">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
          <span>
            <strong>SIMULATED GST SANDBOX:</strong> All reports, tax liabilities, and ARNs are strictly synthetic models for validation. No live data is transmitted to GSTN/NIC portals.
          </span>
        </div>
        <span className="px-2.5 py-1 bg-amber-200 text-amber-900 font-bold rounded font-mono uppercase text-[10px]">
          Sandbox Mode
        </span>
      </div>

      {filingResult && (
        <div className="p-5 bg-gradient-to-r from-emerald-50 via-teal-50 to-blue-50 border-2 border-emerald-400 rounded-xl text-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              <h3 className="font-bold text-slate-900">
                Simulated {filingResult.report_type} Return Filed Successfully!
              </h3>
            </div>
            <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-emerald-600 text-white">
              {filingResult.status}
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs pt-2">
            <div>
              <span className="text-slate-500">Acknowledgement Reference Number (ARN):</span>
              <p className="font-mono font-bold text-slate-900 text-sm mt-0.5">{filingResult.arn}</p>
            </div>
            <div>
              <span className="text-slate-500">Filing Period:</span>
              <p className="font-bold text-slate-800 text-sm mt-0.5">{filingResult.period}</p>
            </div>
            <div>
              <span className="text-slate-500">Timestamp:</span>
              <p className="font-mono text-slate-700 text-sm mt-0.5">{filingResult.filed_at}</p>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-4 text-sm font-medium">
        <button
          onClick={() => setActiveTab("gstr1")}
          className={`pb-3 px-1 border-b-2 transition flex items-center gap-2 ${
            activeTab === "gstr1"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <FileCheck2 className="w-4 h-4" />
          <span>GSTR-1 (Outward Supplies)</span>
        </button>

        <button
          onClick={() => setActiveTab("gstr3b")}
          className={`pb-3 px-1 border-b-2 transition flex items-center gap-2 ${
            activeTab === "gstr3b"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Scale className="w-4 h-4" />
          <span>GSTR-3B (Tax Offsets &amp; Net Payable)</span>
        </button>

        <button
          onClick={() => setActiveTab("calculator")}
          className={`pb-3 px-1 border-b-2 transition flex items-center gap-2 ${
            activeTab === "calculator"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Calculator className="w-4 h-4" />
          <span>Instant GST Calculator (Section 170)</span>
        </button>
      </div>

      {/* Tab 1: GSTR-1 */}
      {activeTab === "gstr1" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div>
              <h3 className="font-bold text-slate-800 text-sm">GSTR-1 Monthly Return Summary</h3>
              <p className="text-xs text-slate-500">
                Period: <strong>{period}</strong> • Simulated GSTIN: <strong>{gstr1?.gstin || "27ABCDE1234F1Z5"}</strong>
              </p>
            </div>
            <button
              onClick={() => handleSimulateFiling("GSTR1")}
              disabled={filing}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded-lg shadow-sm transition flex items-center gap-2 disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{filing ? "Simulating Filing..." : "File Simulated GSTR-1"}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">Total Taxable Value</span>
              <p className="text-2xl font-bold text-slate-900 mt-2">
                ₹{gstr1?.summary?.total_taxable_value || "0.00"}
              </p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">Total Output Tax</span>
              <p className="text-2xl font-bold text-emerald-700 mt-2">
                ₹{gstr1?.summary?.total_tax || "0.00"}
              </p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">Total Invoice Count</span>
              <p className="text-2xl font-bold text-slate-900 mt-2">
                {gstr1?.summary?.total_invoices || 0}
              </p>
            </div>
          </div>

          {/* Table 4 B2B */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-slate-100 bg-slate-50 font-bold text-slate-800 text-xs uppercase">
              Table 4: Taxable Outward B2B Invoices (With Counterparty GSTIN)
            </div>
            <div className="p-4 text-xs text-slate-500">
              {(gstr1?.b2b_invoices || []).length === 0 ? (
                <div className="text-center py-6 text-slate-400">No B2B invoices recorded for this period.</div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {gstr1.b2b_invoices.map((inv: any, idx: number) => (
                    <div key={idx} className="py-2.5 flex justify-between">
                      <span className="font-mono">{inv.counterparty_gstin}</span>
                      <span className="font-bold">₹{inv.total_amount}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: GSTR-3B */}
      {activeTab === "gstr3b" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div>
              <h3 className="font-bold text-slate-800 text-sm">GSTR-3B Self-Assessed Summary &amp; Tax Offsets</h3>
              <p className="text-xs text-slate-500">
                Period: <strong>{period}</strong> • Implements Section 49 IGST/CGST/SGST priority offset rules
              </p>
            </div>
            <button
              onClick={() => handleSimulateFiling("GSTR3B")}
              disabled={filing}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded-lg shadow-sm transition flex items-center gap-2 disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{filing ? "Simulating Filing..." : "File Simulated GSTR-3B"}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">Total Output Tax (Table 3.1)</span>
              <p className="text-2xl font-bold text-slate-900 mt-2">
                ₹{gstr3b?.table_3_1_outward?.total_tax || "0.00"}
              </p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 uppercase font-semibold">Eligible ITC (Table 4)</span>
              <p className="text-2xl font-bold text-blue-700 mt-2">
                ₹{gstr3b?.table_4_itc?.eligible_itc || "0.00"}
              </p>
            </div>
            <div className="bg-emerald-50 p-5 rounded-xl border border-emerald-300 shadow-sm">
              <span className="text-xs text-emerald-800 uppercase font-semibold">Net Cash Payable (Table 6.1)</span>
              <p className="text-2xl font-bold text-emerald-900 mt-2">
                ₹{gstr3b?.table_6_1_payment?.net_cash_payable || "0.00"}
              </p>
            </div>
          </div>

          {/* Tax Breakdown Grid */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
            <h3 className="font-bold text-slate-800 text-sm">Tax Balance Schedule</h3>
            <div className="grid grid-cols-3 gap-4 text-xs">
              <div className="p-3 bg-slate-50 rounded-lg">
                <span className="text-slate-500 font-semibold">CGST (Central Tax)</span>
                <p className="font-bold text-slate-800 text-base mt-1">
                  ₹{gstr3b?.table_3_1_outward?.cgst || "0.00"}
                </p>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg">
                <span className="text-slate-500 font-semibold">SGST (State Tax)</span>
                <p className="font-bold text-slate-800 text-base mt-1">
                  ₹{gstr3b?.table_3_1_outward?.sgst || "0.00"}
                </p>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg">
                <span className="text-slate-500 font-semibold">IGST (Integrated Tax)</span>
                <p className="font-bold text-slate-800 text-base mt-1">
                  ₹{gstr3b?.table_3_1_outward?.igst || "0.00"}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Instant Calculator */}
      {activeTab === "calculator" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-6 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-800 text-base mb-4 flex items-center gap-2">
              <Calculator className="w-5 h-5 text-emerald-600" />
              Section 170 CGST Act Tax Splitter
            </h3>

            <form onSubmit={handleComputeGST} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-slate-700 mb-1">Invoice Amount (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  value={calcAmount}
                  onChange={(e) => setCalcAmount(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-slate-700 mb-1">GST Rate (%)</label>
                  <select
                    value={calcRate}
                    onChange={(e) => setCalcRate(Number(e.target.value))}
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
                  >
                    {[0, 5, 12, 18, 28].map((r) => (
                      <option key={r} value={r}>
                        {r}%
                      </option>
                    ))}
                  </select>
                </div>

                <div className="pt-5 space-y-2">
                  <label className="inline-flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={calcInclusive}
                      onChange={(e) => setCalcInclusive(e.target.checked)}
                      className="rounded text-emerald-600 focus:ring-emerald-500"
                    />
                    <span className="text-slate-700">Tax-Inclusive Price</span>
                  </label>

                  <label className="inline-flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={calcInterstate}
                      onChange={(e) => setCalcInterstate(e.target.checked)}
                      className="rounded text-emerald-600 focus:ring-emerald-500"
                    />
                    <span className="text-slate-700">Inter-State (IGST)</span>
                  </label>
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-lg shadow-sm transition"
              >
                Compute Deterministic Tax Split
              </button>
            </form>
          </div>

          <div className="lg:col-span-6 bg-slate-900 text-slate-200 p-6 rounded-xl border border-slate-800 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <h4 className="font-bold text-white text-sm">Deterministic Calculation Result</h4>
                <span className="text-[10px] bg-slate-800 text-emerald-400 font-mono px-2 py-0.5 rounded">
                  ROUND_HALF_UP (Paisa)
                </span>
              </div>

              {calcResult ? (
                <div className="mt-4 space-y-3 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-800">
                    <span className="text-slate-400">Taxable Value:</span>
                    <span className="font-mono font-bold text-white text-sm">₹{calcResult.taxable_value}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800">
                    <span className="text-slate-400">CGST (Central Tax):</span>
                    <span className="font-mono font-medium text-emerald-400">₹{calcResult.cgst}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800">
                    <span className="text-slate-400">SGST (State Tax):</span>
                    <span className="font-mono font-medium text-emerald-400">₹{calcResult.sgst}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800">
                    <span className="text-slate-400">IGST (Integrated Tax):</span>
                    <span className="font-mono font-medium text-blue-400">₹{calcResult.igst}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800">
                    <span className="text-slate-400">Total Tax Calculated:</span>
                    <span className="font-mono font-bold text-white">₹{calcResult.total_tax}</span>
                  </div>
                  <div className="flex justify-between py-1.5 bg-emerald-950/60 p-2.5 rounded text-emerald-200 font-bold">
                    <span>Section 170 Statutory Rounded Tax:</span>
                    <span className="font-mono text-base">₹{calcResult.section_170_rounded_tax}</span>
                  </div>
                </div>
              ) : null}
            </div>

            <p className="text-[11px] text-slate-500 mt-4 leading-relaxed">
              Section 170 of the CGST Act mandates that amounts of tax, interest, penalty, fine or any other sum payable be rounded off to the nearest rupee.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
