"use client";

import React, { useState, useEffect } from "react";
import {
  BrainCircuit,
  Play,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Cpu,
  Split,
  FileCheck,
  Send,
  HelpCircle,
  XCircle,
  Mic,
  MicOff,
  Volume2,
  Check,
  RotateCcw,
  Zap,
  Layers,
  Settings
} from "lucide-react";
import { api } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";
import { useVoiceAssistant } from "@/lib/useVoiceAssistant";

export default function BookkeepingPage() {
  const { t } = useLanguage();

  const [narration, setNarration] = useState("");
  const [amount, setAmount] = useState("");
  const [direction, setDirection] = useState<"DEBIT" | "CREDIT">("DEBIT");
  const [channel, setChannel] = useState("UPI");
  const [isInterstate, setIsInterstate] = useState(false);
  const [aiMode, setAiMode] = useState<"PRODUCTION_LIVE" | "DEV_SIMULATION">("DEV_SIMULATION");
  const [running, setRunning] = useState(false);
  const [activeStep, setActiveStep] = useState<number>(0);
  const [result, setResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState("");

  // Human Review & Correction State
  const [reviewCategory, setReviewCategory] = useState("");
  const [reviewSubCategory, setReviewSubCategory] = useState("");
  const [reviewCounterparty, setReviewCounterparty] = useState("");
  const [reviewGstRate, setReviewGstRate] = useState<number>(18.0);
  const [reviewIsInterstate, setReviewIsInterstate] = useState(false);
  const [approving, setApproving] = useState(false);
  const [approvalSuccess, setApprovalSuccess] = useState<any>(null);

  // Voice Assistant State
  const [voiceParsing, setVoiceParsing] = useState(false);
  const [voiceExtractedData, setVoiceExtractedData] = useState<any | null>(null);

  const voice = useVoiceAssistant("hi-IN");

  // When speech transcript updates, parse automatically if meaningful
  const handleStopAndParseVoice = async () => {
    voice.stopListening();
    const spokenText = voice.transcript.trim();
    if (!spokenText) return;

    setVoiceParsing(true);
    setErrorMsg("");

    try {
      const res = await api.parseVoiceNarration(spokenText);
      const data = res.data;
      setVoiceExtractedData(data);

      // Auto-populate form
      setNarration(data.suggested_description || spokenText);
      if (data.amount > 0) {
        setAmount(String(data.amount));
      }
      if (data.direction) {
        setDirection(data.direction);
      }
      if (data.channel) {
        setChannel(data.channel);
      }
    } catch (err: any) {
      setErrorMsg("Voice parsing notice: " + (err.message || "Could not extract fields"));
    } finally {
      setVoiceParsing(false);
    }
  };

  const presetExamples = [
    {
      label: "Raw Materials (Supplier Payment)",
      text: "Sharma ji ko cement aur building material ke liye ₹45,000 diya",
      amt: "45000",
      type: "DEBIT",
      channel: "UPI",
    },
    {
      label: "Customer Payment (Jama/Credit)",
      text: "Gupta Traders se sales invoice payment received ₹85,000 via RTGS",
      amt: "85000",
      type: "CREDIT",
      channel: "RTGS",
    },
    {
      label: "Commercial Rent & Utilities",
      text: "Dukaan ka monthly kiraya aur godown maintenance payment ₹25,000",
      amt: "25000",
      type: "DEBIT",
      channel: "NEFT",
    },
    {
      label: "Inter-Bank Transfer",
      text: "Transfer from HDFC current account to SBI overdraft account ₹50,000",
      amt: "50000",
      type: "DEBIT",
      channel: "BANK_TRANSFER",
    },
    {
      label: "Ambiguous (Low Confidence)",
      text: "Old uncle settlement payment kuch personal aur vendor mix ₹4,200",
      amt: "4200",
      type: "DEBIT",
      channel: "CASH",
    },
  ];

  const handleApplyPreset = (p: typeof presetExamples[0]) => {
    setNarration(p.text);
    setAmount(p.amt);
    setDirection(p.type as "DEBIT" | "CREDIT");
    setChannel(p.channel);
    setResult(null);
    setApprovalSuccess(null);
    setErrorMsg("");
    setVoiceExtractedData(null);
  };

  const handleRunWorkflow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!narration || !amount) {
      setErrorMsg("Please enter both transaction narration and amount.");
      return;
    }

    setErrorMsg("");
    setRunning(true);
    setResult(null);
    setApprovalSuccess(null);
    setActiveStep(1);

    try {
      setTimeout(() => setActiveStep(2), 300);
      setTimeout(() => setActiveStep(3), 700);

      const res = await api.processWorkflow({
        raw_narration: narration,
        amount: parseFloat(amount),
        direction,
        channel,
        is_interstate: isInterstate,
        ai_mode: aiMode,
      });

      setActiveStep(4);
      setResult(res);

      // Pre-fill review form with AI suggestions
      setReviewCategory(res.category || "");
      setReviewSubCategory(res.sub_category || "");
      setReviewCounterparty(res.counterparty_name || "");
      setReviewGstRate(res.gst_rate ?? 18.0);
      setReviewIsInterstate(isInterstate);
    } catch (err: any) {
      setErrorMsg(err.message || "LangGraph workflow execution failed.");
    } finally {
      setRunning(false);
    }
  };

  const handleInlineApprove = async () => {
    if (!result?.transaction_id) return;
    setApproving(true);
    setErrorMsg("");
    try {
      const appRes = await api.approveTransaction({
        transaction_id: result.transaction_id,
        category: reviewCategory,
        sub_category: reviewSubCategory,
        gst_rate: reviewGstRate,
        counterparty_name: reviewCounterparty,
        is_interstate: reviewIsInterstate,
      });
      setApprovalSuccess(appRes);
      setResult((prev: any) => ({
        ...prev,
        status: "CONFIRMED",
        ledger_entries_created: appRes.entries_created,
        category: appRes.category,
        sub_category: appRes.sub_category,
        counterparty_name: appRes.counterparty_name,
        message: "Transaction Approved & Posted to Double-Entry Ledger",
      }));
    } catch (err: any) {
      setErrorMsg("Approval error: " + (err.message || "Failed to post to ledger"));
    } finally {
      setApproving(false);
    }
  };

  const workflowSteps = [
    { num: 1, title: "Ingestion & Schema", desc: "Validates currency, channel & sanitizes raw Indian vernacular string" },
    { num: 2, title: "Hash Deduplication", desc: "SHA-256 fingerprint verification against existing bank statement entries" },
    { num: 3, title: aiMode === "PRODUCTION_LIVE" ? "BharatCode Live Qwen" : "Dev Indic Simulator", desc: aiMode === "PRODUCTION_LIVE" ? "Live Qwen 3.8 27B inference on BharatCode API" : "Local deterministic Indic merchant simulation engine" },
    { num: 4, title: "Confidence Router", desc: "Confidence ≥ 0.85 posts to ledger; < 0.85 halts at Human Review" },
  ];

  return (
    <div className="space-y-6">
      {/* Header with Live AI Status Indicator */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BrainCircuit className="w-7 h-7 text-emerald-600" />
            {t("bookkeeping")} — LangGraph Autonomous Agent
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            BharatCode AI model orchestrates multi-agent categorization, confidence routing, and double-entry ledger vouchers with voice assistance.
          </p>
        </div>

        {/* AI Engine Status Badge */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl border bg-white shadow-sm text-xs">
            <Zap className="w-4 h-4 text-emerald-600" />
            <span className="text-slate-500 font-medium">Active Inference:</span>
            {aiMode === "PRODUCTION_LIVE" ? (
              <span className="font-bold text-emerald-700 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Live BharatCode (Qwen 3.8 27B)
              </span>
            ) : (
              <span className="font-bold text-amber-600 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                Dev Simulation
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Preset Suggestions */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
          Quick Test Examples (Indian Vernacular &amp; Edge Cases):
        </span>
        <div className="flex flex-wrap gap-2 mt-2">
          {presetExamples.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleApplyPreset(p)}
              className="text-xs px-3 py-1.5 bg-slate-100 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-300 border border-slate-200 rounded-lg text-slate-700 transition"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Grid: Input Form + LangGraph Visualizer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Form Column */}
        <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-600" />
              Transaction Workbench
            </h2>

            {/* Voice Input Trigger */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  if (voice.isListening) {
                    handleStopAndParseVoice();
                  } else {
                    voice.startListening();
                  }
                }}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition border ${
                  voice.isListening
                    ? "bg-rose-600 text-white border-rose-700 animate-pulse shadow-md"
                    : "bg-emerald-50 hover:bg-emerald-100 border-emerald-300 text-emerald-800"
                }`}
                title={voice.isListening ? "Stop & Extract Fields" : "Speak narration in Hindi or English"}
              >
                {voice.isListening ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
                <span>{voice.isListening ? "Stop & Extract" : "Voice Input"}</span>
              </button>
            </div>
          </div>

          {/* Voice Listening Active Notification */}
          {voice.isListening && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl space-y-1.5 animate-pulse">
              <div className="flex items-center justify-between text-xs font-bold text-rose-800">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-rose-600 animate-ping" />
                  Listening: Speak narration in Hindi/English...
                </span>
                <button
                  type="button"
                  onClick={handleStopAndParseVoice}
                  className="px-2 py-0.5 bg-rose-600 text-white rounded text-[11px]"
                >
                  Done Speaking
                </button>
              </div>
              <p className="text-xs text-rose-900 italic font-mono bg-white/70 p-2 rounded">
                "{voice.transcript || voice.interimTranscript || "..."}"
              </p>
            </div>
          )}

          {/* Voice Extracted Banner */}
          {voiceExtractedData && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl space-y-1 text-xs">
              <div className="flex items-center justify-between font-bold text-emerald-900">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Voice Extracted Fields ({Math.round(voiceExtractedData.confidence_score * 100)}% Confidence)
                </span>
                <button
                  onClick={() => setVoiceExtractedData(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <XCircle className="w-3.5 h-3.5" />
                </button>
              </div>
              <p className="text-slate-700 text-[11px]">
                Identified: <strong>{voiceExtractedData.direction}</strong> of ₹<strong>{voiceExtractedData.amount}</strong> via <strong>{voiceExtractedData.channel}</strong> ({voiceExtractedData.category})
              </p>
            </div>
          )}

          <form onSubmit={handleRunWorkflow} className="space-y-4">
            {/* AI Engine Selection */}
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1 flex items-center justify-between">
                <span>AI Execution Mode</span>
                <span className="text-[10px] text-slate-400 font-mono">Backend: BharatCode Client</span>
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setAiMode("PRODUCTION_LIVE")}
                  className={`py-2 px-3 rounded-xl text-xs font-bold border transition text-left flex items-center gap-2 ${
                    aiMode === "PRODUCTION_LIVE"
                      ? "bg-emerald-50 border-emerald-500 text-emerald-800 ring-1 ring-emerald-400"
                      : "bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${aiMode === "PRODUCTION_LIVE" ? "bg-emerald-500" : "bg-slate-300"}`} />
                  <div>
                    <div className="font-bold">Live BharatCode</div>
                    <div className="text-[10px] text-slate-500 font-normal">qwen-3.8-27b Hosted API</div>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setAiMode("DEV_SIMULATION")}
                  className={`py-2 px-3 rounded-xl text-xs font-bold border transition text-left flex items-center gap-2 ${
                    aiMode === "DEV_SIMULATION"
                      ? "bg-amber-50 border-amber-500 text-amber-800 ring-1 ring-amber-400"
                      : "bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${aiMode === "DEV_SIMULATION" ? "bg-amber-500" : "bg-slate-300"}`} />
                  <div>
                    <div className="font-bold">Dev Simulation</div>
                    <div className="text-[10px] text-slate-500 font-normal">Deterministic Indic Engine</div>
                  </div>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Raw Narration (Hinglish, Hindi, or English)
              </label>
              <textarea
                rows={3}
                value={narration}
                onChange={(e) => setNarration(e.target.value)}
                placeholder="e.g. Sharma ji ko cement aur ret ke liye 25000 cash diya"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 text-slate-900 bg-slate-50/50"
                required
              />
              <span className="text-[11px] text-slate-400">
                Accepts spoken vernacular or manual phrases like "udhari chukta kiya", "kiraya", "petty cash".
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Amount (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="5000.00"
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 text-slate-900"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Direction</label>
                <select
                  value={direction}
                  onChange={(e) => setDirection(e.target.value as any)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white text-slate-800 font-semibold"
                >
                  <option value="DEBIT">Outflow / Expense (Debit)</option>
                  <option value="CREDIT">Inflow / Revenue (Credit)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Payment Channel</label>
                <select
                  value={channel}
                  onChange={(e) => setChannel(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white text-slate-800"
                >
                  <option value="UPI">UPI (GooglePay / PhonePe / Paytm)</option>
                  <option value="NEFT">NEFT / RTGS</option>
                  <option value="IMPS">IMPS</option>
                  <option value="BANK_TRANSFER">Bank Account Transfer</option>
                  <option value="CASH">Cash in Hand</option>
                  <option value="CHEQUE">Bank Cheque</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Tax Jurisdiction</label>
                <div className="pt-2">
                  <label className="inline-flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isInterstate}
                      onChange={(e) => setIsInterstate(e.target.checked)}
                      className="rounded text-emerald-600 focus:ring-emerald-500"
                    />
                    <span>Inter-state Supply (IGST)</span>
                  </label>
                </div>
              </div>
            </div>

            {errorMsg && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs">
                {errorMsg}
              </div>
            )}

            <button
              type="submit"
              disabled={running}
              className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm rounded-xl shadow-md shadow-emerald-600/20 transition flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {running ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>LangGraph Multi-Agent Loop Executing...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>Run Autonomous LangGraph Agent</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* LangGraph Pipeline Visualizer Column */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-slate-900 text-slate-200 p-6 rounded-2xl shadow-xl border border-slate-800">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Cpu className="w-5 h-5 text-emerald-400" />
                <h3 className="font-semibold text-white text-base">LangGraph Multi-Agent State Machine</h3>
              </div>
              <span className="text-xs bg-slate-800 text-emerald-400 px-2.5 py-1 rounded-full font-mono border border-slate-700">
                {aiMode === "PRODUCTION_LIVE" ? "Model: BharatCode qwen-3.8-27b" : "Engine: Indic Simulator"}
              </span>
            </div>

            {/* Workflow Pipeline Steps */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 my-5">
              {workflowSteps.map((step) => {
                const isActive = activeStep === step.num;
                const isPassed = activeStep > step.num;
                return (
                  <div
                    key={step.num}
                    className={`p-3 rounded-xl border text-xs transition ${
                      isActive
                        ? "bg-emerald-950/60 border-emerald-500 text-white shadow-lg shadow-emerald-500/20"
                        : isPassed
                        ? "bg-slate-800/80 border-emerald-600/50 text-emerald-300"
                        : "bg-slate-800/40 border-slate-800 text-slate-400"
                    }`}
                  >
                    <div className="flex items-center justify-between font-bold mb-1">
                      <span>Node {step.num}</span>
                      {isPassed ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      ) : isActive ? (
                        <div className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                      ) : null}
                    </div>
                    <p className="font-semibold text-[13px] text-white">{step.title}</p>
                    <p className="text-[10px] text-slate-400 mt-1 leading-snug">{step.desc}</p>
                  </div>
                );
              })}
            </div>

            {/* Agent Result Display */}
            {result ? (
              <div
                data-testid="autonomous-decision"
                className={`p-5 rounded-xl border mt-4 ${
                  result.status === "CONFIRMED"
                    ? "bg-emerald-950/40 border-emerald-500 text-emerald-100"
                    : result.status === "NEEDS_APPROVAL"
                    ? "bg-amber-950/40 border-amber-500 text-amber-100"
                    : "bg-rose-950/40 border-rose-500 text-rose-100"
                }`}
              >
                {/* Header: Title + Explicit Source Badges */}
                <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 border-b border-white/10 gap-2">
                  <div className="flex items-center gap-2">
                    {result.status === "CONFIRMED" ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                    ) : result.status === "NEEDS_APPROVAL" ? (
                      <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
                    ) : (
                      <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
                    )}
                    <span className="font-bold text-sm tracking-wide">
                      {result.status === "CONFIRMED"
                        ? "Autonomous Decision: Auto-Approved & Ledger Posted"
                        : result.status === "NEEDS_APPROVAL"
                        ? "Autonomous Decision: Flagged for Human Review"
                        : "Autonomous Safeguard: Duplicate Rejected"}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    {/* Visual Source Badge */}
                    {result.ai_source === "FAILED" ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-900/60 text-rose-300 border border-rose-700">
                        <XCircle className="w-3.5 h-3.5 text-rose-400" />
                        AI Unavailable
                      </span>
                    ) : result.live_api || result.ai_source === "BHARATCODE_LIVE" ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-900/70 text-emerald-300 border border-emerald-500 shadow-sm animate-pulse">
                        <span className="w-2 h-2 rounded-full bg-emerald-400" />
                        Live BharatCode (Qwen 3.8 27B)
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-900/60 text-amber-300 border border-amber-600">
                        <span className="w-2 h-2 rounded-full bg-amber-400" />
                        Dev Simulation
                      </span>
                    )}

                    <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-black/40">
                      {result.status}
                    </span>
                  </div>
                </div>

                {/* Structured Classification Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3 text-xs">
                  <div>
                    <span className="text-slate-400">Category</span>
                    <p className="font-bold text-white text-sm mt-0.5">{result.category || "—"}</p>
                    {result.sub_category && (
                      <p className="text-[11px] text-emerald-300">{result.sub_category}</p>
                    )}
                  </div>
                  <div>
                    <span className="text-slate-400">Counterparty</span>
                    <p className="font-bold text-white text-sm mt-0.5">{result.counterparty_name || "Merchant / Self"}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">HSN/SAC &amp; GST</span>
                    <p className="font-mono font-bold text-white text-sm mt-0.5">
                      {result.suggested_hsn_sac || "—"} ({result.gst_rate ?? 0}%)
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400">Confidence Score</span>
                    <p className="font-mono font-bold text-white text-sm mt-0.5 flex items-center gap-1.5">
                      {result.confidence_score ? `${(result.confidence_score * 100).toFixed(0)}%` : "0%"}
                      <span className={`w-2 h-2 rounded-full ${
                        (result.confidence_score || 0) >= 0.85 ? "bg-emerald-400" : "bg-amber-400"
                      }`} />
                    </p>
                  </div>
                </div>

                {/* Ledger Vouchers Count */}
                <div className="mt-3 pt-2 border-t border-white/10 flex items-center justify-between text-xs">
                  <span className="text-slate-400">Ledger Posting Status:</span>
                  <span className="font-bold text-white">
                    {result.ledger_entries_created > 0
                      ? `${result.ledger_entries_created} Balanced Double-Entry Vouchers Posted`
                      : "0 Vouchers (Safeguarded — Awaiting Approval)"}
                  </span>
                </div>

                {/* AI Rationale */}
                {result.rationale && (
                  <div className="mt-3 pt-3 border-t border-white/10 text-xs">
                    <span className="text-slate-400 font-semibold">BharatCode LLM Rationale:</span>
                    <p className="mt-1 text-slate-200 italic font-mono bg-black/30 p-2.5 rounded-lg border border-white/5">
                      "{result.rationale}"
                    </p>
                  </div>
                )}

                {/* Accounting & Double-Entry Suggestions */}
                {result.accounting_suggestions && result.accounting_suggestions.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/10 text-xs">
                    <span className="text-emerald-400 font-bold flex items-center gap-1.5 mb-1.5">
                      <FileCheck className="w-4 h-4 text-emerald-400" />
                      Statutory Double-Entry &amp; ITC Guidance:
                    </span>
                    <div className="space-y-1">
                      {result.accounting_suggestions.map((sug: string, i: number) => (
                        <p key={i} className="text-slate-300 font-mono text-[11px] bg-black/20 px-2.5 py-1 rounded border border-white/5">
                          • {sug}
                        </p>
                      ))}
                    </div>
                  </div>
                )}

                {/* Advisory Warnings if any */}
                {(result.gst_advisory || result.hsn_advisory) && (
                  <div className="mt-3 p-2.5 bg-amber-500/10 border border-amber-500/30 rounded text-xs text-amber-300 space-y-1">
                    {result.gst_advisory && <p>⚠️ {result.gst_advisory}</p>}
                    {result.hsn_advisory && <p>ℹ️ {result.hsn_advisory}</p>}
                  </div>
                )}

                {/* Inline Review & Correction Form when Needs Approval */}
                {result.status === "NEEDS_APPROVAL" && (
                  <div className="mt-4 pt-4 border-t border-amber-500/30 space-y-3 bg-amber-950/20 p-4 rounded-xl border border-amber-500/30">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-sm text-amber-300 flex items-center gap-1.5">
                        <ShieldCheck className="w-4 h-4 text-amber-400" />
                        Human Review &amp; Ledger Posting Checkpoint
                      </h4>
                      <span className="text-[11px] text-amber-400/80">
                        Review / adjust before posting
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div>
                        <label className="block text-slate-300 mb-1 font-semibold">Ledger Category</label>
                        <input
                          type="text"
                          value={reviewCategory}
                          onChange={(e) => setReviewCategory(e.target.value)}
                          className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs focus:ring-1 focus:ring-emerald-500"
                        />
                      </div>
                      <div>
                        <label className="block text-slate-300 mb-1 font-semibold">Sub-category</label>
                        <input
                          type="text"
                          value={reviewSubCategory}
                          onChange={(e) => setReviewSubCategory(e.target.value)}
                          className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs focus:ring-1 focus:ring-emerald-500"
                        />
                      </div>
                      <div>
                        <label className="block text-slate-300 mb-1 font-semibold">Counterparty Name</label>
                        <input
                          type="text"
                          value={reviewCounterparty}
                          onChange={(e) => setReviewCounterparty(e.target.value)}
                          className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs focus:ring-1 focus:ring-emerald-500"
                        />
                      </div>
                      <div>
                        <label className="block text-slate-300 mb-1 font-semibold">GST Rate</label>
                        <select
                          value={reviewGstRate}
                          onChange={(e) => setReviewGstRate(parseFloat(e.target.value))}
                          className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs focus:ring-1 focus:ring-emerald-500"
                        >
                          <option value="0.0">0% (Nil / Exempt)</option>
                          <option value="5.0">5% (Essential Commodities)</option>
                          <option value="12.0">12% (Standard Lower)</option>
                          <option value="18.0">18% (Standard Goods/Services)</option>
                          <option value="28.0">28% (Luxury / De-merit)</option>
                        </select>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-2">
                      <label className="inline-flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={reviewIsInterstate}
                          onChange={(e) => setReviewIsInterstate(e.target.checked)}
                          className="rounded text-emerald-600 focus:ring-emerald-500"
                        />
                        <span>Inter-state supply (IGST)</span>
                      </label>

                      <button
                        type="button"
                        onClick={handleInlineApprove}
                        disabled={approving}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg transition flex items-center gap-2 shadow-md disabled:opacity-50"
                      >
                        {approving ? (
                          <>
                            <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            <span>Posting to Ledger...</span>
                          </>
                        ) : (
                          <>
                            <Check className="w-3.5 h-3.5" />
                            <span>Confirm &amp; Post to Double-Entry Ledger</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )}

                {/* Successful Human Approval Notification */}
                {approvalSuccess && (
                  <div className="mt-3 p-3 bg-emerald-900/50 border border-emerald-500 text-emerald-200 rounded-xl text-xs space-y-1">
                    <div className="flex items-center gap-2 font-bold text-emerald-300">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      <span>Certified by Human &amp; Successfully Posted to Ledger!</span>
                    </div>
                    <p className="text-[11px] text-emerald-100">
                      Transaction <strong>{approvalSuccess.transaction_id}</strong> posted with <strong>{approvalSuccess.entries_created} balanced double-entry vouchers</strong> (Total Balanced Amount: ₹{approvalSuccess.total_balanced_amount}).
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500 text-xs">
                Speak a narration via microphone or select an example above to watch the LangGraph multi-agent loop execute.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
