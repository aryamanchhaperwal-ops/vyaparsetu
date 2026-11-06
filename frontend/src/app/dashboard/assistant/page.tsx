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
  Scale
} from "lucide-react";
import { api } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";
import { useVoiceAssistant } from "@/lib/useVoiceAssistant";

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  intent?: string;
  intentLabel?: string;
  sources?: { section: string; title: string; excerpt?: string }[];
  timestamp: string;
}

const INTENT_BADGES: Record<string, { label: string; bg: string; text: string; icon: any }> = {
  CONVERSATION: { label: "General Conversation", bg: "bg-emerald-100", text: "text-emerald-800", icon: MessageSquare },
  BUSINESS_QUERY: { label: "Business Workspace Data", bg: "bg-blue-100", text: "text-blue-800", icon: Database },
  ANALYTICS_INSIGHTS: { label: "Financial Analytics", bg: "bg-purple-100", text: "text-purple-800", icon: TrendingUp },
  ACCOUNTING_GUIDANCE: { label: "Accounting Principles", bg: "bg-amber-100", text: "text-amber-800", icon: Scale },
  GST_RAG: { label: "GST Statutory RAG", bg: "bg-teal-100", text: "text-teal-800", icon: ShieldCheck },
};

export default function AssistantPage() {
  const { t } = useLanguage();

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "assistant",
      text: "Namaste! I am VyaparSetu's Conversational AI Financial Assistant, powered by BharatCode Qwen 3.8 27B.\n\nYou can ask me general questions, enquire about your real tenant business spend & bank balance, learn double-entry accounting principles, or ask for statutory Indian GST provisions with exact citations.",
      intent: "CONVERSATION",
      intentLabel: "General Conversation",
      timestamp: "Just now",
    },
  ]);

  const [inputQuery, setInputQuery] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState("Hinglish");
  const [asking, setAsking] = useState(false);
  const [activeSpeakingMsgId, setActiveSpeakingMsgId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  const samplePromptGroups = [
    {
      category: "Conversational",
      text: "Namaste, how can you help my business?",
    },
    {
      category: "Business Data",
      text: "What is my total spend and current bank balance?",
    },
    {
      category: "Suppliers",
      text: "Who are my top vendors by outflow volume?",
    },
    {
      category: "GST Law",
      text: "What are the 4 mandatory conditions to claim ITC under Section 16(2)?",
    },
    {
      category: "Blocked Credits",
      text: "Can I claim ITC on motor cars purchased for business under Section 17(5)?",
    },
    {
      category: "Accounting",
      text: "Explain the three golden rules of double-entry accounting.",
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
        sources: (res.citations || res.retrieved_statutes || []).map((s: any) => ({
          section: s.citation || s.section || s.id,
          title: s.title,
          excerpt: s.excerpt || (s.content ? s.content.slice(0, 180) + "..." : undefined),
        })),
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
            {t("assistant")} — Conversational AI Financial Assistant
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Intent-routed conversational intelligence: greetings, tenant business telemetry, double-entry principles, and statutory GST RAG.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-1.5 bg-white border border-slate-300 rounded-xl px-3 py-1.5 shadow-sm text-xs">
            <Globe2 className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={selectedLanguage}
              onChange={(e) => {
                setSelectedLanguage(e.target.value);
                voice.setSelectedLanguage(e.target.value === "Hindi" ? "hi-IN" : "en-IN");
              }}
              className="bg-transparent focus:outline-none font-semibold text-slate-700"
            >
              <option value="Hinglish">Hinglish (Hindi + English)</option>
              <option value="Hindi">हिंदी (Hindi Voice &amp; Text)</option>
              <option value="English">Indian English</option>
            </select>
          </div>
        </div>
      </div>

      {/* Suggested Quick Prompt Chips */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-2">
        <span className="text-[11px] font-bold uppercase text-slate-500 tracking-wider">
          Suggested Inquiries Across Financial Domains:
        </span>
        <div className="flex flex-wrap gap-2">
          {samplePromptGroups.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSend(p.text)}
              disabled={asking}
              className="text-xs px-3 py-1.5 bg-slate-50 hover:bg-emerald-50 hover:text-emerald-800 hover:border-emerald-300 border border-slate-200 rounded-xl text-slate-700 transition flex items-center gap-1.5 text-left font-medium"
            >
              <span className="text-[10px] uppercase font-bold text-slate-400">[{p.category}]</span>
              <span>{p.text}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Stream Container */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[600px]">
        {/* Messages Stream */}
        <div className="flex-1 p-5 overflow-y-auto space-y-4">
          {messages.map((m) => {
            const badgeCfg = m.intent ? INTENT_BADGES[m.intent] : null;
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
                      : "bg-slate-50 text-slate-900 border border-slate-200 rounded-bl-none shadow-sm"
                  }`}
                >
                  {/* Intent Tag & Text-to-Speech Button on Assistant Messages */}
                  {m.sender === "assistant" && (
                    <div className="flex items-center justify-between gap-2 border-b border-slate-200/80 pb-2 mb-2.5">
                      {badgeCfg && (
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${badgeCfg.bg} ${badgeCfg.text}`}
                        >
                          <badgeCfg.icon className="w-3 h-3" />
                          <span>{m.intentLabel || badgeCfg.label}</span>
                        </span>
                      )}
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

                  {/* Statutory Citations Card (if GST RAG) */}
                  {m.sources && m.sources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-200/80 space-y-1.5">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                        <BookOpen className="w-3.5 h-3.5 text-emerald-600" />
                        Official Statutory Authority Cited:
                      </span>
                      <div className="space-y-1">
                        {m.sources.map((s, idx) => (
                          <div key={idx} className="bg-white p-2 rounded-lg border border-slate-200 text-xs shadow-2xs">
                            <strong className="text-slate-800">{s.section}</strong>: {s.title}
                            {s.excerpt && (
                              <p className="text-[11px] text-slate-500 mt-0.5 italic">"{s.excerpt}"</p>
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
              <span>Analyzing intent &amp; querying database / BharatCode engine...</span>
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
              className={`p-2.5 rounded-xl border transition shadow-sm ${
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
              placeholder="Ask anything or click microphone (e.g., 'What is my total spend?', 'Section 16(2) ITC conditions')..."
              className="flex-1 px-4 py-2.5 text-sm bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 shadow-sm text-slate-900"
              disabled={asking}
            />

            <button
              type="submit"
              disabled={asking || !inputQuery.trim()}
              className="p-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-md shadow-emerald-600/20 transition disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
