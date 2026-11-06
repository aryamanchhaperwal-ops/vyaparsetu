"use client";

import React from "react";
import Link from "next/link";
import {
  ArrowRight,
  ShieldCheck,
  Cpu,
  Receipt,
  FileSpreadsheet,
  TrendingUp,
  Globe2,
  CheckCircle2,
  Sparkles,
  Layers,
  Calculator,
  Lock
} from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";

export default function LandingPage() {
  const { lang, setLang } = useLanguage();

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-100 flex flex-col justify-between">
      {/* Top Navigation */}
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-600 via-teal-600 to-amber-500 flex items-center justify-center text-white font-bold text-xl shadow-md shadow-emerald-500/20">
              VS
            </div>
            <div>
              <span className="font-extrabold text-xl tracking-tight text-slate-900">
                Vyapar<span className="text-emerald-600">Setu</span>
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                BharatCode Edition
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Language Switcher */}
            <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-semibold">
              <button
                onClick={() => setLang("en")}
                className={`px-2.5 py-1 rounded-md transition-all ${
                  lang === "en" ? "bg-white text-emerald-700 shadow-sm" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                English
              </button>
              <button
                onClick={() => setLang("hi")}
                className={`px-2.5 py-1 rounded-md transition-all ${
                  lang === "hi" ? "bg-white text-emerald-700 shadow-sm" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                हिंदी
              </button>
            </div>

            <Link
              href="/login"
              className="text-sm font-semibold text-slate-700 hover:text-emerald-600 transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold px-4 py-2 rounded-xl shadow-md shadow-emerald-600/20 transition-all hover:scale-[1.02]"
            >
              Get Started <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1">
        <section className="relative overflow-hidden pt-16 pb-24 lg:pt-20 lg:pb-32">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold mb-6 shadow-sm">
              <Sparkles className="w-4 h-4 text-emerald-600 animate-pulse" />
              Empowering 63 Million Indian MSMEs with Indic AI Bookkeeping
            </div>

            <h1 className="text-4xl sm:text-6xl font-black text-slate-900 tracking-tight max-w-4xl mx-auto leading-tight sm:leading-[1.15]">
              {lang === "hi"
                ? "भारतीय व्यापारियों के लिए AI बहीखाता और GST सारथी"
                : "Multilingual AI Bookkeeping, GST & Financial Intelligence for MSMEs"}
            </h1>

            <p className="mt-6 text-lg sm:text-xl text-slate-600 max-w-2xl mx-auto font-normal leading-relaxed">
              {lang === "hi"
                ? "व्यापारसेतु आपके बैंक स्टेटमेंट, UPI पेमेंट्स और रसीदों को स्वतः दोहरी-प्रविष्टि खाताबही में दर्ज करता है, और सही GST रिपोर्ट तैयार करता है।"
                : "Effortlessly ingest messy Indian UPI narrations, bank statements & receipts. Automatically classify expenses in Hindi & regional terms with BharatCode, maintain balanced double-entry books, and generate simulated GSTR reports."}
            </p>

            {/* Quick Action CTAs */}
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/dashboard"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-base px-8 py-3.5 rounded-2xl shadow-xl shadow-emerald-600/25 transition-all hover:-translate-y-0.5"
              >
                Launch Workspace Dashboard <ArrowRight className="w-5 h-5" />
              </Link>
              <Link
                href="/login?demo=true"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-white hover:bg-slate-50 text-slate-800 font-semibold text-base px-6 py-3.5 rounded-2xl border border-slate-300 shadow-sm transition-all"
              >
                Instant Demo Access (Sharma Traders)
              </Link>
            </div>

            {/* Compliance Badge */}
            <div className="mt-8 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-500 font-medium">
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Powered Exclusively by BharatCode LLM
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" /> LangGraph Multi-Agent Orchestration
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Deterministic Section 170 CGST Engine
              </span>
            </div>
          </div>
        </section>

        {/* Feature Grid */}
        <section className="py-16 bg-white border-y border-slate-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">
                Architected Specifically for the Indian Commercial Reality
              </h2>
              <p className="mt-3 text-slate-600 text-base">
                Generic accounting software fails because Indian MSMEs speak in Hinglish and transact via fragmented UPI QR codes. VyaparSetu solves this natively.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {/* Card 1 */}
              <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:border-emerald-300 transition-all hover:shadow-lg hover:shadow-emerald-500/5 group">
                <div className="w-12 h-12 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
                  <Cpu className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-2">LangGraph Multi-Agent Pipeline</h3>
                <p className="text-sm text-slate-600 leading-relaxed">
                  Decoupled agents for Ingestion, Deduplication, BharatCode Multilingual Classification, Human Checkpointing, and Ledger posting.
                </p>
              </div>

              {/* Card 2 */}
              <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:border-emerald-300 transition-all hover:shadow-lg hover:shadow-emerald-500/5 group">
                <div className="w-12 h-12 rounded-xl bg-teal-100 text-teal-700 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
                  <Calculator className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-2">Deterministic Financial Core</h3>
                <p className="text-sm text-slate-600 leading-relaxed">
                  Financial calculations are never delegated to LLM hallucination. Strict decimal paisa math ensures Debits exactly equal Credits.
                </p>
              </div>

              {/* Card 3 */}
              <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:border-emerald-300 transition-all hover:shadow-lg hover:shadow-emerald-500/5 group">
                <div className="w-12 h-12 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
                  <Receipt className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-2">Multilingual Merchant OCR</h3>
                <p className="text-sm text-slate-600 leading-relaxed">
                  Drop supplier invoices or camera photos of receipts. Extracts vendor 15-char GSTINs, invoice numbers, and auto-matches with bank debits.
                </p>
              </div>

              {/* Card 4 */}
              <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:border-emerald-300 transition-all hover:shadow-lg hover:shadow-emerald-500/5 group">
                <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
                  <FileSpreadsheet className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-2">Simulated GSTR-1 & 3B Reports</h3>
                <p className="text-sm text-slate-600 leading-relaxed">
                  B2B Table 4, B2C Table 7, and HSN Table 12 summaries generated automatically with Section 49 statutory tax offset calculations.
                </p>
              </div>

              {/* Card 5 */}
              <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:border-emerald-300 transition-all hover:shadow-lg hover:shadow-emerald-500/5 group">
                <div className="w-12 h-12 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
                  <Globe2 className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-2">Statutory RAG GST Assistant</h3>
                <p className="text-sm text-slate-600 leading-relaxed">
                  Ask questions in Hindi or Hinglish. Grounded in CGST Sections 16, 17(5), and CBIC circulars with exact statutory citations.
                </p>
              </div>

              {/* Card 6 */}
              <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 hover:border-emerald-300 transition-all hover:shadow-lg hover:shadow-emerald-500/5 group">
                <div className="w-12 h-12 rounded-xl bg-rose-100 text-rose-700 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-2">Global Multi-Tenancy & RBAC</h3>
                <p className="text-sm text-slate-600 leading-relaxed">
                  Isolated workspace boundaries, multi-currency support, multi-business accountant access, and Owner/Admin/Accountant/Employee roles.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 py-12 border-t border-slate-800 text-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-emerald-600 text-white font-bold flex items-center justify-center text-sm">
              VS
            </div>
            <span className="font-bold text-slate-200">VyaparSetu</span>
            <span className="text-slate-500">| BharatCode Hackathon 2026</span>
          </div>

          <p className="text-xs text-slate-500 text-center sm:text-right">
            Designed for Indian MSMEs &middot; Built with LangGraph &amp; BharatCode &middot; Simulated Banking &amp; GST Sandbox
          </p>
        </div>
      </footer>
    </div>
  );
}

