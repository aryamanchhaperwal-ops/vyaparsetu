"use client";

import React, { useState, useEffect } from "react";
import {
  FileSpreadsheet,
  Upload,
  Receipt as ReceiptIcon,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileText,
  Search,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Building
} from "lucide-react";
import { api } from "@/lib/api";
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

interface ExtractedDetails {
  receipt_id: string;
  invoice_number: string;
  vendor_name: string;
  vendor_gstin: string;
  total_amount: string;
  taxable_amount: string;
  cgst: string;
  sgst: string;
  igst: string;
  status: string;
}

export default function InvoicesPage() {
  const { t } = useLanguage();
  const [receipts, setReceipts] = useState<ReceiptItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [latestExtracted, setLatestExtracted] = useState<ExtractedDetails | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const loadReceipts = async () => {
    try {
      setLoading(true);
      const data = await api.getReceipts();
      setReceipts(data || []);
    } catch (err: any) {
      console.error("Failed to load receipts:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReceipts();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setErrorMsg("");
    setUploading(true);
    setLatestExtracted(null);

    try {
      const res = await api.uploadReceipt(file);
      setLatestExtracted(res);
      await loadReceipts();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to process receipt image/PDF.");
    } finally {
      setUploading(false);
    }
  };

  const filteredReceipts = receipts.filter((r) => {
    const term = searchTerm.toLowerCase();
    return (
      (r.vendor_name || "").toLowerCase().includes(term) ||
      (r.invoice_number || "").toLowerCase().includes(term) ||
      (r.vendor_gstin || "").toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <FileSpreadsheet className="w-7 h-7 text-emerald-600" />
            {t("invoices")} &amp; Document OCR
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Automated entity extraction for GST invoices, receipts, and cash purchase vouchers.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-lg shadow-sm cursor-pointer transition">
            <Upload className="w-4 h-4" />
            <span>{uploading ? "Extracting Entities..." : "Upload Invoice / Receipt"}</span>
            <input
              type="file"
              accept=".png,.jpg,.jpeg,.pdf"
              className="hidden"
              onChange={handleFileUpload}
              disabled={uploading}
            />
          </label>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Extracted Card (Highlighted if just uploaded) */}
      {latestExtracted && (
        <div className="bg-gradient-to-r from-emerald-50 via-teal-50 to-blue-50 border-2 border-emerald-400 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-emerald-200">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-600" />
              <h3 className="font-semibold text-slate-800">Entity Extraction Completed</h3>
            </div>
            <span className="px-2.5 py-1 bg-emerald-600 text-white text-xs font-semibold rounded-full uppercase">
              {latestExtracted.status}
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 text-sm">
            <div>
              <span className="text-slate-500 text-xs">Vendor Name</span>
              <p className="font-bold text-slate-900">{latestExtracted.vendor_name || "Unidentified"}</p>
            </div>
            <div>
              <span className="text-slate-500 text-xs">Vendor GSTIN</span>
              <p className="font-mono font-medium text-slate-800">
                {latestExtracted.vendor_gstin || "N/A (Unregistered)"}
              </p>
            </div>
            <div>
              <span className="text-slate-500 text-xs">Invoice Number</span>
              <p className="font-medium text-slate-800">{latestExtracted.invoice_number || "Auto-assigned"}</p>
            </div>
            <div>
              <span className="text-slate-500 text-xs">Total Amount</span>
              <p className="font-bold text-emerald-700 text-base">₹{latestExtracted.total_amount}</p>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-emerald-200 grid grid-cols-4 gap-2 text-xs text-slate-600">
            <div>
              Taxable Value: <strong className="text-slate-900">₹{latestExtracted.taxable_amount}</strong>
            </div>
            <div>
              CGST: <strong className="text-slate-900">₹{latestExtracted.cgst}</strong>
            </div>
            <div>
              SGST: <strong className="text-slate-900">₹{latestExtracted.sgst}</strong>
            </div>
            <div>
              IGST: <strong className="text-slate-900">₹{latestExtracted.igst}</strong>
            </div>
          </div>
        </div>
      )}

      {/* Upload Dropzone Guide */}
      <div className="bg-white rounded-xl border border-dashed border-slate-300 p-8 text-center hover:border-emerald-500 transition">
        <div className="max-w-md mx-auto">
          <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3">
            <Upload className="w-6 h-6" />
          </div>
          <h3 className="font-semibold text-slate-800 text-base">Drop receipts or tax invoices here</h3>
          <p className="text-xs text-slate-500 mt-1 mb-4">
            Supports PDF, PNG, JPG files. Extracts vendor 15-character GSTIN, taxable subtotal, and tax breakdowns.
          </p>
          <label className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs rounded-lg cursor-pointer transition">
            <span>Browse Files</span>
            <input
              type="file"
              accept=".png,.jpg,.jpeg,.pdf"
              className="hidden"
              onChange={handleFileUpload}
              disabled={uploading}
            />
          </label>
        </div>
      </div>

      {/* Receipts Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <ReceiptIcon className="w-5 h-5 text-slate-500" />
            <h3 className="font-semibold text-slate-800">Archived Documents ({receipts.length})</h3>
          </div>

          <div className="relative w-full md:w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search vendor or GSTIN..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-400 text-sm">Loading ingested documents...</div>
        ) : filteredReceipts.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            No invoices uploaded yet. Upload your first invoice or receipt to test OCR extraction.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3">Vendor / Counterparty</th>
                  <th className="px-5 py-3">Vendor GSTIN</th>
                  <th className="px-5 py-3">Invoice #</th>
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3 text-right">Amount</th>
                  <th className="px-5 py-3 text-center">Status</th>
                  <th className="px-5 py-3 text-center">Ledger Match</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredReceipts.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50 transition">
                    <td className="px-5 py-3 font-medium text-slate-800 flex items-center gap-2">
                      <Building className="w-4 h-4 text-slate-400" />
                      {r.vendor_name || "Unspecified Vendor"}
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-slate-600">
                      {r.vendor_gstin || "—"}
                    </td>
                    <td className="px-5 py-3 text-slate-600 font-mono text-xs">
                      {r.invoice_number || "—"}
                    </td>
                    <td className="px-5 py-3 text-slate-500 text-xs">
                      {r.invoice_date || "—"}
                    </td>
                    <td className="px-5 py-3 text-right font-bold text-slate-900">
                      ₹{r.total_amount}
                    </td>
                    <td className="px-5 py-3 text-center">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          r.status === "RECONCILED"
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-blue-100 text-blue-800"
                        }`}
                      >
                        {r.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-center text-xs text-slate-500">
                      {r.transaction_id ? (
                        <span className="text-emerald-600 font-medium flex items-center justify-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Reconciled
                        </span>
                      ) : (
                        <span className="text-amber-600 font-medium flex items-center justify-center gap-1">
                          <Clock className="w-3.5 h-3.5" /> Unlinked
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

