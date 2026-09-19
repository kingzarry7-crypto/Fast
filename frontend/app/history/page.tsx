"use client";

import React, { useState, useEffect } from "react";

// Types
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
}

export default function KingZarryHistoryPage() {
  // State
  const [selectedCategory, setSelectedCategory] = useState<CategoryType>("ALL");
  const [timeFilter, setTimeFilter] = useState<TimeFilter>("ALL TIME");
  const [sortOrder, setSortOrder] = useState<SortOrder>("NEWEST");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRecordId, setSelectedRecordId] = useState<string>("mem-001");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // HUD Dynamic Stats Simulator
  const [hudStats, setHudStats] = useState({
    conversations: 128,
    aiMemories: 342,
    analyses: 87,
    savedItems: 46,
    nodesConnected: 64,
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setHudStats((prev) => ({
        ...prev,
        nodesConnected: 60 + Math.floor(Math.random() * 8),
      }));
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  // Demo Memory Records Data
  const demoRecords: HistoryRecord[] = [
    {
      id: "mem-001",
      category: "CHAT",
      title: "BTC Analysis Discussion",
      description: "KING ZARRY AI conversation regarding market structure, macro liquidity, and key risk levels.",
      timestamp: "Today • 14:32",
      status: "CONTEXT INDEXED",
      source: "CHAT CORE",
      contextPreview: "User requested tactical evaluation of key resistance points. AI summarized multi-frame order flow vectors.",
      memoryId: "KZ-MEM-90812",
      timeframe: "TODAY",
    },
    {
      id: "mem-002",
      category: "AI ANALYSIS",
      title: "Market Structure Synthesis",
      description: "Deep cognitive intelligence analysis compiled based on multi-asset liquidity clusters.",
      timestamp: "Today • 12:18",
      status: "ANALYSIS ARCHIVED",
      source: "REASONING ENGINE",
      contextPreview: "Automated synthesis identified institutional sweep zones across crypto and forex benchmarks.",
      memoryId: "KZ-ANL-40192",
      timeframe: "TODAY",
    },
    {
      id: "mem-003",
      category: "VISION",
      title: "Chart & Technical Image Analysis",
      description: "User uploaded chart screenshot processed by the spatial AI vision module.",
      timestamp: "Yesterday • 21:07",
      status: "SPATIAL VECTOR STORED",
      source: "VISION MATRIX",
      contextPreview: "Pattern detection confirmed double bottom formation with 87.4% historical confluence.",
      memoryId: "KZ-VIS-10843",
      timeframe: "7 DAYS",
    },
    {
      id: "mem-004",
      category: "SIGNALS",
      title: "BTC/USD High Confluence Setup",
      description: "Trading analysis parameters generated from selected algorithmic market telemetry.",
      timestamp: "Yesterday • 18:42",
      status: "SIGNAL SAVED",
      source: "SIGNAL ENGINE",
      contextPreview: "Entry target $97,800 validated against institutional order block parameters.",
      memoryId: "KZ-SIG-77210",
      timeframe: "7 DAYS",
    },
    {
      id: "mem-005",
      category: "SYSTEM",
      title: "Preference & Risk Limits Saved",
      description: "User preferred risk threshold guidelines permanently written to AI memory matrix.",
      timestamp: "2 days ago",
      status: "MEMORY PERSISTED",
      source: "MEMORY CORE",
      contextPreview: "Max daily drawdown risk set to 2.5%. Core system will maintain constraint across all queries.",
      memoryId: "KZ-SYS-00412",
      timeframe: "30 DAYS",
    },
    {
      id: "mem-006",
      category: "AGENTS",
      title: "Agent Alpha Automated Task Execution",
      description: "Autonomous task executed by Agent Alpha screening news triggers and volatility alerts.",
      timestamp: "3 days ago",
      status: "EXECUTION COMPLETE",
      source: "AGENT NETWORK",
      contextPreview: "Task completed in 1.4s with 0 errors detected. 14 indicators validated.",
      memoryId: "KZ-AGN-33019",
      timeframe: "30 DAYS",
    },
  ];

  // Filtering Logic
  const filteredRecords = demoRecords
    .filter((rec) => {
      const matchCat = selectedCategory === "ALL" || rec.category === selectedCategory;
      const matchSearch =
        rec.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rec.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rec.memoryId.toLowerCase().includes(searchQuery.toLowerCase());
      const matchTime = timeFilter === "ALL TIME" || rec.timeframe === timeFilter;
      return matchCat && matchSearch && matchTime;
    })
    .sort((a, b) => {
      if (sortOrder === "NEWEST") return a.id.localeCompare(b.id);
      return b.id.localeCompare(a.id);
    });

  const selectedRecord = demoRecords.find((r) => r.id === selectedRecordId) || demoRecords[0];

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

  return (
    <div className="relative w-full min-h-screen bg-[#03060a] text-cyan-100 font-sans overflow-x-hidden flex flex-col justify-between selection:bg-cyan-500 selection:text-black">
      {/* Background Holographic Atmosphere */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#072438] via-[#020b14] to-[#010408] pointer-events-none" />
      <div className="fixed inset-0 bg-[linear-gradient(to_right,#091a2815_1px,transparent_1px),linear-gradient(to_bottom,#091a2815_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />
      <div className="fixed inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,240,255,0.012)_3px,transparent_4px)] pointer-events-none z-10" />

      {/* Radial Soft Ambient Spheres */}
      <div className="fixed top-[-10%] left-[25%] w-[600px] h-[600px] bg-cyan-600/10 rounded-full blur-[140px] pointer-events-none" />
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
                INTELLIGENCE HISTORY
              </span>
            </div>
            <div className="flex items-center space-x-2 text-[10px] font-mono text-cyan-400/70">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span>MEMORY CORE ONLINE</span>
              <span className="text-cyan-700">•</span>
              <span>INDEXED NODES: {hudStats.nodesConnected}</span>
            </div>
          </div>
        </div>

        {/* Navigation - Desktop */}
        <nav className="hidden lg:flex items-center space-x-1 bg-cyan-950/20 p-1 rounded-lg border border-cyan-500/10">
          {navItems.map((item) => {
            const isActive = item === "HISTORY";
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
              MEMORIES: <span className="text-cyan-300">{hudStats.aiMemories}</span>
            </div>
            <div>
              ANALYSES: <span className="text-cyan-300">{hudStats.analyses}</span>
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
                  item === "HISTORY"
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
              <span>INTELLIGENCE HISTORY</span>
            </h2>
            <p className="text-xs font-mono text-cyan-400/60 mt-1">
              Your conversations, analyses, signals and important AI activity, organized in one memory archive.
            </p>
          </div>

          {/* AI MEMORY INSIGHT PANEL */}
          <div className="p-3 rounded-lg border border-cyan-500/20 bg-cyan-950/20 backdrop-blur-md max-w-md">
            <div className="flex items-center justify-between text-[10px] font-mono text-cyan-400/80 mb-1">
              <span className="font-bold tracking-wider">AI MEMORY INSIGHT</span>
              <span className="text-cyan-400">INDEX: DEMO</span>
            </div>
            <p className="text-xs text-cyan-200">
              "Your history is organized across conversations, analyses, memories and system activity. KING ZARRY AI
              can use relevant context when memory functionality is connected."
            </p>
          </div>
        </div>

        {/* MEMORY CORE HUD DISPLAY */}
        <div className="relative rounded-2xl border border-cyan-500/20 bg-[#020914]/80 p-6 backdrop-blur-md overflow-hidden flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Background Micro Grid Lines */}
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff08_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff08_1px,transparent_1px)] bg-[size:16px_16px]" />

          {/* Central Memory Core Visual */}
          <div className="relative z-10 flex flex-col items-center justify-center w-full md:w-1/3">
            <div className="relative w-36 h-36 flex items-center justify-center">
              {/* Outer Rotating HUD Ring 1 */}
              <div className="absolute inset-0 rounded-full border border-cyan-500/30 animate-[spin_20s_linear_infinite]" />
              {/* Outer Ring 2 (Reverse) */}
              <div className="absolute inset-2 rounded-full border border-dashed border-cyan-400/20 animate-[spin_14s_linear_infinite_reverse]" />
              {/* Core Wave Glowing Pulse */}
              <div className="absolute inset-5 rounded-full bg-cyan-500/10 blur-md animate-pulse shadow-[0_0_25px_rgba(0,240,255,0.3)]" />

              {/* Inner Glowing Core */}
              <div className="relative z-10 flex flex-col items-center justify-center w-16 h-16 rounded-full bg-[#031322] border border-cyan-400/60 shadow-[inset_0_0_15px_rgba(0,240,255,0.4)]">
                <span className="font-extrabold text-lg tracking-tighter text-white">KZ</span>
                <span className="text-[8px] font-mono tracking-widest text-cyan-400/80 -mt-1">CORE</span>
              </div>

              {/* Orbiting Orbital Nodes */}
              <div className="absolute w-full h-full animate-[spin_8s_linear_infinite]">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-300 shadow-[0_0_8px_#00f0ff] absolute top-0 left-1/2 -translate-x-1/2" />
              </div>
              <div className="absolute w-full h-full animate-[spin_12s_linear_infinite_reverse]">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 shadow-[0_0_8px_#818cf8] absolute bottom-0 left-1/2 -translate-x-1/2" />
              </div>
            </div>

            <div className="mt-2 text-center">
              <span className="text-xs font-mono font-bold tracking-widest text-cyan-200 uppercase">MEMORY CORE</span>
              <div className="text-[9px] font-mono text-cyan-500/70">CONVERSATIONS → MEMORY → CONTEXT → INTELLIGENCE</div>
            </div>
          </div>

          {/* MEMORY STATISTICS GRID */}
          <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 gap-3 w-full md:w-2/3">
            <div className="p-3.5 rounded-xl border border-cyan-500/15 bg-cyan-950/20 text-center space-y-1">
              <span className="text-[10px] font-mono text-cyan-400/60 tracking-wider uppercase block">
                CONVERSATIONS
              </span>
              <span className="text-xl font-bold font-mono text-white tracking-wider">{hudStats.conversations}</span>
              <span className="text-[9px] font-mono text-cyan-500/50 block">DEMO INDEX</span>
            </div>

            <div className="p-3.5 rounded-xl border border-cyan-500/15 bg-cyan-950/20 text-center space-y-1">
              <span className="text-[10px] font-mono text-cyan-400/60 tracking-wider uppercase block">
                AI MEMORIES
              </span>
              <span className="text-xl font-bold font-mono text-cyan-300 tracking-wider">{hudStats.aiMemories}</span>
              <span className="text-[9px] font-mono text-cyan-500/50 block">STORED CONTEXT</span>
            </div>

            <div className="p-3.5 rounded-xl border border-cyan-500/15 bg-cyan-950/20 text-center space-y-1">
              <span className="text-[10px] font-mono text-cyan-400/60 tracking-wider uppercase block">ANALYSES</span>
              <span className="text-xl font-bold font-mono text-indigo-300 tracking-wider">{hudStats.analyses}</span>
              <span className="text-[9px] font-mono text-cyan-500/50 block">SYNTHESIZED</span>
            </div>

            <div className="p-3.5 rounded-xl border border-cyan-500/15 bg-cyan-950/20 text-center space-y-1">
              <span className="text-[10px] font-mono text-cyan-400/60 tracking-wider uppercase block">SAVED ITEMS</span>
              <span className="text-xl font-bold font-mono text-emerald-300 tracking-wider">{hudStats.savedItems}</span>
              <span className="text-[9px] font-mono text-cyan-500/50 block">BOOKMARKED</span>
            </div>
          </div>
        </div>

        {/* SEARCH & SYSTEM CONTROLS BAR */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-3 p-3 rounded-xl border border-cyan-500/20 bg-[#020914]/80 backdrop-blur-md">
          {/* Futuristic Search Input */}
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
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search your intelligence history..."
              className="w-full py-2 pl-9 pr-4 bg-cyan-950/30 border border-cyan-500/30 focus:border-cyan-400 rounded-lg text-xs text-white placeholder-cyan-500/40 focus:outline-none transition shadow-[inset_0_0_10px_rgba(0,240,255,0.05)] font-mono"
            />
          </div>

          {/* Timeframe & Sort Controls */}
          <div className="flex items-center space-x-2 w-full md:w-auto justify-between md:justify-end overflow-x-auto pb-1 md:pb-0">
            {/* Time filters */}
            <div className="flex items-center space-x-1 bg-cyan-950/40 p-1 rounded-lg border border-cyan-500/15">
              {(["TODAY", "7 DAYS", "30 DAYS", "ALL TIME"] as TimeFilter[]).map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeFilter(tf)}
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

            {/* Sort order toggle */}
            <button
              onClick={() => setSortOrder(sortOrder === "NEWEST" ? "OLDEST" : "NEWEST")}
              className="px-3 py-1.5 rounded-lg text-[10px] font-mono text-cyan-300 border border-cyan-500/30 bg-cyan-950/30 hover:bg-cyan-500/10 transition whitespace-nowrap"
            >
              {sortOrder === "NEWEST" ? "↓ NEWEST" : "↑ OLDEST"}
            </button>
          </div>
        </div>

        {/* CATEGORY FILTER TABS */}
        <div className="flex items-center space-x-1 overflow-x-auto pb-1 scrollbar-none">
          {categories.map((cat) => {
            const isActive = selectedCategory === cat;
            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
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

        {/* TIMELINE & DETAIL PANEL GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* LEFT 7 COLS: TIMELINE ARCHIVE */}
          <div className="lg:col-span-7 space-y-3">
            {filteredRecords.length === 0 ? (
              <div className="p-8 text-center border border-cyan-500/10 rounded-xl font-mono text-xs text-cyan-500/50">
                NO MEMORY RECORDS MATCHING SPECIFIED SEARCH OR CATEGORY FILTERS.
              </div>
            ) : (
              filteredRecords.map((rec) => {
                const isSelected = rec.id === selectedRecord.id;
                return (
                  <div
                    key={rec.id}
                    onClick={() => setSelectedRecordId(rec.id)}
                    className={`relative rounded-xl p-4 transition-all duration-200 backdrop-blur-md border cursor-pointer ${
                      isSelected
                        ? "bg-cyan-950/40 border-cyan-400/50 shadow-[0_0_20px_rgba(0,240,255,0.15)]"
                        : "bg-[#020914]/70 border-cyan-500/15 hover:border-cyan-500/30 hover:bg-cyan-950/20"
                    }`}
                  >
                    {/* Left Selected Glowing Indicator Bar */}
                    <div
                      className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-xl ${
                        isSelected ? "bg-cyan-400 shadow-[0_0_8px_#00f0ff]" : "bg-transparent"
                      }`}
                    />

                    <div className="flex items-start justify-between gap-2 mb-1 pl-2">
                      <div className="flex items-center space-x-2">
                        <span className="px-2 py-0.5 text-[9px] font-mono font-bold rounded bg-cyan-950/80 text-cyan-300 border border-cyan-500/30">
                          {rec.category}
                        </span>
                        <span className="text-[10px] font-mono text-cyan-400/50">{rec.memoryId}</span>
                      </div>
                      <span className="text-[10px] font-mono text-cyan-400/50">{rec.timestamp}</span>
                    </div>

                    <div className="pl-2 space-y-1">
                      <h3 className="text-sm font-bold tracking-wide text-white">{rec.title}</h3>
                      <p className="text-xs text-cyan-200/80 font-sans leading-relaxed">{rec.description}</p>
                    </div>

                    <div className="mt-3 pt-2 border-t border-cyan-500/10 pl-2 flex items-center justify-between text-[10px] font-mono text-cyan-400/50">
                      <span>SOURCE: {rec.source}</span>
                      <span className="text-cyan-300">{rec.status}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* RIGHT 5 COLS: MEMORY DETAIL RECORD PANEL */}
          <div className="lg:col-span-5">
            <div className="sticky top-6 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md space-y-4 shadow-[0_0_25px_rgba(0,240,255,0.08)]">
              {/* Header */}
              <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                <div className="flex items-center space-x-2">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  <h3 className="text-xs font-mono font-bold text-white tracking-widest uppercase">MEMORY RECORD</h3>
                </div>
                <span className="text-[9px] font-mono text-cyan-400/60">{selectedRecord.memoryId}</span>
              </div>

              {/* Record Metadata Fields */}
              <div className="space-y-2 text-xs font-mono border-b border-cyan-500/15 pb-3">
                <div className="flex justify-between">
                  <span className="text-cyan-500/70">TYPE:</span>
                  <span className="text-cyan-200 font-bold">{selectedRecord.category}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-cyan-500/70">DATE & TIME:</span>
                  <span className="text-cyan-200">{selectedRecord.timestamp}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-cyan-500/70">SOURCE NODE:</span>
                  <span className="text-cyan-200">{selectedRecord.source}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-cyan-500/70">STATUS:</span>
                  <span className="text-emerald-400 font-bold">{selectedRecord.status}</span>
                </div>
              </div>

              {/* Record Context Preview */}
              <div className="space-y-2">
                <span className="text-[10px] font-mono tracking-wider text-cyan-400/70 uppercase">
                  STORED CONTEXT PREVIEW
                </span>
                <div className="p-3 rounded-lg border border-cyan-500/20 bg-cyan-950/30 text-xs font-mono text-cyan-100 leading-relaxed">
                  "{selectedRecord.contextPreview}"
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex items-center space-x-2">
                <button className="flex-1 py-2 rounded-lg text-xs font-mono font-bold text-black bg-cyan-400 hover:bg-cyan-300 transition shadow-[0_0_10px_rgba(0,240,255,0.2)]">
                  RESTORE CONTEXT
                </button>
                <button className="px-3 py-2 rounded-lg text-xs font-mono text-cyan-300 border border-cyan-500/30 hover:bg-cyan-500/10 transition">
                  EXPORT
                </button>
              </div>

              <div className="text-[9px] font-mono text-center text-cyan-500/50 pt-1">
                DEMO RECORD • NO BACKEND DATABASE CONNECTED
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
