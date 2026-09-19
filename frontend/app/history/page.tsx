"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";

type CategoryType =
  | "ALL"
  | "CHAT"
  | "AI ANALYSIS"
  | "SIGNALS"
  | "VISION"
  | "VOICE"
  | "AGENTS"
  | "TOOLS"
  | "MARKETS"
  | "NEWS"
  | "SYSTEM";

type TimeFilter = "TODAY" | "7 DAYS" | "30 DAYS" | "ALL TIME";
type SortOrder = "NEWEST" | "OLDEST";

interface HistoryRecord {
  id: string;
  category: CategoryType;
  title: string;
  description: string;
  timestamp: string;
  status: string;
  source: string;
  contextPreview: string;
  memoryId: string;
  timeframe: TimeFilter;
  createdAt: string;
  conversationId?: string | null;
}

interface HistoryStats {
  conversations: number;
  aiMemories: number;
  analyses: number;
  savedItems: number;
  nodesConnected: number;
}

interface HistoryResponse {
  status?: string;
  stats?: Partial<HistoryStats>;
  records?: HistoryRecord[];
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

const categories: CategoryType[] = [
  "ALL",
  "CHAT",
  "AI ANALYSIS",
  "SIGNALS",
  "VISION",
  "VOICE",
  "AGENTS",
  "TOOLS",
  "MARKETS",
  "NEWS",
  "SYSTEM",
];

const navItems = [
  { label: "HOME", href: "/" },
  { label: "CHAT", href: "/chat" },
  { label: "VISION", href: "/chat" },
  { label: "AGENTS", href: "/chat" },
  { label: "TOOLS", href: "/chat" },
  { label: "MARKETS", href: "/markets" },
  { label: "SIGNALS", href: "/signals" },
  { label: "NEWS", href: "/news" },
  { label: "ALERTS", href: "/alerts" },
  { label: "HISTORY", href: "/history" },
  { label: "MEMORY", href: "/history" },
];

function formatDate(value: string): string {
  if (!value) return "Unknown";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getTimeframe(createdAt: string): TimeFilter {
  const date = new Date(createdAt);

  if (Number.isNaN(date.getTime())) {
    return "ALL TIME";
  }

  const now = Date.now();
  const age = now - date.getTime();

  const day = 24 * 60 * 60 * 1000;

  if (age < day) return "TODAY";
  if (age < 7 * day) return "7 DAYS";
  if (age < 30 * day) return "30 DAYS";

  return "ALL TIME";
}

function normalizeRecord(record: HistoryRecord): HistoryRecord {
  const timeframe =
    record.timeframe || getTimeframe(record.createdAt);

  return {
    ...record,
    timeframe,
    timestamp:
      record.timestamp || formatDate(record.createdAt),
    description:
      record.description ||
      "KING ZARRY AI activity recorded in your intelligence archive.",
    contextPreview:
      record.contextPreview ||
      "No additional context preview is available for this record.",
    source: record.source || "MEMORY CORE",
    status: record.status || "INDEXED",
    memoryId:
      record.memoryId ||
      `KZ-${String(record.id).slice(0, 8).toUpperCase()}`,
  };
}

export default function KingZarryHistoryPage() {
  const [selectedCategory, setSelectedCategory] =
    useState<CategoryType>("ALL");

  const [timeFilter, setTimeFilter] =
    useState<TimeFilter>("ALL TIME");

  const [sortOrder, setSortOrder] =
    useState<SortOrder>("NEWEST");

  const [searchQuery, setSearchQuery] =
    useState("");

  const [selectedRecordId, setSelectedRecordId] =
    useState<string>("");

  const [mobileMenuOpen, setMobileMenuOpen] =
    useState(false);

  const [records, setRecords] =
    useState<HistoryRecord[]>([]);

  const [hudStats, setHudStats] =
    useState<HistoryStats>({
      conversations: 0,
      aiMemories: 0,
      analyses: 0,
      savedItems: 0,
      nodesConnected: 0,
    });

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [authRequired, setAuthRequired] =
    useState(false);

  const [refreshing, setRefreshing] =
    useState(false);

  const [exporting, setExporting] =
    useState(false);

  const [restoring, setRestoring] =
    useState(false);

  // ============================================================
  // LOAD REAL HISTORY
  // ============================================================

  const loadHistory = async () => {
    try {
      setError("");
      setAuthRequired(false);

      const response = await fetch(
        `${API_BASE_URL}/api/history`,
        {
          method: "GET",
          credentials: "include",
          headers: {
            Accept: "application/json",
          },
          cache: "no-store",
        }
      );

      if (response.status === 401) {
        setAuthRequired(true);
        setRecords([]);
        setHudStats({
          conversations: 0,
          aiMemories: 0,
          analyses: 0,
          savedItems: 0,
          nodesConnected: 0,
        });
        return;
      }

      if (!response.ok) {
        let message = "Unable to load history.";

        try {
          const body = await response.json();

          if (body?.detail) {
            message = String(body.detail);
          }
        } catch {
          // Ignore invalid JSON error bodies.
        }

        throw new Error(message);
      }

      const data: HistoryResponse =
        await response.json();

      const nextRecords = Array.isArray(data.records)
        ? data.records.map(normalizeRecord)
        : [];

      setRecords(nextRecords);

      setHudStats({
        conversations:
          Number(data.stats?.conversations ?? 0),

        aiMemories:
          Number(data.stats?.aiMemories ?? 0),

        analyses:
          Number(data.stats?.analyses ?? 0),

        savedItems:
          Number(data.stats?.savedItems ?? 0),

        nodesConnected:
          Number(
            data.stats?.nodesConnected ??
              nextRecords.length
          ),
      });

      if (nextRecords.length > 0) {
        setSelectedRecordId((current) => {
          if (
            current &&
            nextRecords.some(
              (record) => record.id === current
            )
          ) {
            return current;
          }

          return nextRecords[0].id;
        });
      } else {
        setSelectedRecordId("");
      }
    } catch (err) {
      console.error("History loading failed:", err);

      setError(
        err instanceof Error
          ? err.message
          : "Unable to load intelligence history."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  // ============================================================
  // FILTERING
  // ============================================================

  const filteredRecords = useMemo(() => {
    const query =
      searchQuery.trim().toLowerCase();

    return [...records]
      .filter((record) => {
        const categoryMatch =
          selectedCategory === "ALL" ||
          record.category === selectedCategory;

        const timeframeMatch =
          timeFilter === "ALL TIME" ||
          record.timeframe === timeFilter ||
          getTimeframe(record.createdAt) === timeFilter;

        const searchMatch =
          !query ||
          record.title
            .toLowerCase()
            .includes(query) ||
          record.description
            .toLowerCase()
            .includes(query) ||
          record.memoryId
            .toLowerCase()
            .includes(query) ||
          record.contextPreview
            .toLowerCase()
            .includes(query) ||
          record.source
            .toLowerCase()
            .includes(query);

        return (
          categoryMatch &&
          timeframeMatch &&
          searchMatch
        );
      })
      .sort((a, b) => {
        const first =
          new Date(a.createdAt).getTime();

        const second =
          new Date(b.createdAt).getTime();

        if (
          Number.isNaN(first) ||
          Number.isNaN(second)
        ) {
          return 0;
        }

        return sortOrder === "NEWEST"
          ? second - first
          : first - second;
      });
  }, [
    records,
    selectedCategory,
    timeFilter,
    searchQuery,
    sortOrder,
  ]);

  const selectedRecord = useMemo(() => {
    return (
      records.find(
        (record) =>
          record.id === selectedRecordId
      ) ||
      filteredRecords[0] ||
      null
    );
  }, [
    records,
    selectedRecordId,
    filteredRecords,
  ]);

  // ============================================================
  // RESTORE CONTEXT
  // ============================================================

  const handleRestoreContext = () => {
    if (!selectedRecord) return;

    setRestoring(true);

    if (selectedRecord.conversationId) {
      window.location.href = `/chat?conversation=${encodeURIComponent(
        selectedRecord.conversationId
      )}`;
      return;
    }

    window.location.href = "/chat";
  };

  // ============================================================
  // EXPORT
  // ============================================================

  const handleExport = () => {
    if (!selectedRecord) return;

    setExporting(true);

    try {
      const exportData = {
        exportedAt: new Date().toISOString(),
        product: "KING ZARRY AI",
        record: selectedRecord,
      };

      const blob = new Blob(
        [JSON.stringify(exportData, null, 2)],
        {
          type: "application/json",
        }
      );

      const url =
        URL.createObjectURL(blob);

      const anchor =
        document.createElement("a");

      anchor.href = url;

      anchor.download = `king-zarry-history-${selectedRecord.id}.json`;

      document.body.appendChild(anchor);

      anchor.click();

      anchor.remove();

      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  // ============================================================
  // REFRESH
  // ============================================================

  const handleRefresh = () => {
    setRefreshing(true);
    loadHistory();
  };

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="relative w-full min-h-screen bg-[#03060a] text-cyan-100 font-sans overflow-x-hidden flex flex-col selection:bg-cyan-500 selection:text-black">

      {/* Background Atmosphere */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#072438] via-[#020b14] to-[#010408] pointer-events-none" />

      <div className="fixed inset-0 bg-[linear-gradient(to_right,#091a2815_1px,transparent_1px),linear-gradient(to_bottom,#091a2815_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />

      <div className="fixed inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,240,255,0.012)_3px,transparent_4px)] pointer-events-none z-10" />

      <div className="fixed top-[-10%] left-[25%] w-[600px] h-[600px] bg-cyan-600/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="fixed bottom-[-10%] right-[20%] w-[600px] h-[600px] bg-indigo-600/10 rounded-full blur-[140px] pointer-events-none" />

      {/* ====================================================== */}
      {/* HEADER */}
      {/* ====================================================== */}

      <header className="relative z-20 flex items-center justify-between px-6 py-4 border-b border-cyan-500/15 bg-[#030810]/80 backdrop-blur-md">

        <div className="flex items-center space-x-4">

          <div className="relative flex items-center justify-center w-10 h-10 rounded-lg border border-cyan-500/40 bg-cyan-950/30 text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
            <span className="font-extrabold text-lg tracking-wider">
              KZ
            </span>

            <span className="absolute -top-1 -right-1 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500" />
            </span>
          </div>

          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-base font-bold tracking-widest text-white uppercase">
                KING ZARRY AI
              </h1>

              <span className="px-1.5 py-0.5 text-[9px] font-mono tracking-wider text-cyan-400 border border-cyan-500/30 bg-cyan-950/40 rounded">
                INTELLIGENCE HISTORY
              </span>
            </div>

            <div className="flex items-center space-x-2 text-[10px] font-mono text-cyan-400/70">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />

              <span>
                MEMORY CORE ONLINE
              </span>

              <span className="text-cyan-700">
                •
              </span>

              <span>
                INDEXED NODES:{" "}
                {hudStats.nodesConnected}
              </span>
            </div>
          </div>
        </div>

        {/* Desktop navigation */}
        <nav className="hidden lg:flex items-center space-x-1 bg-cyan-950/20 p-1 rounded-lg border border-cyan-500/10">
          {navItems.map((item) => {
            const isActive =
              item.label === "HISTORY";

            return (
              <Link
                key={item.label}
                href={item.href}
                className={`px-3 py-1.5 text-xs font-mono tracking-wider transition-all duration-200 rounded ${
                  isActive
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_10px_rgba(0,240,255,0.2)]"
                    : "text-cyan-400/60 hover:text-cyan-200 hover:bg-cyan-500/10"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Stats + mobile */}
        <div className="flex items-center space-x-4">

          <div className="hidden xl:flex items-center space-x-4 text-[10px] font-mono text-cyan-400/60 border-l border-cyan-500/15 pl-4">
            <div>
              MEMORIES:{" "}
              <span className="text-cyan-300">
                {hudStats.aiMemories}
              </span>
            </div>

            <div>
              ANALYSES:{" "}
              <span className="text-cyan-300">
                {hudStats.analyses}
              </span>
            </div>
          </div>

          <button
            onClick={() =>
              setMobileMenuOpen(
                !mobileMenuOpen
              )
            }
            className="lg:hidden p-2 rounded border border-cyan-500/30 text-cyan-400 bg-cyan-950/40 hover:bg-cyan-500/20"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {mobileMenuOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>
      </header>

      {/* ====================================================== */}
      {/* MOBILE NAV */}
      {/* ====================================================== */}

      {mobileMenuOpen && (
        <div className="lg:hidden relative z-30 bg-[#040c16]/95 border-b border-cyan-500/30 p-4 backdrop-blur-xl">

          <div className="grid grid-cols-3 gap-2">

            {navItems.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                onClick={() =>
                  setMobileMenuOpen(false)
                }
                className={`p-2 text-xs font-mono text-center rounded border ${
                  item.label === "HISTORY"
                    ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/50"
                    : "border-cyan-500/10 text-cyan-400/70 hover:bg-cyan-500/10"
                }`}
              >
                {item.label}
              </Link>
            ))}

          </div>
        </div>
      )}

      {/* ====================================================== */}
      {/* MAIN */}
      {/* ====================================================== */}

      <main className="relative z-20 flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-6">

        {/* Title */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyan-500/10 pb-4">

          <div>
            <h2 className="text-xl md:text-2xl font-bold tracking-widest text-white uppercase">
              INTELLIGENCE HISTORY
            </h2>

            <p className="text-xs font-mono text-cyan-400/60 mt-1">
              Your conversations, analyses, signals and important AI activity, organized in one memory archive.
            </p>
          </div>

          <div className="p-3 rounded-lg border border-cyan-500/20 bg-cyan-950/20 backdrop-blur-md max-w-md">

            <div className="flex items-center justify-between text-[10px] font-mono text-cyan-400/80 mb-1">
              <span className="font-bold tracking-wider">
                AI MEMORY INSIGHT
              </span>

              <span className="text-cyan-400">
                INDEX: LIVE
              </span>
            </div>

            <p className="text-xs text-cyan-200">
              Your history is connected to your personal web AI memory and conversation archive.
            </p>
          </div>
        </div>

        {/* ================================================== */}
        {/* AUTH REQUIRED */}
        {/* ================================================== */}

        {authRequired && (
          <div className="rounded-xl border border-yellow-500/30 bg-yellow-950/20 p-6 text-center">

            <div className="text-yellow-300 font-mono text-sm font-bold mb-2">
              AUTHENTICATION REQUIRED
            </div>

            <p className="text-xs text-yellow-200/70 font-mono mb-4">
              Sign in to access your private intelligence history.
            </p>

            <Link
              href="/login"
              className="inline-flex px-5 py-2 rounded-lg bg-cyan-400 text-black text-xs font-mono font-bold hover:bg-cyan-300 transition"
            >
              SIGN IN
            </Link>
          </div>
        )}

        {/* ================================================== */}
        {/* ERROR */}
        {/* ================================================== */}

        {error && !authRequired && (
          <div className="rounded-xl border border-red-500/30 bg-red-950/20 p-4">

            <div className="flex items-center justify-between gap-4">

              <div>
                <div className="text-red-300 font-mono text-xs font-bold">
                  HISTORY CORE ERROR
                </div>

                <div className="text-red-200/60 font-mono text-[10px] mt-1">
                  {error}
                </div>
              </div>

              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="px-3 py-1.5 rounded border border-red-400/30 text-red-300 text-[10px] font-mono hover:bg-red-500/10 disabled:opacity-50"
              >
                {refreshing
                  ? "RETRYING..."
                  : "RETRY"}
              </button>
            </div>
          </div>
        )}

        {/* ================================================== */}
        {/* MEMORY CORE */}
        {/* ================================================== */}

        <div className="relative rounded-2xl border border-cyan-500/20 bg-[#020914]/80 p-6 backdrop-blur-md overflow-hidden flex flex-col md:flex-row items-center justify-between gap-6">

          <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff08_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff08_1px,transparent_1px)] bg-[size:16px_16px]" />

          {/* Core */}
          <div className="relative z-10 flex flex-col items-center justify-center w-full md:w-1/3">

            <div className="relative w-36 h-36 flex items-center justify-center">

              <div className="absolute inset-0 rounded-full border border-cyan-500/30 animate-[spin_20s_linear_infinite]" />

              <div className="absolute inset-2 rounded-full border border-dashed border-cyan-400/20 animate-[spin_14s_linear_infinite_reverse]" />

              <div className="absolute inset-5 rounded-full bg-cyan-500/10 blur-md animate-pulse shadow-[0_0_25px_rgba(0,240,255,0.3)]" />

              <div className="relative z-10 flex flex-col items-center justify-center w-16 h-16 rounded-full bg-[#031322] border border-cyan-400/60 shadow-[inset_0_0_15px_rgba(0,240,255,0.4)]">
                <span className="font-extrabold text-lg tracking-tighter text-white">
                  KZ
                </span>

                <span className="text-[8px] font-mono tracking-widest text-cyan-400/80 -mt-1">
                  CORE
                </span>
              </div>

              <div className="absolute w-full h-full animate-[spin_8s_linear_infinite]">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-300 shadow-[0_0_8px_#00f0ff] absolute top-0 left-1/2 -translate-x-1/2" />
              </div>

              <div className="absolute w-full h-full animate-[spin_12s_linear_infinite_reverse]">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 shadow-[0_0_8px_#818cf8] absolute bottom-0 left-1/2 -translate-x-1/2" />
              </div>
            </div>

            <div className="mt-2 text-center">
              <span className="text-xs font-mono font-bold tracking-widest text-cyan-200 uppercase">
                MEMORY CORE
              </span>

              <div className="text-[9px] font-mono text-cyan-500/70">
                CONVERSATIONS → MEMORY → CONTEXT → INTELLIGENCE
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 gap-3 w-full md:w-2/3">

            <div className="p-3.5 rounded-xl border border-cyan-500/15 bg-cyan-950/20 text-center space-y-1">
              <span className="text-[10px] font-mono text-cyan-400/60 tracking-wider uppercase block">
                CONVERSATIONS
              </span>

              <span className="text-xl font-bold font-mono text-white tracking-wider">
                {hudStats.conversations}
              </span>

              <span className="text-[9px] font-mono text-cyan-500/50 block">
                LIVE DATABASE
              </span>
            </div>

            <div className="p-3.5 rounded-xl border border-cyan-500/15 bg-cyan-950/20 text-center space-y-1">
              <span className="text-[10px] font-mono text-cyan-400/60 tracking-wider uppercase block">
                AI MEMORIES
              </span>

              <span className="text-xl font-bold font-mono text-cyan-300 tracking-wider">
                {hudStats.aiMemories}
              </span>

              <span className="text-[9px] font-mono text-cyan-500/50 block">
                STORED CONTEXT
              </span>
            </div>

            <div className="p-3.5 rounded-xl border border-cyan-500/15 bg-cyan-950/20 text-center space-y-1">
              <span className="text-[10px] font-mono text-cyan-400/60 tracking-wider uppercase block">
                ANALYSES
              </span>

              <span className="text-xl font-bold font-mono text-indigo-300 tracking-wider">
                {hudStats.analyses}
              </span>

              <span className="text-[9px] font-mono text-cyan-500/50 block">
                INDEXED
              </span>
            </div>

            <div className="p-3.5 rounded-xl border border-cyan-500/15 bg-cyan-950/20 text-center space-y-1">
              <span className="text-[10px] font-mono text-cyan-400/60 tracking-wider uppercase block">
                SAVED ITEMS
              </span>

              <span className="text-xl font-bold font-mono text-emerald-300 tracking-wider">
                {hudStats.savedItems}
              </span>

              <span className="text-[9px] font-mono text-cyan-500/50 block">
                SAVED
              </span>
            </div>

          </div>
        </div>

        {/* ================================================== */}
        {/* CONTROLS */}
        {/* ================================================== */}

        <div className="flex flex-col md:flex-row items-center justify-between gap-3 p-3 rounded-xl border border-cyan-500/20 bg-[#020914]/80 backdrop-blur-md">

          <div className="relative w-full md:w-96 flex items-center">

            <svg
              className="absolute left-3 w-4 h-4 text-cyan-400/60"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>

            <input
              type="text"
              value={searchQuery}
              onChange={(event) =>
                setSearchQuery(
                  event.target.value
                )
              }
              placeholder="Search your intelligence history..."
              className="w-full py-2 pl-9 pr-4 bg-cyan-950/30 border border-cyan-500/30 focus:border-cyan-400 rounded-lg text-xs text-white placeholder-cyan-500/40 focus:outline-none transition shadow-[inset_0_0_10px_rgba(0,240,255,0.05)] font-mono"
            />
          </div>

          <div className="flex items-center space-x-2 w-full md:w-auto justify-between md:justify-end overflow-x-auto pb-1 md:pb-0">

            <div className="flex items-center space-x-1 bg-cyan-950/40 p-1 rounded-lg border border-cyan-500/15">

              {(
                [
                  "TODAY",
                  "7 DAYS",
                  "30 DAYS",
                  "ALL TIME",
                ] as TimeFilter[]
              ).map((tf) => (
                <button
                  key={tf}
                  onClick={() =>
                    setTimeFilter(tf)
                  }
                  className={`px-2.5 py-1 text-[10px] font-mono rounded transition ${
                    timeFilter === tf
                      ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                      : "text-cyan-400/60 hover:text-cyan-200"
                  }`}
                >
                  {tf}
                </button>
              ))}

            </div>

            <button
              onClick={() =>
                setSortOrder(
                  sortOrder === "NEWEST"
                    ? "OLDEST"
                    : "NEWEST"
                )
              }
              className="px-3 py-1.5 rounded-lg text-[10px] font-mono text-cyan-300 border border-cyan-500/30 bg-cyan-950/30 hover:bg-cyan-500/10 transition whitespace-nowrap"
            >
              {sortOrder === "NEWEST"
                ? "↓ NEWEST"
                : "↑ OLDEST"}
            </button>

            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="px-3 py-1.5 rounded-lg text-[10px] font-mono text-cyan-300 border border-cyan-500/30 bg-cyan-950/30 hover:bg-cyan-500/10 transition whitespace-nowrap disabled:opacity-50"
            >
              {refreshing
                ? "SYNC..."
                : "↻ SYNC"}
            </button>
          </div>
        </div>

        {/* ================================================== */}
        {/* CATEGORIES */}
        {/* ================================================== */}

        <div className="flex items-center space-x-1 overflow-x-auto pb-1 scrollbar-none">

          {categories.map((cat) => {
            const isActive =
              selectedCategory === cat;

            return (
              <button
                key={cat}
                onClick={() =>
                  setSelectedCategory(cat)
                }
                className={`px-3 py-1.5 rounded-md text-xs font-mono tracking-wider transition-all whitespace-nowrap ${
                  isActive
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_10px_rgba(0,240,255,0.15)]"
                    : "text-cyan-400/50 hover:text-cyan-200 border border-transparent hover:bg-cyan-950/30"
                }`}
              >
                {cat}
              </button>
            );
          })}

        </div>

        {/* ================================================== */}
        {/* TIMELINE */}
        {/* ================================================== */}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          <div className="lg:col-span-7 space-y-3">

            {loading ? (
              <div className="p-10 text-center border border-cyan-500/10 rounded-xl font-mono text-xs text-cyan-400/60">
                <div className="animate-pulse">
                  CONNECTING TO MEMORY CORE...
                </div>

                <div className="text-[9px] mt-2 text-cyan-500/40">
                  LOADING PRIVATE INTELLIGENCE ARCHIVE
                </div>
              </div>
            ) : filteredRecords.length === 0 ? (
              <div className="p-10 text-center border border-cyan-500/10 rounded-xl font-mono">

                <div className="text-cyan-300 text-xs">
                  NO MEMORY RECORDS FOUND
                </div>

                <div className="text-cyan-500/40 text-[10px] mt-2">
                  {records.length === 0
                    ? "Your intelligence history is currently empty."
                    : "No records match your current search or filters."}
                </div>

              </div>
            ) : (
              filteredRecords.map(
                (rec) => {
                  const isSelected =
                    rec.id ===
                    selectedRecord?.id;

                  return (
                    <div
                      key={rec.id}
                      onClick={() =>
                        setSelectedRecordId(
                          rec.id
                        )
                      }
                      className={`relative rounded-xl p-4 transition-all duration-200 backdrop-blur-md border cursor-pointer ${
                        isSelected
                          ? "bg-cyan-950/40 border-cyan-400/50 shadow-[0_0_20px_rgba(0,240,255,0.15)]"
                          : "bg-[#020914]/70 border-cyan-500/15 hover:border-cyan-500/30 hover:bg-cyan-950/20"
                      }`}
                    >

                      <div
                        className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-xl ${
                          isSelected
                            ? "bg-cyan-400 shadow-[0_0_8px_#00f0ff]"
                            : "bg-transparent"
                        }`}
                      />

                      <div className="flex items-start justify-between gap-2 mb-1 pl-2">

                        <div className="flex items-center space-x-2 flex-wrap gap-y-1">

                          <span className="px-2 py-0.5 text-[9px] font-mono font-bold rounded bg-cyan-950/80 text-cyan-300 border border-cyan-500/30">
                            {rec.category}
                          </span>

                          <span className="text-[10px] font-mono text-cyan-400/50">
                            {rec.memoryId}
                          </span>

                        </div>

                        <span className="text-[10px] font-mono text-cyan-400/50 whitespace-nowrap">
                          {rec.timestamp}
                        </span>

                      </div>

                      <div className="pl-2 space-y-1">

                        <h3 className="text-sm font-bold tracking-wide text-white">
                          {rec.title}
                        </h3>

                        <p className="text-xs text-cyan-200/80 font-sans leading-relaxed">
                          {rec.description}
                        </p>

                      </div>

                      <div className="mt-3 pt-2 border-t border-cyan-500/10 pl-2 flex items-center justify-between gap-3 text-[10px] font-mono text-cyan-400/50">

                        <span className="truncate">
                          SOURCE:{" "}
                          {rec.source}
                        </span>

                        <span className="text-cyan-300 whitespace-nowrap">
                          {rec.status}
                        </span>

                      </div>
                    </div>
                  );
                }
              )
            )}

          </div>

          {/* ================================================== */}
          {/* DETAIL */}
          {/* ================================================== */}

          <div className="lg:col-span-5">

            <div className="sticky top-6 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md space-y-4 shadow-[0_0_25px_rgba(0,240,255,0.08)]">

              {selectedRecord ? (
                <>
                  <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">

                    <div className="flex items-center space-x-2">

                      <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />

                      <h3 className="text-xs font-mono font-bold text-white tracking-widest uppercase">
                        MEMORY RECORD
                      </h3>

                    </div>

                    <span className="text-[9px] font-mono text-cyan-400/60">
                      {selectedRecord.memoryId}
                    </span>
                  </div>

                  <div className="space-y-2 text-xs font-mono border-b border-cyan-500/15 pb-3">

                    <div className="flex justify-between gap-4">
                      <span className="text-cyan-500/70">
                        TYPE:
                      </span>

                      <span className="text-cyan-200 font-bold text-right">
                        {selectedRecord.category}
                      </span>
                    </div>

                    <div className="flex justify-between gap-4">
                      <span className="text-cyan-500/70">
                        DATE & TIME:
                      </span>

                      <span className="text-cyan-200 text-right">
                        {selectedRecord.timestamp}
                      </span>
                    </div>

                    <div className="flex justify-between gap-4">
                      <span className="text-cyan-500/70">
                        SOURCE NODE:
                      </span>

                      <span className="text-cyan-200 text-right">
                        {selectedRecord.source}
                      </span>
                    </div>

                    <div className="flex justify-between gap-4">
                      <span className="text-cyan-500/70">
                        STATUS:
                      </span>

                      <span className="text-emerald-400 font-bold text-right">
                        {selectedRecord.status}
                      </span>
                    </div>

                  </div>

                  <div className="space-y-2">

                    <span className="text-[10px] font-mono tracking-wider text-cyan-400/70 uppercase">
                      STORED CONTEXT PREVIEW
                    </span>

                    <div className="p-3 rounded-lg border border-cyan-500/20 bg-cyan-950/30 text-xs font-mono text-cyan-100 leading-relaxed">
                      "{selectedRecord.contextPreview}"
                    </div>

                  </div>

                  <div className="pt-2 flex items-center space-x-2">

                    <button
                      onClick={
                        handleRestoreContext
                      }
                      disabled={restoring}
                      className="flex-1 py-2 rounded-lg text-xs font-mono font-bold text-black bg-cyan-400 hover:bg-cyan-300 transition shadow-[0_0_10px_rgba(0,240,255,0.2)] disabled:opacity-50"
                    >
                      {restoring
                        ? "OPENING..."
                        : "RESTORE CONTEXT"}
                    </button>

                    <button
                      onClick={
                        handleExport
                      }
                      disabled={exporting}
                      className="px-3 py-2 rounded-lg text-xs font-mono text-cyan-300 border border-cyan-500/30 hover:bg-cyan-500/10 transition disabled:opacity-50"
                    >
                      {exporting
                        ? "..."
                        : "EXPORT"}
                    </button>

                  </div>

                  <div className="text-[9px] font-mono text-center text-cyan-500/50 pt-1">
                    LIVE DATABASE • PRIVATE USER ARCHIVE
                  </div>
                </>
              ) : (
                <div className="py-12 text-center">

                  <div className="text-cyan-300 text-xs font-mono">
                    NO RECORD SELECTED
                  </div>

                  <div className="text-cyan-500/40 text-[10px] font-mono mt-2">
                    Select an intelligence record to inspect its stored context.
                  </div>

                </div>
              )}

            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
