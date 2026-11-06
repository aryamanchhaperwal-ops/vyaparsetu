"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

type Language = "en" | "hi";

interface LanguageContextType {
  lang: Language;
  setLang: (lang: Language) => void;
  t: (key: string) => string;
}

const translations: Record<Language, Record<string, string>> = {
  en: {
    dashboard: "Dashboard",
    transactions: "Transactions",
    invoices: "Invoices & OCR",
    bookkeeping: "AI Bookkeeping",
    approvals: "Approval Queue",
    ledger: "Ledger & Accounts",
    reconciliation: "Reconciliation",
    reports: "Financial Reports",
    gst: "GST Workspace",
    assistant: "AI GST Assistant",
    team: "Team & Roles",
    settings: "Settings & Plan",
    logout: "Log Out",
    welcome: "Welcome back",
    workspace: "Active Workspace",
    total_inflow: "Total Inflow (Revenue)",
    total_outflow: "Total Outflow (Expense)",
    net_cashflow: "Net Cash Flow",
    credit_score: "MSME Credit Health Score",
    runway: "Estimated Cash Runway",
    live_badge: "Simulated BharatCode Sandbox",
    status_confirmed: "Confirmed",
    status_needs_approval: "Needs Approval",
    approve_btn: "Approve & Post",
    reject_btn: "Reject",
    generate_synthetic_btn: "Generate Synthetic Transactions",
    upload_csv: "Upload Bank CSV",
    upload_pdf: "Upload Statement PDF",
    scan_receipt: "Scan / Upload Receipt",
    filter_all: "All Channels",
    amount: "Amount",
    date: "Date",
    narration: "Narration / Particulars",
    category: "Category",
    gst_rate: "GST Rate",
    confidence: "Confidence",
    action: "Action"
  },
  hi: {
    dashboard: "डैशबोर्ड",
    transactions: "लेन-देन (Transactions)",
    invoices: "बिल और रसीदें (OCR)",
    bookkeeping: "AI बहीखाता (Bookkeeping)",
    approvals: "स्वीकृति कतार (Approvals)",
    ledger: "खाताबही (Ledger)",
    reconciliation: "समाधान (Reconciliation)",
    reports: "वित्तीय रिपोर्ट (Reports)",
    gst: "GST कार्यक्षेत्र",
    assistant: "AI GST सलाहकार",
    team: "टीम और अधिकार",
    settings: "सेटिंग्स और प्लान",
    logout: "लॉग आउट",
    welcome: "नमस्ते",
    workspace: "व्यापार खाता",
    total_inflow: "कुल आमदनी (Inflow)",
    total_outflow: "कुल खर्च (Outflow)",
    net_cashflow: "शुद्ध नकदी प्रवाह (Net Cash)",
    credit_score: "MSME क्रेडिट स्कोर",
    runway: "अनुमानित नकदी अवधि (Runway)",
    live_badge: "भारतकोड सिम्युलेटेड सैंडबॉक्स",
    status_confirmed: "पुष्टीकृत (Confirmed)",
    status_needs_approval: "पुष्टि आवश्यक",
    approve_btn: "स्वीकारें और दर्ज करें",
    reject_btn: "अस्वीकार करें",
    generate_synthetic_btn: "सिंथेटिक डेटा जनरेट करें",
    upload_csv: "बैंक CSV अपलोड करें",
    upload_pdf: "स्टेटमेंट PDF अपलोड करें",
    scan_receipt: "रसीद स्कैन / अपलोड करें",
    filter_all: "सभी माध्यम",
    amount: "राशि (Amount)",
    date: "तारीख",
    narration: "विवरण (Narration)",
    category: "श्रेणी (Category)",
    gst_rate: "GST दर",
    confidence: "सटीकता (Confidence)",
    action: "कार्रवाई"
  }
};

const LanguageContext = createContext<LanguageContextType>({
  lang: "en",
  setLang: () => {},
  t: (key: string) => key,
});

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lang, setLang] = useState<Language>("en");

  useEffect(() => {
    const saved = localStorage.getItem("vyaparsetu_lang") as Language;
    if (saved && (saved === "en" || saved === "hi")) {
      setLang(saved);
    }
  }, []);

  const changeLang = (newLang: Language) => {
    setLang(newLang);
    localStorage.setItem("vyaparsetu_lang", newLang);
  };

  const t = (key: string): string => {
    return translations[lang]?.[key] || translations["en"]?.[key] || key;
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang: changeLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);

