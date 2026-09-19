"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";

// ============================================================
// TYPES
// ============================================================

type MarketSymbol =
  | "BTC/USD"
  | "ETH/USD"
  | "SOL/USD"
  | "XAU/USD"
  | "EUR/USD"
  | "GBP/USD"
  | "NASDAQ"
  | "S&P 500";

type TimeframeType = "4H" | "1H" | "15M" | "5M";

type MarketCategory = "ALL" | "CRYPTO" | "FOREX" | "INDICES";

interface MarketItem {
  symbol: MarketSymbol;
  name: string;
  price: string;
  change: string;
  isPositive: boolean;
  trend: "BULLISH" | "BEARISH" | "NEUTRAL";
  volatility: "LOW" | "MODERATE" | "HIGH";
  aiState: string;
  regime: "BULLISH" | "BEARISH" | "ACCUMULATION";
}

// ============================================================
// DEMO MARKET DATA
// ============================================================
// This data is intentionally labelled DEMO.
// Replace with your Railway market endpoint when the live
// market API is connected.
// ============================================================

const marketsData: MarketItem[] = [
  {
    symbol: "BTC/USD",
    name: "Bitcoin / US Dollar",
    price: "$97,842.50",
    change: "+3.42%",
    isPositive: true,
    trend: "BULLISH",
    volatility: "MODERATE",
    aiState: "OPTIMIZED",
    regime: "BULLISH",
  },
  {
    symbol: "ETH/USD",
    name: "Ethereum / US Dollar",
    price: "$3,450.80",
    change: "+1.85%",
    isPositive: true,
    trend: "BULLISH",
    volatility: "MODERATE",
    aiState: "SYNCHRONIZED",
    regime: "BULLISH",
  },
  {
    symbol: "SOL/USD",
    name: "Solana / US Dollar",
    price: "$214.30",
    change: "+5.12%",
    isPositive: true,
    trend: "BULLISH",
    volatility: "HIGH",
    aiState: "MOMENTUM PEAK",
    regime: "BULLISH",
  },
  {
    symbol: "XAU/USD",
    name: "Gold / US Dollar",
    price: "$2,385.10",
    change: "+0.45%",
    isPositive: true,
    trend: "NEUTRAL",
    volatility: "LOW",
    aiState: "ACCUMULATION",
    regime: "ACCUMULATION",
  },
  {
    symbol: "EUR/USD",
    name: "Euro / US Dollar",
    price: "$1.0892",
    change: "-0.12%",
    isPositive: false,
    trend: "BEARISH",
    volatility: "LOW",
    aiState: "RANGE BOUND",
    regime: "BEARISH",
  },
  {
    symbol: "GBP/USD",
    name: "British Pound / USD",
    price: "$1.2740",
    change: "+0.08%",
    isPositive: true,
    trend: "NEUTRAL",
    volatility: "LOW",
    aiState: "STABLE",
    regime: "ACCUMULATION",
  },
  {
    symbol: "NASDAQ",
    name: "Nasdaq 100 Index",
    price: "$18,420.00",
    change: "+1.10%",
    isPositive: true,
    trend: "BULLISH",
    volatility: "MODERATE",
    aiState: "BREAKOUT WATCH",
    regime: "BULLISH",
  },
  {
    symbol: "S&P 500",
    name: "S&P 500 Index",
    price: "$5,240.50",
    change: "+0.85%",
    isPositive: true,
    trend: "BULLISH",
    volatility: "LOW",
    aiState: "STEADY UP",
    regime: "BULLISH",
  },
];

// ============================================================
// NAVIGATION
// ============================================================

const navItems = [
  { label: "HOME", href: "/" },
  { label: "CHAT", href: "/chat" },
  { label: "DASHBOARD", href: "/dashboard" },
  { label: "MARKETS", href: "/markets" },
  { label: "SIGNALS", href: "/signals" },
  { label: "NEWS", href: "/news" },
  { label: "ALERTS", href: "/alerts" },
  { label: "HISTORY", href: "/history" },
  { label: "SETTINGS", href: "/settings" },
];

// ============================================================
// COMPONENT
// ============================================================

export default function KingZarryMarketsPage() {
  const [selectedSymbol, setSelectedSymbol] =
    useState<MarketSymbol>("BTC/USD");

  const [activeTimeframe, setActiveTimeframe] =
    useState<TimeframeType>("1H");

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [marketFilter, setMarketFilter] =
    useState<MarketCategory>("ALL");

  const [showDemoNotice, setShowDemoNotice] = useState(false);

  // ----------------------------------------------------------
  // MARKET NODES
  // ----------------------------------------------------------

  const marketNodes = [
    {
      symbol: "BTC",
      label: "BITCOIN",
      status: "BULLISH",
    },
    {
      symbol: "ETH",
      label: "ETHEREUM",
      status: "NEUTRAL",
    },
    {
      symbol: "SOL",
      label: "SOLANA",
      status: "BULLISH",
    },
    {
      symbol: "XAU",
      label: "GOLD",
      status: "BULLISH",
    },
    {
      symbol: "FX",
      label: "FOREX",
      status: "RANGE",
    },
    {
      symbol: "INDEX",
      label: "GLOBAL",
      status: "BULLISH",
    },
  ];

  // ----------------------------------------------------------
  // SELECTED MARKET
  // ----------------------------------------------------------

  const currentMarket =
    marketsData.find((market) => market.symbol === selectedSymbol) ??
    marketsData[0];

  // ----------------------------------------------------------
  // FILTER
  // ----------------------------------------------------------

  const filteredWatchlist = useMemo(() => {
    if (marketFilter === "ALL") {
      return marketsData;
    }

    if (marketFilter === "CRYPTO") {
      return marketsData.filter(
        (market) =>
          market.symbol === "BTC/USD" ||
          market.symbol === "ETH/USD" ||
          market.symbol === "SOL/USD"
      );
    }

    if (marketFilter === "FOREX") {
      return marketsData.filter(
        (market) =>
          market.symbol === "EUR/USD" ||
          market.symbol === "GBP/USD"
      );
    }

    if (marketFilter === "INDICES") {
      return marketsData.filter(
        (market) =>
          market.symbol === "NASDAQ" ||
          market.symbol === "S&P 500" ||
          market.symbol === "XAU/USD"
      );
    }

    return marketsData;
  }, [marketFilter]);

  // ----------------------------------------------------------
  // DEMO BUTTON HANDLER
  // ----------------------------------------------------------

  const handleDemoAction = () => {
    setShowDemoNotice(true);

    window.setTimeout(() => {
      setShowDemoNotice(false);
    }, 3500);
  };

  return (
    <div className="relative min-h-screen w-full overflow-x-hidden bg-[#03060a] font-sans text-cyan-100 selection:bg-cyan-500 selection:text-black">

      {/* ======================================================
          BACKGROUND
      ====================================================== */}

      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#072438] via-[#020b14] to-[#010408]" />

      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(to_right,#091a2815_1px,transparent_1px),linear-gradient(to_bottom,#091a2815_1px,transparent_1px)] bg-[size:32px_32px]" />

      <div className="pointer-events-none fixed inset-0 z-10 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,240,255,0.012)_3px,transparent_4px)]" />

      <div className="pointer-events-none fixed left-[20%] top-[-10%] h-[600px] w-[600px] rounded-full bg-cyan-600/10 blur-[140px]" />

      <div className="pointer-events-none fixed bottom-[-10%] right-[20%] h-[600px] w-[600px] rounded-full bg-indigo-600/10 blur-[140px]" />

      {/* ======================================================
          HEADER
      ====================================================== */}

      <header className="relative z-30 flex items-center justify-between border-b border-cyan-500/15 bg-[#030810]/85 px-4 py-4 backdrop-blur-md md:px-6">

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
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-sm font-bold uppercase tracking-widest text-white md:text-base">
                KING ZARRY AI
              </h1>

              <span className="rounded border border-cyan-500/30 bg-cyan-950/40 px-1.5 py-0.5 font-mono text-[8px] tracking-wider text-cyan-400 md:text-[9px]">
                MARKET INTELLIGENCE
              </span>
            </div>

            <div className="mt-0.5 flex items-center gap-2 font-mono text-[9px] text-cyan-400/70 md:text-[10px]">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />

              <span>MARKET INTELLIGENCE ONLINE</span>

              <span className="text-cyan-700">
                •
              </span>

              <span className="hidden sm:inline">
                DEMO DATASET
              </span>
            </div>
          </div>
        </Link>

        {/* Desktop navigation */}

        <nav className="hidden items-center space-x-1 rounded-lg border border-cyan-500/10 bg-cyan-950/20 p-1 lg:flex">

          {navItems.map((item) => {
            const active = item.href === "/markets";

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded px-3 py-1.5 text-xs font-mono tracking-wider transition ${
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

        {/* Mobile button */}

        <button
          type="button"
          onClick={() => setMobileMenuOpen((open) => !open)}
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

      {/* ======================================================
          MOBILE NAV
      ====================================================== */}

      {mobileMenuOpen && (
        <div className="relative z-30 border-b border-cyan-500/30 bg-[#040c16]/95 p-4 backdrop-blur-xl lg:hidden">

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">

            {navItems.map((item) => {
              const active = item.href === "/markets";

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`rounded border p-2 text-center font-mono text-xs transition ${
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
          DEMO NOTICE
      ====================================================== */}

      {showDemoNotice && (
        <div className="fixed right-4 top-20 z-50 max-w-sm rounded-xl border border-yellow-400/30 bg-[#11140d]/95 p-4 shadow-[0_0_30px_rgba(250,204,21,0.15)] backdrop-blur-xl">

          <div className="flex items-start gap-3">
            <div className="mt-0.5 text-yellow-300">
              ⚠
            </div>

            <div>
              <div className="font-mono text-xs font-bold tracking-wider text-yellow-300">
                DEMO FUNCTION
              </div>

              <p className="mt-1 font-mono text-[10px] leading-relaxed text-yellow-100/70">
                Live market synchronization will be enabled when the
                market data API is connected.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================
          MAIN
      ====================================================== */}

      <main className="relative z-20 mx-auto w-full max-w-7xl flex-1 space-y-6 p-4 md:p-6">

        {/* ====================================================
            TITLE
        ==================================================== */}

        <div className="flex flex-col justify-between gap-4 border-b border-cyan-500/10 pb-4 md:flex-row md:items-center">

          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold uppercase tracking-widest text-white md:text-2xl">
                MARKET INTELLIGENCE
              </h2>

              <span className="rounded border border-yellow-500/30 bg-yellow-500/10 px-2 py-1 font-mono text-[8px] text-yellow-300">
                DEMO DATA
              </span>
            </div>

            <p className="mt-1 font-mono text-xs text-cyan-400/60">
              Market visibility across crypto, forex, commodities and indices.
            </p>
          </div>

          {/* AI insight */}

          <div className="max-w-md rounded-lg border border-cyan-500/20 bg-cyan-950/20 p-3 backdrop-blur-md">

            <div className="mb-1 flex items-center justify-between font-mono text-[10px] text-cyan-400/80">

              <span className="font-bold tracking-wider">
                AI MARKET LAYER
              </span>

              <span className="text-yellow-300">
                PREVIEW
              </span>

            </div>

            <p className="text-xs leading-relaxed text-cyan-200/80">
              Price structure, momentum, volatility and market context
              can be combined here once the live market feed is connected.
            </p>
          </div>
        </div>

        {/* ====================================================
            MARKET CORE
        ==================================================== */}

        <section className="relative flex flex-col items-center justify-between gap-6 overflow-hidden rounded-2xl border border-cyan-500/20 bg-[#020914]/80 p-5 backdrop-blur-md md:flex-row md:p-6">

          <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff08_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff08_1px,transparent_1px)] bg-[size:16px_16px]" />

          {/* Core */}

          <div className="relative z-10 flex w-full flex-col items-center justify-center md:w-1/3">

            <div className="relative flex h-36 w-36 items-center justify-center">

              <div className="absolute inset-0 animate-[spin_25s_linear_infinite] rounded-full border border-cyan-500/30" />

              <div className="absolute inset-2 animate-[spin_18s_linear_infinite_reverse] rounded-full border border-dashed border-cyan-400/20" />

              <div className="absolute inset-5 animate-pulse rounded-full bg-cyan-500/10 blur-md shadow-[0_0_25px_rgba(0,240,255,0.3)]" />

              <div className="relative z-10 flex h-16 w-16 flex-col items-center justify-center rounded-full border border-cyan-400/60 bg-[#031322] shadow-[inset_0_0_15px_rgba(0,240,255,0.4)]">

                <span className="text-lg font-extrabold tracking-tighter text-white">
                  KZ
                </span>

                <span className="-mt-1 font-mono text-[8px] tracking-widest text-cyan-400/80">
                  CORE
                </span>
              </div>

              <div className="absolute h-full w-full animate-[spin_10s_linear_infinite]">
                <div className="absolute left-1/2 top-0 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-cyan-300 shadow-[0_0_8px_#00f0ff]" />
              </div>
            </div>

            <div className="mt-2 text-center">
              <span className="font-mono text-xs font-bold uppercase tracking-widest text-cyan-200">
                MARKET CORE
              </span>

              <div className="font-mono text-[9px] text-cyan-500/70">
                MARKETS → DATA → AI ANALYSIS → INTELLIGENCE
              </div>
            </div>
          </div>

          {/* Nodes */}

          <div className="relative z-10 grid w-full grid-cols-2 gap-3 sm:grid-cols-3 md:w-2/3">

            {marketNodes.map((node) => (
              <div
                key={node.symbol}
                className="flex items-center justify-between rounded-xl border border-cyan-500/15 bg-cyan-950/20 p-3"
              >
                <div>
                  <span className="block font-mono text-xs font-bold text-white">
                    {node.symbol}
                  </span>

                  <span className="block font-mono text-[9px] text-cyan-400/60">
                    {node.label}
                  </span>
                </div>

                <span className="rounded border border-cyan-500/30 bg-cyan-500/20 px-1.5 py-0.5 font-mono text-[9px] text-cyan-300">
                  {node.status}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* ====================================================
            CONTROLS
        ==================================================== */}

        <section className="flex flex-col justify-between gap-3 rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-3 backdrop-blur-md md:flex-row md:items-center">

          <div className="flex w-full items-center space-x-1 overflow-x-auto pb-1 md:w-auto md:pb-0">

            {(["ALL", "CRYPTO", "FOREX", "INDICES"] as MarketCategory[]).map(
              (category) => (
                <button
                  key={category}
                  type="button"
                  onClick={() => setMarketFilter(category)}
                  className={`whitespace-nowrap rounded px-3 py-1.5 font-mono text-xs transition ${
                    marketFilter === category
                      ? "border border-cyan-500/40 bg-cyan-500/20 text-cyan-300"
                      : "text-cyan-400/60 hover:bg-cyan-500/10 hover:text-cyan-200"
                  }`}
                >
                  {category}
                </button>
              )
            )}
          </div>

          <button
            type="button"
            onClick={handleDemoAction}
            className="rounded-lg bg-cyan-400 px-3.5 py-1.5 font-mono text-xs font-bold text-black shadow-[0_0_10px_rgba(0,240,255,0.2)] transition hover:bg-cyan-300"
          >
            + ADD MARKET
          </button>
        </section>

        {/* ====================================================
            MARKET OVERVIEW
        ==================================================== */}

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">

          {marketsData.slice(0, 4).map((market) => {

            const isSelected =
              market.symbol === selectedSymbol;

            return (
              <button
                key={market.symbol}
                type="button"
                onClick={() =>
                  setSelectedSymbol(market.symbol)
                }
                className={`cursor-pointer rounded-xl border p-4 text-left backdrop-blur-md transition-all duration-200 ${
                  isSelected
                    ? "border-cyan-400 bg-cyan-950/40 shadow-[0_0_20px_rgba(0,240,255,0.2)]"
                    : "border-cyan-500/15 bg-[#020914]/70 hover:border-cyan-500/30 hover:bg-cyan-950/20"
                }`}
              >

                <div className="mb-2 flex items-center justify-between">

                  <span className="font-mono text-xs font-bold text-white">
                    {market.symbol}
                  </span>

                  <span
                    className={`rounded border px-1.5 py-0.5 font-mono text-[10px] ${
                      market.isPositive
                        ? "border-emerald-500/30 bg-emerald-500/20 text-emerald-300"
                        : "border-red-500/30 bg-red-500/20 text-red-300"
                    }`}
                  >
                    {market.change}
                  </span>
                </div>

                <div className="mb-2 font-mono text-lg font-bold tracking-wider text-cyan-100">
                  {market.price}
                </div>

                <div className="flex items-center justify-between border-t border-cyan-500/10 pt-2 font-mono text-[10px] text-cyan-400/60">

                  <span>
                    VOL: {market.volatility}
                  </span>

                  <span className="text-cyan-300">
                    {market.aiState}
                  </span>
                </div>
              </button>
            );
          })}
        </section>

        {/* ====================================================
            DETAIL + AI
        ==================================================== */}

        <section className="grid grid-cols-1 gap-6 lg:grid-cols-12">

          {/* ==================================================
              CHART
          ================================================== */}

          <div className="space-y-4 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md lg:col-span-8">

            <div className="flex flex-col justify-between gap-3 border-b border-cyan-500/15 pb-3 sm:flex-row sm:items-center">

              <div>

                <div className="flex flex-wrap items-center gap-2">

                  <h3 className="font-mono text-base font-bold text-white">
                    {selectedSymbol}
                  </h3>

                  <span className="rounded border border-yellow-500/30 bg-yellow-500/10 px-2 py-0.5 font-mono text-[8px] text-yellow-300">
                    DEMO FEED
                  </span>
                </div>

                <span className="font-mono text-xs text-cyan-400/60">
                  {currentMarket.name} • {currentMarket.price}
                </span>
              </div>

              {/* Timeframe */}

              <div className="flex items-center space-x-1 rounded-lg border border-cyan-500/15 bg-cyan-950/40 p-1">

                {(["4H", "1H", "15M", "5M"] as TimeframeType[]).map(
                  (timeframe) => (
                    <button
                      key={timeframe}
                      type="button"
                      onClick={() =>
                        setActiveTimeframe(timeframe)
                      }
                      className={`rounded px-2.5 py-1 font-mono text-[10px] transition ${
                        activeTimeframe === timeframe
                          ? "border border-cyan-500/40 bg-cyan-500/20 text-cyan-300"
                          : "text-cyan-400/60 hover:text-cyan-200"
                      }`}
                    >
                      {timeframe}
                    </button>
                  )
                )}
              </div>
            </div>

            {/* Chart */}

            <div className="relative h-64 overflow-hidden rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-4">

              <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff06_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff06_1px,transparent_1px)] bg-[size:24px_24px]" />

              <div className="absolute left-0 right-0 top-12 border-t border-dashed border-red-500/30">

                <span className="absolute right-3 -top-3 bg-[#020914] px-1 font-mono text-[8px] text-red-400">
                  RESISTANCE • DEMO
                </span>
              </div>

              <div className="absolute bottom-16 left-0 right-0 border-t border-dashed border-emerald-500/30">

                <span className="absolute right-3 -top-3 bg-[#020914] px-1 font-mono text-[8px] text-emerald-400">
                  SUPPORT • DEMO
                </span>
              </div>

              <div className="relative z-10 flex h-full items-end">

                <svg
                  className="h-full w-full overflow-visible"
                  viewBox="0 0 500 180"
                  preserveAspectRatio="none"
                >
                  <defs>
                    <linearGradient
                      id="chartGradient"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="0%"
                        stopColor="#00f0ff"
                        stopOpacity="0.3"
                      />

                      <stop
                        offset="100%"
                        stopColor="#00f0ff"
                        stopOpacity="0"
                      />
                    </linearGradient>
                  </defs>

                  <path
                    d="M 0,120 Q 80,100 150,80 T 300,50 T 420,30 T 500,20 L 500,180 L 0,180 Z"
                    fill="url(#chartGradient)"
                  />

                  <path
                    d="M 0,120 Q 80,100 150,80 T 300,50 T 420,30 T 500,20"
                    fill="none"
                    stroke="#00f0ff"
                    strokeWidth="2"
                    className="drop-shadow-[0_0_8px_#00f0ff]"
                  />
                </svg>
              </div>

              <div className="absolute bottom-3 left-4 right-4 z-20 flex items-center justify-between border-t border-cyan-500/10 pt-2 font-mono text-[10px] text-cyan-400/60">

                <span>
                  TIMEFRAME: {activeTimeframe}
                </span>

                <span>
                  TREND:{" "}
                  <strong className="text-cyan-300">
                    {currentMarket.trend}
                  </strong>
                </span>
              </div>
            </div>

            {/* Multi timeframe */}

            <div className="flex flex-col justify-between gap-3 rounded-xl border border-cyan-500/15 bg-cyan-950/20 p-3 sm:flex-row sm:items-center">

              <span className="font-mono text-[10px] font-bold text-cyan-400/80">
                MULTI-TIMEFRAME INTELLIGENCE
              </span>

              <div className="flex flex-wrap gap-2">

                {(["4H", "1H", "15M", "5M"] as TimeframeType[]).map(
                  (timeframe) => (
                    <span
                      key={timeframe}
                      className="rounded border border-cyan-500/30 bg-cyan-950/60 px-2 py-0.5 font-mono text-[9px] text-cyan-300"
                    >
                      {timeframe}: {currentMarket.trend}
                    </span>
                  )
                )}
              </div>
            </div>
          </div>

          {/* ==================================================
              AI PANEL
          ================================================== */}

          <div className="space-y-6 lg:col-span-4">

            {/* AI analysis */}

            <div className="space-y-4 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md">

              <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">

                <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
                  AI MARKET ANALYSIS
                </h3>

                <span className="font-mono text-[9px] text-cyan-400/60">
                  PREVIEW
                </span>
              </div>

              <div className="space-y-1 rounded-xl border border-cyan-500/20 bg-cyan-950/30 p-3 text-center">

                <span className="block font-mono text-[9px] text-cyan-400/60">
                  MARKET REGIME
                </span>

                <span className="font-mono text-base font-bold tracking-wider text-cyan-300">
                  {currentMarket.regime}
                </span>
              </div>

              <div className="space-y-2 font-mono text-xs">

                <div className="flex justify-between border-b border-cyan-500/10 py-1">

                  <span className="text-cyan-500/70">
                    TREND:
                  </span>

                  <span className="text-cyan-200">
                    {currentMarket.trend}
                  </span>
                </div>

                <div className="flex justify-between border-b border-cyan-500/10 py-1">

                  <span className="text-cyan-500/70">
                    VOLATILITY:
                  </span>

                  <span className="text-cyan-200">
                    {currentMarket.volatility}
                  </span>
                </div>

                <div className="flex justify-between border-b border-cyan-500/10 py-1">

                  <span className="text-cyan-500/70">
                    AI STATE:
                  </span>

                  <span className="text-cyan-300">
                    {currentMarket.aiState}
                  </span>
                </div>

                <div className="flex justify-between py-1">

                  <span className="text-cyan-500/70">
                    CONFIDENCE:
                  </span>

                  <span className="text-yellow-300">
                    NOT AVAILABLE
                  </span>
                </div>
              </div>

              <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-3">

                <p className="font-mono text-[9px] leading-relaxed text-yellow-200/70">
                  Live AI confidence, indicators and market signals will
                  appear here after the backend market-analysis service
                  is connected.
                </p>
              </div>
            </div>

            {/* Signal engine */}

            <div className="space-y-3 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md">

              <div className="flex items-center justify-between border-b border-cyan-500/15 pb-2">

                <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
                  AI SIGNAL ENGINE
                </h3>

                <span className="font-mono text-[9px] text-yellow-300">
                  NOT CONNECTED
                </span>
              </div>

              <div className="flex items-center justify-between font-mono text-xs">

                <span className="text-cyan-500/70">
                  PAIR & TF:
                </span>

                <span className="font-bold text-white">
                  {selectedSymbol} • {activeTimeframe}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-1">

                <div className="rounded border border-cyan-500/15 bg-cyan-950/30 p-2">

                  <span className="block font-mono text-[9px] text-cyan-400/60">
                    DIRECTION
                  </span>

                  <span className="font-mono text-xs font-bold text-cyan-300">
                    AWAITING DATA
                  </span>
                </div>

                <div className="rounded border border-cyan-500/15 bg-cyan-950/30 p-2">

                  <span className="block font-mono text-[9px] text-cyan-400/60">
                    ENTRY
                  </span>

                  <span className="font-mono text-xs font-bold text-cyan-300">
                    AWAITING DATA
                  </span>
                </div>
              </div>

              <div className="pt-1 text-center font-mono text-[9px] text-cyan-500/55">
                SIGNAL ENGINE REQUIRES LIVE MARKET DATA
              </div>

              <Link
                href="/signals"
                className="block rounded-lg border border-cyan-500/20 bg-cyan-500/5 px-3 py-2 text-center font-mono text-[10px] text-cyan-300 transition hover:bg-cyan-500/10"
              >
                OPEN SIGNAL CENTER →
              </Link>
            </div>
          </div>
        </section>

        {/* ====================================================
            WATCHLIST
        ==================================================== */}

        <section className="space-y-4 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md">

          <div className="flex flex-col justify-between gap-2 border-b border-cyan-500/15 pb-3 sm:flex-row sm:items-center">

            <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
              MARKET WATCHLIST
            </h3>

            <span className="font-mono text-[9px] text-cyan-400/60">
              {filteredWatchlist.length} INSTRUMENTS
            </span>
          </div>

          <div className="overflow-x-auto">

            <table className="w-full min-w-[650px] text-left font-mono text-xs">

              <thead>

                <tr className="border-b border-cyan-500/15 text-[10px] text-cyan-400/60">

                  <th className="pb-2 font-normal">
                    MARKET
                  </th>

                  <th className="pb-2 font-normal">
                    PRICE
                  </th>

                  <th className="pb-2 font-normal">
                    CHANGE
                  </th>

                  <th className="pb-2 font-normal">
                    TREND
                  </th>

                  <th className="pb-2 font-normal">
                    VOLATILITY
                  </th>

                  <th className="pb-2 text-right font-normal">
                    AI STATE
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-cyan-500/10">

                {filteredWatchlist.map((market) => (

                  <tr
                    key={market.symbol}
                    onClick={() =>
                      setSelectedSymbol(market.symbol)
                    }
                    className={`cursor-pointer transition ${
                      selectedSymbol === market.symbol
                        ? "bg-cyan-950/40"
                        : "hover:bg-cyan-950/30"
                    }`}
                  >

                    <td className="py-3 font-bold text-white">

                      <div className="flex items-center gap-2">

                        <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_7px_#00f0ff]" />

                        <span>
                          {market.symbol}
                        </span>
                      </div>
                    </td>

                    <td className="py-3 text-cyan-100">
                      {market.price}
                    </td>

                    <td
                      className={`py-3 font-bold ${
                        market.isPositive
                          ? "text-emerald-400"
                          : "text-red-400"
                      }`}
                    >
                      {market.change}
                    </td>

                    <td className="py-3 text-cyan-300">
                      {market.trend}
                    </td>

                    <td className="py-3 text-cyan-300/70">
                      {market.volatility}
                    </td>

                    <td className="py-3 text-right text-cyan-400/70">
                      {market.aiState}
                    </td>
                  </tr>
                ))}

              </tbody>
            </table>
          </div>
        </section>

        {/* ====================================================
            FOOTER STATUS
        ==================================================== */}

        <section className="flex flex-col justify-between gap-3 border-t border-cyan-500/10 pt-4 font-mono text-[9px] text-cyan-500/50 sm:flex-row">

          <span>
            KING ZARRY AI • MARKET INTELLIGENCE
          </span>

          <span>
            LIVE DATA: NOT CONNECTED • UI READY
          </span>

          <span>
            SELECTED: {selectedSymbol}
          </span>
        </section>
      </main>
    </div>
  );
}
