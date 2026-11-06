"use client";

import React, { useState, useEffect } from "react";
import {
  Users2,
  UserPlus,
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  AlertCircle,
  Mail,
  User as UserIcon,
  X,
  RefreshCw,
  Building2,
  Lock
} from "lucide-react";
import { api, getStoredTenantId } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

interface MemberItem {
  membership_id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: "OWNER" | "ADMIN" | "ACCOUNTANT" | "EMPLOYEE";
  is_active: boolean;
  created_at: string;
}

export default function TeamPage() {
  const { t } = useLanguage();
  const [members, setMembers] = useState<MemberItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("EMPLOYEE");
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const tenantId = getStoredTenantId();

  const loadMembers = async () => {
    if (!tenantId) return;
    try {
      setLoading(true);
      const data = await api.getMembers(tenantId);
      setMembers(data || []);
    } catch (err: any) {
      console.error("Failed to load members:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMembers();
  }, [tenantId]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId || !inviteEmail) return;

    setSubmitting(true);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      await api.inviteMember(tenantId, inviteEmail, inviteRole);
      setSuccessMsg(`Successfully invited ${inviteEmail} as ${inviteRole}!`);
      setInviteEmail("");
      setInviteModalOpen(false);
      await loadMembers();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to invite member.");
    } finally {
      setSubmitting(false);
    }
  };

  const roleDescriptions = [
    {
      role: "OWNER",
      desc: "Full administrative and fiduciary authority. Can manage billing, configure workspace settings, and delete tenant.",
      color: "bg-purple-100 text-purple-800 border-purple-200",
    },
    {
      role: "ADMIN",
      desc: "Manages team access, approves pending transactions, and views all ledgers and financial statements.",
      color: "bg-blue-100 text-blue-800 border-blue-200",
    },
    {
      role: "ACCOUNTANT",
      desc: "Dedicated financial expert. Can manage multiple businesses, post journal vouchers, and prepare simulated GST filings.",
      color: "bg-emerald-100 text-emerald-800 border-emerald-200",
    },
    {
      role: "EMPLOYEE",
      desc: "Standard staff. Can log cash transactions and upload receipts. Blocked from GST filings and subscription upgrades.",
      color: "bg-slate-100 text-slate-800 border-slate-200",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Users2 className="w-7 h-7 text-emerald-600" />
            {t("team")} &amp; Role-Based Access Control
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage workspace members, grant accountant access, and enforce multi-tenant authorization boundaries.
          </p>
        </div>

        <button
          onClick={() => setInviteModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded-lg shadow-sm transition"
        >
          <UserPlus className="w-4 h-4" />
          <span>Invite Team Member</span>
        </button>
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-600" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Role Hierarchy Guide */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {roleDescriptions.map((r) => (
          <div key={r.role} className={`p-4 rounded-xl border ${r.color} space-y-1.5`}>
            <div className="flex items-center justify-between">
              <span className="font-bold text-xs uppercase tracking-wider">{r.role}</span>
              <Lock className="w-3.5 h-3.5 opacity-60" />
            </div>
            <p className="text-[11px] leading-relaxed opacity-90">{r.desc}</p>
          </div>
        ))}
      </div>

      {/* Members Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800 text-sm">Active Workspace Members ({members.length})</h3>
          <button
            onClick={loadMembers}
            disabled={loading}
            className="p-1 text-slate-400 hover:text-slate-600 rounded"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-400 text-sm">Loading workspace team...</div>
        ) : members.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">No members found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase border-b border-slate-200">
                <tr>
                  <th className="px-5 py-3">Member Name</th>
                  <th className="px-5 py-3">Email Address</th>
                  <th className="px-5 py-3">Assigned Role</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Member Since</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {members.map((m) => (
                  <tr key={m.membership_id} className="hover:bg-slate-50 transition">
                    <td className="px-5 py-3 font-medium text-slate-800 flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold text-xs">
                        {m.full_name?.charAt(0) || "U"}
                      </div>
                      {m.full_name || "Workspace Member"}
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-slate-600">{m.email}</td>
                    <td className="px-5 py-3">
                      <span
                        className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase border ${
                          m.role === "OWNER"
                            ? "bg-purple-100 text-purple-800 border-purple-300"
                            : m.role === "ADMIN"
                            ? "bg-blue-100 text-blue-800 border-blue-300"
                            : m.role === "ACCOUNTANT"
                            ? "bg-emerald-100 text-emerald-800 border-emerald-300"
                            : "bg-slate-100 text-slate-700 border-slate-300"
                        }`}
                      >
                        {m.role}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Active
                      </span>
                    </td>
                    <td className="px-5 py-3 text-xs text-slate-400">
                      {m.created_at ? new Date(m.created_at).toLocaleDateString() : "Active"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Invite Member Modal */}
      {inviteModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-emerald-600" />
                <h3 className="font-bold text-slate-900">Invite New Workspace Member</h3>
              </div>
              <button
                onClick={() => setInviteModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleInvite} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-slate-700 mb-1">Collaborator Email</label>
                <input
                  type="email"
                  placeholder="ca.sharma@firm.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  required
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Role &amp; Permissions</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
                >
                  <option value="ACCOUNTANT">ACCOUNTANT (Multi-business ledger &amp; GST access)</option>
                  <option value="ADMIN">ADMIN (Workspace management &amp; approvals)</option>
                  <option value="EMPLOYEE">EMPLOYEE (Entry logging &amp; receipts only)</option>
                </select>
              </div>

              {errorMsg && (
                <div className="p-3 bg-red-50 text-red-700 border border-red-200 rounded text-xs">
                  {errorMsg}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setInviteModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 hover:bg-slate-50 text-slate-700 font-medium rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg shadow-sm transition flex items-center gap-2 disabled:opacity-50"
                >
                  <Mail className="w-4 h-4" />
                  <span>{submitting ? "Inviting..." : "Send Invitation"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

