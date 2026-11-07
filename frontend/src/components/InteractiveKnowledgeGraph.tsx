"use client";

import React, { useState, useMemo, useRef } from "react";
import {
  Search,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Layers,
  Info,
  X,
  ExternalLink,
  Building2,
  Users,
  Store,
  UserCheck,
  FileText,
  CreditCard,
  BookOpen,
  Receipt as ReceiptIcon,
  ShieldCheck,
  Link2,
  ChevronRight
} from "lucide-react";

interface Node {
  id: string;
  label: string;
  type: string;
  metadata: Record<string, any>;
  x?: number;
  y?: number;
}

interface Edge {
  source: string;
  target: string;
  relation: string;
  weight: number;
  metadata?: Record<string, any>;
}

interface KnowledgeGraphProps {
  data: {
    summary?: Record<string, any>;
    nodes: Node[];
    edges: Edge[];
  } | null;
}

const ENTITY_CONFIG: Record<string, { label: string; color: string; bg: string; border: string; icon: any }> = {
  BUSINESS: { label: "Business Entity", color: "#059669", bg: "#ecfdf5", border: "#10b981", icon: Building2 },
  USER: { label: "User / Member", color: "#4f46e5", bg: "#eef2ff", border: "#6366f1", icon: Users },
  VENDOR: { label: "Vendor / Supplier", color: "#e11d48", bg: "#fff1f2", border: "#f43f5e", icon: Store },
  CUSTOMER: { label: "Customer / Client", color: "#0284c7", bg: "#f0f9ff", border: "#0ea5e9", icon: UserCheck },
  INVOICE: { label: "Invoice / Receipt", color: "#7c3aed", bg: "#f5f3ff", border: "#8b5cf6", icon: FileText },
  TRANSACTION: { label: "Bank / UPI Txn", color: "#2563eb", bg: "#eff6ff", border: "#3b82f6", icon: CreditCard },
  LEDGER_ACCOUNT: { label: "Ledger Account", color: "#d97706", bg: "#fffbeb", border: "#f59e0b", icon: BookOpen },
  LEDGER_ENTRY: { label: "Journal Voucher", color: "#ea580c", bg: "#fff7ed", border: "#f97316", icon: ReceiptIcon },
  GST_RECORD: { label: "GST Return Table", color: "#0d9488", bg: "#f0fdfa", border: "#14b8a6", icon: ShieldCheck },
  RECONCILIATION_MATCH: { label: "Reconciliation Pair", color: "#9333ea", bg: "#faf5ff", border: "#a855f7", icon: Link2 },
};

export default function InteractiveKnowledgeGraph({ data }: KnowledgeGraphProps) {
  const [search, setSearch] = useState("");
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [visibleTypes, setVisibleTypes] = useState<Set<string>>(
    new Set([
      "BUSINESS",
      "USER",
      "VENDOR",
      "CUSTOMER",
      "INVOICE",
      "TRANSACTION",
      "LEDGER_ACCOUNT",
      "LEDGER_ENTRY",
      "GST_RECORD",
      "RECONCILIATION_MATCH",
    ])
  );

  // Pan & Zoom State
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const containerRef = useRef<HTMLDivElement>(null);

  // Compute Layout Coordinates with Orbit Clustering
  const positionedNodes = useMemo(() => {
    if (!data?.nodes) return [];

    const nodes = data.nodes.filter((n) => visibleTypes.has(n.type));
    const width = 1000;
    const height = 650;
    const centerX = width / 2;
    const centerY = height / 2;

    // Group nodes by type
    const groups: Record<string, Node[]> = {};
    nodes.forEach((n) => {
      groups[n.type] = groups[n.type] || [];
      groups[n.type].push(n);
    });

    const result: (Node & { x: number; y: number })[] = [];

    // Business at Center
    const bizNodes = groups["BUSINESS"] || [];
    bizNodes.forEach((b) => {
      result.push({ ...b, x: centerX, y: centerY });
    });

    // Orbit 1: Users, Ledger Accounts, GST Records (Radius: 180px)
    const orbit1Types = ["USER", "LEDGER_ACCOUNT", "GST_RECORD"];
    const orbit1Nodes: Node[] = [];
    orbit1Types.forEach((t) => (orbit1Nodes.push(...(groups[t] || []))));

    orbit1Nodes.forEach((n, idx) => {
      const angle = (idx / Math.max(orbit1Nodes.length, 1)) * 2 * Math.PI;
      const r = 180;
      result.push({
        ...n,
        x: centerX + r * Math.cos(angle),
        y: centerY + r * Math.sin(angle),
      });
    });

    // Orbit 2: Vendors, Customers, Invoices, Transactions (Radius: 310px)
    const orbit2Types = ["VENDOR", "CUSTOMER", "INVOICE", "TRANSACTION", "LEDGER_ENTRY", "RECONCILIATION_MATCH"];
    const orbit2Nodes: Node[] = [];
    orbit2Types.forEach((t) => (orbit2Nodes.push(...(groups[t] || []))));

    orbit2Nodes.forEach((n, idx) => {
      const angle = (idx / Math.max(orbit2Nodes.length, 1)) * 2 * Math.PI + 0.3;
      const r = 310 + (idx % 2 === 0 ? 30 : -20);
      result.push({
        ...n,
        x: centerX + r * Math.cos(angle),
        y: centerY + r * Math.sin(angle),
      });
    });

    return result;
  }, [data?.nodes, visibleTypes]);

  const nodeMap = useMemo(() => {
    const map = new Map<string, Node & { x: number; y: number }>();
    positionedNodes.forEach((n) => map.set(n.id, n));
    return map;
  }, [positionedNodes]);

  // Edges between visible nodes
  const visibleEdges = useMemo(() => {
    if (!data?.edges) return [];
    return data.edges.filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target));
  }, [data?.edges, nodeMap]);

  // Connected Edges for Selected Node
  const selectedNodeConnections = useMemo(() => {
    if (!selectedNode || !data?.edges) return { incoming: [], outgoing: [] };

    const incoming = data.edges.filter((e) => e.target === selectedNode.id);
    const outgoing = data.edges.filter((e) => e.source === selectedNode.id);

    return { incoming, outgoing };
  }, [selectedNode, data?.edges]);

  const toggleType = (t: string) => {
    const next = new Set(visibleTypes);
    if (next.has(t)) {
      if (next.size > 1) next.delete(t);
    } else {
      next.add(t);
    }
    setVisibleTypes(next);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).tagName === "circle" || (e.target as HTMLElement).tagName === "text") {
      return;
    }
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setSelectedNode(null);
    setSearch("");
  };

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="p-12 text-center bg-white rounded-2xl border border-slate-200">
        <Building2 className="w-10 h-10 text-slate-300 mx-auto mb-3" />
        <h4 className="font-bold text-slate-700">Financial Knowledge Graph Empty</h4>
        <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
          Ingest transactions, add vendor receipts, or create ledger vouchers to generate the multi-entity financial graph.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Top Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* Search */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search vendor, invoice, account, txn..."
            className="w-full pl-10 pr-3.5 py-2 bg-slate-50 border border-slate-300 rounded-xl text-xs font-medium focus:ring-2 focus:ring-emerald-500 text-slate-900"
          />
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-1.5 self-end md:self-auto">
          <button
            onClick={() => setZoom((z) => Math.min(z + 0.2, 2.5))}
            className="p-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-slate-700 text-xs font-bold transition"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(z - 0.2, 0.4))}
            className="p-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-slate-700 text-xs font-bold transition"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={resetView}
            className="inline-flex items-center gap-1 px-3 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-slate-700 text-xs font-bold transition"
            title="Reset View"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>
        </div>
      </div>

      {/* Entity Type Filter Badges */}
      <div className="flex flex-wrap items-center gap-1.5 p-3 bg-slate-50 rounded-2xl border border-slate-200">
        <span className="text-[11px] font-bold text-slate-500 mr-1 flex items-center gap-1">
          <Layers className="w-3.5 h-3.5" /> Filter Entities:
        </span>
        {Object.entries(ENTITY_CONFIG).map(([typeKey, cfg]) => {
          const isActive = visibleTypes.has(typeKey);
          const count = data.summary?.entity_type_counts?.[typeKey] || 0;
          return (
            <button
              key={typeKey}
              onClick={() => toggleType(typeKey)}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold transition border ${
                isActive
                  ? "bg-white shadow-sm border-slate-300 text-slate-800"
                  : "bg-slate-200/60 border-transparent text-slate-400 opacity-60"
              }`}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: cfg.color }}
              />
              <span>{cfg.label}</span>
              <span className="text-[10px] opacity-75">({count})</span>
            </button>
          );
        })}
      </div>

      {/* Interactive Graph Canvas & Side Drawer */}
      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="relative bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-inner h-[620px] cursor-grab active:cursor-grabbing"
      >
        <svg
          viewBox="0 0 1000 650"
          className="w-full h-full select-none"
        >
          <defs>
            <marker
              id="arrowhead"
              markerWidth="8"
              markerHeight="6"
              refX="18"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 8 3, 0 6" fill="#475569" />
            </marker>
            <radialGradient id="bizGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#047857" stopOpacity="0.2" />
            </radialGradient>
          </defs>

          {/* Canvas Transform Layer */}
          <g
            transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}
            transform-origin="500 325"
          >
            {/* Background Grid Pattern */}
            <g opacity="0.15">
              {Array.from({ length: 25 }).map((_, i) => (
                <line
                  key={`gx_${i}`}
                  x1={i * 45}
                  y1="0"
                  x2={i * 45}
                  y2="650"
                  stroke="#334155"
                  strokeWidth="0.8"
                />
              ))}
              {Array.from({ length: 18 }).map((_, i) => (
                <line
                  key={`gy_${i}`}
                  x1="0"
                  y1={i * 40}
                  x2="1000"
                  y2={i * 40}
                  stroke="#334155"
                  strokeWidth="0.8"
                />
              ))}
            </g>

            {/* Orbit Guidelines */}
            <circle cx="500" cy="325" r="180" fill="none" stroke="#1e293b" strokeWidth="1" strokeDasharray="4 4" />
            <circle cx="500" cy="325" r="310" fill="none" stroke="#1e293b" strokeWidth="1" strokeDasharray="4 4" />

            {/* Relationship Edges */}
            {visibleEdges.map((edge, idx) => {
              const src = nodeMap.get(edge.source);
              const tgt = nodeMap.get(edge.target);
              if (!src || !tgt) return null;

              const isConnectedToSelected =
                selectedNode && (selectedNode.id === edge.source || selectedNode.id === edge.target);

              return (
                <g key={`edge_${idx}`}>
                  <line
                    x1={src.x}
                    y1={src.y}
                    x2={tgt.x}
                    y2={tgt.y}
                    stroke={isConnectedToSelected ? "#10b981" : "#334155"}
                    strokeWidth={isConnectedToSelected ? 2.5 : 1.2}
                    strokeOpacity={isConnectedToSelected ? 0.9 : 0.5}
                    markerEnd="url(#arrowhead)"
                  />
                  {/* Midpoint Relationship Label (on hover or active connection) */}
                  {isConnectedToSelected && (
                    <text
                      x={(src.x + tgt.x) / 2}
                      y={(src.y + tgt.y) / 2 - 4}
                      fill="#94a3b8"
                      fontSize="9"
                      fontFamily="monospace"
                      textAnchor="middle"
                      className="bg-slate-900 font-bold"
                    >
                      {edge.relation}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Entity Nodes */}
            {positionedNodes.map((node) => {
              const cfg = ENTITY_CONFIG[node.type] || {
                color: "#94a3b8",
                bg: "#0f172a",
                border: "#64748b",
              };
              const isSelected = selectedNode?.id === node.id;
              const matchesSearch =
                search.trim().length > 0 &&
                (node.label.toLowerCase().includes(search.toLowerCase()) ||
                  node.type.toLowerCase().includes(search.toLowerCase()) ||
                  JSON.stringify(node.metadata).toLowerCase().includes(search.toLowerCase()));

              const isBusiness = node.type === "BUSINESS";
              const radius = isBusiness ? 24 : node.type === "GST_RECORD" || node.type === "LEDGER_ACCOUNT" ? 18 : 14;

              const dimmed = search.trim().length > 0 && !matchesSearch;

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedNode(node);
                  }}
                  className="cursor-pointer transition-all duration-150"
                  opacity={dimmed ? 0.25 : 1}
                >
                  {/* Outer Pulsing Aura for Selected or Match */}
                  {(isSelected || matchesSearch) && (
                    <circle
                      r={radius + 8}
                      fill="none"
                      stroke={cfg.border}
                      strokeWidth="2"
                      strokeDasharray="3 3"
                      className="animate-spin"
                    />
                  )}

                  {/* Main Node Circle */}
                  <circle
                    r={radius}
                    fill={isBusiness ? "url(#bizGlow)" : cfg.bg}
                    stroke={cfg.border}
                    strokeWidth={isSelected ? 3 : 2}
                    filter="drop-shadow(0 4px 6px rgba(0,0,0,0.4))"
                  />

                  {/* Node Label Text */}
                  <text
                    y={radius + 12}
                    textAnchor="middle"
                    fill={isSelected ? "#ffffff" : "#cbd5e1"}
                    fontSize={isBusiness ? 11 : 9}
                    fontWeight={isBusiness || isSelected ? "bold" : "medium"}
                    className="pointer-events-none"
                  >
                    {node.label.length > 20 ? node.label.slice(0, 18) + "…" : node.label}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        {/* Slide-Over Node Details Drawer */}
        {selectedNode && (
          <div className="absolute top-4 right-4 bottom-4 w-84 bg-slate-900/95 backdrop-blur-md border border-slate-700 rounded-2xl shadow-2xl p-5 text-white flex flex-col justify-between overflow-y-auto animate-in slide-in-from-right-4 duration-200">
            <div className="space-y-4">
              {/* Drawer Header */}
              <div className="flex items-start justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2.5">
                  <span
                    className="w-3.5 h-3.5 rounded-full"
                    style={{ backgroundColor: ENTITY_CONFIG[selectedNode.type]?.color || "#94a3b8" }}
                  />
                  <div>
                    <span className="text-[10px] font-bold tracking-wider uppercase text-slate-400">
                      {ENTITY_CONFIG[selectedNode.type]?.label || selectedNode.type}
                    </span>
                    <h3 className="text-sm font-bold text-white line-clamp-1">{selectedNode.label}</h3>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Node Metadata Inspector */}
              <div className="space-y-2">
                <span className="text-[10px] font-bold uppercase text-slate-400">Entity Attributes:</span>
                <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 space-y-1.5 text-xs">
                  {Object.entries(selectedNode.metadata || {}).map(([key, val]) => (
                    <div key={key} className="flex justify-between items-center text-[11px]">
                      <span className="text-slate-400 font-mono capitalize">{key.replace(/_/g, " ")}:</span>
                      <span className="font-semibold text-slate-200 max-w-[160px] truncate text-right">
                        {typeof val === "object" ? JSON.stringify(val) : String(val)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Connected Relationships */}
              <div className="space-y-2">
                <span className="text-[10px] font-bold uppercase text-slate-400">Connected Graph Links:</span>
                <div className="space-y-1.5 max-h-44 overflow-y-auto text-[11px]">
                  {selectedNodeConnections.outgoing.map((outEdge, i) => (
                    <div
                      key={`out_${i}`}
                      className="p-2 bg-slate-800/60 rounded-lg flex items-center justify-between border border-slate-700/60"
                    >
                      <span className="text-emerald-400 font-mono font-bold text-[10px]">
                        → {outEdge.relation}
                      </span>
                      <span className="text-slate-300 truncate max-w-[110px]">
                        {nodeMap.get(outEdge.target)?.label || outEdge.target}
                      </span>
                    </div>
                  ))}

                  {selectedNodeConnections.incoming.map((inEdge, i) => (
                    <div
                      key={`in_${i}`}
                      className="p-2 bg-slate-800/60 rounded-lg flex items-center justify-between border border-slate-700/60"
                    >
                      <span className="text-blue-400 font-mono font-bold text-[10px]">
                        ← {inEdge.relation}
                      </span>
                      <span className="text-slate-300 truncate max-w-[110px]">
                        {nodeMap.get(inEdge.source)?.label || inEdge.source}
                      </span>
                    </div>
                  ))}

                  {selectedNodeConnections.outgoing.length === 0 &&
                    selectedNodeConnections.incoming.length === 0 && (
                      <p className="text-slate-500 text-xs italic">No direct connections recorded.</p>
                    )}
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
              <span className="text-[10px] text-slate-500 font-mono">ID: {selectedNode.id}</span>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-xs font-semibold text-emerald-400 hover:text-emerald-300"
              >
                Close Drawer
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

