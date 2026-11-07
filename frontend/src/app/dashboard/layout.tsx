"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Receipt,
  FileSpreadsheet,
  BrainCircuit,
  CheckSquare,
  BookOpen,
  GitCompare,
  BarChart3,
  Landmark,
  BotMessageSquare,
  Users2,
  Settings,
  LogOut,
  Building2,
  ChevronDown,
  Globe2,
  ShieldCheck,
  Menu,
  X,
  TerminalSquare
} from "lucide-react";
import { api, User, Tenant, Membership, clearStoredToken, setStoredTenantId, getStoredTenantId } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { lang, setLang, t } = useLanguage();

  const [user, setUser] = useState<User | null>(null);
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [workspaces, setWorkspaces] = useState<Membership[]>([]);
  const [currentRole, setCurrentRole] = useState<string>("OWNER");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [workspaceDropdownOpen, setWorkspaceDropdownOpen] = useState(false);
  const [aiMode, setAiMode] = useState<string>("DEV_SIMULATION");

  useEffect(() => {
    api.getHealth()
      .then((h) => setAiMode(h.ai_mode || "DEV_SIMULATION"))
      .catch(() => {});
  }, []);

  useEffect(() => {
    // Load initial user and workspaces
    Promise.all([api.getMe(), api.getWorkspaces()])
      .then(([u, ws]) => {
        setUser(u);
        setWorkspaces(ws);

        const savedTenantId = getStoredTenantId();
        const activeMembership = ws.find((w) => w.tenant.id === savedTenantId) || ws[0];
        if (activeMembership) {
          setTenant(activeMembership.tenant);
          setCurrentRole(activeMembership.role);
          setStoredTenantId(activeMembership.tenant.id);
        }
      })
      .catch((err) => {
        console.error("Auth check failed:", err);
        router.push("/login");
      });
  }, [router]);

  const handleSwitchTenant = (m: Membership) => {
    setTenant(m.tenant);
    setCurrentRole(m.role);
    setStoredTenantId(m.tenant.id);
    setWorkspaceDropdownOpen(false);
    // Reload active view with new tenant context
    window.location.reload();
  };

  const handleLogout = () => {
    clearStoredToken();
    router.push("/login");
  };

  const navItems = [
    { name: t("command_centre") || "Command Centre", href: "/dashboard/command", icon: TerminalSquare },
    { name: t("dashboard"), href: "/dashboard", icon: LayoutDashboard },
    { name: t("transactions"), href: "/dashboard/transactions", icon: Receipt },
    { name: t("invoices"), href: "/dashboard/invoices", icon: FileSpreadsheet },
    { name: t("bookkeeping"), href: "/dashboard/bookkeeping", icon: BrainCircuit },
    { name: t("approvals"), href: "/dashboard/approvals", icon: CheckSquare },
    { name: t("ledger"), href: "/dashboard/ledger", icon: BookOpen },
    { name: t("reconciliation"), href: "/dashboard/reconciliation", icon: GitCompare },
    { name: t("reports"), href: "/dashboard/reports", icon: BarChart3 },
    { name: t("gst"), href: "/dashboard/gst", icon: Landmark },
    { name: t("assistant"), href: "/dashboard/assistant", icon: BotMessageSquare },
    { name: t("team"), href: "/dashboard/team", icon: Users2 },
    { name: t("settings"), href: "/dashboard/settings", icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col lg:flex-row">
      {/* Mobile Top Header */}
      <div className="lg:hidden bg-slate-900 text-white p-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-emerald-600 font-bold flex items-center justify-center text-sm">
            VS
          </div>
          <span className="font-bold text-base">VyaparSetu</span>
        </div>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-1.5 rounded-lg bg-slate-800 text-slate-200"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Sidebar Navigation */}
      <aside
        className={`fixed lg:sticky top-0 h-screen w-64 bg-slate-900 text-slate-300 flex flex-col justify-between z-40 transition-transform ${
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div>
          {/* Logo Brand */}
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <Link href="/dashboard" className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-emerald-600 via-teal-600 to-amber-500 flex items-center justify-center text-white font-bold text-lg shadow-md">
                VS
              </div>
              <div>
                <div className="font-extrabold text-lg text-white tracking-tight">
                  Vyapar<span className="text-emerald-400">Setu</span>
                </div>
                <div className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">
                  Multi-Tenant AI Core
                </div>
              </div>
            </Link>
          </div>

          {/* Active Tenant Selector Pill */}
          <div className="p-3">
            <div className="relative">
              <button
                type="button"
                onClick={() => setWorkspaceDropdownOpen(!workspaceDropdownOpen)}
                className="w-full flex items-center justify-between p-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-left transition-all"
              >
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <div className="h-7 w-7 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center flex-shrink-0">
                    <Building2 className="w-4 h-4" />
                  </div>
                  <div className="truncate">
                    <div className="text-xs font-bold text-white truncate">
                      {tenant?.name || "Loading..."}
                    </div>
                    <div className="text-[10px] text-slate-400 flex items-center gap-1">
                      <span className="px-1.5 py-0.2 rounded bg-slate-700 text-slate-300 font-semibold">
                        {currentRole}
                      </span>
                      <span>{tenant?.base_currency}</span>
                    </div>
                  </div>
                </div>
                <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
              </button>

              {/* Workspace Switcher Menu */}
              {workspaceDropdownOpen && (
                <div className="absolute top-full left-0 right-0 mt-1.5 bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-50 p-1">
                  <div className="px-2.5 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    Your Businesses & Workspaces
                  </div>
                  {workspaces.map((m) => (
                    <button
                      key={m.tenant.id}
                      onClick={() => handleSwitchTenant(m)}
                      className={`w-full text-left px-2.5 py-2 rounded-lg text-xs flex items-center justify-between transition-colors ${
                        tenant?.id === m.tenant.id
                          ? "bg-emerald-600 text-white font-bold"
                          : "text-slate-300 hover:bg-slate-700"
                      }`}
                    >
                      <span className="truncate">{m.tenant.name}</span>
                      <span className="text-[10px] opacity-75 font-semibold uppercase">{m.role}</span>
                    </button>
                  ))}
                  <div className="border-t border-slate-700 mt-1 pt-1">
                    <Link
                      href="/onboarding"
                      onClick={() => setWorkspaceDropdownOpen(false)}
                      className="block text-center py-1.5 text-xs text-emerald-400 hover:text-emerald-300 font-semibold"
                    >
                      + Create New Business
                    </Link>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="px-3 space-y-1 overflow-y-auto max-h-[calc(100vh-250px)]">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
                    isActive
                      ? "bg-emerald-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-white hover:bg-slate-800/60"
                  }`}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Bottom User Profile & Language Controls */}
        <div className="p-3 border-t border-slate-800">
          {/* Language Toggle in Sidebar */}
          <div className="flex items-center justify-between mb-3 px-2 py-1 bg-slate-800/60 rounded-lg text-xs">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Globe2 className="w-3.5 h-3.5" /> Language
            </span>
            <div className="flex gap-1 font-semibold text-[11px]">
              <button
                onClick={() => setLang("en")}
                className={`px-1.5 py-0.5 rounded ${
                  lang === "en" ? "bg-emerald-600 text-white" : "text-slate-400"
                }`}
              >
                EN
              </button>
              <button
                onClick={() => setLang("hi")}
                className={`px-1.5 py-0.5 rounded ${
                  lang === "hi" ? "bg-emerald-600 text-white" : "text-slate-400"
                }`}
              >
                हिंदी
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between p-2 rounded-xl bg-slate-800/40">
            <div className="truncate">
              <div className="text-xs font-bold text-white truncate">{user?.full_name || "User"}</div>
              <div className="text-[10px] text-slate-400 truncate">{user?.email}</div>
            </div>
            <button
              onClick={handleLogout}
              title="Log Out"
              className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-h-screen overflow-x-hidden">
        {/* Top Breadcrumb & Live Sandbox Notice */}
        <header className="bg-white border-b border-slate-200 px-6 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm sticky top-0 z-30">
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              {tenant?.trade_name || tenant?.name}
            </span>
            <span className="text-slate-300">/</span>
            <span className="text-sm font-extrabold text-slate-900 capitalize">
              {pathname.split("/").pop() || "Dashboard"}
            </span>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            {aiMode === "PRODUCTION_BHARATCODE" ? (
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-300 text-emerald-800 text-[11px] font-bold">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                BharatCode Qwen 3.8 27B (Live)
              </div>
            ) : (
              <div
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-50 border border-amber-300 text-amber-800 text-[11px] font-bold"
                title="Testing Mode: Deterministic Indic Engine active while BharatCode student tier is pending verification"
              >
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                AI Mode: DEV SIMULATION (Indic Engine)
              </div>
            )}
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-slate-500" />
              <span>{tenant?.tax_jurisdiction} &middot; {tenant?.currency_symbol} {tenant?.base_currency}</span>
            </div>
          </div>
        </header>

        {/* View Content */}
        <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">{children}</div>
      </main>
    </div>
  );
}

