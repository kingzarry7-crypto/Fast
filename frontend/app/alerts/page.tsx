"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";

// ============================================================
// TYPES
// ============================================================

type AlertPriority = "CRITICAL" | "HIGH" | "MEDIUM" | "INFO";

type AlertCategory =
  | "ALL"
  | "MARKET"
  | "AI"
  | "NEWS"
  | "SYSTEM"
  | "AGENT"
  | "SECURITY";

interface AlertItem {
  id: string;
  category: Exclude<AlertCategory, "ALL">;
  priority: AlertPriority;
  title: string;
  description: string;
  timestamp: string;
  read: boolean;
  statusText: string;
}

// ============================================================
// PAGE
// ============================================================

export default function KingZarryAlertsPage() {
  const [selectedCategory, setSelectedCategory] =
    useState<AlertCategory>("ALL");

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  // ==========================================================
  // NAVIGATION
  // ==========================================================

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

  // ==========================================================
  // FILTER CATEGORIES
  // ==========================================================

  const categories: AlertCategory[] = [
    "ALL",
    "MARKET",
    "AI",
    "NEWS",
    "SYSTEM",
    "AGENT",
    "SECURITY",
  ];

  // ==========================================================
  // ACTIVE MONITORS
  // ==========================================================

  const activeMonitors = [
    {
      label: "BTC/USD",
      status: "READY",
    },
    {
      label: "ETH/USD",
      status: "READY",
    },
    {
      label: "SOL/USD",
      status: "READY",
    },
    {
      label: "XAU/USD",
      status: "READY",
    },
    {
      label: "GLOBAL NEWS",
      status: "READY",
    },
    {
      label: "AI CORE",
      status: "READY",
    },
    {
      label: "AGENT NETWORK",
      status: "READY",
    },
  ];

  // ==========================================================
  // REAL FILTERING
  // ==========================================================

  const filteredAlerts = useMemo(() => {
    if (selectedCategory === "ALL") {
      return alerts;
    }

    return alerts.filter(
      (alert) => alert.category === selectedCategory
    );
  }, [alerts, selectedCategory]);

  const unreadCount = useMemo(() => {
    return alerts.filter((alert) => !alert.read).length;
  }, [alerts]);

  // ==========================================================
  // MARK ALL READ
  // ==========================================================

  const markAllRead = () => {
    setAlerts((current) =>
      current.map((alert) => ({
        ...alert,
        read: true,
      }))
    );
  };

  // ==========================================================
  // MARK SINGLE ALERT READ
  // ==========================================================

  const markAlertRead = (id: string) => {
    setAlerts((current) =>
      current.map((alert) =>
        alert.id === id
          ? {
              ...alert,
              read: true,
            }
          : alert
      )
    );
  };

  // ==========================================================
  // PRIORITY COLORS
  // ==========================================================

  const getPriorityStyles = (
    priority: AlertPriority,
    read: boolean
  ) => {
    if (read) {
      return {
        container:
          "bg-[#020914]/60 border-cyan-500/10",
        accent: "bg-cyan-900",
        badge:
          "bg-cyan-950/50 text-cyan-400/60 border-cyan-500/10",
      };
    }

    switch (priority) {
      case "CRITICAL":
        return {
          container:
            "bg-red-950/20 border-red-500/40 shadow-[0_0_20px_rgba(239,68,68,0.12)]",
          accent:
            "bg-red-500 shadow-[0_0_10px_#ef4444]",
          badge:
            "bg-red-950/80 text-red-300 border-red-500/40",
        };

      case "HIGH":
        return {
          container:
            "bg-cyan-950/30 border-cyan-500/40 shadow-[0_0_15px_rgba(0,240,255,0.10)]",
          accent:
            "bg-cyan-400 shadow-[0_0_10px_#00f0ff]",
          badge:
            "bg-cyan-950/80 text-cyan-300 border-cyan-500/30",
        };

      case "MEDIUM":
        return {
          container:
            "bg-[#041120]/80 border-indigo-500/25",
          accent:
            "bg-indigo-400 shadow-[0_0_8px_#818cf8]",
          badge:
            "bg-indigo-950/50 text-indigo-300 border-indigo-500/30",
        };

      default:
        return {
          container:
            "bg-[#020914]/70 border-cyan-500/15",
          accent:
            "bg-cyan-700",
          badge:
            "bg-cyan-950/60 text-cyan-300 border-cyan-500/20",
        };
    }
  };

  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div className="relative min-h-screen w-full overflow-x-hidden bg-[#03060a] font-sans text-cyan-100 selection:bg-cyan-500 selection:text-black">

      {/* ======================================================
          BACKGROUND
      ====================================================== */}

      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#072438] via-[#020b14] to-[#010408]" />

      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(to_right,#091a2815_1px,transparent_1px),linear-gradient(to_bottom,#091a2815_1px,transparent_1px)] bg-[size:32px_32px]" />

      <div className="pointer-events-none fixed inset-0 z-10 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,240,255,0.012)_3px,transparent_4px)]" />

      <div className="pointer-events-none fixed left-[30%] top-[-10%] h-[600px] w-[600px] rounded-full bg-cyan-600/10 blur-[140px]" />

      <div className="pointer-events-none fixed bottom-[-10%] right-[20%] h-[600px] w-[600px] rounded-full bg-indigo-600/10 blur-[140px]" />

      {/* ======================================================
          HEADER
      ====================================================== */}

      <header className="relative z-20 flex items-center justify-between border-b border-cyan-500/15 bg-[#030810]/80 px-4 py-4 backdrop-blur-md md:px-6">

        {/* BRAND */}

        <Link
          href="/"
          className="flex items-center space-x-3"
        >
          <div className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-cyan-500/40 bg-cyan-950/30 text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.2)]">

            <span className="text-lg font-extrabold tracking-wider">
              KZ
            </span>

            <span className="absolute -right-1 -top-1 flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-500" />
            </span>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold uppercase tracking-widest text-white md:text-base">
                KING ZARRY AI
              </h1>

              <span className="hidden rounded border border-cyan-500/30 bg-cyan-950/40 px-1.5 py-0.5 font-mono text-[9px] tracking-wider text-cyan-400 sm:inline-block">
                INTELLIGENCE ALERTS
              </span>
            </div>

            <div className="flex items-center gap-2 font-mono text-[9px] text-cyan-400/70 md:text-[10px]">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />

              <span>
                ALERT CENTER ONLINE
              </span>

              <span className="text-cyan-700">
                •
              </span>

              <span>
                {unreadCount} UNREAD
              </span>
            </div>
          </div>
        </Link>

        {/* DESKTOP NAV */}

        <nav className="hidden items-center space-x-1 rounded-lg border border-cyan-500/10 bg-cyan-950/20 p-1 lg:flex">

          {navItems.map((item) => {
            const active = item.label === "ALERTS";

            return (
              <Link
                key={item.label}
                href={item.href}
                className={`rounded px-3 py-1.5 font-mono text-xs tracking-wider transition-all ${
                  active
                    ? "border border-cyan-500/40 bg-cyan-500/20 text-cyan-300 shadow-[0_0_10px_rgba(0,240,255,0.2)]"
                    : "text-cyan-400/60 hover:bg-cyan-500/10 hover:text-cyan-200"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* MOBILE BUTTON */}

        <button
          onClick={() =>
            setMobileMenuOpen((current) => !current)
          }
          className="rounded border border-cyan-500/30 bg-cyan-950/40 p-2 text-cyan-400 hover:bg-cyan-500/20 lg:hidden"
          aria-label="Open navigation"
        >
          <svg
            className="h-5 w-5"
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
      </header>

      {/* ======================================================
          MOBILE NAV
      ====================================================== */}

      {mobileMenuOpen && (
        <div className="relative z-30 border-b border-cyan-500/30 bg-[#040c16]/95 p-4 backdrop-blur-xl lg:hidden">

          <div className="grid grid-cols-3 gap-2">
            {navItems.map((item) => {
              const active = item.label === "ALERTS";

              return (
                <Link
                  key={item.label}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`rounded border p-2 text-center font-mono text-xs ${
                    active
                      ? "border-cyan-500/50 bg-cyan-500/20 text-cyan-300"
                      : "border-cyan-500/10 text-cyan-400/70 hover:bg-cyan-500/10"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* ======================================================
          MAIN
      ====================================================== */}

      <main className="relative z-20 mx-auto w-full max-w-7xl flex-1 space-y-6 p-4 md:p-6">

        {/* PAGE HEADER */}

        <div className="flex flex-col justify-between gap-4 border-b border-cyan-500/10 pb-4 md:flex-row md:items-center">

          <div>
            <h2 className="text-xl font-bold uppercase tracking-widest text-white md:text-2xl">
              INTELLIGENCE ALERTS
            </h2>

            <p className="mt-1 font-mono text-xs text-cyan-400/60">
              Signals, events and intelligence requiring your attention.
            </p>
          </div>

          {/* STATUS PANEL */}

          <div className="max-w-md rounded-lg border border-cyan-500/20 bg-cyan-950/20 p-3 backdrop-blur-md">

            <div className="mb-1 flex items-center justify-between font-mono text-[10px] text-cyan-400/80">
              <span className="font-bold tracking-wider">
                ALERT INTELLIGENCE
              </span>

              <span className="text-cyan-400">
                SECURE SESSION
              </span>
            </div>

            <p className="text-xs text-cyan-200">
              {alerts.length === 0
                ? "No alert records are currently stored for this account."
                : `${unreadCount} alert${unreadCount === 1 ? "" : "s"} require your attention.`}
            </p>
          </div>
        </div>

        {/* ====================================================
            MAIN GRID
        ==================================================== */}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">

          {/* ==================================================
              LEFT
          ================================================== */}

          <div className="flex flex-col space-y-6 lg:col-span-5">

            {/* ALERT CORE */}

            <div className="relative flex min-h-[320px] flex-col items-center justify-center overflow-hidden rounded-2xl border border-cyan-500/20 bg-[#020914]/80 p-6 backdrop-blur-md">

              <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff08_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff08_1px,transparent_1px)] bg-[size:16px_16px]" />

              <div className="relative my-4 flex h-44 w-44 items-center justify-center">

                <div className="absolute inset-0 animate-[spin_24s_linear_infinite] rounded-full border border-cyan-500/30" />

                <div className="absolute inset-2 animate-[spin_16s_linear_infinite_reverse] rounded-full border border-dashed border-cyan-400/20" />

                <div className="absolute inset-5 animate-[spin_6s_linear_infinite] rounded-full border-2 border-transparent border-r-cyan-400/40 border-t-cyan-400" />

                <div className="absolute inset-8 animate-pulse rounded-full bg-cyan-500/10 blur-md shadow-[0_0_30px_rgba(0,240,255,0.3)]" />

                <div className="relative z-10 flex h-20 w-20 flex-col items-center justify-center rounded-full border border-cyan-400/60 bg-[#031322] shadow-[inset_0_0_15px_rgba(0,240,255,0.4)]">

                  <span className="font-mono text-xs font-bold text-cyan-300">
                    ALERT
                  </span>

                  <span className="text-lg font-extrabold text-white">
                    CORE
                  </span>
                </div>

                <div className="absolute h-full w-full animate-[spin_10s_linear_infinite]">
                  <div className="absolute left-1/2 top-1 h-2 w-2 -translate-x-1/2 rounded-full bg-cyan-300 shadow-[0_0_10px_#00f0ff]" />
                </div>

                <div className="absolute h-full w-full animate-[spin_18s_linear_infinite_reverse]">
                  <div className="absolute bottom-2 left-1/2 h-2 w-2 -translate-x-1/2 rounded-full bg-indigo-400 shadow-[0_0_10px_#818cf8]" />
                </div>
              </div>

              <div className="relative z-10 mt-2 space-y-1 text-center">
                <div className="font-mono text-xs uppercase tracking-widest text-cyan-300">
                  ALERT CENTER
                </div>

                <div className="font-mono text-[10px] text-cyan-500/70">
                  USER-SCOPED INTELLIGENCE CHANNEL
                </div>
              </div>
            </div>

            {/* ACTIVE MONITORS */}

            <div className="space-y-3 rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-4 backdrop-blur-md">

              <div className="flex items-center justify-between border-b border-cyan-500/15 pb-2 font-mono text-xs text-cyan-400">

                <span className="font-bold uppercase tracking-wider">
                  ACTIVE MONITORS
                </span>

                <span className="text-[10px] text-cyan-500/60">
                  {activeMonitors.length} CHANNELS
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-2">

                {activeMonitors.map((monitor) => (
                  <div
                    key={monitor.label}
                    className="flex items-center justify-between rounded border border-cyan-500/15 bg-cyan-950/20 px-2.5 py-1.5 font-mono text-[11px]"
                  >
                    <span className="text-cyan-200">
                      {monitor.label}
                    </span>

                    <span className="flex items-center gap-1 text-[9px] text-cyan-400/70">
                      <span className="h-1 w-1 rounded-full bg-cyan-400" />
                      <span>{monitor.status}</span>
                    </span>
                  </div>
                ))}

              </div>
            </div>
          </div>

          {/* ==================================================
              RIGHT
          ================================================== */}

          <div className="flex flex-col space-y-4 lg:col-span-7">

            {/* COMMAND BAR */}

            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-3 backdrop-blur-md">

              <div className="flex flex-wrap items-center gap-2">

                <button
                  type="button"
                  disabled
                  className="cursor-not-allowed rounded-lg border border-cyan-500/20 bg-cyan-950/40 px-3 py-1.5 font-mono text-xs font-bold text-cyan-500/40"
                >
                  + CREATE ALERT
                </button>

                <button
                  type="button"
                  disabled
                  className="cursor-not-allowed rounded-lg border border-cyan-500/20 bg-cyan-950/20 px-3 py-1.5 font-mono text-xs text-cyan-500/40"
                >
                  MANAGE MONITORS
                </button>

              </div>

              <button
                type="button"
                onClick={markAllRead}
                disabled={unreadCount === 0}
                className={`rounded-lg px-3 py-1.5 font-mono text-xs transition ${
                  unreadCount > 0
                    ? "text-cyan-300 hover:bg-cyan-500/10"
                    : "cursor-not-allowed text-cyan-700/40"
                }`}
              >
                MARK ALL READ
              </button>
            </div>

            {/* CATEGORY FILTER */}

            <div className="flex items-center space-x-1 overflow-x-auto pb-1 scrollbar-none">

              {categories.map((category) => {
                const active =
                  selectedCategory === category;

                return (
                  <button
                    key={category}
                    type="button"
                    onClick={() =>
                      setSelectedCategory(category)
                    }
                    className={`whitespace-nowrap rounded-md px-3 py-1.5 font-mono text-xs tracking-wider transition-all ${
                      active
                        ? "border border-cyan-500/40 bg-cyan-500/20 text-cyan-300 shadow-[0_0_10px_rgba(0,240,255,0.15)]"
                        : "border border-transparent text-cyan-400/50 hover:bg-cyan-950/30 hover:text-cyan-200"
                    }`}
                  >
                    {category}
                  </button>
                );
              })}
            </div>

            {/* ALERT FEED */}

            <div className="space-y-3">

              {filteredAlerts.length === 0 ? (
                <div className="rounded-xl border border-cyan-500/15 bg-[#020914]/70 p-10 text-center">

                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-cyan-500/20 bg-cyan-950/30">

                    <svg
                      className="h-6 w-6 text-cyan-500/50"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                      />
                    </svg>

                  </div>

                  <div className="font-mono text-xs font-bold tracking-wider text-cyan-300">
                    NO ALERT RECORDS
                  </div>

                  <p className="mx-auto mt-2 max-w-md font-mono text-[10px] leading-relaxed text-cyan-500/50">
                    {selectedCategory === "ALL"
                      ? "Your account currently has no stored alert records."
                      : `No ${selectedCategory.toLowerCase()} alerts are currently available.`}
                  </p>

                </div>
              ) : (
                filteredAlerts.map((alert) => {

                  const styles = getPriorityStyles(
                    alert.priority,
                    alert.read
                  );

                  return (
                    <button
                      key={alert.id}
                      type="button"
                      onClick={() =>
                        markAlertRead(alert.id)
                      }
                      className={`relative w-full rounded-xl border p-4 text-left backdrop-blur-md transition-all duration-300 ${styles.container}`}
                    >

                      {/* ACCENT */}

                      <div
                        className={`absolute bottom-0 left-0 top-0 w-1 rounded-l-xl ${styles.accent}`}
                      />

                      {/* META */}

                      <div className="mb-1 flex items-start justify-between gap-2 pl-2">

                        <div className="flex items-center space-x-2">

                          <span
                            className={`rounded border px-2 py-0.5 font-mono text-[9px] font-bold ${styles.badge}`}
                          >
                            {alert.category}
                          </span>

                          <span className="font-mono text-[9px] tracking-widest text-cyan-400/70">
                            {alert.priority}
                          </span>

                        </div>

                        <span className="font-mono text-[10px] text-cyan-400/50">
                          {alert.timestamp}
                        </span>

                      </div>

                      {/* CONTENT */}

                      <div className="space-y-1 pl-2">

                        <h3 className="text-sm font-bold tracking-wide text-white">
                          {alert.title}
                        </h3>

                        <p className="font-sans text-xs leading-relaxed text-cyan-200/80">
                          {alert.description}
                        </p>

                      </div>

                      {/* FOOTER */}

                      <div className="mt-3 flex items-center justify-between border-t border-cyan-500/10 pl-2 pt-2 font-mono text-[10px] text-cyan-400/50">

                        <span>
                          {alert.statusText}
                        </span>

                        {!alert.read && (
                          <span className="text-cyan-300">
                            ● UNREAD
                          </span>
                        )}

                      </div>

                    </button>
                  );
                })
              )}

            </div>

          </div>
        </div>
      </main>
    </div>
  );
}
