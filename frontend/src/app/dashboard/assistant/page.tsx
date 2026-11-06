"use client";

import React, { useState } from "react";
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
  Globe2
} from "lucide-react";
import { api } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  sources?: { section: string; title: string; excerpt?: string }[];
  timestamp: string;
}

export default function AssistantPage() {
  const { t } = useLanguage();

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      sender: "assistant",
      text: "Namaste! I am VyaparSetu's AI GST and Financial Assistant, powered exclusively by the BharatCode hosted LLM. I provide answers grounded directly in official CGST and IGST statutory provisions. How can I help your business today?",
      sources: [
        { section: "Central Goods and Services Tax Act, 2017", title: "Statutory Regulatory Corpus" },
      ],
      timestamp: "Just now",
    },
  ]);

  const [inputQuery, setInputQuery] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState("Hinglish");
  const [asking, setAsking] = useState(false);

  const sampleQuestions = [
    "What are the 4 mandatory conditions to claim Input Tax Credit under Section 16(2)?",
    "Can I claim ITC on motor cars purchased for business under Section 17(5)?",
    "What is the statutory rule for rounding off tax under Section 170?",
    "Kya inter-state supply par CGST aur SGST lagta hai ya IGST?",
    "What is the penalty for late filing of GSTR-3B under Section 47?",
  ];

  const handleSend = async (queryText?: string) => {
    const q = (queryText || inputQuery).trim();
    if (!q) return;

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
        sources: (res.retrieved_statutes || []).map((s: any) => ({
          section: s.section,
          title: s.title,
          excerpt: s.content?.slice(0, 180) + "...",
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

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BotMessageSquare className="w-7 h-7 text-emerald-600" />
            {t("assistant")} — BharatCode RAG Assistant
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Grounded in CGST &amp; IGST statutes. Provides section citations and answers in English, Hindi, and Hinglish.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Globe2 className="w-4 h-4 text-slate-500" />
          <select
            value={selectedLanguage}
            onChange={(e) => setSelectedLanguage(e.target.value)}
            className="text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="Hinglish">Hinglish (Hindi + English)</option>
            <option value="Hindi">हिंदी (Pure Hindi)</option>
            <option value="English">English</option>
          </select>
        </div>
      </div>

      {/* Suggested Questions */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
          Suggested Questions Grounded in Indian Law:
        </span>
        <div className="flex flex-wrap gap-2 mt-2">
          {sampleQuestions.map((sq, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSend(sq)}
              disabled={asking}
              className="text-xs px-3 py-1.5 bg-slate-100 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-300 border border-slate-200 rounded-lg text-slate-700 transition text-left"
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Container */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[580px]">
        {/* Messages Stream */}
        <div className="flex-1 p-5 overflow-y-auto space-y-4">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex flex-col ${m.sender === "user" ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-2xl rounded-2xl p-4 text-sm leading-relaxed ${
                  m.sender === "user"
                    ? "bg-emerald-600 text-white rounded-br-none"
                    : "bg-slate-100 text-slate-900 border border-slate-200 rounded-bl-none"
                }`}
              >
                <div className="whitespace-pre-wrap">{m.text}</div>

                {/* Sources Card */}
                {m.sources && m.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-200/80 space-y-1.5">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                      <BookOpen className="w-3.5 h-3.5 text-emerald-600" />
                      Statutory Authority Cited:
                    </span>
                    <div className="space-y-1">
                      {m.sources.map((s, idx) => (
                        <div key={idx} className="bg-white p-2 rounded border border-slate-200 text-xs">
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
          ))}

          {asking && (
            <div className="flex items-center gap-2 text-slate-400 text-xs p-2">
              <div className="w-4 h-4 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
              <span>BharatCode model retrieving statutory sections &amp; formulating response...</span>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="p-3 border-t border-slate-200 bg-slate-50">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask a question about GST, Section 17(5) blocked credit, reverse charge, or ledger rules..."
              className="flex-1 px-4 py-2.5 text-sm bg-white border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500"
              disabled={asking}
            />
            <button
              type="submit"
              disabled={asking || !inputQuery.trim()}
              className="p-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-sm transition disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

