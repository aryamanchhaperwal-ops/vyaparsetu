"use client";

import React, { useState, useEffect } from "react";
import {
  Plus,
  Upload,
  FileText,
  Search,
  Filter,
  RefreshCw,
  Sparkles,
  ArrowUpRight,
  ArrowDownLeft,
  X,
  CheckCircle2
} from "lucide-react";
import { api, Transaction, Tenant } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

export default function TransactionsPage() {
  const { t } = useLanguage();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");

  // Modals state
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [manualForm, setManualForm] = useState({
    transaction_date: new Date().toISOString().split("T")[0],
    description: "",
    raw_narration: "",
    amount: "",
    type: "DEBIT",
    channel: "UPI",
    category: "Raw Materials",
    tax_rate: "18.0",
    reference_number: ""
  });

  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  const fetchTransactions = async () => {
    try {
      setLoading(true);
      const [tData, txs] = await Promise.all([
        api.getCurrentTenant(),
        api.getTransactions()
      ]);
      setTenant(tData);
      setTransactions(txs);
    } catch (err) {
      console.error("Error loading transactions:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, []);

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createTransaction({
        ...manualForm,
        amount: parseFloat(manualForm.amount),
        tax_rate: parseFloat(manualForm.tax_rate),
        raw_narration: manualForm.raw_narration || manualForm.description
      });
      setIsManualModalOpen(false);
      setManualForm({
        transaction_date: new Date().toISOString().split("T")[0],
        description: "",
        raw_narration: "",
        amount: "",
        type: "DEBIT",
        channel: "UPI",
        category: "Raw Materials",
        tax_rate: "18.0",
        reference_number: ""
      });
      fetchTransactions();
    } catch (err: any) {
      alert("Error adding transaction: " + err.message);
    }
  };

  const handleCSVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setUploadMessage("Parsing and ingesting bank statement CSV...");
      const res = await api.uploadCSV(file);
      setUploadMessage(`Successfully ingested ${res.inserted} transactions (${res.duplicates_skipped} duplicates skipped).`);
      fetchTransactions();
    } catch (err: any) {
      alert("CSV upload failed: " + err.message);
      setUploadMessage(null);
    }
  };

  const handlePDFUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setUploadMessage("Extracting text streams from bank statement PDF...");
      const res = await api.uploadPDF(file);
      setUploadMessage(`Successfully extracted and posted ${res.inserted} statement records.`);
      fetchTransactions();
    } catch (err: any) {
      alert("PDF upload failed: " + err.message);
      setUploadMessage(null);
    }
  };

  const filteredTransactions = transactions.filter((tx) => {
    const matchSearch =
      tx.raw_narration.toLowerCase().includes(search.toLowerCase()) ||
      tx.description.toLowerCase().includes(search.toLowerCase()) ||
      (tx.reference_number && tx.reference_number.toLowerCase().includes(search.toLowerCase())) ||
      tx.category.toLowerCase().includes(search.toLowerCase());
    const matchType = typeFilter ? tx.type === typeFilter : true;
    const matchChannel = channelFilter ? tx.channel === channelFilter : true;
    return matchSearch && matchType && matchChannel;
  });

  const symbol = tenant?.currency_symbol || "₹";

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">
            Bank & UPI Transactions Ledger
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Ingest statements, manage vouchers, and track double-entry status
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          {/* CSV File Upload Input */}
          <label className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-slate-50 border border-slate-300 rounded-xl text-xs font-bold text-slate-700 shadow-sm transition-all">
            <Upload className="w-3.5 h-3.5 text-emerald-600" />
            <span>Upload Bank CSV</span>
            <input type="file" accept=".csv" onChange={handleCSVUpload} className="hidden" />
          </label>

          {/* PDF File Upload Input */}
          <label className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-slate-50 border border-slate-300 rounded-xl text-xs font-bold text-slate-700 shadow-sm transition-all">
            <FileText className="w-3.5 h-3.5 text-teal-600" />
            <span>Upload PDF Statement</span>
            <input type="file" accept=".pdf" onChange={handlePDFUpload} className="hidden" />
          </label>

          {/* Manual Entry Button */}
          <button
            onClick={() => setIsManualModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-600/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add Manual Entry</span>
          </button>
        </div>
      </div>

      {uploadMessage && (
        <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-900 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" /> {uploadMessage}
          </span>
          <button onClick={() => setUploadMessage(null)} className="text-slate-400 hover:text-slate-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by narration, UTR or category..."
            className="w-full pl-10 pr-3.5 py-2 bg-slate-50 border border-slate-300 rounded-xl text-xs font-medium focus:ring-2 focus:ring-emerald-500 text-slate-900"
          />
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-auto">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-xs font-semibold text-slate-700"
          >
            <option value="">All Flow (Debit & Credit)</option>
            <option value="CREDIT">Inflow / Credit Only</option>
            <option value="DEBIT">Outflow / Debit Only</option>
          </select>

          <select
            value={channelFilter}
            onChange={(e) => setChannelFilter(e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-xs font-semibold text-slate-700"
          >
            <option value="">All Channels</option>
            <option value="UPI">UPI</option>
            <option value="NEFT">NEFT</option>
            <option value="RTGS">RTGS</option>
            <option value="CASH">CASH</option>
            <option value="CHEQUE">CHEQUE</option>
          </select>

          <button
            onClick={fetchTransactions}
            className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Transactions Data Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-bold">
              <tr>
                <th className="py-3 px-4">Date</th>
                <th className="py-3 px-4">Narration & Details</th>
                <th className="py-3 px-4">Channel / Ref</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">GST Rate</th>
                <th className="py-3 px-4 text-right">Amount</th>
                <th className="py-3 px-4 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {filteredTransactions.length > 0 ? (
                filteredTransactions.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4 whitespace-nowrap text-slate-500 font-semibold">
                      {tx.transaction_date}
                    </td>
                    <td className="py-3 px-4 max-w-xs sm:max-w-md truncate">
                      <div className="font-bold text-slate-900 truncate">
                        {tx.raw_narration || tx.description}
                      </div>
                      <div className="text-[10px] text-slate-400 truncate">
                        {tx.description}
                      </div>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="font-semibold text-slate-800">{tx.channel}</span>
                      {tx.reference_number && (
                        <div className="text-[10px] text-slate-400 font-mono">
                          {tx.reference_number}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-semibold">
                        {tx.category}
                      </span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap text-slate-500">
                      {tx.tax_rate ? `${parseFloat(tx.tax_rate)}%` : "0%"}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap text-right font-black">
                      <span className={tx.type === "CREDIT" ? "text-emerald-600" : "text-slate-900"}>
                        {tx.type === "CREDIT" ? "+" : "-"}{symbol} {tx.amount}
                      </span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          tx.status === "CONFIRMED"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : "bg-amber-50 text-amber-700 border border-amber-200"
                        }`}
                      >
                        {tx.status}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400 text-xs">
                    {loading ? "Loading transactions..." : "No matching transactions found."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Manual Entry Modal */}
      {isManualModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
            <div className="flex items-center justify-between mb-4 border-b pb-3">
              <h3 className="font-bold text-base text-slate-900">Record Manual Transaction</h3>
              <button onClick={() => setIsManualModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleManualSubmit} className="space-y-4 text-xs font-medium">
              <div>
                <label className="block text-slate-700 font-bold mb-1">Date</label>
                <input
                  type="date"
                  required
                  value={manualForm.transaction_date}
                  onChange={(e) => setManualForm({ ...manualForm, transaction_date: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 border rounded-xl"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Description / Narration</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Paid cash to helper for shop cleaning"
                  value={manualForm.description}
                  onChange={(e) => setManualForm({ ...manualForm, description: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 border rounded-xl"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-bold mb-1">Amount ({symbol})</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    placeholder="1500.00"
                    value={manualForm.amount}
                    onChange={(e) => setManualForm({ ...manualForm, amount: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border rounded-xl"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-bold mb-1">Direction</label>
                  <select
                    value={manualForm.type}
                    onChange={(e) => setManualForm({ ...manualForm, type: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border rounded-xl font-bold"
                  >
                    <option value="DEBIT">Debit (Outflow / Expense)</option>
                    <option value="CREDIT">Credit (Inflow / Sale)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-bold mb-1">Channel</label>
                  <select
                    value={manualForm.channel}
                    onChange={(e) => setManualForm({ ...manualForm, channel: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border rounded-xl"
                  >
                    <option value="UPI">UPI</option>
                    <option value="CASH">CASH</option>
                    <option value="NEFT">NEFT</option>
                    <option value="CHEQUE">CHEQUE</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-700 font-bold mb-1">GST Rate</label>
                  <select
                    value={manualForm.tax_rate}
                    onChange={(e) => setManualForm({ ...manualForm, tax_rate: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border rounded-xl"
                  >
                    <option value="0.0">0% (Exempt)</option>
                    <option value="5.0">5%</option>
                    <option value="12.0">12%</option>
                    <option value="18.0">18% (Standard)</option>
                    <option value="28.0">28%</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Category</label>
                <select
                  value={manualForm.category}
                  onChange={(e) => setManualForm({ ...manualForm, category: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 border rounded-xl"
                >
                  <option value="Raw Materials">Raw Materials</option>
                  <option value="Sales Revenue">Sales Revenue</option>
                  <option value="Rent & Utilities">Rent & Utilities</option>
                  <option value="Salaries & Wages">Salaries & Wages</option>
                  <option value="Logistics & Transport">Logistics & Transport</option>
                  <option value="Office & Miscellaneous">Office & Miscellaneous</option>
                </select>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsManualModalOpen(false)}
                  className="px-4 py-2 border rounded-xl text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-sm"
                >
                  Save & Post
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

