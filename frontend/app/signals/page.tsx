"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";

type Direction = "BUY" | "SELL" | "WAIT";
type Control =
  | "ANALYZE MARKET"
  | "CHANGE MARKET"
  | "CHANGE TIMEFRAME"
  | "SIGNAL HISTORY"
  | "SIGNAL SETTINGS"
  | null;

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://fast-production-0eba.up.railway.app";

const navRoutes: Record<string, string> = {
  HOME: "/",
  CHAT: "/chat",
  MARKETS: "/markets",
  SIGNALS: "/signals",
  NEWS: "/news",
  ALERTS: "/alerts",
  HISTORY: "/history",
  MEMORY: "/history",
  PRICING: "/pricing",
  SETTINGS: "/settings",
};

const navItems = [
  "HOME",
  "CHAT",
  "VISION",
  "AGENTS",
  "TOOLS",
  "MARKETS",
  "SIGNALS",
  "NEWS",
  "ALERTS",
  "HISTORY",
  "MEMORY",
  "PRICING",
  "SETTINGS",
];

const markets = [
  "BTC/USD",
  "ETH/USD",
  "SOL/USD",
  "XAU/USD",
  "EUR/USD",
  "GBP/USD",
];

const timeframes = ["4H", "1H", "15M", "5M", "1M"];

const coreInputs = [
  "STRUCTURE",
  "MOMENTUM",
  "RSI",
  "EMA",
  "ATR",
  "VOLUME",
  "VOLATILITY",
  "MULTI-TIMEFRAME",
];

const analysisInputsList = [
  { name: "EMA 9 / 21 / 50", status: "INPUT" },
  { name: "RSI 14", status: "INPUT" },
  { name: "ATR 14", status: "INPUT" },
  { name: "MARKET STRUCTURE", status: "INPUT" },
  { name: "SWING LEVELS", status: "INPUT" },
  { name: "MOMENTUM", status: "INPUT" },
  { name: "VOLATILITY", status: "INPUT" },
];

const defaultMultiTimeframes = [
  { tf: "4H", regime: "UNAVAILABLE", desc: "MAJOR REGIME" },
  { tf: "1H", regime: "UNAVAILABLE", desc: "DIRECTIONAL" },
  { tf: "15M", regime: "UNAVAILABLE", desc: "PRIMARY SETUP" },
  { tf: "5M", regime: "UNAVAILABLE", desc: "ENTRY TIMING" },
];

function getDirectionStyle(direction: Direction) {
  if (direction === "BUY") {
    return {
      text: "text-emerald-400",
      border: "border-emerald-500/40",
      bg: "bg-emerald-500/10",
    };
  }

  if (direction === "SELL") {
    return {
      text: "text-red-400",
      border: "border-red-500/40",
      bg: "bg-red-500/10",
    };
  }

  return {
    text: "text-yellow-300",
    border: "border-yellow-500/40",
    bg: "bg-yellow-500/10",
  };
}

export default function KingZarrySignalsPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [selectedMarket, setSelectedMarket] = useState("BTC/USD");
  const [selectedTimeframe, setSelectedTimeframe] = useState("15M");
  const [activeControl, setActiveControl] = useState<Control>(null);

  const [direction, setDirection] = useState<Direction>("WAIT");
  const [analysisText, setAnalysisText] = useState(
    "No live signal has been generated for this session."
  );

  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [lastAnalyzed, setLastAnalyzed] = useState("");

  const [showSettings, setShowSettings] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const directionStyle = useMemo(
    () => getDirectionStyle(direction),
    [direction]
  );

  const runAnalysis = async () => {
    setAnalysisLoading(true);
    setAnalysisError("");
    setActiveControl("ANALYZE MARKET");

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: `Analyze ${selectedMarket} on the ${selectedTimeframe} timeframe.

This is a trading-analysis request.

Use available market data/tools if available. Do NOT invent a live price or market condition.

Return:
1. Direction: BUY, SELL, or WAIT
2. Market structure
3. Momentum
4. RSI
5. EMA 9/21/50
6. ATR
7. Volatility
8. Multi-timeframe context
9. Entry condition
10. Stop loss condition
11. TP1 condition
12. TP2 condition
13. TP3 condition
14. Confidence level
15. Short explanation

If reliable live market data is unavailable, clearly say that the signal cannot be confirmed and return WAIT.`,
        }),
      });

      if (response.status === 401) {
        setAnalysisError("Authentication required. Please log in first.");
        setDirection("WAIT");
        return;
      }

      if (!response.ok) {
        throw new Error(`Signal request failed with status ${response.status}`);
      }

      const data = await response.json();

      const reply =
        data?.reply ??
        data?.response ??
        data?.message ??
        data?.content ??
        "";

      if (!reply) {
        throw new Error("The AI returned an empty analysis.");
      }

      setAnalysisText(String(reply));
      setLastAnalyzed(new Date().toLocaleTimeString());

      const upperReply = String(reply).toUpperCase();

      if (
        /\bWAIT\b/.test(upperReply) &&
        !/\bBUY\b/.test(upperReply) &&
        !/\bSELL\b/.test(upperReply)
      ) {
        setDirection("WAIT");
      } else if (/\bBUY\b/.test(upperReply)) {
        setDirection("BUY");
      } else if (/\bSELL\b/.test(upperReply)) {
        setDirection("SELL");
      } else {
        setDirection("WAIT");
      }
    } catch (error) {
      console.error("Signal analysis error:", error);

      setDirection("WAIT");
      setAnalysisError(
        error instanceof Error
          ? error.message
          : "Unable to generate the analysis."
      );
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleMarketChange = (market: string) => {
    setSelectedMarket(market);
    setDirection("WAIT");
    setAnalysisText(
      "Market changed. Run analysis to request a new signal."
    );
    setLastAnalyzed("");
    setAnalysisError("");
    setActiveControl("CHANGE MARKET");
  };

  const handleTimeframeChange = (timeframe: string) => {
    setSelectedTimeframe(timeframe);
    setDirection("WAIT");
    setAnalysisText(
      "Timeframe changed. Run analysis to request a new signal."
    );
    setLastAnalyzed("");
    setAnalysisError("");
    setActiveControl("CHANGE TIMEFRAME");
  };

  const openHistory = () => {
    setActiveControl("SIGNAL HISTORY");
    window.location.href = "/history";
  };

  const closeMobileMenu = () => {
    setMobileMenuOpen(false);
  };

  return (
    <div className="relative min-h-screen w-full overflow-x-hidden bg-[#03060a] font-sans text-cyan-100 selection:bg-cyan-500 selection:text-black">
      {/* BACKGROUND */}
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#072438] via-[#020b14] to-[#010408]" />
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(to_right,#091a2815_1px,transparent_1px),linear-gradient(to_bottom,#091a2815_1px,transparent_1px)] bg-[size:32px_32px]" />
      <div className="pointer-events-none fixed inset-0 z-10 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,240,255,0.012)_3px,transparent_4px)]" />

      <div className="pointer-events-none fixed left-[20%] top-[-10%] h-[600px] w-[600px] rounded-full bg-cyan-600/10 blur-[140px]" />
      <div className="pointer-events-none fixed bottom-[-10%] right-[20%] h-[600px] w-[600px] rounded-full bg-indigo-600/10 blur-[140px]" />

      {/* HEADER */}
      <header className="relative z-20 flex items-center justify-between border-b border-cyan-500/15 bg-[#030810]/80 px-6 py-4 backdrop-blur-md">
        <Link href="/" className="flex items-center space-x-4">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-cyan-500/40 bg-cyan-950/30 text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
            <span className="text-lg font-extrabold tracking-wider">KZ</span>

            <span className="absolute -right-1 -top-1 flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-500" />
            </span>
          </div>

          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-base font-bold uppercase tracking-widest text-white">
                KING ZARRY AI
              </h1>

              <span className="rounded border border-cyan-500/30 bg-cyan-950/40 px-1.5 py-0.5 font-mono text-[9px] tracking-wider text-cyan-400">
                MARKET INTELLIGENCE
              </span>
            </div>

            <div className="flex items-center space-x-2 font-mono text-[10px] text-cyan-400/70">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
              <span>SIGNAL WORKSPACE</span>
              <span className="text-cyan-700">•</span>
              <span>AI ANALYSIS</span>
            </div>
          </div>
        </Link>

        {/* DESKTOP NAV */}
        <nav className="hidden items-center space-x-1 rounded-lg border border-cyan-500/10 bg-cyan-950/20 p-1 lg:flex">
          {navItems.map((item) => {
            const href = navRoutes[item];
            const isActive = item === "SIGNALS";

            if (!href) {
              return (
                <span
                  key={item}
                  title={`${item} module is not connected yet`}
                  className="cursor-not-allowed rounded px-3 py-1.5 font-mono text-xs tracking-wider text-cyan-400/30"
                >
                  {item}
                </span>
              );
            }

            return (
              <Link
                key={item}
                href={href}
                className={`rounded px-3 py-1.5 font-mono text-xs tracking-wider transition-all duration-200 ${
                  isActive
                    ? "border border-cyan-500/40 bg-cyan-500/20 text-cyan-300 shadow-[0_0_10px_rgba(0,240,255,0.2)]"
                    : "text-cyan-400/60 hover:bg-cyan-500/10 hover:text-cyan-200"
                }`}
              >
                {item}
              </Link>
            );
          })}
        </nav>

        {/* MOBILE BUTTON */}
        <button
          onClick={() => setMobileMenuOpen((value) => !value)}
          aria-label="Toggle navigation"
          className="rounded border border-cyan-500/30 bg-cyan-950/40 p-2 text-cyan-400 hover:bg-cyan-500/20 lg:hidden"
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

      {/* MOBILE NAV */}
      {mobileMenuOpen && (
        <div className="relative z-30 border-b border-cyan-500/30 bg-[#040c16]/95 p-4 backdrop-blur-xl lg:hidden">
          <div className="grid grid-cols-3 gap-2">
            {navItems.map((item) => {
              const href = navRoutes[item];

              if (!href) {
                return (
                  <span
                    key={item}
                    className="cursor-not-allowed rounded border border-cyan-500/10 p-2 text-center font-mono text-xs text-cyan-400/30"
                  >
                    {item}
                  </span>
                );
              }

              return (
                <Link
                  key={item}
                  href={href}
                  onClick={closeMobileMenu}
                  className={`rounded border p-2 text-center font-mono text-xs ${
                    item === "SIGNALS"
                      ? "border-cyan-500/50 bg-cyan-500/20 text-cyan-300"
                      : "border-cyan-500/10 text-cyan-400/70 hover:bg-cyan-500/10"
                  }`}
                >
                  {item}
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* MAIN */}
      <main className="relative z-20 mx-auto w-full max-w-7xl flex-1 space-y-6 p-4 md:p-6">
        {/* PAGE HEADER */}
        <div className="flex flex-col justify-between gap-4 border-b border-cyan-500/10 pb-4 md:flex-row md:items-center">
          <div>
            <div className="mb-1 flex items-center space-x-2">
              <span className="font-mono text-[10px] uppercase tracking-widest text-cyan-400/60">
                KING ZARRY AI
              </span>
              <span className="text-cyan-700">/</span>
              <span className="font-mono text-[10px] uppercase tracking-widest text-cyan-400">
                SIGNAL ENGINE
              </span>
            </div>

            <h2 className="flex items-center space-x-3 text-xl font-bold uppercase tracking-widest text-white md:text-2xl">
              SIGNAL INTELLIGENCE
            </h2>

            <p className="mt-1 font-mono text-xs text-cyan-400/60">
              Request AI-assisted market analysis for the selected instrument
              and timeframe.
            </p>
          </div>

          <div className="flex items-center space-x-3 rounded-lg border border-cyan-500/20 bg-cyan-950/25 p-3 backdrop-blur-md">
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                analysisLoading ? "animate-pulse bg-yellow-300" : "bg-cyan-500"
              }`}
            />

            <div className="font-mono text-xs">
              <span className="text-cyan-400/60">WORKSPACE: </span>

              <strong className="tracking-wider text-cyan-300">
                {analysisLoading ? "ANALYZING" : "READY"}
              </strong>
            </div>
          </div>
        </div>

        {/* CONTROL BAR */}
        <div className="flex items-center justify-between gap-2 overflow-x-auto rounded-xl border-y border-cyan-500/15 bg-cyan-950/10 px-4 py-2">
          <div className="flex min-w-max items-center space-x-2">
            <span className="mr-2 font-mono text-[10px] uppercase tracking-widest text-cyan-400/50">
              CONTROLS:
            </span>

            <button
              onClick={runAnalysis}
              disabled={analysisLoading}
              className={`rounded-lg border px-3 py-1.5 font-mono text-xs transition ${
                activeControl === "ANALYZE MARKET"
                  ? "border-cyan-400 bg-cyan-500/25 text-cyan-300 shadow-[0_0_10px_rgba(0,240,255,0.2)]"
                  : "border-cyan-500/20 bg-cyan-950/30 text-cyan-400/70 hover:bg-cyan-500/10 hover:text-cyan-200"
              } disabled:cursor-wait disabled:opacity-60`}
            >
              {analysisLoading ? "ANALYZING..." : "ANALYZE MARKET"}
            </button>

            <button
              onClick={() => setActiveControl("CHANGE MARKET")}
              className={`rounded-lg border px-3 py-1.5 font-mono text-xs transition ${
                activeControl === "CHANGE MARKET"
                  ? "border-cyan-400 bg-cyan-500/25 text-cyan-300"
                  : "border-cyan-500/20 bg-cyan-950/30 text-cyan-400/70 hover:bg-cyan-500/10"
              }`}
            >
              CHANGE MARKET
            </button>

            <button
              onClick={() => setActiveControl("CHANGE TIMEFRAME")}
              className={`rounded-lg border px-3 py-1.5 font-mono text-xs transition ${
                activeControl === "CHANGE TIMEFRAME"
                  ? "border-cyan-400 bg-cyan-500/25 text-cyan-300"
                  : "border-cyan-500/20 bg-cyan-950/30 text-cyan-400/70 hover:bg-cyan-500/10"
              }`}
            >
              CHANGE TIMEFRAME
            </button>

            <button
              onClick={openHistory}
              className="rounded-lg border border-cyan-500/20 bg-cyan-950/30 px-3 py-1.5 font-mono text-xs text-cyan-400/70 transition hover:bg-cyan-500/10 hover:text-cyan-200"
            >
              SIGNAL HISTORY
            </button>

            <button
              onClick={() => {
                setActiveControl("SIGNAL SETTINGS");
                setShowSettings((value) => !value);
              }}
              className={`rounded-lg border px-3 py-1.5 font-mono text-xs transition ${
                activeControl === "SIGNAL SETTINGS"
                  ? "border-cyan-400 bg-cyan-500/25 text-cyan-300"
                  : "border-cyan-500/20 bg-cyan-950/30 text-cyan-400/70 hover:bg-cyan-500/10"
              }`}
            >
              SIGNAL SETTINGS
            </button>
          </div>

          <span className="hidden whitespace-nowrap font-mono text-[10px] text-cyan-500/50 xl:inline">
            WEB SIGNAL WORKSPACE
          </span>
        </div>

        {/* SETTINGS PANEL */}
        {showSettings && (
          <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <h3 className="font-mono text-xs font-bold tracking-widest text-white">
                  SIGNAL WORKSPACE SETTINGS
                </h3>
                <p className="mt-1 font-mono text-[10px] text-cyan-400/60">
                  These controls affect this browser session only.
                </p>
              </div>

              <label className="flex cursor-pointer items-center gap-3 font-mono text-xs text-cyan-200">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(event) => setAutoRefresh(event.target.checked)}
                  className="h-4 w-4 accent-cyan-400"
                />
                AUTO REFRESH
              </label>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-cyan-500/20 bg-cyan-950/25 p-3">
                <span className="block font-mono text-[9px] text-cyan-400/50">
                  MARKET
                </span>
                <span className="font-mono text-sm font-bold text-cyan-200">
                  {selectedMarket}
                </span>
              </div>

              <div className="rounded-xl border border-cyan-500/20 bg-cyan-950/25 p-3">
                <span className="block font-mono text-[9px] text-cyan-400/50">
                  TIMEFRAME
                </span>
                <span className="font-mono text-sm font-bold text-cyan-200">
                  {selectedTimeframe}
                </span>
              </div>

              <div className="rounded-xl border border-cyan-500/20 bg-cyan-950/25 p-3">
                <span className="block font-mono text-[9px] text-cyan-400/50">
                  LAST ANALYSIS
                </span>
                <span className="font-mono text-sm font-bold text-cyan-200">
                  {lastAnalyzed || "NONE"}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* SELECTORS */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <div className="rounded-2xl border border-cyan-500/20 bg-[#020914]/80 p-4 backdrop-blur-md lg:col-span-8">
            <div className="mb-2 font-mono text-[10px] font-bold uppercase tracking-widest text-cyan-400/60">
              MARKET SELECTOR
            </div>

            <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
              {markets.map((market) => {
                const selected = selectedMarket === market;

                return (
                  <button
                    key={market}
                    onClick={() => handleMarketChange(market)}
                    className={`rounded-xl border p-2.5 text-center font-mono text-xs font-bold transition ${
                      selected
                        ? "border-cyan-400 bg-cyan-500/20 text-cyan-300 shadow-[0_0_12px_rgba(0,240,255,0.25)]"
                        : "border-cyan-500/15 bg-cyan-950/20 text-cyan-400/70 hover:bg-cyan-500/10 hover:text-cyan-200"
                    }`}
                  >
                    {market}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="rounded-2xl border border-cyan-500/20 bg-[#020914]/80 p-4 backdrop-blur-md lg:col-span-4">
            <div className="mb-2 font-mono text-[10px] font-bold uppercase tracking-widest text-cyan-400/60">
              TIMEFRAME
            </div>

            <div className="grid grid-cols-5 gap-1.5">
              {timeframes.map((timeframe) => {
                const selected = selectedTimeframe === timeframe;

                return (
                  <button
                    key={timeframe}
                    onClick={() => handleTimeframeChange(timeframe)}
                    className={`rounded-lg border py-2 text-center font-mono text-xs font-bold transition ${
                      selected
                        ? "border-cyan-400 bg-cyan-500/20 text-cyan-300 shadow-[0_0_10px_rgba(0,240,255,0.25)]"
                        : "border-cyan-500/15 bg-cyan-950/20 text-cyan-400/70 hover:bg-cyan-500/10 hover:text-cyan-200"
                    }`}
                  >
                    {timeframe}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* CORE + SIGNAL */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* SIGNAL CORE */}
          <div className="relative flex min-h-[380px] flex-col items-center justify-center overflow-hidden rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md lg:col-span-6">
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff06_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff06_1px,transparent_1px)] bg-[size:20px_20px]" />

            <div className="absolute left-4 top-4 font-mono text-[10px] uppercase tracking-widest text-cyan-400/70">
              SIGNAL CORE
            </div>

            <div className="relative my-6 flex h-48 w-48 items-center justify-center">
              <div className="absolute inset-0 animate-[spin_30s_linear_infinite] rounded-full border border-cyan-500/30" />
              <div className="absolute inset-2 animate-[spin_20s_linear_infinite_reverse] rounded-full border border-dashed border-cyan-400/20" />
              <div className="absolute inset-6 animate-[spin_12s_linear_infinite] rounded-full border border-cyan-500/40" />
              <div className="absolute inset-10 animate-pulse rounded-full bg-cyan-500/10 blur-xl shadow-[0_0_30px_rgba(0,240,255,0.3)]" />

              <div className="relative z-10 flex h-20 w-20 flex-col items-center justify-center rounded-full border border-cyan-400/60 bg-[#031322] shadow-[inset_0_0_20px_rgba(0,240,255,0.4)]">
                <span className="text-xl font-extrabold tracking-tighter text-white">
                  KZ
                </span>
                <span className="mt-[-4px] font-mono text-[8px] tracking-widest text-cyan-400/80">
                  SIGNAL
                </span>
              </div>

              <div className="absolute h-full w-full animate-[spin_15s_linear_infinite]">
                <div className="absolute left-1/2 top-2 h-2 w-2 -translate-x-1/2 rounded-full bg-cyan-300 shadow-[0_0_8px_#00f0ff]" />
              </div>

              <div className="absolute h-full w-full animate-[spin_10s_linear_infinite_reverse]">
                <div className="absolute bottom-3 right-4 h-1.5 w-1.5 rounded-full bg-indigo-400 shadow-[0_0_8px_#6366f1]" />
              </div>
            </div>

            <div className="relative z-10 grid w-full grid-cols-4 gap-2">
              {coreInputs.map((input) => (
                <div
                  key={input}
                  className="truncate rounded border border-cyan-500/20 bg-cyan-950/30 px-2 py-1 text-center font-mono text-[9px] text-cyan-300"
                >
                  {input}
                </div>
              ))}
            </div>
          </div>

          {/* PRIMARY SIGNAL */}
          <div className="flex flex-col space-y-6 lg:col-span-6">
            <div className="relative flex flex-1 flex-col justify-between rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md">
              <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                <div className="flex items-center space-x-2 font-mono text-xs">
                  <span className="font-bold text-cyan-300">
                    {selectedMarket}
                  </span>
                  <span className="text-cyan-500/60">•</span>
                  <span className="text-cyan-400">
                    {selectedTimeframe}
                  </span>
                </div>

                <span className="rounded border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 font-mono text-[9px] text-cyan-300">
                  AI ANALYSIS
                </span>
              </div>

              <div className="flex items-center justify-between py-6">
                <div>
                  <span className="mb-1 block font-mono text-[10px] uppercase tracking-widest text-cyan-400/60">
                    CURRENT OUTPUT
                  </span>

                  <div
                    className={`text-4xl font-black tracking-wider drop-shadow-[0_0_15px_rgba(0,240,255,0.2)] md:text-5xl ${directionStyle.text}`}
                  >
                    {analysisLoading ? "..." : direction}
                  </div>
                </div>

                <div className="text-right font-mono">
                  <span className="mb-1 block text-[10px] uppercase tracking-widest text-cyan-400/60">
                    CONFIDENCE
                  </span>

                  <div className="text-2xl font-bold text-cyan-200 md:text-3xl">
                    {analysisLoading ? "..." : "UNSET"}
                  </div>
                </div>
              </div>

              <div
                className={`rounded-xl border p-3 font-mono text-xs ${directionStyle.border} ${directionStyle.bg}`}
              >
                {analysisError ? (
                  <span className="text-red-300">{analysisError}</span>
                ) : (
                  <span className="text-cyan-200/80">
                    {analysisText}
                  </span>
                )}
              </div>

              {lastAnalyzed && (
                <div className="mt-3 text-right font-mono text-[9px] text-cyan-400/50">
                  LAST REQUEST: {lastAnalyzed}
                </div>
              )}
            </div>

            {/* RISK STRUCTURE */}
            <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md">
              <div className="mb-3 font-mono text-[10px] font-bold uppercase tracking-widest text-cyan-400/70">
                RISK STRUCTURE
              </div>

              <div className="grid grid-cols-2 gap-2 font-mono text-xs sm:grid-cols-5">
                {["ENTRY", "STOP LOSS", "TP1", "TP2", "TP3"].map((label) => (
                  <div
                    key={label}
                    className="rounded-xl border border-cyan-500/20 bg-cyan-950/30 p-2.5 text-center"
                  >
                    <span className="mb-0.5 block text-[9px] text-cyan-400/60">
                      {label}
                    </span>

                    <span className="font-bold text-cyan-200">
                      NOT SET
                    </span>
                  </div>
                ))}
              </div>

              <p className="mt-3 font-mono text-[9px] text-cyan-400/50">
                Risk levels are not displayed until a verified analysis
                provides the required market data.
              </p>
            </div>
          </div>
        </div>

        {/* MULTI-TIMEFRAME + INPUTS */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="space-y-4 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md lg:col-span-6">
            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
                MULTI-TIMEFRAME INTELLIGENCE
              </h3>

              <span className="font-mono text-[9px] text-cyan-400/60">
                AWAITING ANALYSIS
              </span>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {defaultMultiTimeframes.map((item) => (
                <div
                  key={item.tf}
                  className="flex items-center justify-between rounded-xl border border-cyan-500/20 bg-cyan-950/25 p-3.5 font-mono"
                >
                  <div>
                    <span className="block text-xs font-bold text-white">
                      {item.tf} TIMEFRAME
                    </span>

                    <span className="block text-[9px] text-cyan-400/60">
                      {item.desc}
                    </span>
                  </div>

                  <span className="rounded border border-cyan-500/30 bg-cyan-500/10 px-2 py-1 text-[10px] font-bold text-cyan-300">
                    {item.regime}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md lg:col-span-6">
            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
                ANALYSIS INPUTS
              </h3>

              <span className="font-mono text-[9px] text-cyan-400/60">
                ENGINE INPUTS
              </span>
            </div>

            <div className="grid max-h-[220px] grid-cols-1 gap-2.5 overflow-y-auto pr-1 sm:grid-cols-2">
              {analysisInputsList.map((input) => (
                <div
                  key={input.name}
                  className="flex items-center justify-between rounded-xl border border-cyan-500/20 bg-cyan-950/25 p-2.5 font-mono text-xs"
                >
                  <span className="font-bold text-cyan-100">
                    {input.name}
                  </span>

                  <span className="rounded border border-cyan-500/30 bg-cyan-500/20 px-1.5 py-0.5 text-[9px] text-cyan-300">
                    {input.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* STRUCTURE VISUALIZATION */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="space-y-4 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md lg:col-span-7">
            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
                MARKET STRUCTURE VISUALIZATION
              </h3>

              <span className="font-mono text-[9px] text-cyan-400/60">
                WAITING FOR VERIFIED DATA
              </span>
            </div>

            <div className="relative flex h-56 w-full flex-col justify-between overflow-hidden rounded-xl border border-cyan-500/20 bg-[#01060e] p-4">
              <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff05_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff05_1px,transparent_1px)] bg-[size:24px_24px]" />

              <div className="relative z-10 flex justify-between font-mono text-[9px] text-cyan-400/50">
                <span>PRICE STRUCTURE</span>
                <span>NO LIVE SERIES</span>
              </div>

              <div className="relative z-10 flex flex-1 items-center justify-center">
                <div className="text-center font-mono">
                  <div className="mb-2 text-3xl text-cyan-500/20">
                    ∿
                  </div>

                  <p className="text-[10px] uppercase tracking-widest text-cyan-400/50">
                    LIVE MARKET DATA REQUIRED
                  </p>
                </div>
              </div>

              <div className="relative z-10 flex justify-between font-mono text-[9px] text-cyan-400/50">
                <span>SUPPORT: NOT SET</span>
                <span>RESISTANCE: NOT SET</span>
              </div>
            </div>
          </div>

          {/* WHY SIGNAL */}
          <div className="space-y-4 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md lg:col-span-5">
            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
                WHY THIS SIGNAL?
              </h3>

              <span className="font-mono text-[9px] text-cyan-400/60">
                AI REASONING
              </span>
            </div>

            <p className="font-sans text-xs leading-relaxed text-cyan-100/80">
              The analysis request asks the AI to consider market structure,
              momentum, volatility and multi-timeframe context before returning
              a directional setup.
            </p>

            <div className="grid grid-cols-2 gap-2 pt-2">
              {[
                "STRUCTURE",
                "MOMENTUM",
                "VOLATILITY",
                "TIMEFRAME ALIGNMENT",
              ].map((factor, index) => (
                <div
                  key={factor}
                  className="rounded-xl border border-cyan-500/20 bg-cyan-950/25 p-2.5 font-mono text-[10px]"
                >
                  <span className="block text-cyan-400/60">
                    FACTOR 0{index + 1}
                  </span>

                  <span className="font-bold text-cyan-200">
                    {factor}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* SESSION STATUS */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md lg:col-span-7">
            <div className="mb-4 flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
                SIGNAL SESSION
              </h3>

              <span className="font-mono text-[9px] text-cyan-400/60">
                CURRENT SESSION
              </span>
            </div>

            <div className="space-y-2.5">
              <div className="flex items-center justify-between rounded-xl border border-cyan-500/20 bg-cyan-950/25 p-3 font-mono text-xs">
                <span className="font-bold text-white">
                  SELECTED MARKET
                </span>
                <span className="text-cyan-300">{selectedMarket}</span>
              </div>

              <div className="flex items-center justify-between rounded-xl border border-cyan-500/20 bg-cyan-950/25 p-3 font-mono text-xs">
                <span className="font-bold text-white">
                  SELECTED TIMEFRAME
                </span>
                <span className="text-cyan-300">{selectedTimeframe}</span>
              </div>

              <div className="flex items-center justify-between rounded-xl border border-cyan-500/20 bg-cyan-950/25 p-3 font-mono text-xs">
                <span className="font-bold text-white">
                  ANALYSIS STATUS
                </span>
                <span className="text-cyan-300">
                  {analysisLoading ? "RUNNING" : "IDLE"}
                </span>
              </div>

              <div className="flex items-center justify-between rounded-xl border border-cyan-500/20 bg-cyan-950/25 p-3 font-mono text-xs">
                <span className="font-bold text-white">
                  LAST RESULT
                </span>
                <span className="text-cyan-300">
                  {direction}
                </span>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md lg:col-span-5">
            <div className="mb-4 flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
                SIGNAL ENGINE
              </h3>

              <span className="font-mono text-[9px] text-cyan-400/60">
                STATUS
              </span>
            </div>

            <div className="space-y-2.5 font-mono text-xs">
              {[
                {
                  label: "WEB API",
                  state: "CONFIGURED",
                },
                {
                  label: "AUTH SESSION",
                  state: "REQUIRED",
                },
                {
                  label: "AI ANALYSIS",
                  state: "AVAILABLE",
                },
                {
                  label: "LIVE SIGNAL",
                  state: "ON REQUEST",
                },
              ].map((row) => (
                <div
                  key={row.label}
                  className="flex items-center justify-between rounded-xl border border-cyan-500/20 bg-cyan-950/25 p-3"
                >
                  <span className="font-bold text-white">
                    {row.label}
                  </span>

                  <span className="rounded border border-cyan-500/30 bg-cyan-500/20 px-2 py-0.5 text-[10px] text-cyan-300">
                    {row.state}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ACTION */}
        <div className="rounded-2xl border border-cyan-500/30 bg-cyan-950/15 p-5 text-center backdrop-blur-md">
          <button
            onClick={runAnalysis}
            disabled={analysisLoading}
            className="rounded-xl border border-cyan-400/50 bg-cyan-500/15 px-6 py-3 font-mono text-xs font-bold tracking-widest text-cyan-200 transition hover:bg-cyan-500/25 disabled:cursor-wait disabled:opacity-50"
          >
            {analysisLoading
              ? "RUNNING AI ANALYSIS..."
              : `ANALYZE ${selectedMarket} • ${selectedTimeframe}`}
          </button>

          <p className="mt-3 font-mono text-[10px] text-cyan-400/60">
            Analysis requires an authenticated session. Never treat an AI
            output as guaranteed financial advice.
          </p>
        </div>
      </main>

      {/* FOOTER */}
      <footer className="relative z-20 mt-8 border-t border-cyan-500/15 bg-[#030810]/80 px-6 py-4">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 font-mono text-xs text-cyan-400/60 sm:flex-row">
          <span>KING ZARRY AI • SIGNAL INTELLIGENCE</span>
          <span>AI ANALYSIS WORKSPACE</span>
        </div>
      </footer>
    </div>
  );
}
