"use client";

import React, { useState } from "react";
import {
  Upload,
  X,
  FileSpreadsheet,
  FileText,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  ArrowRight,
  Layers,
  Database,
  RefreshCw,
  Sliders,
  Filter
} from "lucide-react";
import { api } from "@/lib/api";

interface StatementImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (message: string) => void;
}

export default function StatementImportModal({
  isOpen,
  onClose,
  onSuccess,
}: StatementImportModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Preview Data State
  const [previewData, setPreviewData] = useState<any | null>(null);
  const [selectedSheet, setSelectedSheet] = useState<string>("");
  const [skipDuplicates, setSkipDuplicates] = useState(true);
  const [autoPostLedger, setAutoPostLedger] = useState(true);
  const [selectedRowIndices, setSelectedRowIndices] = useState<Set<number>>(new Set());
  const [filterMode, setFilterMode] = useState<"ALL" | "VALID" | "DUPLICATES">("ALL");

  if (!isOpen) return null;

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setErrorMsg(null);
    await runPreview(file);
  };

  const runPreview = async (file: File, sheetName?: string) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.previewStatement(file, sheetName);
      setPreviewData(data);
      if (data.active_sheet) {
        setSelectedSheet(data.active_sheet);
      }
      // Select all valid rows by default
      const initialSelected = new Set<number>();
      (data.preview_rows || []).forEach((row: any) => {
        if (row.is_valid && (!row.is_duplicate || !skipDuplicates)) {
          initialSelected.add(row.row_index);
        }
      });
      setSelectedRowIndices(initialSelected);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to parse and preview statement.");
      setPreviewData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSheetChange = async (newSheet: string) => {
    setSelectedSheet(newSheet);
    if (selectedFile) {
      await runPreview(selectedFile, newSheet);
    }
  };

  const handleToggleRow = (idx: number) => {
    const next = new Set(selectedRowIndices);
    if (next.has(idx)) {
      next.delete(idx);
    } else {
      next.add(idx);
    }
    setSelectedRowIndices(next);
  };

  const handleToggleSelectAll = () => {
    if (!previewData?.preview_rows) return;
    if (selectedRowIndices.size === previewData.preview_rows.length) {
      setSelectedRowIndices(new Set());
    } else {
      const all = new Set<number>();
      previewData.preview_rows.forEach((r: any) => all.add(r.row_index));
      setSelectedRowIndices(all);
    }
  };

  const handleConfirm = async () => {
    if (!previewData?.preview_rows) return;

    // Filter confirmed rows
    const rowsToCommit = previewData.preview_rows.filter((r: any) =>
      selectedRowIndices.has(r.row_index)
    );

    if (rowsToCommit.length === 0) {
      setErrorMsg("Please select at least one transaction row to import.");
      return;
    }

    setConfirming(true);
    setErrorMsg(null);

    try {
      const res = await api.confirmStatement(
        rowsToCommit,
        skipDuplicates,
        autoPostLedger
      );

      onSuccess(
        `Successfully ingested ${res.inserted} transactions (${res.duplicates_skipped} duplicates skipped, ${res.ledger_entries_created} balanced ledger entries generated).`
      );
      handleClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to confirm transaction ingestion.");
    } finally {
      setConfirming(false);
    }
  };

  const handleClose = () => {
    setSelectedFile(null);
    setPreviewData(null);
    setErrorMsg(null);
    setLoading(false);
    setConfirming(false);
    onClose();
  };

  const displayedRows = (previewData?.preview_rows || []).filter((r: any) => {
    if (filterMode === "VALID") return r.is_valid && !r.is_duplicate;
    if (filterMode === "DUPLICATES") return r.is_duplicate;
    return true;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                Financial Statement Ingestion Pipeline
              </h2>
              <p className="text-xs text-slate-500">
                Multi-format ingestion with header detection, column mapping, row validation &amp; deduplication
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-200 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-5">
          {errorMsg && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Upload Drop Area */}
          {!previewData && !loading && (
            <div className="border-2 border-dashed border-slate-300 hover:border-emerald-500 rounded-2xl p-8 text-center transition bg-slate-50/50">
              <div className="flex justify-center gap-3 mb-3 text-slate-400">
                <FileSpreadsheet className="w-8 h-8 text-emerald-600" />
                <FileText className="w-8 h-8 text-teal-600" />
              </div>
              <h3 className="text-sm font-bold text-slate-800 mb-1">
                Select your Bank or UPI Statement
              </h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto mb-4">
                Supports CSV, Excel (.xlsx, .xls), and digital PDF statements from Indian banks (SBI, HDFC, ICICI, Axis, Kotak, Canara, PNB, etc.).
              </p>
              <label className="cursor-pointer inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-600/20 transition">
                <Upload className="w-4 h-4" />
                <span>Choose File to Preview</span>
                <input
                  type="file"
                  accept=".csv, .xlsx, .xls, .pdf"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </label>
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="py-16 text-center space-y-3">
              <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin mx-auto" />
              <p className="text-sm font-semibold text-slate-800">
                Analyzing and validating statement records...
              </p>
              <p className="text-xs text-slate-500">
                Detecting delimiters, skipping metadata headers, checking UTR duplicates...
              </p>
            </div>
          )}

          {/* Preview Review Screen */}
          {previewData && (
            <div className="space-y-4">
              {/* File Info & Excel Sheet Switcher */}
              <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-100 rounded-xl text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-700">File:</span>
                  <span className="font-mono bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-800">
                    {previewData.filename}
                  </span>
                  <span className="px-2 py-0.5 rounded font-bold uppercase text-[10px] bg-emerald-100 text-emerald-800">
                    {previewData.file_type}
                  </span>
                </div>

                {previewData.sheet_names && previewData.sheet_names.length > 1 && (
                  <div className="flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5 text-slate-500" />
                    <span className="font-semibold text-slate-600">Worksheet:</span>
                    <select
                      value={selectedSheet}
                      onChange={(e) => handleSheetChange(e.target.value)}
                      className="bg-white border border-slate-300 rounded px-2 py-1 text-xs font-medium text-slate-800"
                    >
                      {previewData.sheet_names.map((name: string) => (
                        <option key={name} value={name}>
                          {name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <label className="cursor-pointer text-emerald-700 hover:text-emerald-800 font-semibold text-xs flex items-center gap-1">
                  <span>Replace File</span>
                  <input
                    type="file"
                    accept=".csv, .xlsx, .xls, .pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </label>
              </div>

              {/* Validation Summary Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-white border border-slate-200 rounded-xl shadow-sm">
                  <span className="text-[10px] uppercase font-bold text-slate-500">Total Rows</span>
                  <p className="text-xl font-black text-slate-900 mt-0.5">{previewData.total_rows}</p>
                </div>
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl shadow-sm">
                  <span className="text-[10px] uppercase font-bold text-emerald-800">Valid Transactions</span>
                  <p className="text-xl font-black text-emerald-700 mt-0.5">{previewData.valid_rows}</p>
                </div>
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl shadow-sm">
                  <span className="text-[10px] uppercase font-bold text-amber-800">Duplicates Detected</span>
                  <p className="text-xl font-black text-amber-700 mt-0.5">{previewData.duplicates_count}</p>
                </div>
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl shadow-sm">
                  <span className="text-[10px] uppercase font-bold text-blue-800">Selected For Import</span>
                  <p className="text-xl font-black text-blue-700 mt-0.5">{selectedRowIndices.size}</p>
                </div>
              </div>

              {/* Table Filter Tabs */}
              <div className="flex items-center justify-between text-xs border-b border-slate-200 pb-2">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setFilterMode("ALL")}
                    className={`px-2.5 py-1 rounded-lg font-bold transition ${
                      filterMode === "ALL"
                        ? "bg-slate-800 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    All Rows ({previewData.total_rows})
                  </button>
                  <button
                    onClick={() => setFilterMode("VALID")}
                    className={`px-2.5 py-1 rounded-lg font-bold transition ${
                      filterMode === "VALID"
                        ? "bg-emerald-700 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    Valid Only ({previewData.valid_rows})
                  </button>
                  {previewData.duplicates_count > 0 && (
                    <button
                      onClick={() => setFilterMode("DUPLICATES")}
                      className={`px-2.5 py-1 rounded-lg font-bold transition ${
                        filterMode === "DUPLICATES"
                          ? "bg-amber-600 text-white"
                          : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                      }`}
                    >
                      Duplicates ({previewData.duplicates_count})
                    </button>
                  )}
                </div>

                <button
                  onClick={handleToggleSelectAll}
                  className="text-emerald-700 hover:text-emerald-900 font-bold"
                >
                  {selectedRowIndices.size === previewData.preview_rows.length
                    ? "Deselect All"
                    : "Select All Rows"}
                </button>
              </div>

              {/* Candidate Records Table */}
              <div className="border border-slate-200 rounded-xl overflow-hidden max-h-72 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold sticky top-0">
                    <tr>
                      <th className="p-2.5 w-10 text-center">
                        <input
                          type="checkbox"
                          checked={
                            selectedRowIndices.size === previewData.preview_rows.length &&
                            previewData.preview_rows.length > 0
                          }
                          onChange={handleToggleSelectAll}
                          className="rounded text-emerald-600 focus:ring-emerald-500"
                        />
                      </th>
                      <th className="p-2.5">Date</th>
                      <th className="p-2.5">Narration / Description</th>
                      <th className="p-2.5">Type</th>
                      <th className="p-2.5">Amount</th>
                      <th className="p-2.5">Channel</th>
                      <th className="p-2.5">UTR / Ref</th>
                      <th className="p-2.5">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {displayedRows.map((r: any) => {
                      const isSelected = selectedRowIndices.has(r.row_index);
                      return (
                        <tr
                          key={r.row_index}
                          onClick={() => handleToggleRow(r.row_index)}
                          className={`cursor-pointer transition hover:bg-slate-50 ${
                            isSelected ? "bg-emerald-50/40" : ""
                          }`}
                        >
                          <td className="p-2.5 text-center" onClick={(e) => e.stopPropagation()}>
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => handleToggleRow(r.row_index)}
                              className="rounded text-emerald-600 focus:ring-emerald-500"
                            />
                          </td>
                          <td className="p-2.5 font-medium whitespace-nowrap text-slate-700">
                            {r.transaction_date}
                          </td>
                          <td className="p-2.5 max-w-xs truncate text-slate-800 font-medium">
                            {r.description || r.raw_narration}
                          </td>
                          <td className="p-2.5 whitespace-nowrap">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                r.type === "CREDIT"
                                  ? "bg-emerald-100 text-emerald-800"
                                  : "bg-rose-100 text-rose-800"
                              }`}
                            >
                              {r.type}
                            </span>
                          </td>
                          <td className="p-2.5 font-bold whitespace-nowrap text-slate-900">
                            ₹{r.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                          </td>
                          <td className="p-2.5 whitespace-nowrap text-slate-600 font-semibold text-[11px]">
                            {r.channel}
                          </td>
                          <td className="p-2.5 font-mono text-[11px] text-slate-500 whitespace-nowrap">
                            {r.reference_number || "—"}
                          </td>
                          <td className="p-2.5 whitespace-nowrap">
                            {r.is_duplicate ? (
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded">
                                <AlertTriangle className="w-3 h-3" /> Duplicate
                              </span>
                            ) : r.is_valid ? (
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                                <CheckCircle2 className="w-3 h-3" /> Ready
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-700 bg-rose-100 px-2 py-0.5 rounded">
                                <AlertCircle className="w-3 h-3" /> Error
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Ingestion Settings */}
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
                <label className="flex items-center gap-2 cursor-pointer font-medium text-slate-700">
                  <input
                    type="checkbox"
                    checked={skipDuplicates}
                    onChange={(e) => setSkipDuplicates(e.target.checked)}
                    className="rounded text-emerald-600 focus:ring-emerald-500"
                  />
                  <span>Automatically skip transactions with duplicate reference/UTR numbers</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer font-medium text-slate-700">
                  <input
                    type="checkbox"
                    checked={autoPostLedger}
                    onChange={(e) => setAutoPostLedger(e.target.checked)}
                    className="rounded text-emerald-600 focus:ring-emerald-500"
                  />
                  <span>Automatically post to General Ledger &amp; generate double-entry vouchers</span>
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <button
            onClick={handleClose}
            className="px-4 py-2 border border-slate-300 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100 transition"
          >
            Cancel
          </button>

          {previewData && (
            <button
              onClick={handleConfirm}
              disabled={confirming || selectedRowIndices.size === 0}
              className="inline-flex items-center gap-2 px-5 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-600/20 transition"
            >
              {confirming ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Ingesting Transactions...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Confirm &amp; Import ({selectedRowIndices.size} Transactions)</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
