"use client";

import React, { useState } from "react";

export default function KingZarrySignalsPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [selectedMarket, setSelectedMarket] = useState("BTC/USD");
  const [selectedTimeframe, setSelectedTimeframe] = useState("15M");
  const [activeControl, setActiveControl] = useState<string | null>(null);

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

  const markets = ["BTC/USD", "ETH/USD", "SOL/USD", "XAU/USD", "EUR/USD", "GBP/USD"];
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

  const multiTimeframes = [
    { tf: "4H", regime: "BEARISH", desc: "MAJOR REGIME" },
    { tf: "1H", regime: "BEARISH", desc: "DIRECTIONAL" },
    { tf: "15M", regime: "BULLISH", desc: "PRIMARY SETUP" },
    { tf: "5M", regime: "BEARISH", desc: "ENTRY TIMING" },
  ];

  const analysisInputsList = [
    { name: "EMA 9 / 21 / 50", status: "DEMO" },
    { name: "RSI 14", status: "READY" },
    { name: "ATR 14", status: "ANALYSIS INPUT" },
    { name: "MARKET STRUCTURE", status: "READY" },
    { name: "SWING LEVELS", status: "DEMO" },
    { name: "MOMENTUM", status: "READY" },
    { name: "VOLATILITY", status: "ANALYSIS INPUT" },
  ];

  const signalHistoryList = [
    { market: "BTC/USD", tf: "15M", dir: "BUY", time: "14:20 UTC", status: "DEMO" },
    { market: "ETH/USD", tf: "1H", dir: "SELL", time: "12:05 UTC", status: "DEMO" },
    { market: "XAU/USD", tf: "4H", dir: "BUY", time: "09:45 UTC", status: "DEMO" },
  ];

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
              <span>SIGNAL ENGINE ONLINE</span>
              <span className="text-cyan-700">•</span>
              <span>INTELLIGENCE SYSTEM</span>
            </div>
          </div>
        </div>

        {/* Navigation - Desktop */}
        <nav className="hidden lg:flex items-center space-x-1 bg-cyan-950/20 p-1 rounded-lg border border-cyan-500/10">
          {navItems.map((item) => {
            const isActive = item === "SIGNALS";
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
                  item === "SIGNALS"
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
        {/* PAGE IDENTITY HEADER */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyan-500/10 pb-4">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-[10px] font-mono text-cyan-400/60 uppercase tracking-widest">KING ZARRY AI</span>
              <span className="text-cyan-700">/</span>
              <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">SIGNAL ENGINE</span>
            </div>
            <h2 className="text-xl md:text-2xl font-bold tracking-widest text-white uppercase flex items-center space-x-3">
              <span>SIGNAL INTELLIGENCE</span>
            </h2>
            <p className="text-xs font-mono text-cyan-400/60 mt-1">
              AI analysis of market structure, momentum and conditions.
            </p>
          </div>

          <div className="flex items-center space-x-3 p-3 rounded-lg border border-cyan-500/20 bg-cyan-950/25 backdrop-blur-md">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500"></span>
            </span>
            <div className="text-xs font-mono">
              <span className="text-cyan-400/60">SYSTEM STATUS: </span>
              <strong className="text-cyan-300 tracking-wider">SIGNAL ENGINE ONLINE</strong>
            </div>
          </div>
        </div>

        {/* CONTROL BAR (Futuristic Controls) */}
        <div className="flex items-center justify-between overflow-x-auto py-2 border-y border-cyan-500/15 bg-cyan-950/10 px-4 rounded-xl gap-2">
          <div className="flex items-center space-x-2 min-w-max">
            <span className="text-[10px] font-mono text-cyan-400/50 uppercase tracking-widest mr-2">TELEMETRY CONTROLS:</span>
            {[
              "ANALYZE MARKET",
              "CHANGE MARKET",
              "CHANGE TIMEFRAME",
              "SIGNAL HISTORY",
              "SIGNAL SETTINGS",
            ].map((ctrl) => (
              <button
                key={ctrl}
                onClick={() => setActiveControl(ctrl)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono border transition ${
                  activeControl === ctrl
                    ? "bg-cyan-500/25 text-cyan-300 border-cyan-400 shadow-[0_0_10px_rgba(0,240,255,0.2)]"
                    : "bg-cyan-950/30 text-cyan-400/70 border-cyan-500/20 hover:bg-cyan-500/10 hover:text-cyan-200"
                }`}
              >
                {ctrl}
              </button>
            ))}
          </div>
          <span className="hidden xl:inline-block text-[10px] font-mono text-cyan-500/60">
            ENGINE_ID: KZ_SIG_V2.4
          </span>
        </div>

        {/* MARKET & TIMEFRAME SELECTORS */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* Market Selector */}
          <div className="lg:col-span-8 p-4 rounded-2xl border border-cyan-500/20 bg-[#020914]/80 backdrop-blur-md">
            <div className="text-[10px] font-mono font-bold tracking-widest text-cyan-400/60 uppercase mb-2">
              MARKET SELECTOR [DEMO]
            </div>
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
              {markets.map((mkt) => {
                const isSelected = selectedMarket === mkt;
                return (
                  <button
                    key={mkt}
                    onClick={() => setSelectedMarket(mkt)}
                    className={`p-2.5 rounded-xl text-xs font-mono font-bold transition border text-center ${
                      isSelected
                        ? "bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-[0_0_12px_rgba(0,240,255,0.25)]"
                        : "bg-cyan-950/20 text-cyan-400/70 border-cyan-500/15 hover:bg-cyan-500/10 hover:text-cyan-200"
                    }`}
                  >
                    {mkt}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Timeframe Selector */}
          <div className="lg:col-span-4 p-4 rounded-2xl border border-cyan-500/20 bg-[#020914]/80 backdrop-blur-md">
            <div className="text-[10px] font-mono font-bold tracking-widest text-cyan-400/60 uppercase mb-2">
              TIMEFRAME SELECTOR
            </div>
            <div className="grid grid-cols-5 gap-1.5">
              {timeframes.map((tf) => {
                const isSelected = selectedTimeframe === tf;
                return (
                  <button
                    key={tf}
                    onClick={() => setSelectedTimeframe(tf)}
                    className={`py-2 rounded-lg text-xs font-mono font-bold transition border text-center ${
                      isSelected
                        ? "bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-[0_0_10px_rgba(0,240,255,0.25)]"
                        : "bg-cyan-950/20 text-cyan-400/70 border-cyan-500/15 hover:bg-cyan-500/10 hover:text-cyan-200"
                    }`}
                  >
                    {tf}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* CENTRAL SIGNAL CORE & PRIMARY SIGNAL SECTION */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* CENTRAL SIGNAL CORE (Visual Anchor) */}
          <div className="lg:col-span-6 relative rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md flex flex-col items-center justify-center overflow-hidden min-h-[380px]">
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff06_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff06_1px,transparent_1px)] bg-[size:20px_20px]" />
            
            <div className="absolute top-4 left-4 text-[10px] font-mono tracking-widest text-cyan-400/70 uppercase">
              SIGNAL CORE — DATA → ANALYSIS → SIGNAL
            </div>

            {/* Holographic Core Graphic */}
            <div className="relative w-48 h-48 flex items-center justify-center my-6">
              <div className="absolute inset-0 rounded-full border border-cyan-500/30 animate-[spin_30s_linear_infinite]" />
              <div className="absolute inset-2 rounded-full border border-dashed border-cyan-400/20 animate-[spin_20s_linear_infinite_reverse]" />
              <div className="absolute inset-6 rounded-full border border-cyan-500/40 animate-[spin_12s_linear_infinite]" />
              <div className="absolute inset-10 rounded-full bg-cyan-500/10 blur-xl animate-pulse shadow-[0_0_30px_rgba(0,240,255,0.3)]" />

              <div className="relative z-10 flex flex-col items-center justify-center w-20 h-20 rounded-full bg-[#031322] border border-cyan-400/60 shadow-[inset_0_0_20px_rgba(0,240,255,0.4)]">
                <span className="font-extrabold text-xl tracking-tighter text-white">KZ</span>
                <span className="text-[8px] font-mono tracking-widest text-cyan-400/80 -mt-1">SIGNAL</span>
              </div>

              {/* Orbiting Nodes */}
              <div className="absolute w-full h-full animate-[spin_15s_linear_infinite]">
                <div className="w-2 h-2 rounded-full bg-cyan-300 shadow-[0_0_8px_#00f0ff] absolute top-2 left-1/2 -translate-x-1/2" />
              </div>
              <div className="absolute w-full h-full animate-[spin_10s_linear_infinite_reverse]">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 shadow-[0_0_8px_#6366f1] absolute bottom-3 right-4" />
              </div>
            </div>

            {/* Intelligence Inputs Ring Tags */}
            <div className="relative z-10 grid grid-cols-4 gap-2 w-full mt-2">
              {coreInputs.map((input) => (
                <div key={input} className="px-2 py-1 rounded border border-cyan-500/20 bg-cyan-950/30 text-[9px] font-mono text-center text-cyan-300 truncate">
                  {input}
                </div>
              ))}
            </div>
          </div>

          {/* PRIMARY SIGNAL & CONFIDENCE PANEL */}
          <div className="lg:col-span-6 flex flex-col space-y-6">
            {/* Primary Signal Display */}
            <div className="relative rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md flex flex-col justify-between flex-1">
              <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                <div className="flex items-center space-x-2 font-mono text-xs">
                  <span className="text-cyan-300 font-bold">{selectedMarket}</span>
                  <span className="text-cyan-500/60">•</span>
                  <span className="text-cyan-400">{selectedTimeframe}</span>
                  <span className="text-cyan-500/60">•</span>
                  <span className="text-cyan-400/70">DEMO SIGNAL</span>
                </div>
                <span className="px-2 py-0.5 text-[9px] font-mono rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  SIGNAL STATUS: DEMONSTRATION
                </span>
              </div>

              <div className="py-6 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono text-cyan-400/60 uppercase tracking-widest block mb-1">
                    GENERATED SETUP DIRECTION
                  </span>
                  <div className="text-4xl md:text-5xl font-black font-mono tracking-wider text-emerald-400 drop-shadow-[0_0_15px_rgba(16,185,129,0.3)]">
                    BUY
                  </div>
                </div>

                <div className="text-right font-mono">
                  <span className="text-[10px] text-cyan-400/60 uppercase tracking-widest block mb-1">
                    AI SIGNAL CONFIDENCE
                  </span>
                  <div className="text-2xl md:text-3xl font-bold text-cyan-200">
                    DEMO <span className="text-xs text-cyan-400 font-normal">CONFIDENCE</span>
                  </div>
                </div>
              </div>

              {/* Visual Progress Meter */}
              <div className="space-y-1.5 font-mono">
                <div className="flex justify-between text-[10px] text-cyan-400/70">
                  <span>CONFIDENCE METER [DEMO VISUALIZATION]</span>
                  <span>78% EQUIVALENT</span>
                </div>
                <div className="w-full h-2 rounded-full bg-cyan-950/60 border border-cyan-500/30 overflow-hidden p-0.5">
                  <div className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-400 w-[78%] shadow-[0_0_10px_rgba(0,240,255,0.4)]" />
                </div>
              </div>
            </div>

            {/* ENTRY / RISK STRUCTURE */}
            <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md">
              <div className="text-[10px] font-mono font-bold tracking-widest text-cyan-400/70 uppercase mb-3">
                HOLOGRAPHIC MARKET STRUCTURE & RISK LEVELS
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 font-mono text-xs">
                {[
                  { label: "ENTRY", val: "DEMO" },
                  { label: "STOP LOSS", val: "DEMO" },
                  { label: "TP1", val: "DEMO" },
                  { label: "TP2", val: "DEMO" },
                  { label: "TP3", val: "DEMO" },
                ].map((item) => (
                  <div key={item.label} className="p-2.5 rounded-xl border border-cyan-500/20 bg-cyan-950/30 text-center">
                    <span className="text-[9px] text-cyan-400/60 block mb-0.5">{item.label}</span>
                    <span className="text-cyan-200 font-bold">{item.val}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* MULTI-TIMEFRAME INTELLIGENCE & TECHNICAL ANALYSIS INPUTS */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Multi-Timeframe Intelligence */}
          <div className="lg:col-span-6 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md space-y-4">
            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">MULTI-TIMEFRAME INTELLIGENCE</h3>
              <span className="text-[9px] font-mono text-cyan-400/60">4 TIMEFRAME SYNC</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {multiTimeframes.map((item) => (
                <div key={item.tf} className="p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/25 flex items-center justify-between font-mono">
                  <div>
                    <span className="text-xs font-bold text-white block">{item.tf} TIMEFRAME</span>
                    <span className="text-[9px] text-cyan-400/60 block">{item.desc}</span>
                  </div>
                  <span className={`px-2 py-1 text-[10px] font-bold rounded border ${
                    item.regime === "BULLISH"
                      ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                      : "bg-red-500/20 text-red-300 border-red-500/40"
                  }`}>
                    {item.regime}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Technical Analysis Inputs */}
          <div className="lg:col-span-6 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md space-y-4">
            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">ANALYSIS INPUTS</h3>
              <span className="text-[9px] font-mono text-cyan-400/60">INDICATORS & METRICS</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-[220px] overflow-y-auto pr-1">
              {analysisInputsList.map((input, idx) => (
                <div key={idx} className="p-2.5 rounded-xl border border-cyan-500/20 bg-cyan-950/25 flex items-center justify-between font-mono text-xs">
                  <span className="text-cyan-100 font-bold">{input.name}</span>
                  <span className="px-1.5 py-0.5 text-[9px] rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                    {input.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* MARKET STRUCTURE VISUALIZATION & AI EXPLANATION */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Market Structure SVG Chart Visualization */}
          <div className="lg:col-span-7 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md space-y-4">
            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">MARKET STRUCTURE VISUALIZATION</h3>
              <span className="text-[9px] font-mono text-cyan-400/60">HIGHER HIGHS / SWING LEVELS</span>
            </div>

            {/* Stylized SVG Chart */}
            <div className="relative w-full h-56 rounded-xl border border-cyan-500/20 bg-[#01060e] p-4 flex flex-col justify-between overflow-hidden">
              <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff05_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff05_1px,transparent_1px)] bg-[size:24px_24px]" />
              
              <div className="relative z-10 flex justify-between text-[9px] font-mono text-cyan-400/60">
                <span>RESISTANCE • DEMO ZONE</span>
                <span>SUPPORT • DEMO ZONE</span>
              </div>

              {/* SVG Trendline Chart */}
              <div className="relative z-10 w-full h-32 flex items-center">
                <svg className="w-full h-full overflow-visible" viewBox="0 0 500 150" preserveAspectRatio="none">
                  {/* Grid Lines */}
                  <line x1="0" y1="37" x2="500" y2="37" stroke="rgba(0,240,255,0.1)" strokeDasharray="4 4" />
                  <line x1="0" y1="75" x2="500" y2="75" stroke="rgba(0,240,255,0.1)" strokeDasharray="4 4" />
                  <line x1="0" y1="112" x2="500" y2="112" stroke="rgba(0,240,255,0.1)" strokeDasharray="4 4" />

                  {/* Price Path */}
                  <path
                    d="M 10 120 L 70 90 L 130 105 L 190 60 L 250 80 L 310 40 L 370 55 L 430 25 L 490 45"
                    fill="none"
                    stroke="#00f0ff"
                    strokeWidth="2.5"
                    className="drop-shadow-[0_0_8px_rgba(0,240,255,0.6)]"
                  />

                  {/* Nodes */}
                  <circle cx="70" cy="90" r="3.5" fill="#00f0ff" />
                  <circle cx="190" cy="60" r="3.5" fill="#00f0ff" />
                  <circle cx="310" cy="40" r="3.5" fill="#10b981" />
                  <circle cx="430" cy="25" r="4" fill="#10b981" className="animate-ping" />
                </svg>
              </div>

              <div className="relative z-10 flex justify-between text-[9px] font-mono text-cyan-300">
                <span>STRUCTURE: HIGHER HIGHS & HIGHER LOWS</span>
                <span>AI INTERPRETATION: BULLISH CONTINUATION</span>
              </div>
            </div>
          </div>

          {/* AI Signal Explanation */}
          <div className="lg:col-span-5 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md space-y-4">
            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">WHY THIS SIGNAL?</h3>
              <span className="text-[9px] font-mono text-cyan-400/60">REASONING EXPLANATION</span>
            </div>

            <p className="text-xs font-sans text-cyan-100/90 leading-relaxed">
              The signal engine combines market structure, momentum, volatility and multi-timeframe context before producing a setup.
            </p>

            <div className="grid grid-cols-2 gap-2 pt-2">
              {["STRUCTURE", "MOMENTUM", "VOLATILITY", "TIMEFRAME ALIGNMENT"].map((factor, idx) => (
                <div key={idx} className="p-2.5 rounded-xl border border-cyan-500/20 bg-cyan-950/25 font-mono text-[10px]">
                  <span className="text-cyan-400/60 block">FACTOR 0{idx + 1}</span>
                  <span className="text-cyan-200 font-bold">{factor}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* SIGNAL HISTORY & SYSTEM STATUS SECTION */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Signal History Timeline */}
          <div className="lg:col-span-7 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md space-y-4">
            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">SIGNAL HISTORY [DEMONSTRATION HISTORY]</h3>
              <span className="text-[9px] font-mono text-cyan-400/60">TIMELINE LOGS</span>
            </div>

            <div className="space-y-2.5">
              {signalHistoryList.map((item, idx) => (
                <div key={idx} className="p-3 rounded-xl border border-cyan-500/20 bg-cyan-950/25 flex items-center justify-between font-mono text-xs">
                  <div className="flex items-center space-x-3">
                    <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[10px]">
                      {item.market}
                    </span>
                    <span className="text-cyan-400/70">{item.tf}</span>
                    <span className="text-cyan-500/60">•</span>
                    <span className="text-emerald-400 font-bold">{item.dir}</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className="text-[10px] text-cyan-400/60">{item.time}</span>
                    <span className="px-1.5 py-0.5 text-[9px] rounded bg-cyan-950/40 text-cyan-400 border border-cyan-500/20">
                      {item.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Signal Engine Status */}
          <div className="lg:col-span-5 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md space-y-4">
            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">SIGNAL ENGINE STATUS</h3>
              <span className="text-[9px] font-mono text-cyan-400/60">TELEMETRY</span>
            </div>

            <div className="space-y-2.5 font-mono text-xs">
              {[
                { label: "MARKET DATA", state: "READY" },
                { label: "ANALYSIS ENGINE", state: "READY" },
                { label: "MULTI-TIMEFRAME", state: "READY" },
                { label: "SIGNAL OUTPUT", state: "DEMO" },
              ].map((row, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded-xl border border-cyan-500/20 bg-cyan-950/25">
                  <span className="text-white font-bold">{row.label}</span>
                  <span className="px-2 py-0.5 text-[10px] rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                    {row.state}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RISK NOTICE DISCLAIMER */}
        <div className="p-4 rounded-xl border border-cyan-500/20 bg-cyan-950/15 backdrop-blur-md text-center">
          <p className="text-[11px] font-mono text-cyan-400/70 tracking-wide">
            DEMONSTRATION ONLY. AI-generated market analysis is not financial advice and does not guarantee outcomes.
          </p>
        </div>
      </main>

      {/* FOOTER */}
      <footer className="relative z-20 border-t border-cyan-500/15 bg-[#030810]/80 px-6 py-4 mt-8">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between text-xs font-mono text-cyan-400/60 gap-2">
          <span>KING ZARRY AI • SIGNAL INTELLIGENCE SYSTEM</span>
          <span>SECURE TELEMETRY ACTIVE</span>
        </div>
      </footer>
    </div>
  );
}
