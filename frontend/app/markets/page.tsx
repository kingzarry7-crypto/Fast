"use client";

import React, { useState, useEffect } from "react";

// Types
type MarketSymbol = "BTC/USD" | "ETH/USD" | "SOL/USD" | "XAU/USD" | "EUR/USD" | "GBP/USD" | "NASDAQ" | "S&P 500";
type TimeframeType = "4H" | "1H" | "15M" | "5M";

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

export default function KingZarryMarketsPage() {
  // State
  const [selectedSymbol, setSelectedSymbol] = useState<MarketSymbol>("BTC/USD");
  const [activeTimeframe, setActiveTimeframe] = useState<TimeframeType>("1H");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [marketFilter, setMarketFilter] = useState<string>("ALL");

  // Pulsing HUD Node Simulator
  const [marketNodes] = useState([
    { symbol: "BTC", label: "BITCOIN", status: "BULLISH" },
    { symbol: "ETH", label: "ETHEREUM", status: "NEUTRAL" },
    { symbol: "SOL", label: "SOLANA", status: "BULLISH" },
    { symbol: "XAU", label: "GOLD", status: "BULLISH" },
    { symbol: "FX", label: "FOREX", status: "RANGE" },
    { symbol: "INDEX", label: "GLOBAL", status: "BULLISH" },
  ]);

  // Demo Market Watchlist Data
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

  const currentMarket = marketsData.find((m) => m.symbol === selectedSymbol) || marketsData[0];

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
  ];

  const filteredWatchlist = marketsData.filter((m) => {
    if (marketFilter === "ALL") return true;
    if (marketFilter === "CRYPTO") return m.symbol.includes("USD") && !m.symbol.includes("EUR") && !m.symbol.includes("XAU");
    if (marketFilter === "FOREX") return m.symbol.includes("EUR") || m.symbol.includes("GBP");
    if (marketFilter === "INDICES") return m.symbol.includes("NASDAQ") || m.symbol.includes("S&P") || m.symbol.includes("XAU");
    return true;
  });

  return (
    <div className="relative w-full min-h-screen bg-[#03060a] text-cyan-100 font-sans overflow-x-hidden flex flex-col justify-between selection:bg-cyan-500 selection:text-black">
      {/* Background Holographic Atmosphere */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#072438] via-[#020b14] to-[#010408] pointer-events-none" />
      <div className="fixed inset-0 bg-[linear-gradient(to_right,#091a2815_1px,transparent_1px),linear-gradient(to_bottom,#091a2815_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />
      <div className="fixed inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,240,255,0.012)_3px,transparent_4px)] pointer-events-none z-10" />

      {/* Radial Ambient Glow Spheres */}
      <div className="fixed top-[-10%] left-[20%] w-[600px] h-[600px] bg-cyan-600/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="fixed bottom-[-10%] right-[20%] w-[600px] h-[600px] bg-indigo-600/10 rounded-full blur-[140px] pointer-events-none" />

      {/* HEADER / NAVIGATION HUD */}
      <header className="relative z-20 flex items-center justify-between px-6 py-4 border-b border-cyan-500/15 bg-[#030810]/80 backdrop-blur-md">
        <div className="flex items-center space-x-4">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-lg border border-cyan-500/40 bg-cyan-950/30 text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
            <span className="font-extrabold text-lg tracking-wider">KZ</span>
            <span className="absolute -top-1 -right-1 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
            </span>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-base font-bold tracking-widest text-white uppercase">KING ZARRY AI</h1>
              <span className="px-1.5 py-0.5 text-[9px] font-mono tracking-wider text-cyan-400 border border-cyan-500/30 bg-cyan-950/40 rounded">
                MARKET INTELLIGENCE
              </span>
            </div>
            <div className="flex items-center space-x-2 text-[10px] font-mono text-cyan-400/70">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span>MARKET INTELLIGENCE ONLINE</span>
              <span className="text-cyan-700">•</span>
              <span>TELEMETRY: SYNCHRONIZED</span>
            </div>
          </div>
        </div>

        {/* Navigation - Desktop */}
        <nav className="hidden lg:flex items-center space-x-1 bg-cyan-950/20 p-1 rounded-lg border border-cyan-500/10">
          {navItems.map((item) => {
            const isActive = item === "MARKETS";
            return (
              <button
                key={item}
                className={`px-3 py-1.5 text-xs font-mono tracking-wider transition-all duration-200 rounded ${
                  isActive
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_10px_rgba(0,240,255,0.2)]"
                    : "text-cyan-400/60 hover:text-cyan-200 hover:bg-cyan-500/10"
                }`}
              >
                {item}
              </button>
            );
          })}
        </nav>

        {/* Mobile Toggle Button */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-2 rounded border border-cyan-500/30 text-cyan-400 bg-cyan-950/40 hover:bg-cyan-500/20"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {mobileMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </header>

      {/* MOBILE NAV DRAWER */}
      {mobileMenuOpen && (
        <div className="lg:hidden relative z-30 bg-[#040c16]/95 border-b border-cyan-500/30 p-4 backdrop-blur-xl">
          <div className="grid grid-cols-3 gap-2">
            {navItems.map((item) => (
              <button
                key={item}
                className={`p-2 text-xs font-mono text-center rounded border ${
                  item === "MARKETS"
                    ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/50"
                    : "border-cyan-500/10 text-cyan-400/70 hover:bg-cyan-500/10"
                }`}
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* MAIN CONTENT AREA */}
      <main className="relative z-20 flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-6">
        {/* TOP TITLE SUB HEADER */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyan-500/10 pb-4">
          <div>
            <h2 className="text-xl md:text-2xl font-bold tracking-widest text-white uppercase flex items-center space-x-3">
              <span>MARKET INTELLIGENCE</span>
            </h2>
            <p className="text-xs font-mono text-cyan-400/60 mt-1">
              AI-powered visibility across the markets you follow.
            </p>
          </div>

          {/* AI MARKET INSIGHT PANEL */}
          <div className="p-3 rounded-lg border border-cyan-500/20 bg-cyan-950/20 backdrop-blur-md max-w-md">
            <div className="flex items-center justify-between text-[10px] font-mono text-cyan-400/80 mb-1">
              <span className="font-bold tracking-wider">AI MARKET INSIGHT</span>
              <span className="text-cyan-400">DEMO MODE</span>
            </div>
            <p className="text-xs text-cyan-200">
              "The market intelligence layer combines price structure, momentum, volatility and contextual information to help interpret market conditions."
            </p>
          </div>
        </div>

        {/* MARKET CORE HUD DISPLAY */}
        <div className="relative rounded-2xl border border-cyan-500/20 bg-[#020914]/80 p-6 backdrop-blur-md overflow-hidden flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff08_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff08_1px,transparent_1px)] bg-[size:16px_16px]" />

          {/* Central AI Market Core */}
          <div className="relative z-10 flex flex-col items-center justify-center w-full md:w-1/3">
            <div className="relative w-36 h-36 flex items-center justify-center">
              <div className="absolute inset-0 rounded-full border border-cyan-500/30 animate-[spin_25s_linear_infinite]" />
              <div className="absolute inset-2 rounded-full border border-dashed border-cyan-400/20 animate-[spin_18s_linear_infinite_reverse]" />
              <div className="absolute inset-5 rounded-full bg-cyan-500/10 blur-md animate-pulse shadow-[0_0_25px_rgba(0,240,255,0.3)]" />

              <div className="relative z-10 flex flex-col items-center justify-center w-16 h-16 rounded-full bg-[#031322] border border-cyan-400/60 shadow-[inset_0_0_15px_rgba(0,240,255,0.4)]">
                <span className="font-extrabold text-lg tracking-tighter text-white">KZ</span>
                <span className="text-[8px] font-mono tracking-widest text-cyan-400/80 -mt-1">CORE</span>
              </div>

              <div className="absolute w-full h-full animate-[spin_10s_linear_infinite]">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-300 shadow-[0_0_8px_#00f0ff] absolute top-0 left-1/2 -translate-x-1/2" />
              </div>
            </div>

            <div className="mt-2 text-center">
              <span className="text-xs font-mono font-bold tracking-widest text-cyan-200 uppercase">MARKET CORE</span>
              <div className="text-[9px] font-mono text-cyan-500/70">MARKETS → DATA → AI ANALYSIS → INTELLIGENCE</div>
            </div>
          </div>

          {/* Market Nodes Connected Visual */}
          <div className="relative z-10 grid grid-cols-2 sm:grid-cols-3 gap-3 w-full md:w-2/3">
            {marketNodes.map((node) => (
              <div key={node.symbol} className="p-3 rounded-xl border border-cyan-500/15 bg-cyan-950/20 flex items-center justify-between">
                <div>
                  <span className="text-xs font-mono font-bold text-white block">{node.symbol}</span>
                  <span className="text-[9px] font-mono text-cyan-400/60 block">{node.label}</span>
                </div>
                <span className="px-1.5 py-0.5 text-[9px] font-mono rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  {node.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* CONTROL BAR */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-3 p-3 rounded-xl border border-cyan-500/20 bg-[#020914]/80 backdrop-blur-md">
          <div className="flex items-center space-x-1 overflow-x-auto w-full md:w-auto pb-1 md:pb-0">
            {["ALL", "CRYPTO", "FOREX", "INDICES"].map((cat) => (
              <button
                key={cat}
                onClick={() => setMarketFilter(cat)}
                className={`px-3 py-1.5 text-xs font-mono rounded transition whitespace-nowrap ${
                  marketFilter === cat
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    : "text-cyan-400/60 hover:text-cyan-200 hover:bg-cyan-500/10"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          <div className="flex items-center space-x-2 w-full md:w-auto justify-end">
            <button className="px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold text-black bg-cyan-400 hover:bg-cyan-300 transition shadow-[0_0_10px_rgba(0,240,255,0.2)]">
              + ADD MARKET
            </button>
          </div>
        </div>

        {/* MARKET OVERVIEW CARDS GRID */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {marketsData.slice(0, 4).map((m) => {
            const isSelected = m.symbol === selectedSymbol;
            return (
              <div
                key={m.symbol}
                onClick={() => setSelectedSymbol(m.symbol)}
                className={`p-4 rounded-xl border backdrop-blur-md cursor-pointer transition-all duration-200 ${
                  isSelected
                    ? "bg-cyan-950/40 border-cyan-400 shadow-[0_0_20px_rgba(0,240,255,0.2)]"
                    : "bg-[#020914]/70 border-cyan-500/15 hover:border-cyan-500/30 hover:bg-cyan-950/20"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono font-bold text-white">{m.symbol}</span>
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${m.isPositive ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : "bg-red-500/20 text-red-300 border border-red-500/30"}`}>
                    {m.change}
                  </span>
                </div>
                <div className="text-lg font-bold font-mono text-cyan-100 tracking-wider mb-2">{m.price}</div>
                <div className="flex items-center justify-between text-[10px] font-mono text-cyan-400/60 pt-2 border-t border-cyan-500/10">
                  <span>VOL: {m.volatility}</span>
                  <span className="text-cyan-300">{m.aiState}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* SELECTED MARKET CHART & AI ANALYSIS GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* LEFT 8 COLS: MARKET DETAIL CHART PANEL */}
          <div className="lg:col-span-8 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-cyan-500/15 pb-3">
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-base font-bold font-mono text-white">{selectedSymbol}</h3>
                  <span className="px-2 py-0.5 text-[9px] font-mono rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                    MARKET STRUCTURE
                  </span>
                </div>
                <span className="text-xs font-mono text-cyan-400/60">{currentMarket.name} • {currentMarket.price}</span>
              </div>

              {/* Timeframe selector */}
              <div className="flex items-center space-x-1 bg-cyan-950/40 p-1 rounded-lg border border-cyan-500/15">
                {(["4H", "1H", "15M", "5M"] as TimeframeType[]).map((tf) => (
                  <button
                    key={tf}
                    onClick={() => setActiveTimeframe(tf)}
                    className={`px-2.5 py-1 text-[10px] font-mono rounded transition ${
                      activeTimeframe === tf
                        ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                        : "text-cyan-400/60 hover:text-cyan-200"
                    }`}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </div>

            {/* Polished Visual Demo Chart Area */}
            <div className="relative h-64 rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-4 flex flex-col justify-between overflow-hidden">
              {/* Grid Background Lines */}
              <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff06_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff06_1px,transparent_1px)] bg-[size:24px_24px]" />

              {/* Resistance & Support Indicator Lines */}
              <div className="absolute top-12 left-0 right-0 border-t border-dashed border-red-500/30 flex justify-end px-3">
                <span className="text-[8px] font-mono text-red-400 bg-[#020914] px-1">RESISTANCE ZONE (DEMO)</span>
              </div>
              <div className="absolute bottom-16 left-0 right-0 border-t border-dashed border-emerald-500/30 flex justify-end px-3">
                <span className="text-[8px] font-mono text-emerald-400 bg-[#020914] px-1">SUPPORT ZONE (DEMO)</span>
              </div>

              {/* Simulated SVG Candlestick / Price Curve */}
              <div className="relative z-10 flex-1 flex items-end">
                <svg className="w-full h-full overflow-visible" viewBox="0 0 500 180" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.3" />
                      <stop offset="100%" stopColor="#00f0ff" stopOpacity="0.0" />
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

              {/* Chart Overlay Telemetry */}
              <div className="relative z-10 flex items-center justify-between text-[10px] font-mono text-cyan-400/60 pt-2 border-t border-cyan-500/10">
                <span>TIMEFRAME: {activeTimeframe}</span>
                <span>AI TREND VECTOR: <strong className="text-cyan-300">{currentMarket.trend}</strong></span>
              </div>
            </div>

            {/* Multi-Timeframe Intelligence bar */}
            <div className="p-3 rounded-xl border border-cyan-500/15 bg-cyan-950/20 flex items-center justify-between">
              <span className="text-[10px] font-mono text-cyan-400/80 font-bold">MULTI-TIMEFRAME INTELLIGENCE</span>
              <div className="flex items-center space-x-2">
                {(["4H", "1H", "15M", "5M"] as TimeframeType[]).map((tf) => (
                  <span key={tf} className="px-2 py-0.5 text-[9px] font-mono rounded bg-cyan-950/60 text-cyan-300 border border-cyan-500/30">
                    {tf}: {currentMarket.trend}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT 4 COLS: AI MARKET ANALYSIS & SIGNAL PREVIEW */}
          <div className="lg:col-span-4 space-y-6">
            {/* AI MARKET ANALYSIS */}
            <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md space-y-4">
              <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                <h3 className="text-xs font-mono font-bold text-white tracking-widest uppercase">AI MARKET ANALYSIS</h3>
                <span className="text-[9px] font-mono text-cyan-400/60">SYNTHESIS</span>
              </div>

              <div className="p-3 rounded-xl border border-cyan-500/20 bg-cyan-950/30 text-center space-y-1">
                <span className="text-[9px] font-mono text-cyan-400/60 block">MARKET REGIME</span>
                <span className="text-base font-bold font-mono text-cyan-300 tracking-wider">{currentMarket.regime}</span>
              </div>

              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-cyan-500/10">
                  <span className="text-cyan-500/70">TREND:</span>
                  <span className="text-cyan-200">{currentMarket.trend} STRUCTURE</span>
                </div>
                <div className="flex justify-between py-1 border-b border-cyan-500/10">
                  <span className="text-cyan-500/70">MOMENTUM:</span>
                  <span className="text-emerald-400">POSITIVE</span>
                </div>
                <div className="flex justify-between py-1 border-b border-cyan-500/10">
                  <span className="text-cyan-500/70">VOLATILITY:</span>
                  <span className="text-cyan-200">{currentMarket.volatility}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-cyan-500/70">AI CONFIDENCE:</span>
                  <span className="text-cyan-300">DEMO</span>
                </div>
              </div>
            </div>

            {/* AI SIGNAL ENGINE PREVIEW */}
            <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md space-y-3">
              <div className="flex items-center justify-between border-b border-cyan-500/15 pb-2">
                <h3 className="text-xs font-mono font-bold text-white tracking-widest uppercase">AI SIGNAL ENGINE</h3>
                <span className="text-[9px] font-mono text-cyan-400/60">DEMO SETUP</span>
              </div>

              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-cyan-500/70">PAIR & TF:</span>
                <span className="text-white font-bold">{selectedSymbol} • 15M</span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-1">
                <div className="p-2 rounded bg-cyan-950/30 border border-cyan-500/15">
                  <span className="text-[9px] text-cyan-400/60 block">DIRECTION</span>
                  <span className="text-emerald-400 font-bold">BUY / LONG</span>
                </div>
                <div className="p-2 rounded bg-cyan-950/30 border border-cyan-500/15">
                  <span className="text-[9px] text-cyan-400/60 block">ENTRY TARGET</span>
                  <span className="text-cyan-200 font-bold">$97,500</span>
                </div>
              </div>

              <div className="text-[9px] font-mono text-center text-cyan-500/55 pt-1">
                SIGNAL STATUS: DEMONSTRATION ONLY
              </div>
            </div>
          </div>
        </div>

        {/* HOLOGRAPHIC WATCHLIST TABLE */}
        <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md space-y-4">
          <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
            <h3 className="text-xs font-mono font-bold text-white tracking-widest uppercase">MARKET WATCHLIST</h3>
            <span className="text-[9px] font-mono text-cyan-400/60">{filteredWatchlist.length} INSTRUMENTS INDEXED</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-cyan-500/15 text-cyan-400/60 text-[10px]">
                  <th className="pb-2 font-normal">MARKET</th>
                  <th className="pb-2 font-normal">PRICE</th>
                  <th className="pb-2 font-normal">CHANGE</th>
                  <th className="pb-2 font-normal">TREND</th>
                  <th className="pb-2 font-normal text-right">AI STATE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-cyan-500/10">
                {filteredWatchlist.map((m) => (
                  <tr
                    key={m.symbol}
                    onClick={() => setSelectedSymbol(m.symbol)}
                    className="hover:bg-cyan-950/30 cursor-pointer transition"
                  >
                    <td className="py-3 font-bold text-white flex items-center space-x-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                      <span>{m.symbol}</span>
                    </td>
                    <td className="py-3 text-cyan-100">{m.price}</td>
                    <td className={`py-3 font-bold ${m.isPositive ? "text-emerald-400" : "text-red-400"}`}>
                      {m.change}
                    </td>
                    <td className="py-3 text-cyan-300">{m.trend}</td>
                    <td className="py-3 text-right text-cyan-400/70">{m.aiState}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
