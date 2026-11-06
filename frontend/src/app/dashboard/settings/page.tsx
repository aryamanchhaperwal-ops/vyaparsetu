"use client";

import React, { useState, useEffect } from "react";
import {
  Settings,
  ShieldCheck,
  CreditCard,
  Building2,
  Clock,
  Globe2,
  Coins,
  CheckCircle2,
  AlertCircle,
  FileText,
  Zap,
  ArrowUpRight,
  RefreshCw,
  Lock
} from "lucide-react";
import { api, Tenant } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

interface UsageData {
  tenant_id: string;
  subscription_plan: string;
  billing_period: string;
  transactions_used: number;
  transactions_limit: number;
  ocr_scans_used: number;
  ocr_scans_limit: number;
  llm_tokens_used: number;
  llm_tokens_limit: number;
  plan_limit_exceeded: boolean;
}

interface AuditLogItem {
  id: string;
  action: string;
  entity_type: string;
  ip_address: string;
  created_at: string;
  details: any;
}

export default function SettingsPage() {
  const { t } = useLanguage();

  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Settings Form State
  const [name, setName] = useState("");
  const [tradeName, setTradeName] = useState("");
  const [countryCode, setCountryCode] = useState("IN");
  const [baseCurrency, setBaseCurrency] = useState("INR");
  const [currencySymbol, setCurrencySymbol] = useState("₹");
  const [fyStartMonth, setFyStartMonth] = useState(4);
  const [timezone, setTimezone] = useState("Asia/Kolkata");

  const [savingSettings, setSavingSettings] = useState(false);
  const [upgrading, setUpgrading] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [curTenant, curUsage, logs] = await Promise.all([
        api.getCurrentTenant(),
        api.getUsage(),
        api.getAuditLogs(),
      ]);
      setTenant(curTenant);
      setUsage(curUsage);
      setAuditLogs(logs || []);

      if (curTenant) {
        setName(curTenant.name);
        setTradeName(curTenant.trade_name || "");
        setCountryCode(curTenant.country_code || "IN");
        setBaseCurrency(curTenant.base_currency || "INR");
        setCurrencySymbol(curTenant.currency_symbol || "₹");
        setFyStartMonth(curTenant.financial_year_start_month || 4);
        setTimezone(curTenant.timezone || "Asia/Kolkata");
      }
    } catch (err: any) {
      console.error("Failed to load settings:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingSettings(true);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      const updated = await api.updateTenantSettings({
        name,
        trade_name: tradeName,
        country_code: countryCode,
        base_currency: baseCurrency,
        currency_symbol: currencySymbol,
        financial_year_start_month: Number(fyStartMonth),
        timezone,
      });
      setTenant(updated);
      setSuccessMsg("Workspace configuration updated successfully!");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to update settings.");
    } finally {
      setSavingSettings(false);
    }
  };

  const handleUpgradePlan = async (targetPlan: string) => {
    setUpgrading(true);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      await api.upgradePlan(targetPlan);
      setSuccessMsg(`Successfully upgraded subscription tier to ${targetPlan}!`);
      await loadData();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to upgrade subscription.");
    } finally {
      setUpgrading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Settings className="w-7 h-7 text-emerald-600" />
            {t("settings")} &amp; Subscription Quotas
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Global multi-tenant configuration, regional currencies, usage tiers, and immutable audit logs.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-lg shadow-sm transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Reload</span>
        </button>
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

      {/* Section 1: SaaS Subscription & Usage Quotas */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-amber-500" />
              <h3 className="font-bold text-slate-900 text-base">Subscription Plan &amp; Monthly Usage</h3>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Active Tier: <strong className="text-emerald-700 font-mono">{usage?.subscription_plan || "FREE"}</strong> • Billing Period: {usage?.billing_period}
            </p>
          </div>

          <span className="px-3 py-1 bg-emerald-100 text-emerald-800 font-bold text-xs rounded-full uppercase">
            Active Tenant
          </span>
        </div>

        {/* Quota Progress Bars */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Transactions Quota */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs font-medium text-slate-700">
              <span>Transactions</span>
              <span className="font-mono">
                {usage?.transactions_used} / {usage?.transactions_limit}
              </span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-emerald-600 h-2.5 rounded-full transition-all"
                style={{
                  width: `${Math.min(
                    100,
                    ((usage?.transactions_used || 0) / (usage?.transactions_limit || 1)) * 100
                  )}%`,
                }}
              />
            </div>
          </div>

          {/* OCR Scans Quota */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs font-medium text-slate-700">
              <span>OCR Scans</span>
              <span className="font-mono">
                {usage?.ocr_scans_used} / {usage?.ocr_scans_limit}
              </span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all"
                style={{
                  width: `${Math.min(
                    100,
                    ((usage?.ocr_scans_used || 0) / (usage?.ocr_scans_limit || 1)) * 100
                  )}%`,
                }}
              />
            </div>
          </div>

          {/* LLM Tokens Quota */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs font-medium text-slate-700">
              <span>BharatCode LLM Tokens</span>
              <span className="font-mono">
                {usage?.llm_tokens_used?.toLocaleString()} / {usage?.llm_tokens_limit?.toLocaleString()}
              </span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-purple-600 h-2.5 rounded-full transition-all"
                style={{
                  width: `${Math.min(
                    100,
                    ((usage?.llm_tokens_used || 0) / (usage?.llm_tokens_limit || 1)) * 100
                  )}%`,
                }}
              />
            </div>
          </div>
        </div>

        {/* Upgrade Plan Cards */}
        <div className="pt-4 border-t border-slate-100 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/40 flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-emerald-800 uppercase">PRO Plan (High Volume)</span>
              <p className="text-xs text-slate-600 mt-0.5">
                5,000 monthly transactions • 500 OCR scans • 1M BharatCode tokens
              </p>
            </div>
            <button
              onClick={() => handleUpgradePlan("PRO")}
              disabled={upgrading || usage?.subscription_plan === "PRO"}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded-lg shadow-sm transition disabled:opacity-50"
            >
              {usage?.subscription_plan === "PRO" ? "Current Tier" : "Upgrade ₹1,499"}
            </button>
          </div>

          <div className="p-4 rounded-xl border border-purple-200 bg-purple-50/40 flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-purple-800 uppercase">ENTERPRISE Plan</span>
              <p className="text-xs text-slate-600 mt-0.5">
                50,000 transactions • Unlimited OCR • Dedicated BharatCode endpoints
              </p>
            </div>
            <button
              onClick={() => handleUpgradePlan("ENTERPRISE")}
              disabled={upgrading || usage?.subscription_plan === "ENTERPRISE"}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-medium text-xs rounded-lg shadow-sm transition disabled:opacity-50"
            >
              {usage?.subscription_plan === "ENTERPRISE" ? "Current Tier" : "Upgrade ₹4,999"}
            </button>
          </div>
        </div>
      </div>

      {/* Section 2: Global Workspace Configuration */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
          <Globe2 className="w-5 h-5 text-emerald-600" />
          <h3 className="font-bold text-slate-900 text-base">Global Multi-Tenant Business Profile</h3>
        </div>

        <form onSubmit={handleSaveSettings} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block font-medium text-slate-700 mb-1">Legal Registered Entity Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                required
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Trade / Commercial Brand Name</label>
              <input
                type="text"
                value={tradeName}
                onChange={(e) => setTradeName(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="block font-medium text-slate-700 mb-1">Country</label>
              <select
                value={countryCode}
                onChange={(e) => {
                  setCountryCode(e.target.value);
                  if (e.target.value === "IN") {
                    setBaseCurrency("INR");
                    setCurrencySymbol("₹");
                    setTimezone("Asia/Kolkata");
                    setFyStartMonth(4);
                  } else if (e.target.value === "US") {
                    setBaseCurrency("USD");
                    setCurrencySymbol("$");
                    setTimezone("America/New_York");
                    setFyStartMonth(1);
                  } else if (e.target.value === "AE") {
                    setBaseCurrency("AED");
                    setCurrencySymbol("د.إ");
                    setTimezone("Asia/Dubai");
                    setFyStartMonth(1);
                  }
                }}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
              >
                <option value="IN">India (IN)</option>
                <option value="US">United States (US)</option>
                <option value="AE">United Arab Emirates (AE)</option>
                <option value="SG">Singapore (SG)</option>
                <option value="GB">United Kingdom (GB)</option>
              </select>
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Base Currency</label>
              <input
                type="text"
                value={baseCurrency}
                onChange={(e) => setBaseCurrency(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">Currency Symbol</label>
              <input
                type="text"
                value={currencySymbol}
                onChange={(e) => setCurrencySymbol(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-bold"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-700 mb-1">FY Start Month</label>
              <select
                value={fyStartMonth}
                onChange={(e) => setFyStartMonth(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
              >
                <option value={1}>January (Month 1)</option>
                <option value={4}>April (Month 4 — India)</option>
                <option value={7}>July (Month 7)</option>
                <option value={10}>October (Month 10)</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end pt-3">
            <button
              type="submit"
              disabled={savingSettings}
              className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded-lg shadow-sm transition flex items-center gap-2 disabled:opacity-50"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>{savingSettings ? "Saving Settings..." : "Save Workspace Configuration"}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Section 3: Immutable Audit Trail */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-slate-600" />
            <h3 className="font-bold text-slate-900 text-base">Immutable Security Audit Trail</h3>
          </div>
          <span className="text-xs text-slate-400">Append-only compliance log</span>
        </div>

        {auditLogs.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs">No audit logs recorded yet.</div>
        ) : (
          <div className="divide-y divide-slate-100 max-h-72 overflow-y-auto">
            {auditLogs.map((log) => (
              <div key={log.id} className="p-4 flex items-center justify-between text-xs hover:bg-slate-50 transition">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-slate-800">{log.action}</span>
                    <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded uppercase">
                      {log.entity_type}
                    </span>
                  </div>
                  <p className="text-slate-500 text-[11px]">
                    IP: {log.ip_address || "127.0.0.1"} • Timestamp: {new Date(log.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="text-right font-mono text-[11px] text-slate-400">
                  {log.details ? JSON.stringify(log.details).slice(0, 40) + "..." : ""}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

