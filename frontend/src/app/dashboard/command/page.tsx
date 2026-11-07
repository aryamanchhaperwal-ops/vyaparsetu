"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Terminal,
  Mic,
  MicOff,
  Paperclip,
  Send,
  CheckCircle2,
  Clock,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  Volume2,
  VolumeX,
  FileText,
  X,
  ShieldCheck,
  Check,
  Layers,
  TrendingUp,
  Scale,
  Receipt,
  Download,
  Bot,
  User,
  Trash2,
  ArrowUpDown,
  FileSpreadsheet,
  AlertCircle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Loader2
} from "lucide-react";
import { api } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

interface StepPlan {
  step: number;
  title: string;
  agent: string;
  status: "PENDING" | "RUNNING" | "WAITING_APPROVAL" | "COMPLETED" | "FAILED";
  details?: string;
}

interface ApprovalSummary {
  intent?: string;
  financial_period?: string;
  proposed_transactions_count?: number;
  proposed_transactions_amount?: string;
  reconciled_pairs_count?: number;
  audit_anomalies_count?: number;
  net_gst_payable?: string;
  net_profit?: string;
  trial_balance_balanced?: boolean;
}

interface WorkflowRunResponse {
  run_id: string;
  intent?: string;
  status: "PENDING" | "RUNNING" | "WAITING_APPROVAL" | "COMPLETED" | "FAILED";
  execution_plan?: StepPlan[];
  selected_tools?: string[];
  dynamic_tool_results?: any;
  missing_information?: string[];
  clarification_question?: string;
  proposed_transactions?: any[];
  reconciliation_results?: any;
  audit_anomalies?: any;
  gst_summary?: any;
  financial_reports?: any;
  approval_summary?: ApprovalSummary;
  retrieval_strategy?: string;
  retrieved_evidence?: any;
  retrieval_citations?: any[];
  retrieval_confidence?: number;
  consolidated_report?: any;
  spoken_response?: string;
  execution_results?: any;
  error?: string;
  conversation_id?: string;
}

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  run?: WorkflowRunResponse;
}

export default function CommandCentrePage() {
  const { lang, t } = useLanguage();
  const [instruction, setInstruction] = useState("");
  const [selectedPeriod, setSelectedPeriod] = useState("2026-10");
  const [cmdLanguage, setCmdLanguage] = useState<"en" | "hi">("en");
  const [conversationId, setConversationId] = useState<string>("conv_main");
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [isListening, setIsListening] = useState(false);
  const [speechSynthesisActive, setSpeechSynthesisActive] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [currentRun, setCurrentRun] = useState<WorkflowRunResponse | null>(null);
  const [pastRuns, setPastRuns] = useState<any[]>([]);
  const [clarificationInput, setClarificationInput] = useState("");
  const [expandedDags, setExpandedDags] = useState<Record<string, boolean>>({});

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "assistant",
      text: "Namaste! I am Lekha, your AI financial operations assistant powered by BharatCode Qwen. You can speak or type any accounting, tax, reconciliation, or reporting request in English, Hindi, or Hinglish.",
      timestamp: "Just now",
    },
  ]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Load past runs on mount
  useEffect(() => {
    loadPastRuns();
  }, []);

  const loadPastRuns = () => {
    api
      .getCommandRuns(10)
      .then((runs) => setPastRuns(runs || []))
      .catch((err) => console.error("Error loading runs:", err));
  };

  // Toggle DAG visibility
  const toggleDag = (msgId: string) => {
    setExpandedDags((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  // Speech Recognition
  const toggleListening = () => {
    setSpeechError(null);
    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsListening(false);
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSpeechError(
        "Speech recognition is not supported in this browser. Please use Google Chrome or Edge, or type your instruction below."
      );
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = cmdLanguage === "hi" ? "hi-IN" : "en-IN";
      recognition.continuous = true;
      recognition.interimResults = true;

      recognition.onstart = () => {
        setIsListening(true);
        setSpeechError(null);
      };

      recognition.onresult = (event: any) => {
        let finalAccumulated = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalAccumulated += event.results[i][0].transcript + " ";
          }
        }
        if (finalAccumulated.trim()) {
          setInstruction((prev) =>
            prev ? `${prev.trim()} ${finalAccumulated.trim()}` : finalAccumulated.trim()
          );
        }
      };

      recognition.onerror = (event: any) => {
        console.warn("Speech recognition error:", event.error);
        if (event.error !== "no-speech") {
          setSpeechError(`Microphone notice: ${event.error}. You can type your request directly.`);
        }
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err: any) {
      console.error("Speech init error:", err);
      setSpeechError("Unable to access microphone. Please verify browser permissions.");
      setIsListening(false);
    }
  };

  // Speech Synthesis
  const speakText = (text: string) => {
    if (!speechSynthesisActive || typeof window === "undefined" || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const cleanText = text
      .replace(/[*#_`$]/g, "")
      .replace(/\[.*?\]\(.*?\)/g, "")
      .replace(/₹/g, "Rupees ");
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = cmdLanguage === "hi" ? "hi-IN" : "en-IN";
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
  };

  // File Handlers
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const filesArray = Array.from(e.target.files);
      setAttachedFiles((prev) => [...prev, ...filesArray]);
    }
  };

  const removeFile = (idx: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  // Clear Chat History & Start New Conversation
  const handleClearChat = async () => {
    try {
      await api.clearConversationHistory(conversationId);
    } catch (e) {
      console.warn("Could not clear backend conversation store:", e);
    }
    const newId = `conv_${Date.now()}`;
    setConversationId(newId);
    setMessages([
      {
        id: "welcome_new",
        sender: "assistant",
        text: "New financial session started. How can I assist you with your books, invoices, or GST today?",
        timestamp: "Just now",
      },
    ]);
    setCurrentRun(null);
  };

  // Execute Command
  const handleExecute = async (overrideText?: string) => {
    const textToRun = overrideText || instruction;
    if (!textToRun && attachedFiles.length === 0) return;

    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }

    // Add user message to persistent chat
    const userMessageId = `usr_${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMessageId,
      sender: "user",
      text: textToRun,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInstruction("");

    setIsLoading(true);
    try {
      let res: WorkflowRunResponse;
      if (attachedFiles.length > 0) {
        const formData = new FormData();
        formData.append("instruction", textToRun);
        formData.append("language", cmdLanguage);
        formData.append("financial_period", selectedPeriod);
        formData.append("conversation_id", conversationId);
        attachedFiles.forEach((file) => formData.append("files", file));
        res = await api.executeUploadCommand(formData);
        setAttachedFiles([]);
      } else {
        res = await api.executeCommand({
          instruction: textToRun,
          language: cmdLanguage,
          financial_period: selectedPeriod,
          conversation_id: conversationId,
        });
      }

      setCurrentRun(res);

      const assistantMessageId = `asst_${Date.now()}`;
      const assistantText =
        res.spoken_response ||
        res.execution_results?.summary ||
        res.clarification_question ||
        "Financial instruction processed.";

      const assistantMsg: ChatMessage = {
        id: assistantMessageId,
        sender: "assistant",
        text: assistantText,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        run: res,
      };

      setMessages((prev) => [...prev, assistantMsg]);
      // Default to expanding DAG for active run
      setExpandedDags((prev) => ({ ...prev, [assistantMessageId]: true }));

      if (res.spoken_response) {
        speakText(res.spoken_response);
      }
      loadPastRuns();
    } catch (err: any) {
      console.error("Execution failed:", err);
      const errMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        sender: "assistant",
        text: `Error: ${err.message || "Failed to process financial request."}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  // Submit Clarification
  const handleClarificationSubmit = async () => {
    if (!clarificationInput.trim()) return;
    const combined = `${currentRun?.clarification_question || ""}: ${clarificationInput.trim()}`;
    setClarificationInput("");
    await handleExecute(combined);
  };

  // Approve Checkpoint
  const handleApprove = async () => {
    if (!currentRun?.run_id) return;
    setIsApproving(true);
    try {
      const res = await api.approveCommandRun({
        run_id: currentRun.run_id,
        approved: true,
      });

      const updatedRun: WorkflowRunResponse = {
        ...currentRun,
        status: res.status,
        execution_plan: res.execution_plan || currentRun.execution_plan,
        execution_results: res.execution_results,
        spoken_response: res.spoken_response,
      };

      setCurrentRun(updatedRun);

      // Append confirmation message to chat
      const confirmationMsg: ChatMessage = {
        id: `asst_appr_${Date.now()}`,
        sender: "assistant",
        text:
          res.spoken_response ||
          `Approved and posted to general ledger. Committed ${
            res.execution_results?.committed_transactions || 0
          } transactions and created ${
            res.execution_results?.ledger_entries_created || 0
          } balanced double-entry vouchers.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        run: updatedRun,
      };
      setMessages((prev) => [...prev, confirmationMsg]);

      if (res.spoken_response) {
        speakText(res.spoken_response);
      }
      loadPastRuns();
    } catch (err: any) {
      console.error("Approval failed:", err);
      alert(err.message || "Approval commitment failed.");
    } finally {
      setIsApproving(false);
    }
  };

  // Suggested Prompts (Optional Shortcuts — Not a whitelist)
  const quickPrompts = [
    {
      label: "Close October Accounts",
      text: "Close my October accounts. Process my bank statements, classify transactions, reconcile invoices and payments, prepare my GST summary, run a compliance audit and generate my financial reports.",
    },
    {
      label: "Top 5 Vendors Paid",
      text: "Show me the five vendors I paid the most this quarter.",
    },
    {
      label: "Unmatched Sharma Payments",
      text: "Find payments to Sharma Traders that do not have matching invoices.",
    },
    {
      label: "Compare Oct vs Sep",
      text: "Compare my October expenses with September.",
    },
    {
      label: "Overdue Invoices",
      text: "Which customers have overdue invoices?",
    },
    {
      label: "Expenses > ₹25,000 & Audit",
      text: "Find all transactions above ₹25,000 and flag unusual entries.",
    },
    {
      label: "Explain Cash Decrease",
      text: "Explain why my cash balance decreased this month.",
    },
    {
      label: "GST ITC Status",
      text: "Show the GST input tax credit status of my purchases.",
    },
    {
      label: "Monthly Financial Summary Export",
      text: "Generate a monthly financial summary and export it.",
    },
    {
      label: "Hindi: October Khate Band Karo",
      text: "October ke khate band karo. Bank statements process karo, transactions classify karo, GST summary aur audit reports nikalo.",
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Header Console */}
      <div className="bg-slate-900 rounded-2xl p-6 text-white shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-2.5 mb-2 flex-wrap">
              <span className="p-2 bg-indigo-600/30 border border-indigo-400/30 rounded-xl text-indigo-400">
                <Terminal className="w-5 h-5" />
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Agentic Financial Operations Chatbot
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                BharatCode Qwen 3.8 27B
              </span>
            </div>
            <h1 className="text-2xl font-black tracking-tight text-white">
              Autonomous Financial Operations Command Centre
            </h1>
            <p className="text-slate-400 text-xs mt-1">
              Ask questions, inspect ledger records, audit compliance, compare expenses, or execute full accounting cycles using natural voice or text.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Audio Feedback Toggle */}
            <button
              type="button"
              onClick={() => setSpeechSynthesisActive(!speechSynthesisActive)}
              className={`p-2.5 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                speechSynthesisActive
                  ? "bg-indigo-600/30 border-indigo-500/40 text-indigo-300"
                  : "bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700"
              }`}
              title={speechSynthesisActive ? "Spoken response enabled" : "Spoken response muted"}
            >
              {speechSynthesisActive ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
              <span>{speechSynthesisActive ? "Audio ON" : "Muted"}</span>
            </button>

            {/* Language Selector */}
            <select
              value={cmdLanguage}
              onChange={(e) => setCmdLanguage(e.target.value as "en" | "hi")}
              className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs font-semibold text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="en">English (India)</option>
              <option value="hi">हिन्दी (Hindi)</option>
            </select>

            {/* Period Selector */}
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs font-semibold text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="2026-10">Period: Oct 2026</option>
              <option value="2026-11">Period: Nov 2026</option>
              <option value="2026-12">Period: Dec 2026</option>
            </select>

            {/* Clear Chat Button */}
            <button
              type="button"
              onClick={handleClearChat}
              className="p-2.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-rose-900/40 text-slate-300 hover:text-rose-300 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
              title="Reset conversation session memory"
            >
              <Trash2 className="w-4 h-4" />
              <span>New Session</span>
            </button>
          </div>
        </div>
      </div>

      {/* Quick Suggestion Chips (Optional shortcuts, not a whitelist) */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 space-y-2">
        <div className="flex items-center gap-1.5 text-xs text-slate-400 font-semibold">
          <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
          <span>Quick Prompts &amp; Operations (Examples):</span>
        </div>
        <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
          {quickPrompts.map((prompt, i) => (
            <button
              key={i}
              type="button"
              onClick={() => {
                setInstruction(prompt.text);
                handleExecute(prompt.text);
              }}
              className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium whitespace-nowrap transition-colors flex-shrink-0 cursor-pointer"
            >
              {prompt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Conversational Feed */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 min-h-[420px] max-h-[700px] overflow-y-auto space-y-6 shadow-inner">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3.5 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.sender === "assistant" && (
              <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center flex-shrink-0 shadow-sm">
                <Bot className="w-4 h-4" />
              </div>
            )}

            <div
              className={`max-w-3xl space-y-3.5 ${
                msg.sender === "user"
                  ? "bg-slate-900 text-white rounded-2xl rounded-tr-sm p-4 shadow-sm"
                  : "bg-white border border-slate-200 text-slate-800 rounded-2xl rounded-tl-sm p-5 shadow-sm w-full"
              }`}
            >
              <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-2">
                <span className="text-[11px] font-bold text-slate-400">
                  {msg.sender === "user" ? "Merchant Instruction" : "Lekha AI Financial Assistant"}
                </span>
                <span className="text-[10px] text-slate-400 font-mono">{msg.timestamp}</span>
              </div>

              {/* Message Content */}
              <div className="text-sm whitespace-pre-wrap leading-relaxed">{msg.text}</div>

              {/* Assistant Card Rich Outputs */}
              {msg.run && (
                <div className="space-y-4 pt-2">
                  {/* Tool Activity & Strategy Badges */}
                  <div className="flex items-center gap-2 flex-wrap pt-1">
                    {msg.run.selected_tools && msg.run.selected_tools.length > 0 && (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 font-mono">
                        <Terminal className="w-3 h-3" />
                        Tools: {msg.run.selected_tools.join(", ")}
                      </span>
                    )}

                    {msg.run.retrieval_strategy && (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200 font-mono">
                        <Sparkles className="w-3 h-3" />
                        {msg.run.retrieval_strategy} ({(msg.run.retrieval_confidence || 0.85) * 100}% Grounded)
                      </span>
                    )}

                    {msg.run.spoken_response && (
                      <button
                        type="button"
                        onClick={() => speakText(msg.run?.spoken_response || "")}
                        className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition-colors cursor-pointer"
                      >
                        <Volume2 className="w-3 h-3 text-indigo-600" />
                        Replay Audio
                      </button>
                    )}
                  </div>

                  {/* Dynamic Tool 1: Top Vendors Table */}
                  {(msg.run.dynamic_tool_results?.top_vendors || msg.run.dynamic_tool_results?.get_top_vendors) && (
                    <div className="border border-slate-200 rounded-xl overflow-hidden mt-3 bg-slate-50/50">
                      <div className="bg-slate-100 px-4 py-2 text-xs font-bold text-slate-700 flex justify-between">
                        <span>Top Vendors Expenditure Ranking</span>
                        <span>Total Spend: ₹{(msg.run.dynamic_tool_results.top_vendors || msg.run.dynamic_tool_results.get_top_vendors).total_spend?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-slate-50 text-slate-500 text-[10px] uppercase">
                            <tr>
                              <th className="px-3 py-2">Rank</th>
                              <th className="px-3 py-2">Vendor Name</th>
                              <th className="px-3 py-2">Primary Category</th>
                              <th className="px-3 py-2 text-center">Transactions</th>
                              <th className="px-3 py-2 text-right">Total Paid (₹)</th>
                              <th className="px-3 py-2 text-right">Share (%)</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200/60 bg-white">
                            {(msg.run.dynamic_tool_results.top_vendors || msg.run.dynamic_tool_results.get_top_vendors).top_vendors?.map((v: any, idx: number) => (
                              <tr key={idx} className="hover:bg-slate-50">
                                <td className="px-3 py-2 font-bold text-slate-500">#{v.rank}</td>
                                <td className="px-3 py-2 font-semibold text-slate-900">{v.vendor_name}</td>
                                <td className="px-3 py-2 text-slate-600">{v.primary_category}</td>
                                <td className="px-3 py-2 text-center">{v.transaction_count}</td>
                                <td className="px-3 py-2 text-right font-bold text-slate-900">
                                  ₹{v.total_paid?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                                </td>
                                <td className="px-3 py-2 text-right text-indigo-600 font-semibold">{v.share_of_spend_pct}%</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Dynamic Tool 1b: Unmatched Payments Table */}
                  {(msg.run.dynamic_tool_results?.unmatched_payments || msg.run.dynamic_tool_results?.find_unmatched_vendor_payments) && (
                    <div className="border border-slate-200 rounded-xl overflow-hidden mt-3 bg-slate-50/50">
                      <div className="bg-slate-100 px-4 py-2 text-xs font-bold text-slate-700 flex justify-between">
                        <span>Unmatched Payments &amp; Missing Invoices: {(msg.run.dynamic_tool_results?.unmatched_payments || msg.run.dynamic_tool_results?.find_unmatched_vendor_payments).vendor_name}</span>
                        <span className="text-amber-700 font-bold">
                          {(msg.run.dynamic_tool_results?.unmatched_payments || msg.run.dynamic_tool_results?.find_unmatched_vendor_payments).unmatched_count} Unmatched Payments (₹{(msg.run.dynamic_tool_results?.unmatched_payments || msg.run.dynamic_tool_results?.find_unmatched_vendor_payments).unmatched_amount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })})
                        </span>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-slate-50 text-slate-500 text-[10px] uppercase">
                            <tr>
                              <th className="px-3 py-2">Date</th>
                              <th className="px-3 py-2">Reference / UTR</th>
                              <th className="px-3 py-2">Channel</th>
                              <th className="px-3 py-2 text-right">Amount (₹)</th>
                              <th className="px-3 py-2">Reconciliation Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200/60 bg-white">
                            {(msg.run.dynamic_tool_results?.unmatched_payments || msg.run.dynamic_tool_results?.find_unmatched_vendor_payments).unmatched_payments?.map((p: any, idx: number) => (
                              <tr key={idx} className="hover:bg-slate-50">
                                <td className="px-3 py-2 text-slate-600">{p.date}</td>
                                <td className="px-3 py-2 font-mono font-semibold text-slate-800">{p.reference_number || "N/A"}</td>
                                <td className="px-3 py-2 text-slate-600">{p.channel}</td>
                                <td className="px-3 py-2 text-right font-bold text-slate-900">
                                  ₹{p.amount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                                </td>
                                <td className="px-3 py-2">
                                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 uppercase">
                                    No Matching Invoice Found
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Dynamic Tool 2: Expense Comparison Table */}
                  {msg.run.dynamic_tool_results?.expense_comparison && (
                    <div className="border border-slate-200 rounded-xl overflow-hidden mt-3 bg-slate-50/50">
                      <div className="bg-slate-100 px-4 py-2 text-xs font-bold text-slate-700 flex justify-between">
                        <span>Expense Comparison: {msg.run.dynamic_tool_results.expense_comparison.period_a} vs {msg.run.dynamic_tool_results.expense_comparison.period_b}</span>
                        <span className={msg.run.dynamic_tool_results.expense_comparison.net_difference > 0 ? "text-rose-600" : "text-emerald-600"}>
                          Net Diff: ₹{msg.run.dynamic_tool_results.expense_comparison.net_difference?.toLocaleString("en-IN", { minimumFractionDigits: 2 })} ({msg.run.dynamic_tool_results.expense_comparison.pct_change}%)
                        </span>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-slate-50 text-slate-500 text-[10px] uppercase">
                            <tr>
                              <th className="px-3 py-2">Category</th>
                              <th className="px-3 py-2 text-right">{msg.run.dynamic_tool_results.expense_comparison.period_a} (₹)</th>
                              <th className="px-3 py-2 text-right">{msg.run.dynamic_tool_results.expense_comparison.period_b} (₹)</th>
                              <th className="px-3 py-2 text-right">Difference (₹)</th>
                              <th className="px-3 py-2 text-right">Trend</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200/60 bg-white">
                            {msg.run.dynamic_tool_results.expense_comparison.categories_breakdown?.map((c: any, idx: number) => (
                              <tr key={idx} className="hover:bg-slate-50">
                                <td className="px-3 py-2 font-semibold text-slate-800">{c.category}</td>
                                <td className="px-3 py-2 text-right font-medium">₹{c[`period_${msg.run?.dynamic_tool_results.expense_comparison.period_a}`]?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                                <td className="px-3 py-2 text-right font-medium">₹{c[`period_${msg.run?.dynamic_tool_results.expense_comparison.period_b}`]?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                                <td className="px-3 py-2 text-right font-bold text-slate-900">
                                  {c.difference >= 0 ? "+" : ""}₹{c.difference?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                                </td>
                                <td className="px-3 py-2 text-right">
                                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                    c.direction === "INCREASED" ? "bg-rose-100 text-rose-700" : "bg-emerald-100 text-emerald-700"
                                  }`}>
                                    {c.pct_change}%
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Dynamic Tool 3: Overdue Invoices Table */}
                  {msg.run.dynamic_tool_results?.overdue_invoices && (
                    <div className="border border-slate-200 rounded-xl overflow-hidden mt-3 bg-slate-50/50">
                      <div className="bg-slate-100 px-4 py-2 text-xs font-bold text-slate-700 flex justify-between">
                        <span>Aging Overdue Invoices</span>
                        <span className="text-rose-600 font-bold">
                          Total Overdue: ₹{msg.run.dynamic_tool_results.overdue_invoices.total_overdue_amount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                        </span>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-slate-50 text-slate-500 text-[10px] uppercase">
                            <tr>
                              <th className="px-3 py-2">Invoice #</th>
                              <th className="px-3 py-2">Counterparty</th>
                              <th className="px-3 py-2">Invoice Date</th>
                              <th className="px-3 py-2 text-center">Days Overdue</th>
                              <th className="px-3 py-2 text-right">Amount (₹)</th>
                              <th className="px-3 py-2">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200/60 bg-white">
                            {msg.run.dynamic_tool_results.overdue_invoices.overdue_invoices?.map((inv: any, idx: number) => (
                              <tr key={idx} className="hover:bg-slate-50">
                                <td className="px-3 py-2 font-mono font-semibold text-slate-800">{inv.invoice_number}</td>
                                <td className="px-3 py-2 font-medium text-slate-900">{inv.counterparty_name}</td>
                                <td className="px-3 py-2 text-slate-600">{inv.invoice_date}</td>
                                <td className="px-3 py-2 text-center">
                                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                                    {inv.days_overdue} Days
                                  </span>
                                </td>
                                <td className="px-3 py-2 text-right font-bold text-slate-900">
                                  ₹{inv.amount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                                </td>
                                <td className="px-3 py-2">
                                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 uppercase">
                                    {inv.status}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Dynamic Tool 4: Large & Anomalous Transactions Table */}
                  {msg.run.dynamic_tool_results?.large_transactions && (
                    <div className="border border-slate-200 rounded-xl overflow-hidden mt-3 bg-slate-50/50">
                      <div className="bg-slate-100 px-4 py-2 text-xs font-bold text-slate-700 flex justify-between">
                        <span>Transactions &gt;= ₹{msg.run.dynamic_tool_results.large_transactions.threshold?.toLocaleString("en-IN")}</span>
                        <span className="text-amber-700 font-bold">
                          {msg.run.dynamic_tool_results.large_transactions.anomalies_count} Anomalies Detected
                        </span>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-slate-50 text-slate-500 text-[10px] uppercase">
                            <tr>
                              <th className="px-3 py-2">Date</th>
                              <th className="px-3 py-2">Counterparty</th>
                              <th className="px-3 py-2">Channel</th>
                              <th className="px-3 py-2 text-right">Amount (₹)</th>
                              <th className="px-3 py-2">Compliance / Audit Flags</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200/60 bg-white">
                            {msg.run.dynamic_tool_results.large_transactions.transactions?.map((tx: any, idx: number) => (
                              <tr key={idx} className={tx.is_flagged ? "bg-amber-50/40" : "hover:bg-slate-50"}>
                                <td className="px-3 py-2 text-slate-600">{tx.date}</td>
                                <td className="px-3 py-2 font-semibold text-slate-900">{tx.counterparty_name}</td>
                                <td className="px-3 py-2 text-slate-600">{tx.channel}</td>
                                <td className="px-3 py-2 text-right font-extrabold text-slate-900">
                                  ₹{tx.amount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                                </td>
                                <td className="px-3 py-2 text-xs">
                                  {tx.anomalies && tx.anomalies.length > 0 ? (
                                    <div className="space-y-1">
                                      {tx.anomalies.map((f: string, fIdx: number) => (
                                        <span key={fIdx} className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">
                                          {f}
                                        </span>
                                      ))}
                                    </div>
                                  ) : (
                                    <span className="text-emerald-600 font-semibold text-[11px]">✓ Clean</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Dynamic Tool 5: Cash Decrease Variance Analysis */}
                  {msg.run.dynamic_tool_results?.cash_decrease_explanation && (
                    <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                      <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                        <span>Cash Flow Variance Analysis ({msg.run.dynamic_tool_results.cash_decrease_explanation.period})</span>
                        <span className="text-rose-600 font-extrabold">
                          Net Outflow: ₹{Math.abs(msg.run.dynamic_tool_results.cash_decrease_explanation.net_cash_flow)?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        <div className="p-3 bg-white rounded-lg border border-slate-200">
                          <div className="text-[10px] text-slate-400 uppercase font-semibold">Inflows (Collections)</div>
                          <div className="text-sm font-extrabold text-emerald-700 mt-0.5">
                            ₹{msg.run.dynamic_tool_results.cash_decrease_explanation.total_inflows?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                          </div>
                        </div>
                        <div className="p-3 bg-white rounded-lg border border-slate-200">
                          <div className="text-[10px] text-slate-400 uppercase font-semibold">Outflows (Disbursements)</div>
                          <div className="text-sm font-extrabold text-rose-700 mt-0.5">
                            ₹{msg.run.dynamic_tool_results.cash_decrease_explanation.total_outflows?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                          </div>
                        </div>
                        <div className="p-3 bg-white rounded-lg border border-slate-200 col-span-2 md:col-span-1">
                          <div className="text-[10px] text-slate-400 uppercase font-semibold">Primary Outflow Driver</div>
                          <div className="text-xs font-bold text-slate-800 mt-0.5">
                            {msg.run.dynamic_tool_results.cash_decrease_explanation.top_outflow_drivers?.[0]?.category || "Operating"}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Dynamic Tool 6: GST ITC Status */}
                  {msg.run.dynamic_tool_results?.gst_itc_status && (
                    <div className="p-4 bg-teal-50/50 border border-teal-200 rounded-xl space-y-3">
                      <div className="flex items-center justify-between text-xs font-bold text-teal-900">
                        <span>Input Tax Credit (ITC) Summary ({msg.run.dynamic_tool_results.gst_itc_status.period})</span>
                        <span className="text-teal-700 text-[10px] font-mono">Section 16 &amp; 17(5)</span>
                      </div>
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div className="p-3 bg-white rounded-lg border border-teal-100">
                          <div className="text-[10px] text-teal-600 font-bold uppercase">Section 16(1) Eligible ITC</div>
                          <div className="text-base font-extrabold text-teal-900 mt-0.5">
                            ₹{msg.run.dynamic_tool_results.gst_itc_status.eligible_itc?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                          </div>
                          <div className="text-[10px] text-slate-500 mt-0.5">Reflected in GSTR-2B</div>
                        </div>
                        <div className="p-3 bg-white rounded-lg border border-rose-100">
                          <div className="text-[10px] text-rose-600 font-bold uppercase">Section 17(5) Blocked Credit</div>
                          <div className="text-base font-extrabold text-rose-900 mt-0.5">
                            ₹{msg.run.dynamic_tool_results.gst_itc_status.blocked_itc?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                          </div>
                          <div className="text-[10px] text-slate-500 mt-0.5">Food, vehicles, personal</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Dynamic Tool 7: Financial Summary Export Ready */}
                  {msg.run.dynamic_tool_results?.financial_summary_export && (
                    <div className="p-4 bg-emerald-50/50 border border-emerald-200 rounded-xl space-y-3">
                      <div className="flex items-center justify-between text-xs font-bold text-emerald-950">
                        <span>Monthly Financial Operations Export Package</span>
                        <button
                          type="button"
                          onClick={() => {
                            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(msg.run?.dynamic_tool_results.financial_summary_export.report, null, 2));
                            const downloadAnchor = document.createElement("a");
                            downloadAnchor.setAttribute("href", dataStr);
                            downloadAnchor.setAttribute("download", `financial_summary_${selectedPeriod}.json`);
                            document.body.appendChild(downloadAnchor);
                            downloadAnchor.click();
                            downloadAnchor.remove();
                          }}
                          className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1 cursor-pointer transition-colors"
                        >
                          <Download className="w-3.5 h-3.5" />
                          Download JSON Export
                        </button>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div className="p-2.5 bg-white rounded-lg border border-emerald-100 text-center">
                          <div className="text-[10px] text-slate-400 uppercase font-semibold">Net Profit</div>
                          <div className="text-sm font-extrabold text-emerald-700 mt-0.5">
                            ₹{msg.run.dynamic_tool_results.financial_summary_export.report?.profit_and_loss?.net_profit || "0.00"}
                          </div>
                        </div>
                        <div className="p-2.5 bg-white rounded-lg border border-emerald-100 text-center">
                          <div className="text-[10px] text-slate-400 uppercase font-semibold">Net GST Payable</div>
                          <div className="text-sm font-extrabold text-slate-800 mt-0.5">
                            ₹{msg.run.dynamic_tool_results.financial_summary_export.report?.gst_summary?.net_cash_payable || "0.00"}
                          </div>
                        </div>
                        <div className="p-2.5 bg-white rounded-lg border border-emerald-100 text-center">
                          <div className="text-[10px] text-slate-400 uppercase font-semibold">Trial Balance</div>
                          <div className="text-sm font-extrabold text-emerald-600 mt-0.5">Balanced ✓</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Dynamic Execution DAG Dropdown */}
                  {msg.run.execution_plan && msg.run.execution_plan.length > 0 && (
                    <div className="border border-slate-200 rounded-xl overflow-hidden mt-2 bg-slate-50/50">
                      <button
                        type="button"
                        onClick={() => toggleDag(msg.id)}
                        className="w-full px-4 py-2 bg-slate-100/80 hover:bg-slate-100 flex items-center justify-between text-xs font-bold text-slate-700 cursor-pointer"
                      >
                        <span className="flex items-center gap-1.5">
                          <Layers className="w-3.5 h-3.5 text-indigo-600" />
                          Dynamic Execution Plan ({msg.run.execution_plan.length} Steps)
                        </span>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            msg.run.status === "COMPLETED"
                              ? "bg-emerald-100 text-emerald-800"
                              : msg.run.status === "WAITING_APPROVAL"
                              ? "bg-amber-100 text-amber-800"
                              : "bg-blue-100 text-blue-800"
                          }`}>
                            {msg.run.status}
                          </span>
                          {expandedDags[msg.id] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </div>
                      </button>

                      {expandedDags[msg.id] && (
                        <div className="p-3 grid grid-cols-1 md:grid-cols-2 gap-2 bg-white">
                          {msg.run.execution_plan.map((step, sIdx) => (
                            <div
                              key={sIdx}
                              className={`p-2.5 rounded-lg border text-xs ${
                                step.status === "COMPLETED"
                                  ? "bg-emerald-50/40 border-emerald-200"
                                  : step.status === "WAITING_APPROVAL"
                                  ? "bg-amber-50/60 border-amber-300"
                                  : "bg-slate-50 border-slate-200"
                              }`}
                            >
                              <div className="flex items-center justify-between text-[11px] font-bold text-slate-600">
                                <span>Step {step.step}: {step.title}</span>
                                {step.status === "COMPLETED" && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}
                                {step.status === "WAITING_APPROVAL" && <Clock className="w-3.5 h-3.5 text-amber-600 animate-pulse" />}
                              </div>
                              <div className="text-[10px] text-indigo-600 font-semibold mt-0.5">{step.agent}</div>
                              {step.details && <div className="text-[11px] text-slate-500 mt-1 leading-snug">{step.details}</div>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Approval Checkpoint Card (For Consequential Financial Mutations) */}
                  {msg.run.status === "WAITING_APPROVAL" && msg.run.approval_summary && (
                    <div className="bg-amber-50/80 border-2 border-amber-300 rounded-2xl p-5 shadow-sm space-y-4 mt-3">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center gap-2">
                          <ShieldCheck className="w-5 h-5 text-amber-800" />
                          <h3 className="font-bold text-slate-900 text-sm">
                            Consolidated Merchant Approval Checkpoint
                          </h3>
                        </div>
                        <button
                          type="button"
                          onClick={handleApprove}
                          disabled={isApproving}
                          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl flex items-center gap-1.5 transition-colors shadow-sm disabled:bg-slate-300 cursor-pointer"
                        >
                          {isApproving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                          Approve &amp; Post to Ledger
                        </button>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                        <div className="p-2.5 bg-white rounded-lg border border-amber-200">
                          <div className="text-[10px] text-slate-500 font-semibold">Proposed Transactions</div>
                          <div className="text-base font-extrabold text-slate-900 mt-0.5">
                            {msg.run.approval_summary.proposed_transactions_count || 0}
                          </div>
                        </div>
                        <div className="p-2.5 bg-white rounded-lg border border-amber-200">
                          <div className="text-[10px] text-slate-500 font-semibold">Reconciled Pairs</div>
                          <div className="text-base font-extrabold text-emerald-800 mt-0.5">
                            {msg.run.approval_summary.reconciled_pairs_count || 0}
                          </div>
                        </div>
                        <div className="p-2.5 bg-white rounded-lg border border-amber-200">
                          <div className="text-[10px] text-slate-500 font-semibold">Audit Flags</div>
                          <div className="text-base font-extrabold text-amber-900 mt-0.5">
                            {msg.run.approval_summary.audit_anomalies_count || 0}
                          </div>
                        </div>
                        <div className="p-2.5 bg-white rounded-lg border border-amber-200">
                          <div className="text-[10px] text-slate-500 font-semibold">Net GST Cash</div>
                          <div className="text-base font-extrabold text-emerald-600 mt-0.5">
                            ₹{msg.run.approval_summary.net_gst_payable || "0.00"}
                          </div>
                        </div>
                      </div>

                      {/* Proposed Transactions Table */}
                      {msg.run.proposed_transactions && msg.run.proposed_transactions.length > 0 && (
                        <div className="border border-slate-200 rounded-xl overflow-hidden bg-white mt-2">
                          <div className="bg-slate-50 px-4 py-1.5 text-xs font-bold text-slate-700 border-b border-slate-200">
                            Proposed Ledger Vouchers
                          </div>
                          <div className="max-h-48 overflow-y-auto">
                            <table className="w-full text-xs text-left">
                              <thead className="bg-slate-50/50 text-slate-500 text-[10px] uppercase">
                                <tr>
                                  <th className="px-3 py-1.5">Date</th>
                                  <th className="px-3 py-1.5">Narration</th>
                                  <th className="px-3 py-1.5">Counterparty</th>
                                  <th className="px-3 py-1.5">Category</th>
                                  <th className="px-3 py-1.5">Type</th>
                                  <th className="px-3 py-1.5 text-right">Amount (₹)</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100">
                                {msg.run.proposed_transactions.map((tx: any, idx: number) => (
                                  <tr key={idx} className="hover:bg-slate-50">
                                    <td className="px-3 py-1.5 text-slate-600">{tx.transaction_date}</td>
                                    <td className="px-3 py-1.5 text-slate-800 font-medium truncate max-w-xs">{tx.description}</td>
                                    <td className="px-3 py-1.5 text-slate-700">{tx.counterparty_name || "-"}</td>
                                    <td className="px-3 py-1.5 text-slate-600">{tx.category}</td>
                                    <td className="px-3 py-1.5">
                                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                        tx.type === "DEBIT" ? "bg-rose-100 text-rose-700" : "bg-emerald-100 text-emerald-700"
                                      }`}>
                                        {tx.type}
                                      </span>
                                    </td>
                                    <td className="px-3 py-1.5 text-right font-bold text-slate-900">
                                      ₹{Number(tx.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {msg.sender === "user" && (
              <div className="w-8 h-8 rounded-xl bg-slate-800 text-white flex items-center justify-center flex-shrink-0 shadow-sm">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3.5 items-center text-slate-500 text-xs italic">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center flex-shrink-0 animate-pulse">
              <Bot className="w-4 h-4" />
            </div>
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
              <span>Analyzing instruction &amp; dispatching specialized agents...</span>
            </div>
          </div>
        )}

        <div ref={chatBottomRef} />
      </div>

      {/* Missing Information Clarification Bar */}
      {currentRun?.clarification_question && currentRun.status === "WAITING_APPROVAL" && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 shadow-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-amber-700 flex-shrink-0" />
          <div className="flex-1">
            <span className="text-xs font-bold text-amber-900">Clarification Needed: </span>
            <span className="text-xs text-amber-800">{currentRun.clarification_question}</span>
            <div className="flex gap-2 mt-2">
              <input
                type="text"
                value={clarificationInput}
                onChange={(e) => setClarificationInput(e.target.value)}
                placeholder="Type clarification here... e.g. '₹15,000 to Sharma Enterprises'"
                className="flex-1 px-3 py-1.5 text-xs border border-amber-300 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-amber-500"
                onKeyDown={(e) => e.key === "Enter" && handleClarificationSubmit()}
              />
              <button
                type="button"
                onClick={handleClarificationSubmit}
                className="px-4 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs rounded-xl cursor-pointer"
              >
                Submit Answer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Voice Status & Error Banners */}
      {isListening && (
        <div className="px-4 py-2.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center justify-between animate-pulse">
          <div className="flex items-center gap-2 font-bold">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-600 animate-ping" />
            <span>
              Listening in {cmdLanguage === "hi" ? "Hindi (हिन्दी)" : "Indian English"}... Speak your instruction now!
            </span>
          </div>
          <button
            type="button"
            onClick={toggleListening}
            className="text-xs font-bold text-rose-700 hover:text-rose-900 underline cursor-pointer"
          >
            Done Speaking
          </button>
        </div>
      )}

      {speechError && (
        <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl text-xs flex items-center justify-between">
          <span>{speechError}</span>
          <button onClick={() => setSpeechError(null)} className="text-amber-600 hover:text-amber-800 font-bold ml-2">
            Dismiss
          </button>
        </div>
      )}

      {/* Bottom Conversational Input Console */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 space-y-3">
        <div className="relative">
          <textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleExecute();
              }
            }}
            placeholder={
              cmdLanguage === "hi"
                ? "निर्देश यहाँ लिखें या बोलें... जैसे 'Show top 5 vendors' ya 'Sharma ji ko kitna payment kiya pichhle mahine?'"
                : "Type or speak any financial request... e.g. 'Show me the five vendors I paid the most this quarter' or 'Compare my October expenses with September'"
            }
            rows={2}
            className="w-full rounded-xl border border-slate-300 p-3 pr-24 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent resize-none"
          />

          <div className="absolute right-3 bottom-3 flex items-center gap-2">
            {/* Attachment Button */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              multiple
              accept=".csv,.xlsx,.xls,.pdf,image/*"
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors cursor-pointer"
              title="Attach statement CSV, Excel, PDF or receipts"
            >
              <Paperclip className="w-5 h-5" />
            </button>

            {/* Microphone Toggle */}
            <button
              type="button"
              onClick={toggleListening}
              className={`p-2 rounded-lg transition-all cursor-pointer ${
                isListening
                  ? "bg-rose-500 text-white animate-pulse"
                  : "text-slate-500 hover:text-slate-800 hover:bg-slate-100"
              }`}
              title={isListening ? "Listening... click to stop" : "Speak instruction in Hindi or English"}
            >
              {isListening ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
            </button>

            {/* Send Button */}
            <button
              type="button"
              onClick={() => handleExecute()}
              disabled={isLoading || (!instruction && attachedFiles.length === 0)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white font-semibold text-xs rounded-xl flex items-center gap-1.5 transition-colors shadow-sm cursor-pointer"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Send</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Attached Files List */}
        {attachedFiles.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {attachedFiles.map((f, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-100 border border-slate-200 text-slate-700 rounded-lg text-xs font-medium"
              >
                <FileText className="w-3.5 h-3.5 text-indigo-500" />
                {f.name} ({(f.size / 1024).toFixed(0)} KB)
                <button
                  type="button"
                  onClick={() => removeFile(idx)}
                  className="text-slate-400 hover:text-rose-500 ml-1 cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Past Autonomous Operations Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-slate-600" />
            <h2 className="font-bold text-slate-800 text-base">Past Autonomous Operations</h2>
          </div>
          <button
            type="button"
            onClick={loadPastRuns}
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Refresh Runs
          </button>
        </div>

        {pastRuns.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-400">
            No autonomous command runs recorded yet. Issue your first instruction above.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-500 text-[10px] uppercase border-y border-slate-200">
                <tr>
                  <th className="px-4 py-2.5">Run ID</th>
                  <th className="px-4 py-2.5">Instruction</th>
                  <th className="px-4 py-2.5">Workflow / Intent</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Created At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pastRuns.map((r, i) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono text-[11px] text-slate-600">{r.run_id}</td>
                    <td className="px-4 py-3 font-medium text-slate-800 max-w-xs truncate">
                      {r.input_payload?.instruction || "Multi-document batch"}
                    </td>
                    <td className="px-4 py-3 text-indigo-600 font-semibold">{r.current_node || r.workflow_name}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          r.status === "COMPLETED"
                            ? "bg-emerald-100 text-emerald-800"
                            : r.status === "WAITING_APPROVAL"
                            ? "bg-amber-100 text-amber-800"
                            : r.status === "FAILED"
                            ? "bg-rose-100 text-rose-800"
                            : "bg-blue-100 text-blue-800 animate-pulse"
                        }`}
                      >
                        {r.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-[11px]">
                      {r.created_at ? new Date(r.created_at).toLocaleString() : "-"}
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
