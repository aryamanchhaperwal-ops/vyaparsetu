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
  RotateCcw
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
  const [running, setRunning] = useState(false);
  const [activeStep, setActiveStep] = useState<number>(0);
  const [result, setResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState("");

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
      label: "Raw Materials (Hinglish)",
      text: "Sharma ji ko cement aur building material ke liye ₹45,000 diya",
      amt: "45000",
      type: "DEBIT",
      channel: "UPI",
    },
    {
      label: "Rent / Kiraya (Hindi/Urdu)",
      text: "Dukaan ka monthly kiraya aur godown maintenance payment ₹25,000",
      amt: "25000",
      type: "DEBIT",
      channel: "NEFT",
    },
    {
      label: "Salary (English/Hindi)",
      text: "Monthly staff salary transfer for 4 workers ₹60,000",
      amt: "60000",
      type: "DEBIT",
      channel: "BANK_TRANSFER",
    },
    {
      label: "Customer Payment (Jama/Credit)",
      text: "Gupta Traders se mal ka payment received ₹85,000 via RTGS",
      amt: "85000",
      type: "CREDIT",
      channel: "RTGS",
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
    setActiveStep(1);

    try {
      setTimeout(() => setActiveStep(2), 400);
      setTimeout(() => setActiveStep(3), 900);

      const res = await api.processWorkflow({
        raw_narration: narration,
        amount: parseFloat(amount),
        direction,
        channel,
        is_interstate: isInterstate,
      });

      setActiveStep(4);
      setResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || "LangGraph workflow execution failed.");
    } finally {
      setRunning(false);
    }
  };

  const workflowSteps = [
    { num: 1, title: "Ingestion & Schema", desc: "Validates currency, channel & sanitizes raw Indian vernacular string" },
    { num: 2, title: "Hash Deduplication", desc: "SHA-256 fingerprint verification against existing bank statement entries" },
    { num: 3, title: "BharatCode LLM", desc: "Indic reasoning maps mercantile phrases to 18 MSME ledger accounts" },
    { num: 4, title: "Confidence Router", desc: "Confidence ≥ 0.85 posts to ledger; < 0.85 halts at Human Checkpoint" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
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
                Model: BharatCode-Hosted
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
                className={`p-4 rounded-xl border mt-4 ${
                  result.status === "CONFIRMED"
                    ? "bg-emerald-950/40 border-emerald-500 text-emerald-100"
                    : result.status === "NEEDS_APPROVAL"
                    ? "bg-amber-950/40 border-amber-500 text-amber-100"
                    : "bg-rose-950/40 border-rose-500 text-rose-100"
                }`}
              >
                <div className="flex items-center justify-between pb-3 border-b border-white/10">
                  <div className="flex items-center gap-2">
                    {result.status === "CONFIRMED" ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    ) : result.status === "NEEDS_APPROVAL" ? (
                      <AlertTriangle className="w-5 h-5 text-amber-400" />
                    ) : (
                      <XCircle className="w-5 h-5 text-rose-400" />
                    )}
                    <span className="font-bold text-sm tracking-wide">
                      {result.status === "CONFIRMED"
                        ? "Autonomous Decision: Auto-Approved & Ledger Posted"
                        : result.status === "NEEDS_APPROVAL"
                        ? "Autonomous Decision: Low Confidence — Flagged for Human Review"
                        : "Autonomous Safeguard: Duplicate Transaction Rejected"}
                    </span>
                  </div>
                  <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-black/40">
                    {result.status}
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-3 text-xs">
                  <div>
                    <span className="text-slate-400">Assigned Category</span>
                    <p className="font-bold text-white text-sm mt-0.5">{result.category || "—"}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Confidence Score</span>
                    <p className="font-mono font-bold text-white text-sm mt-0.5">
                      {result.confidence_score ? `${(result.confidence_score * 100).toFixed(0)}%` : "N/A"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400">Ledger Vouchers</span>
                    <p className="font-bold text-white text-sm mt-0.5">
                      {result.ledger_entries_created ? `${result.ledger_entries_created} Balanced Vouchers` : "0 (Pending Approval)"}
                    </p>
                  </div>
                </div>

                {result.rationale && (
                  <div className="mt-3 pt-3 border-t border-white/10 text-xs">
                    <span className="text-slate-400 font-semibold">BharatCode LLM Rationale:</span>
                    <p className="mt-1 text-slate-200 italic font-mono bg-black/20 p-2 rounded">
                      "{result.rationale}"
                    </p>
                  </div>
                )}

                {result.status === "NEEDS_APPROVAL" && (
                  <div className="mt-3 text-xs bg-amber-500/10 border border-amber-500/30 p-2.5 rounded text-amber-200 flex items-center justify-between">
                    <span>This transaction has been routed to the <strong>Human Approval Queue</strong> for merchant sign-off.</span>
                    <a
                      href="/dashboard/approvals"
                      className="ml-2 px-2.5 py-1 bg-amber-500 text-slate-950 font-bold rounded hover:bg-amber-400 transition"
                    >
                      Review Queue
                    </a>
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
