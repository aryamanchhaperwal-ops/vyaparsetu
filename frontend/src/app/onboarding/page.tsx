"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Globe, DollarSign, Calendar, Clock, CheckCircle2, ArrowRight } from "lucide-react";
import { api, Tenant } from "@/lib/api";

const COUNTRIES = [
  { code: "IN", name: "India", currency: "INR", symbol: "₹", tax: "INDIA_GST", fy: 4, tz: "Asia/Kolkata" },
  { code: "US", name: "United States", currency: "USD", symbol: "$", tax: "US_SALES_TAX", fy: 1, tz: "America/New_York" },
  { code: "AE", name: "United Arab Emirates", currency: "AED", symbol: "AED ", tax: "UAE_VAT", fy: 1, tz: "Asia/Dubai" },
  { code: "GB", name: "United Kingdom", currency: "GBP", symbol: "£", tax: "UK_VAT", fy: 4, tz: "Europe/London" },
  { code: "SG", name: "Singapore", currency: "SGD", symbol: "S$", tax: "SG_GST", fy: 1, tz: "Asia/Singapore" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [selectedCountry, setSelectedCountry] = useState("IN");
  const [baseCurrency, setBaseCurrency] = useState("INR");
  const [currencySymbol, setCurrencySymbol] = useState("₹");
  const [taxJurisdiction, setTaxJurisdiction] = useState("INDIA_GST");
  const [financialYearMonth, setFinancialYearMonth] = useState(4);
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [category, setCategory] = useState("Retail & Hardware Supplies");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getCurrentTenant()
      .then((t) => {
        setTenant(t);
        setSelectedCountry(t.country_code || "IN");
        setBaseCurrency(t.base_currency || "INR");
        setCurrencySymbol(t.currency_symbol || "₹");
        setTaxJurisdiction(t.tax_jurisdiction || "INDIA_GST");
        setFinancialYearMonth(t.financial_year_start_month || 4);
        setTimezone(t.timezone || "Asia/Kolkata");
      })
      .catch(() => router.push("/login"));
  }, [router]);

  const handleCountryChange = (code: string) => {
    setSelectedCountry(code);
    const c = COUNTRIES.find((x) => x.code === code);
    if (c) {
      setBaseCurrency(c.currency);
      setCurrencySymbol(c.symbol);
      setTaxJurisdiction(c.tax);
      setFinancialYearMonth(c.fy);
      setTimezone(c.tz);
    }
  };

  const handleSaveAndContinue = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.updateTenantSettings({
        country_code: selectedCountry,
        base_currency: baseCurrency,
        currency_symbol: currencySymbol,
        tax_jurisdiction: taxJurisdiction,
        financial_year_start_month: financialYearMonth,
        timezone: timezone,
        business_category: category,
      });
      router.push("/dashboard");
    } catch (err: any) {
      alert("Failed to save settings: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-xl mx-auto w-full">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold mb-3">
            Step 2 of 2: Global Configuration
          </div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">
            Configure Your Business Workspace
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Set up multi-currency, regional tax jurisdiction, and financial year settings for{" "}
            <span className="font-semibold text-slate-900">{tenant?.name || "your firm"}</span>.
          </p>
        </div>

        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-xl shadow-slate-200/50">
          <form onSubmit={handleSaveAndContinue} className="space-y-6">
            {/* Country Selector */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2 flex items-center gap-1.5">
                <Globe className="w-4 h-4 text-emerald-600" /> Country & Primary Market
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {COUNTRIES.map((c) => (
                  <button
                    key={c.code}
                    type="button"
                    onClick={() => handleCountryChange(c.code)}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      selectedCountry === c.code
                        ? "border-emerald-600 bg-emerald-50/50 ring-2 ring-emerald-500/20"
                        : "border-slate-200 hover:border-slate-300 bg-white"
                    }`}
                  >
                    <div className="font-bold text-sm text-slate-900">{c.name}</div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {c.currency} ({c.symbol})
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Base Currency & Symbol */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1 flex items-center gap-1.5">
                  <DollarSign className="w-4 h-4 text-emerald-600" /> Base Currency
                </label>
                <input
                  type="text"
                  required
                  value={baseCurrency}
                  onChange={(e) => setBaseCurrency(e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold"
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                  Currency Symbol
                </label>
                <input
                  type="text"
                  required
                  value={currencySymbol}
                  onChange={(e) => setCurrencySymbol(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold"
                />
              </div>
            </div>

            {/* Tax Jurisdiction & FY Start */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1 flex items-center gap-1.5">
                  <Calendar className="w-4 h-4 text-emerald-600" /> Financial Year Start
                </label>
                <select
                  value={financialYearMonth}
                  onChange={(e) => setFinancialYearMonth(parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-sm font-medium"
                >
                  <option value={4}>April (India, UK standard)</option>
                  <option value={1}>January (Calendar year, US/UAE)</option>
                  <option value={7}>July (Australia standard)</option>
                  <option value={10}>October</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1 flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-emerald-600" /> Timezone
                </label>
                <input
                  type="text"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-sm font-medium"
                />
              </div>
            </div>

            {/* Business Category */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                Commercial Sector
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-sm font-medium"
              >
                <option value="Retail & Hardware Supplies">Retail & Hardware Supplies</option>
                <option value="Wholesale FMCG & Provisions">Wholesale FMCG & Provisions</option>
                <option value="Manufacturing & Fabrication">Manufacturing & Fabrication</option>
                <option value="Logistics & Transport Services">Logistics & Transport Services</option>
                <option value="Professional & IT Consulting">Professional & IT Consulting</option>
                <option value="Pharmacy & Healthcare Supplies">Pharmacy & Healthcare Supplies</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center items-center gap-2 py-3.5 px-4 rounded-xl shadow-md text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 transition-all"
            >
              {loading ? "Saving Settings..." : "Complete Setup & Launch Dashboard"} <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

