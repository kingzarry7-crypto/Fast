"use client";

import React, { useState, useEffect } from "react";

// Alert Interfaces
type AlertPriority = "CRITICAL" | "HIGH" | "MEDIUM" | "INFO";
type AlertCategory = "ALL" | "MARKET" | "AI" | "NEWS" | "SYSTEM" | "AGENT" | "SECURITY";

interface AlertItem {
  id: string;
  category: AlertCategory;
  priority: AlertPriority;
  title: string;
  description: string;
  timestamp: string;
  read: boolean;
  statusText: string;
}

export default function KingZarryAlertsPage() {
  // State Management
  const [selectedCategory, setSelectedCategory] = useState<AlertCategory>("ALL");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [hudStats, setHudStats] = useState({
    scansPerSec: 1420,
    activeStreams: 18,
    latency: 11,
    nodesOnline: 64,
  });

  // Demo Alert Data
  const [alerts, setAlerts] = useState<AlertItem[]>([
    {
      id: "alt-001",
      category: "MARKET",
      priority: "CRITICAL",
      title: "BTC/USD THRESHOLD TRIGGERED",
      description: "Bitcoin reached the monitored $98,500 upper liquidity resistance level.",
      timestamp: "2 MIN AGO",
      read: false,
      statusText: "PRICE MONITORED EXCEEDED",
    },
    {
      id: "alt-002",
      category: "NEWS",
      priority: "HIGH",
      title: "HIGH-IMPACT NEWS DETECTED",
      description: "A potentially significant macroeconomic event statement has been indexed.",
      timestamp: "18 MIN AGO",
      read: false,
      statusText: "NLP SIGNAL IMPACT 8.9/10",
    },
    {
      id: "alt-003",
      category: "AI",
      priority: "HIGH",
      title: "INTELLIGENCE ANALYSIS READY",
      description: "KING ZARRY AI completed a new multi-vector contextual synthesis report.",
      timestamp: "42 MIN AGO",
      read: false,
      statusText: "REPORT #KZ-9041 SYNTHESIZED",
    },
    {
      id: "alt-004",
      category: "SYSTEM",
      priority: "INFO",
      title: "MEMORY VECTOR SYNCHRONIZED",
      description: "AI neural context vector database successfully synced across nodes.",
      timestamp: "1 HR AGO",
      read: true,
      statusText: "CONTEXT BUFFERS STABLE",
    },
    {
      id: "alt-005",
      category: "AGENT",
      priority: "MEDIUM",
      title: "SCHEDULED AGENT TASK COMPLETED",
      description: "Agent Alpha-4 completed automated signal screening cycle.",
      timestamp: "3 HRS AGO",
      read: true,
      statusText: "EXECUTION SUCCESSFUL",
    },
    {
      id: "alt-006",
      category: "SECURITY",
      priority: "MEDIUM",
      title: "NEW SESSION ENCRYPTED",
      description: "New authenticated session initiated from encrypted terminal node.",
      timestamp: "5 HRS AGO",
      read: true,
      statusText: "2FA VERIFIED • KZ-NODE",
    },
  ]);

  // Telemetry fluctuation simulator
  useEffect(() => {
    const interval = setInterval(() => {
      setHudStats({
        scansPerSec: 1400 + Math.floor(Math.random() * 45),
        activeStreams: 18,
        latency: 10 + Math.floor(Math.random() * 4),
        nodesOnline: 64,
      });
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  // Filter alerts by category
  const filteredAlerts = alerts.filter(
    (alt) => selectedCategory === "ALL" || alt.category === selectedCategory
  );

  const markAllRead = () => {
    setAlerts((prev) => prev.map((item) => ({ ...item, read: true })));
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
    "MEMORY",
  ];

  const categories: AlertCategory[] = [
    "ALL",
    "MARKET",
    "AI",
    "NEWS",
    "SYSTEM",
    "AGENT",
    "SECURITY",
  ];

  const activeMonitors = [
    { label: "BTC/USD", status: "ACTIVE" },
    { label: "ETH/USD", status: "ACTIVE" },
    { label: "SOL/USD", status: "ACTIVE" },
    { label: "XAU/USD", status: "ACTIVE" },
    { label: "GLOBAL NEWS", status: "SCANNING" },
    { label: "AI CORE", status: "NOMINAL" },
    { label: "AGENT NETWORK", status: "SYNCED" },
  ];

  return (
    <div className="relative w-full min-h-screen bg-[#03060a] text-cyan-100 font-sans overflow-x-hidden flex flex-col justify-between selection:bg-cyan-500 selection:text-black">
      {/* Background Holographic Atmosphere */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#072438] via-[#020b14] to-[#010408] pointer-events-none" />
      <div className="fixed inset-0 bg-[linear-gradient(to_right,#091a2815_1px,transparent_1px),linear-gradient(to_bottom,#091a2815_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />
      <div className="fixed inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,240,255,0.012)_3px,transparent_4px)] pointer-events-none z-10" />

      {/* Radial Glows */}
      <div className="fixed top-[-10%] left-[30%] w-[600px] h-[600px] bg-cyan-600/10 rounded-full blur-[140px] pointer-events-none" />
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
                INTELLIGENCE ALERTS
              </span>
            </div>
            <div className="flex items-center space-x-2 text-[10px] font-mono text-cyan-400/70">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span>MONITORING ACTIVE</span>
              <span className="text-cyan-600">•</span>
              <span>SCANS: {hudStats.scansPerSec}/SEC</span>
            </div>
          </div>
        </div>

        {/* Navigation - Desktop */}
        <nav className="hidden lg:flex items-center space-x-1 bg-cyan-950/20 p-1 rounded-lg border border-cyan-500/10">
          {navItems.map((item) => {
            const isActive = item === "ALERTS";
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

        {/* Telemetry Stats & Mobile Toggle */}
        <div className="flex items-center space-x-4">
          <div className="hidden xl:flex items-center space-x-4 text-[10px] font-mono text-cyan-400/60 border-l border-cyan-500/15 pl-4">
            <div>
              STREAMS: <span className="text-cyan-300">{hudStats.activeStreams}</span>
            </div>
            <div>
              LATENCY: <span className="text-cyan-300">{hudStats.latency}ms</span>
            </div>
          </div>

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
                  item === "ALERTS"
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

      {/* MAIN CONTENT CONTENT */}
      <main className="relative z-20 flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-6">
        {/* SUB HEADER */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyan-500/10 pb-4">
          <div>
            <h2 className="text-xl md:text-2xl font-bold tracking-widest text-white uppercase flex items-center space-x-3">
              <span>INTELLIGENCE ALERTS</span>
            </h2>
            <p className="text-xs font-mono text-cyan-400/60 mt-1">
              Signals, events and intelligence requiring your attention.
            </p>
          </div>

          {/* AI ALERT INSIGHT PANEL */}
          <div className="p-3 rounded-lg border border-cyan-500/20 bg-cyan-950/20 backdrop-blur-md max-w-md">
            <div className="flex items-center justify-between text-[10px] font-mono text-cyan-400/80 mb-1">
              <span className="font-bold tracking-wider">AI ALERT INTELLIGENCE</span>
              <span className="text-emerald-400">SYSTEM STATUS: STABLE</span>
            </div>
            <p className="text-xs text-cyan-200">
              "No critical unhandled security breaches. 1 market liquidity threshold triggered for immediate review."
            </p>
          </div>
        </div>

        {/* MAIN HUD LAYOUT GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* LEFT 5 COLS: ALERT CORE HUD MONITOR */}
          <div className="lg:col-span-5 flex flex-col space-y-6">
            {/* ALERT CORE ORB MONITOR */}
            <div className="relative rounded-2xl border border-cyan-500/20 bg-[#020914]/80 p-6 backdrop-blur-md flex flex-col items-center justify-center overflow-hidden min-h-[320px]">
              {/* Background HUD Grid Lines */}
              <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff08_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff08_1px,transparent_1px)] bg-[size:16px_16px]" />

              {/* Central Glowing Orb */}
              <div className="relative w-44 h-44 flex items-center justify-center my-4">
                {/* Outer Ring 1 */}
                <div className="absolute inset-0 rounded-full border border-cyan-500/30 animate-[spin_24s_linear_infinite]" />
                {/* Outer Ring 2 */}
                <div className="absolute inset-2 rounded-full border border-dashed border-cyan-400/20 animate-[spin_16s_linear_infinite_reverse]" />
                {/* Core Radial Scanning Arc */}
                <div className="absolute inset-5 rounded-full border-2 border-transparent border-t-cyan-400 border-r-cyan-400/40 animate-[spin_6s_linear_infinite]" />

                {/* Core Wave Glowing Pulse */}
                <div className="absolute inset-8 rounded-full bg-cyan-500/10 blur-md animate-pulse shadow-[0_0_30px_rgba(0,240,255,0.3)]" />

                {/* Center Core HUD Node */}
                <div className="relative z-10 flex flex-col items-center justify-center w-20 h-20 rounded-full bg-[#031322] border border-cyan-400/60 shadow-[inset_0_0_15px_rgba(0,240,255,0.4)]">
                  <span className="font-mono text-xs font-bold text-cyan-300">ALERT</span>
                  <span className="font-extrabold text-lg text-white">CORE</span>
                </div>

                {/* Orbiting Orbital Nodes */}
                <div className="absolute w-full h-full animate-[spin_10s_linear_infinite]">
                  <div className="w-2 h-2 rounded-full bg-cyan-300 shadow-[0_0_10px_#00f0ff] absolute top-1 left-1/2 -translate-x-1/2" />
                </div>
                <div className="absolute w-full h-full animate-[spin_18s_linear_infinite_reverse]">
                  <div className="w-2 h-2 rounded-full bg-red-400 shadow-[0_0_10px_#f87171] absolute bottom-2 left-1/2 -translate-x-1/2" />
                </div>
              </div>

              {/* Status Banner */}
              <div className="relative z-10 text-center space-y-1 mt-2">
                <div className="text-xs font-mono tracking-widest text-cyan-300 uppercase">
                  MONITORING ACTIVE NODE NETWORKS
                </div>
                <div className="text-[10px] font-mono text-cyan-500/70">
                  SCANNING FREQUENCY: HIGH-PRECISION CONTINUOUS
                </div>
              </div>
            </div>

            {/* ACTIVE MONITORS PANEL */}
            <div className="rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-4 backdrop-blur-md space-y-3">
              <div className="flex items-center justify-between text-xs font-mono text-cyan-400 border-b border-cyan-500/15 pb-2">
                <span className="font-bold tracking-wider uppercase">ACTIVE MONITORS</span>
                <span className="text-[10px] text-cyan-500/60">7 CHANNELS</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-2 gap-2">
                {activeMonitors.map((mon) => (
                  <div
                    key={mon.label}
                    className="flex items-center justify-between px-2.5 py-1.5 rounded border border-cyan-500/15 bg-cyan-950/20 text-[11px] font-mono"
                  >
                    <span className="text-cyan-200">{mon.label}</span>
                    <span className="text-[9px] text-emerald-400 flex items-center space-x-1">
                      <span className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse" />
                      <span>{mon.status}</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT 7 COLS: ALERT FEED & COMMAND CONTROLS */}
          <div className="lg:col-span-7 flex flex-col space-y-4">
            {/* COMMAND CONTROL BAR */}
            <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-xl border border-cyan-500/20 bg-[#020914]/80 backdrop-blur-md">
              <div className="flex flex-wrap items-center gap-2">
                <button className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold text-black bg-cyan-400 hover:bg-cyan-300 shadow-[0_0_12px_rgba(0,240,255,0.3)] transition">
                  + CREATE ALERT
                </button>
                <button className="px-3 py-1.5 rounded-lg text-xs font-mono text-cyan-300 border border-cyan-500/30 hover:bg-cyan-500/10 transition">
                  MANAGE MONITORS
                </button>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={markAllRead}
                  className="px-3 py-1.5 rounded-lg text-xs font-mono text-cyan-400/70 hover:text-cyan-200 hover:bg-cyan-500/10 transition"
                >
                  MARK ALL READ
                </button>
                <button className="px-2 py-1.5 rounded-lg text-xs font-mono text-cyan-400/70 hover:text-cyan-200 hover:bg-cyan-500/10 transition">
                  ⚙️
                </button>
              </div>
            </div>

            {/* CATEGORY FILTER BAR */}
            <div className="flex items-center space-x-1 overflow-x-auto pb-1 scrollbar-none">
              {categories.map((cat) => {
                const isActive = selectedCategory === cat;
                return (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-3 py-1 rounded-md text-xs font-mono tracking-wider transition-all whitespace-nowrap ${
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

            {/* ALERT FEED LIST */}
            <div className="space-y-3">
              {filteredAlerts.length === 0 ? (
                <div className="p-8 text-center border border-cyan-500/10 rounded-xl font-mono text-xs text-cyan-500/50">
                  NO ALERTS FOUND FOR SELECTED CATEGORY FILTER.
                </div>
              ) : (
                filteredAlerts.map((alt) => {
                  const isCritical = alt.priority === "CRITICAL";
                  const isHigh = alt.priority === "HIGH";

                  return (
                    <div
                      key={alt.id}
                      className={`relative rounded-xl p-4 transition-all duration-300 backdrop-blur-md border ${
                        !alt.read
                          ? isCritical
                            ? "bg-red-950/20 border-red-500/40 shadow-[0_0_20px_rgba(239,68,68,0.15)]"
                            : isHigh
                            ? "bg-cyan-950/30 border-cyan-500/40 shadow-[0_0_15px_rgba(0,240,255,0.1)]"
                            : "bg-[#041120]/80 border-cyan-500/30"
                          : "bg-[#020914]/60 border-cyan-500/10 text-cyan-400/60"
                      }`}
                    >
                      {/* Left Accent Bar */}
                      <div
                        className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-xl ${
                          isCritical
                            ? "bg-red-500 shadow-[0_0_8px_#ef4444]"
                            : isHigh
                            ? "bg-cyan-400 shadow-[0_0_8px_#00f0ff]"
                            : "bg-cyan-800"
                        }`}
                      />

                      <div className="flex items-start justify-between gap-2 mb-1 pl-2">
                        <div className="flex items-center space-x-2">
                          <span
                            className={`px-2 py-0.5 text-[9px] font-mono rounded font-bold ${
                              isCritical
                                ? "bg-red-950/80 text-red-300 border border-red-500/40"
                                : "bg-cyan-950/80 text-cyan-300 border border-cyan-500/30"
                            }`}
                          >
                            {alt.category}
                          </span>
                          <span
                            className={`text-[9px] font-mono tracking-widest ${
                              isCritical ? "text-red-400" : "text-cyan-400/70"
                            }`}
                          >
                            {alt.priority}
                          </span>
                        </div>
                        <span className="text-[10px] font-mono text-cyan-400/50">{alt.timestamp}</span>
                      </div>

                      <div className="pl-2 space-y-1">
                        <h3 className="text-sm font-bold tracking-wide text-white">{alt.title}</h3>
                        <p className="text-xs text-cyan-200/80 font-sans leading-relaxed">{alt.description}</p>
                      </div>

                      <div className="mt-3 pt-2 border-t border-cyan-500/10 pl-2 flex items-center justify-between text-[10px] font-mono text-cyan-400/50">
                        <span>{alt.statusText}</span>
                        {!alt.read && <span className="text-cyan-300">● UNREAD</span>}
                      </div>
                    </div>
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
