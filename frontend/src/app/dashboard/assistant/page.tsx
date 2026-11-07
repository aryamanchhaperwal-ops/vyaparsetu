"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  BotMessageSquare,
  Send,
  Sparkles,
  BookOpen,
  ShieldCheck,
  CheckCircle2,
  HelpCircle,
  ExternalLink,
  MessageSquare,
  Globe2,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Database,
  TrendingUp,
  Receipt,
  Scale,
  GitFork,
  FileText,
  Search,
  Upload,
  Trash2,
  Layers,
  ArrowRight,
  AlertCircle,
  Network
} from "lucide-react";
import { api } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";
import { useVoiceAssistant } from "@/lib/useVoiceAssistant";

interface CitationItem {
  source?: string;
  section?: string;
  document_type?: string;
  legal_title?: string;
  title?: string;
  excerpt?: string;
  snippet?: string;
  score?: number;
}

interface GraphEntityItem {
  entity?: string;
  name?: string;
  type?: string;
  id?: string;
  details?: any;
  label?: string;
}

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  intent?: string;
  intentLabel?: string;
  strategyUsed?: string;
  confidenceScore?: number;
  sources?: CitationItem[];
  graphEntities?: GraphEntityItem[];
  timestamp: string;
}

const STRATEGY_CONFIG: Record<string, { label: string; bg: string; text: string; icon: any }> = {
  HYBRID_GRAPH_VECTOR: { label: "Hybrid Graph + Vector RAG", bg: "bg-purple-100", text: "text-purple-800", icon: Sparkles },
  GRAPH_SEARCH: { label: "Relational Knowledge Graph RAG", bg: "bg-indigo-100", text: "text-indigo-800", icon: GitFork },
  DOCUMENT_SEARCH: { label: "ChromaDB + BM25 Hybrid Retrieval", bg: "bg-blue-100", text: "text-blue-800", icon: FileText },
  RECONCILIATION_SEARCH: { label: "Reconciliation Audit Trail RAG", bg: "bg-amber-100", text: "text-amber-800", icon: Scale },
  STATUTORY_SEARCH: { label: "Statutory Indian GST Corpus RAG", bg: "bg-teal-100", text: "text-teal-800", icon: ShieldCheck },
  CONVERSATION: { label: "General Conversation", bg: "bg-emerald-100", text: "text-emerald-800", icon: MessageSquare },
  BUSINESS_QUERY: { label: "Deterministic SQL Query", bg: "bg-cyan-100", text: "text-cyan-800", icon: Database },
  ANALYTICS_INSIGHTS: { label: "Financial Analytics Engine", bg: "bg-violet-100", text: "text-violet-800", icon: TrendingUp },
  ACCOUNTING_GUIDANCE: { label: "Accounting Principles KB", bg: "bg-amber-100", text: "text-amber-800", icon: BookOpen },
  GST_RAG: { label: "GST Legal Authority RAG", bg: "bg-teal-100", text: "text-teal-800", icon: ShieldCheck },
};

export default function AssistantPage() {
  const { t } = useLanguage();

  const [activeTab, setActiveTab] = useState<"chat" | "rag_inspector">("chat");

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "assistant",
      text: "Namaste! I am Lekha's Conversational AI Financial Assistant, powered by BharatCode Qwen 3.8 27B and Multi-Strategy Graph + Vector RAG.\n\nYou can query tenant spend & bank balances, trace vendor invoices & payment trails through the knowledge graph, locate indexed contract/statement chunks in ChromaDB, or obtain legally grounded statutory GST interpretations under the CGST/IGST Acts.",
      strategyUsed: "HYBRID_GRAPH_VECTOR",
      confidenceScore: 0.95,
      timestamp: "Just now",
    },
  ]);

  const [inputQuery, setInputQuery] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState("Hinglish");
  const [asking, setAsking] = useState(false);
  const [activeSpeakingMsgId, setActiveSpeakingMsgId] = useState<string | null>(null);

  // RAG Document Storage State
  const [ragDocuments, setRagDocuments] = useState<any[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [selectedDocType, setSelectedDocType] = useState("INVOICE");
  const [graphTrailQuery, setGraphTrailQuery] = useState("Goyal Hardware");
  const [graphTrailType, setGraphTrailType] = useState<"vendor" | "reconciliation">("vendor");
  const [graphTrailResult, setGraphTrailResult] = useState<any | null>(null);
  const [loadingTrail, setLoadingTrail] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Voice Assistant Integration
  const voice = useVoiceAssistant(selectedLanguage === "Hindi" ? "hi-IN" : "en-IN");

  useEffect(() => {
    if (voice.transcript) {
      setInputQuery(voice.transcript);
    }
  }, [voice.transcript]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, asking]);

  useEffect(() => {
    if (activeTab === "rag_inspector") {
      fetchRagDocuments();
    }
  }, [activeTab]);

  const fetchRagDocuments = async () => {
    setLoadingDocs(true);
    try {
      const res = await api.getRAGDocuments();
      setRagDocuments(res.documents || []);
    } catch (e) {
      console.error("Failed to load RAG documents", e);
    } finally {
      setLoadingDocs(false);
    }
  };

  const handleDocumentUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingDoc(true);
    try {
      await api.uploadRAGDocument(file, selectedDocType);
      await fetchRagDocuments();
    } catch (err: any) {
      alert(`Upload failed: ${err.message || "Failed to index document"}`);
    } finally {
      setUploadingDoc(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!confirm("Are you sure you want to remove this document and its embeddings from the vector store?")) return;
    try {
      await api.deleteRAGDocument(docId);
      await fetchRagDocuments();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleFetchGraphTrail = async () => {
    if (!graphTrailQuery.trim()) return;
    setLoadingTrail(true);
    try {
      const res = await api.getGraphTrail(graphTrailQuery, graphTrailType);
      setGraphTrailResult(res);
    } catch (err: any) {
      alert(`Graph trail error: ${err.message}`);
    } finally {
      setLoadingTrail(false);
    }
  };

  const samplePromptGroups = [
    {
      category: "Document RAG",
      text: "Find the electricity invoice from October",
    },
    {
      category: "Graph RAG",
      text: "Which payments belong to this vendor?",
    },
    {
      category: "Audit Trail",
      text: "Why does this bank transaction remain unreconciled?",
    },
    {
      category: "Statutory Law",
      text: "What are the 4 mandatory conditions to claim ITC under Section 16(2)?",
    },
    {
      category: "Blocked Credits",
      text: "Can I claim ITC on motor cars purchased for business under Section 17(5)?",
    },
    {
      category: "Business Data",
      text: "What is my total spend and current bank balance?",
    },
    {
      category: "Cash Flow",
      text: "How is my 30-day forward cash flow and runway looking?",
    },
  ];

  const handleSend = async (queryText?: string) => {
    const q = (queryText || inputQuery).trim();
    if (!q) return;

    if (voice.isListening) {
      voice.stopListening();
    }
    voice.clearTranscript();

    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      sender: "user",
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery("");
    setAsking(true);

    try {
      const res = await api.askAssistant(q, selectedLanguage);

      const assistantMsg: ChatMessage = {
        id: `ast_${Date.now()}`,
        sender: "assistant",
        text: res.answer,
        intent: res.intent,
        intentLabel: res.intent_label,
        strategyUsed: res.strategy_used || (res.intent === "GST_RAG" ? "STATUTORY_SEARCH" : res.intent),
        confidenceScore: res.confidence_score !== undefined ? res.confidence_score : 0.85,
        sources: (res.citations || res.retrieved_statutes || []).map((s: any) => ({
          section: s.section || s.citation || s.id || "REFERENCE",
          title: s.legal_title || s.title || s.source || "Evidence Source",
          source: s.source,
          document_type: s.document_type,
          excerpt: s.snippet || s.excerpt || (s.content ? s.content.slice(0, 180) + "..." : undefined),
        })),
        graphEntities: res.graph_entities || [],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        sender: "assistant",
        text: `Error contacting BharatCode Assistant: ${err.message || "Unknown error"}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setAsking(false);
    }
  };

  const handleToggleSpeak = (msgId: string, text: string) => {
    if (voice.isSpeaking && activeSpeakingMsgId === msgId) {
      voice.stopSpeaking();
      setActiveSpeakingMsgId(null);
    } else {
      voice.speak(text, selectedLanguage === "Hindi" ? "hi-IN" : "en-IN");
      setActiveSpeakingMsgId(msgId);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BotMessageSquare className="w-7 h-7 text-emerald-600" />
            {t("assistant")} — Multi-Strategy Financial RAG Assistant
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Grounded intelligence across ChromaDB vector store, BM25 keyword index, relational knowledge graphs, and Indian GST statutes.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Sub-tab Navigation */}
          <div className="bg-slate-100 p-1 rounded-xl flex items-center text-xs font-semibold">
            <button
              onClick={() => setActiveTab("chat")}
              className={`px-3 py-1.5 rounded-lg transition ${
                activeTab === "chat" ? "bg-white text-emerald-700 shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Conversational Chat
            </button>
            <button
              onClick={() => setActiveTab("rag_inspector")}
              className={`px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 ${
                activeTab === "rag_inspector" ? "bg-white text-indigo-700 shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              ChromaDB &amp; Graph RAG Hub
            </button>
          </div>

          <div className="flex items-center gap-1.5 bg-white border border-slate-300 rounded-xl px-3 py-1.5 shadow-xs text-xs">
            <Globe2 className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={selectedLanguage}
              onChange={(e) => {
                setSelectedLanguage(e.target.value);
                voice.setSelectedLanguage(e.target.value === "Hindi" ? "hi-IN" : "en-IN");
              }}
              className="bg-transparent focus:outline-none font-semibold text-slate-700 cursor-pointer"
            >
              <option value="Hinglish">Hinglish (Hindi + English)</option>
              <option value="Hindi">हिंदी (Hindi Voice &amp; Text)</option>
              <option value="English">Indian English</option>
            </select>
          </div>
        </div>
      </div>

      {activeTab === "chat" ? (
        <>
          {/* Suggested Quick Prompt Chips */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-2">
            <span className="text-[11px] font-bold uppercase text-slate-500 tracking-wider">
              Explore RAG Capabilities Across Multi-Strategy Engines:
            </span>
            <div className="flex flex-wrap gap-2">
              {samplePromptGroups.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSend(p.text)}
                  disabled={asking}
                  className="text-xs px-3 py-1.5 bg-slate-50 hover:bg-emerald-50 hover:text-emerald-800 hover:border-emerald-300 border border-slate-200 rounded-xl text-slate-700 transition flex items-center gap-1.5 text-left font-medium cursor-pointer"
                >
                  <span className="text-[10px] uppercase font-bold text-slate-400">[{p.category}]</span>
                  <span>{p.text}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Main Chat Stream Container */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden flex flex-col h-[600px]">
            {/* Messages Stream */}
            <div className="flex-1 p-5 overflow-y-auto space-y-4">
              {messages.map((m) => {
                const stratCfg = m.strategyUsed ? STRATEGY_CONFIG[m.strategyUsed] : (m.intent ? STRATEGY_CONFIG[m.intent] : null);
                const isSpeakingThis = voice.isSpeaking && activeSpeakingMsgId === m.id;

                return (
                  <div
                    key={m.id}
                    className={`flex flex-col ${m.sender === "user" ? "items-end" : "items-start"}`}
                  >
                    <div
                      className={`max-w-2xl rounded-2xl p-4 text-sm leading-relaxed ${
                        m.sender === "user"
                          ? "bg-emerald-600 text-white rounded-br-none shadow-md shadow-emerald-600/10"
                          : "bg-slate-50 text-slate-900 border border-slate-200 rounded-bl-none shadow-xs"
                      }`}
                    >
                      {/* Strategy Badge, Confidence Meter & Audio Playback on Assistant Messages */}
                      {m.sender === "assistant" && (
                        <div className="flex items-center justify-between gap-2 border-b border-slate-200/80 pb-2 mb-2.5">
                          <div className="flex items-center gap-2 flex-wrap">
                            {stratCfg && (
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${stratCfg.bg} ${stratCfg.text}`}
                              >
                                <stratCfg.icon className="w-3 h-3" />
                                <span>{stratCfg.label}</span>
                              </span>
                            )}
                            {m.confidenceScore !== undefined && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-semibold">
                                <CheckCircle2 className="w-2.5 h-2.5" />
                                {(m.confidenceScore * 100).toFixed(0)}% Grounded
                              </span>
                            )}
                          </div>

                          <button
                            onClick={() => handleToggleSpeak(m.id, m.text)}
                            className={`p-1.5 rounded-lg border transition ${
                              isSpeakingThis
                                ? "bg-emerald-100 border-emerald-300 text-emerald-800"
                                : "bg-white border-slate-200 text-slate-500 hover:text-slate-800"
                            }`}
                            title={isSpeakingThis ? "Stop Voice Playback" : "Listen in Hindi/English"}
                          >
                            {isSpeakingThis ? (
                              <VolumeX className="w-3.5 h-3.5 animate-pulse text-emerald-700" />
                            ) : (
                              <Volume2 className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      )}

                      <div className="whitespace-pre-wrap">{m.text}</div>

                      {/* Graph Entities Relationship Card */}
                      {m.graphEntities && m.graphEntities.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-slate-200/80 space-y-1.5">
                          <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-700 flex items-center gap-1">
                            <Network className="w-3.5 h-3.5" />
                            Linked Knowledge Graph Entities:
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {m.graphEntities.map((ent, idx) => (
                              <span
                                key={idx}
                                className="inline-flex items-center gap-1 px-2 py-1 bg-indigo-50 border border-indigo-200 text-indigo-800 rounded-lg text-xs font-medium"
                              >
                                <span className="text-[10px] font-bold text-indigo-500 uppercase">{ent.type || "ENTITY"}:</span>
                                <span>{ent.name || ent.entity || ent.id}</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Citations Card */}
                      {m.sources && m.sources.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-slate-200/80 space-y-1.5">
                          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1">
                            <BookOpen className="w-3.5 h-3.5 text-emerald-600" />
                            Verified Evidence Citations &amp; Statutory Authority Cited:
                          </span>
                          <div className="space-y-1.5">
                            {m.sources.map((s, idx) => (
                              <div key={idx} className="bg-white p-2.5 rounded-xl border border-slate-200 text-xs shadow-2xs">
                                <div className="flex items-center justify-between text-slate-800 font-bold">
                                  <span>{s.title || s.source || s.section}</span>
                                  {s.document_type && (
                                    <span className="px-1.5 py-0.2 bg-slate-100 text-slate-500 rounded text-[9px] uppercase font-mono">
                                      {s.document_type}
                                    </span>
                                  )}
                                </div>
                                {s.excerpt && (
                                  <p className="text-[11px] text-slate-600 mt-1 italic leading-snug">
                                    &ldquo;{s.excerpt}&rdquo;
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    <span className="text-[10px] text-slate-400 mt-1 px-1">{m.timestamp}</span>
                  </div>
                );
              })}

              {asking && (
                <div className="flex items-center gap-2 text-slate-500 text-xs p-3 bg-slate-50 rounded-xl border border-slate-200 w-fit">
                  <div className="w-4 h-4 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
                  <span>Executing Multi-Strategy RAG &amp; BharatCode inference...</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Live Voice Recording Status Banner */}
            {voice.isListening && (
              <div className="px-4 py-2.5 bg-rose-50 border-t border-rose-200 text-rose-800 text-xs flex items-center justify-between animate-pulse">
                <div className="flex items-center gap-2 font-bold">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-600 animate-ping" />
                  <span>
                    Listening in {voice.selectedLanguage === "hi-IN" ? "Hindi (हिंदी)" : "Indian English"}... Speak now!
                  </span>
                </div>
                <button
                  onClick={voice.stopListening}
                  className="text-xs font-bold text-rose-700 hover:text-rose-900 underline"
                >
                  Stop Microphone
                </button>
              </div>
            )}

            {/* Voice Error Notice */}
            {voice.error && (
              <div className="px-4 py-1.5 bg-amber-50 border-t border-amber-200 text-amber-800 text-[11px]">
                {voice.error}
              </div>
            )}

            {/* Input Bar */}
            <div className="p-3.5 border-t border-slate-200 bg-slate-50">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSend();
                }}
                className="flex items-center gap-2"
              >
                {/* Microphone Voice Button */}
                <button
                  type="button"
                  onClick={() => {
                    if (voice.isListening) {
                      voice.stopListening();
                    } else {
                      voice.startListening();
                    }
                  }}
                  className={`p-2.5 rounded-xl border transition shadow-xs ${
                    voice.isListening
                      ? "bg-rose-600 text-white border-rose-700 animate-pulse"
                      : "bg-white text-slate-700 border-slate-300 hover:bg-slate-100"
                  }`}
                  title={voice.isListening ? "Stop Voice Input" : "Speak your question (Hindi or English)"}
                >
                  {voice.isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4 text-emerald-600" />}
                </button>

                <input
                  type="text"
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  placeholder="Ask anything or click microphone (e.g. 'Which payments belong to this vendor?', 'Find October electricity bill')..."
                  className="flex-1 px-4 py-2.5 text-sm bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 shadow-xs text-slate-900"
                  disabled={asking}
                />

                <button
                  type="submit"
                  disabled={asking || !inputQuery.trim()}
                  className="p-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-md shadow-emerald-600/20 transition disabled:opacity-50 cursor-pointer"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>
          </div>
        </>
      ) : (
        /* ========================================================
           RAG & KNOWLEDGE GRAPH INSPECTOR HUB
           ======================================================== */
        <div className="space-y-6">
          {/* Document Ingestion Card */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Database className="w-5 h-5 text-indigo-600" />
                  ChromaDB Persistent Document Vector Repository
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Tenant-isolated semantic chunk indexing with SHA-256 deduplication and hybrid BM25 lexical support.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <select
                  value={selectedDocType}
                  onChange={(e) => setSelectedDocType(e.target.value)}
                  className="px-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-xl font-semibold text-slate-700"
                >
                  <option value="INVOICE">Vendor Invoice</option>
                  <option value="BANK_STATEMENT">Bank Statement</option>
                  <option value="CONTRACT">Agreement / Contract</option>
                  <option value="TAX_CIRCULAR">Tax Circular</option>
                  <option value="RECEIPT">Expense Receipt</option>
                </select>

                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleDocumentUpload}
                  accept=".pdf,.csv,.xlsx,.xls,.txt"
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadingDoc}
                  className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl flex items-center gap-1.5 transition shadow-xs disabled:opacity-50 cursor-pointer"
                >
                  {uploadingDoc ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Indexing...
                    </>
                  ) : (
                    <>
                      <Upload className="w-3.5 h-3.5" />
                      Index Document
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Document List Table */}
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-500 text-[10px] uppercase font-bold tracking-wider">
                  <tr>
                    <th className="px-4 py-2.5">Document Name</th>
                    <th className="px-4 py-2.5">Type</th>
                    <th className="px-4 py-2.5">Chunks</th>
                    <th className="px-4 py-2.5">Indexed At</th>
                    <th className="px-4 py-2.5">SHA-256 Hash</th>
                    <th className="px-4 py-2.5 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {loadingDocs ? (
                    <tr>
                      <td colSpan={6} className="text-center py-6 text-slate-500">
                        Loading indexed vector documents...
                      </td>
                    </tr>
                  ) : ragDocuments.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center py-6 text-slate-400 italic">
                        No documents indexed for this tenant yet. Click "Index Document" above to upload PDF, CSV, Excel, or TXT statements.
                      </td>
                    </tr>
                  ) : (
                    ragDocuments.map((doc) => (
                      <tr key={doc.doc_id} className="hover:bg-slate-50 transition">
                        <td className="px-4 py-2.5 font-bold text-slate-800 flex items-center gap-1.5">
                          <FileText className="w-4 h-4 text-indigo-500 flex-shrink-0" />
                          <span className="truncate max-w-xs">{doc.filename}</span>
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-semibold">
                            {doc.document_type || "GENERAL"}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 font-mono text-slate-600">{doc.chunk_count}</td>
                        <td className="px-4 py-2.5 text-slate-500 whitespace-nowrap">
                          {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : "Recent"}
                        </td>
                        <td className="px-4 py-2.5 font-mono text-[10px] text-slate-400">
                          {doc.content_hash ? `${doc.content_hash.slice(0, 12)}...` : "-"}
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <button
                            onClick={() => handleDeleteDocument(doc.doc_id)}
                            className="p-1 text-slate-400 hover:text-rose-600 transition"
                            title="Delete from Vector Store"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Graph RAG Trail Explorer */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Network className="w-5 h-5 text-indigo-600" />
                Knowledge Graph Trail &amp; Reconciliation Auditor
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Explore multi-hop entity traversal: Business &rarr; Vendor &rarr; Invoice &rarr; Payment &rarr; Bank Transaction &rarr; Ledger Entry &rarr; Tax Record.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-2">
              <select
                value={graphTrailType}
                onChange={(e) => setGraphTrailType(e.target.value as any)}
                className="px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl font-semibold text-slate-700"
              >
                <option value="vendor">Vendor Payment Trail</option>
                <option value="reconciliation">Unreconciled Transaction Discrepancy</option>
              </select>

              <input
                type="text"
                value={graphTrailQuery}
                onChange={(e) => setGraphTrailQuery(e.target.value)}
                placeholder="Search vendor name or transaction narration (e.g. 'Goyal Hardware', 'Electricity', 'Sharma')..."
                className="flex-1 px-3 py-2 text-xs bg-white border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />

              <button
                onClick={handleFetchGraphTrail}
                disabled={loadingTrail || !graphTrailQuery.trim()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl flex items-center gap-1.5 transition shadow-xs disabled:opacity-50 cursor-pointer"
              >
                {loadingTrail ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Tracing...
                  </>
                ) : (
                  <>
                    <Search className="w-3.5 h-3.5" />
                    Trace Relational Graph
                  </>
                )}
              </button>
            </div>

            {/* Trail Results Display */}
            {graphTrailResult && (
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800">
                    Trail Result: {graphTrailResult.vendor_name || graphTrailResult.transaction_query || "Relational Path"}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    graphTrailResult.reconciled === true
                      ? "bg-emerald-100 text-emerald-800"
                      : graphTrailResult.reconciled === false
                      ? "bg-amber-100 text-amber-800"
                      : "bg-indigo-100 text-indigo-800"
                  }`}>
                    {graphTrailResult.status || (graphTrailResult.reconciled === false ? "UNRECONCILED" : "VERIFIED")}
                  </span>
                </div>

                {graphTrailResult.trail_narration && (
                  <p className="text-xs text-slate-700 bg-white p-3 rounded-lg border border-slate-200 font-mono">
                    {graphTrailResult.trail_narration}
                  </p>
                )}

                {graphTrailResult.missing_link && (
                  <div className="flex items-start gap-2 p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-xs">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 text-amber-600 mt-0.5" />
                    <div>
                      <span className="font-bold">Audit Recommendation: </span>
                      {graphTrailResult.recommended_action || graphTrailResult.missing_link}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
