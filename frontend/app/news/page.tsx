"use client";

import React, { useState } from "react";

// Types
type CategoryType =
  | "ALL"
  | "WORLD"
  | "BUSINESS"
  | "TECH"
  | "AI"
  | "CRYPTO"
  | "MARKETS"
  | "SCIENCE"
  | "SECURITY"
  | "TRENDING";

type RelevanceType = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

interface NewsItem {
  id: string;
  category: string;
  headline: string;
  summary: string;
  source: string;
  timestamp: string;
  relevance: RelevanceType;
  fullAnalysis: {
    summary: string;
    keyPoints: string[];
    context: string;
    relatedTopics: string[];
    aiInterpretation: string;
  };
}

export default function KingZarryNewsPage() {
  // State
  const [activeCategory, setActiveCategory] = useState<CategoryType>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [filterMode, setFilterMode] = useState<string>("LATEST");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [selectedStoryId, setSelectedStoryId] = useState<string>("story-1");

  // Information nodes for the Central AI News Core
  const newsNodes = [
    { label: "GLOBAL", status: "SYNCED" },
    { label: "MARKETS", status: "ACTIVE" },
    { label: "TECH", status: "OPTIMIZED" },
    { label: "AI", status: "PRIMARY" },
    { label: "CRYPTO", status: "MONITORING" },
    { label: "BUSINESS", status: "INDEXED" },
    { label: "SCIENCE", status: "SCANNING" },
    { label: "WORLD", status: "STREAMING" },
  ];

  // Trending Intelligence Nodes
  const trendingNodes = [
    "ARTIFICIAL INTELLIGENCE",
    "BITCOIN",
    "GLOBAL MARKETS",
    "TECHNOLOGY",
    "ENERGY",
    "CYBERSECURITY",
    "ECONOMY",
  ];

  // Demo News Stream Data
  const newsItems: NewsItem[] = [
    {
      id: "story-1",
      category: "AI",
      headline: "AI SYSTEMS CONTINUE TO TRANSFORM HOW INFORMATION IS ANALYZED",
      summary: "A demonstration intelligence summary showing how KING ZARRY AI could organize and interpret important information across decentralized channels.",
      source: "DEMO SOURCE",
      timestamp: "24 MIN AGO",
      relevance: "CRITICAL",
      fullAnalysis: {
        summary: "Advanced recursive neural networks process unstructured multi-stream feeds to extract deterministic semantic markers.",
        keyPoints: [
          "Cross-vector data aggregation active across 14 nodes.",
          "Noise filtration efficiency reached 99.4% in demo simulation.",
          "Contextual correlation maps established for immediate retrieval."
        ],
        context: "This information connects directly to automated decision frameworks, enterprise systems, and next-generation intelligence layers.",
        relatedTopics: ["AI", "TECH", "MARKETS", "BUSINESS"],
        aiInterpretation: "The intelligence core identifies this development as a structural shift in autonomous information processing."
      }
    },
    {
      id: "story-2",
      category: "MARKETS",
      headline: "GLOBAL MARKET CONDITIONS UNDER REVIEW",
      summary: "Demonstration intelligence item describing how market information, volatility metrics, and liquidity flows could be summarized in real time.",
      source: "DEMO SOURCE",
      timestamp: "1 HR AGO",
      relevance: "HIGH",
      fullAnalysis: {
        summary: "Liquidity distribution across major fiat and digital pairs demonstrates shifting correlation coefficients.",
        keyPoints: [
          "Volatility indices remain stable within expected baseline parameters.",
          "Institutional inflow patterns show accumulation phases.",
          "Cross-market arbitrage thresholds evaluated by autonomous agents."
        ],
        context: "Macroeconomic sentiment indicators reflect caution ahead of upcoming liquidity auctions.",
        relatedTopics: ["MARKETS", "BUSINESS", "ECONOMY"],
        aiInterpretation: "Price structure and volume vectors suggest a consolidation phase before secondary breakout validation."
      }
    },
    {
      id: "story-3",
      category: "TECHNOLOGY",
      headline: "EMERGING TECHNOLOGY TRENDS AND INFRASTRUCTURE SCALING",
      summary: "A demonstration news item representing technology intelligence, distributed edge computing, and hardware acceleration advancements.",
      source: "DEMO SOURCE",
      timestamp: "2 HR AGO",
      relevance: "MEDIUM",
      fullAnalysis: {
        summary: "Decentralized compute grids achieve lower latency benchmarks across secure optical channels.",
        keyPoints: [
          "Edge node synchronization improved by 14%.",
          "Encrypted protocol layers verified against adversarial interference.",
          "Hardware acceleration standards updated for neural processing."
        ],
        context: "Infrastructure scaling remains the primary bottleneck for real-time global intelligence pipelines.",
        relatedTopics: ["TECH", "SECURITY", "AI"],
        aiInterpretation: "System resilience scales linearly with distributed node participation rates."
      }
    },
    {
      id: "story-4",
      category: "WORLD",
      headline: "GLOBAL POLICY FRAMEWORKS FOR AUTONOMOUS SYSTEMS",
      summary: "Demonstration report regarding international coordination standards, ethical boundaries, and safety protocols for intelligent networks.",
      source: "DEMO SOURCE",
      timestamp: "3 HR AGO",
      relevance: "HIGH",
      fullAnalysis: {
        summary: "Multi-lateral governance panels release updated recommendations for autonomous software deployment.",
        keyPoints: [
          "Transparency requirements mandated for critical decision nodes.",
          "Cross-border data compliance frameworks aligned.",
          "Auditing mechanisms proposed for automated trading and analysis engines."
        ],
        context: "Regulatory alignment creates predictable operational parameters for advanced intelligence deployments.",
        relatedTopics: ["WORLD", "SECURITY", "BUSINESS"],
        aiInterpretation: "Structured compliance protocols enhance long-term system trustworthiness and integration stability."
      }
    },
    {
      id: "story-5",
      category: "CRYPTO",
      headline: "DECENTRALIZED SETTLEMENT LAYERS AND PROTOCOL UPGRADES",
      summary: "Demonstration intelligence item examining cryptographic security standards, consensus throughput, and ledger efficiency.",
      source: "DEMO SOURCE",
      timestamp: "4 HR AGO",
      relevance: "MEDIUM",
      fullAnalysis: {
        summary: "Zero-knowledge verification protocols reduce transaction overhead while preserving cryptographic privacy.",
        keyPoints: [
          "Consensus finality times decreased across testnet environments.",
          "Smart contract verification models audited by automated fuzzers.",
          "Interoperability bridges secured via multi-sig telemetry."
        ],
        context: "Protocol upgrades reflect continuous maturation of decentralized settlement infrastructure.",
        relatedTopics: ["CRYPTO", "TECH", "SECURITY"],
        aiInterpretation: "Cryptographic verification layers provide tamper-proof state records for high-value operations."
      }
    }
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

  const categories: CategoryType[] = [
    "ALL",
    "WORLD",
    "BUSINESS",
    "TECH",
    "AI",
    "CRYPTO",
    "MARKETS",
    "SCIENCE",
    "SECURITY",
    "TRENDING",
  ];

  const filteredNews = newsItems.filter((item) => {
    if (activeCategory !== "ALL" && item.category !== activeCategory) {
      return false;
    }
    if (searchQuery.trim() !== "") {
      const q = searchQuery.toLowerCase();
      return (
        item.headline.toLowerCase().includes(q) ||
        item.summary.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const selectedStory = newsItems.find((s) => s.id === selectedStoryId) || newsItems[0];

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
                INTELLIGENCE NEWS
              </span>
            </div>
            <div className="flex items-center space-x-2 text-[10px] font-mono text-cyan-400/70">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span>INTELLIGENCE FEED ONLINE</span>
              <span className="text-cyan-700">•</span>
              <span>SYNCHRONIZED</span>
            </div>
          </div>
        </div>

        {/* Navigation - Desktop */}
        <nav className="hidden lg:flex items-center space-x-1 bg-cyan-950/20 p-1 rounded-lg border border-cyan-500/10">
          {navItems.map((item) => {
            const isActive = item === "NEWS";
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
                  item === "NEWS"
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
              <span>INTELLIGENCE NEWS</span>
            </h2>
            <p className="text-xs font-mono text-cyan-400/60 mt-1">
              Information filtered, organized and interpreted by your AI system.
            </p>
          </div>

          {/* AI NEWS BRIEF PANEL */}
          <div className="p-3 rounded-lg border border-cyan-500/20 bg-cyan-950/20 backdrop-blur-md max-w-md">
            <div className="flex items-center justify-between text-[10px] font-mono text-cyan-400/80 mb-1">
              <span className="font-bold tracking-wider">AI NEWS BRIEF</span>
              <span className="text-cyan-400">NEWS INTELLIGENCE: DEMO</span>
            </div>
            <p className="text-xs text-cyan-200">
              "Several information streams are being organized into broader themes. Select a story to explore its context and relationships."
            </p>
          </div>
        </div>

        {/* CENTRAL AI NEWS CORE HUD */}
        <div className="relative rounded-2xl border border-cyan-500/20 bg-[#020914]/80 p-6 backdrop-blur-md overflow-hidden flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff08_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff08_1px,transparent_1px)] bg-[size:16px_16px]" />

          {/* Central Core Display */}
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
              <span className="text-xs font-mono font-bold tracking-widest text-cyan-200 uppercase">NEWS INTELLIGENCE CORE</span>
              <div className="text-[9px] font-mono text-cyan-500/70">RAW INFORMATION → AI → UNDERSTANDING</div>
            </div>
          </div>

          {/* Information Nodes */}
          <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 gap-3 w-full md:w-2/3">
            {newsNodes.map((node) => (
              <div key={node.label} className="p-3 rounded-xl border border-cyan-500/15 bg-cyan-950/20 flex items-center justify-between">
                <div>
                  <span className="text-xs font-mono font-bold text-white block">{node.label}</span>
                  <span className="text-[8px] font-mono text-cyan-400/60 block">STREAM ONLINE</span>
                </div>
                <span className="px-1.5 py-0.5 text-[9px] font-mono rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  {node.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* SEARCH & FILTER CONTROLS */}
        <div className="flex flex-col lg:flex-row items-center justify-between gap-4 p-4 rounded-xl border border-cyan-500/20 bg-[#020914]/80 backdrop-blur-md">
          {/* Search Box */}
          <div className="relative w-full lg:w-80">
            <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-cyan-400/60">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </span>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search intelligence..."
              className="w-full pl-9 pr-4 py-2 rounded-lg bg-cyan-950/30 border border-cyan-500/30 text-xs font-mono text-cyan-100 placeholder-cyan-500/50 focus:outline-none focus:border-cyan-400 focus:shadow-[0_0_10px_rgba(0,240,255,0.2)] transition"
            />
          </div>

          {/* Filter Bar */}
          <div className="flex items-center space-x-1 overflow-x-auto w-full lg:w-auto pb-1 lg:pb-0">
            {["LATEST", "MOST RELEVANT", "MARKETS", "AI", "TECH", "WORLD", "BUSINESS"].map((f) => (
              <button
                key={f}
                onClick={() => setFilterMode(f)}
                className={`px-3 py-1.5 text-xs font-mono rounded transition whitespace-nowrap ${
                  filterMode === f
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    : "text-cyan-400/60 hover:text-cyan-200 hover:bg-cyan-500/10"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* CATEGORY CHANNELS */}
        <div className="flex items-center space-x-2 overflow-x-auto pb-2 border-b border-cyan-500/10">
          {categories.map((cat) => {
            const isActive = activeCategory === cat;
            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-3 py-1.5 text-xs font-mono tracking-wider transition whitespace-nowrap rounded-lg border ${
                  isActive
                    ? "bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-[0_0_12px_rgba(0,240,255,0.25)]"
                    : "bg-cyan-950/20 text-cyan-400/70 border-cyan-500/15 hover:bg-cyan-500/10 hover:text-cyan-200"
                }`}
              >
                {cat}
              </button>
            );
          })}
        </div>

        {/* FEATURED INTELLIGENCE & AI SUMMARY HERO */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* FEATURED INTELLIGENCE (8 cols) */}
          <div className="lg:col-span-8 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md space-y-4 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-48 h-48 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">FEATURED INTELLIGENCE</h3>
              </div>
              <span className="px-2 py-0.5 text-[9px] font-mono rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                DEMO ARTICLE
              </span>
            </div>

            <div className="space-y-3">
              <span className="text-[10px] font-mono text-cyan-400/70 tracking-wider block">AI • DEMO SOURCE • 12 MIN AGO</span>
              <h2 className="text-lg md:text-xl font-bold font-mono text-white tracking-wide">
                AI SYSTEMS CONTINUE TO TRANSFORM HOW INFORMATION IS ANALYZED
              </h2>
              <p className="text-xs text-cyan-200/80 leading-relaxed font-sans">
                A demonstration intelligence summary showing how KING ZARRY AI could organize and interpret important information across decentralized streams, filtering background noise and synthesizing actionable context in real time.
              </p>
            </div>

            <div className="pt-2 flex items-center justify-between text-xs font-mono border-t border-cyan-500/10">
              <span className="text-cyan-400/60">RELEVANCE: <strong className="text-cyan-300">CRITICAL</strong></span>
              <button 
                onClick={() => setSelectedStoryId("story-1")}
                className="px-3 py-1 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/30 transition"
              >
                EXPLORE CONTEXT →
              </button>
            </div>
          </div>

          {/* AI SUMMARY PANEL (4 cols) */}
          <div className="lg:col-span-4 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md space-y-4">
            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">AI SUMMARY</h3>
              <span className="text-[9px] font-mono text-cyan-400/60">SYNTHESIS</span>
            </div>

            <p className="text-xs text-cyan-200 leading-relaxed">
              KING ZARRY AI identifies the major themes, separates important information from background noise and provides context around the selected story.
            </p>

            <div className="space-y-2 pt-2 text-xs font-mono">
              <div className="flex justify-between py-1 border-b border-cyan-500/10">
                <span className="text-cyan-500/70">RELEVANCE</span>
                <span className="text-cyan-300">HIGH</span>
              </div>
              <div className="flex justify-between py-1 border-b border-cyan-500/10">
                <span className="text-cyan-500/70">CONTEXT</span>
                <span className="text-emerald-400">VERIFIED</span>
              </div>
              <div className="flex justify-between py-1 border-b border-cyan-500/10">
                <span className="text-cyan-500/70">IMPACT</span>
                <span className="text-cyan-200">STRATEGIC</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-cyan-500/70">SENTIMENT</span>
                <span className="text-cyan-300">NEUTRAL / BULLISH</span>
              </div>
            </div>
          </div>
        </div>

        {/* MAIN FEED & AI CONTEXT / STORY ANALYSIS GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* LEFT 7 COLS: INTELLIGENCE FEED STREAM */}
          <div className="lg:col-span-7 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md space-y-4">
            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
              <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">INTELLIGENCE FEED</h3>
              <span className="text-[9px] font-mono text-cyan-400/60">{filteredNews.length} ITEMS STREAMING</span>
            </div>

            <div className="space-y-3">
              {filteredNews.map((item) => {
                const isSelected = item.id === selectedStoryId;
                return (
                  <div
                    key={item.id}
                    onClick={() => setSelectedStoryId(item.id)}
                    className={`p-4 rounded-xl border transition-all duration-200 cursor-pointer ${
                      isSelected
                        ? "bg-cyan-950/40 border-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.2)]"
                        : "bg-cyan-950/20 border-cyan-500/15 hover:border-cyan-500/30 hover:bg-cyan-950/30"
                    }`}
                  >
                    <div className="flex items-center justify-between text-[10px] font-mono mb-1.5">
                      <div className="flex items-center space-x-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                        <span className="text-cyan-300 font-bold">{item.category}</span>
                        <span className="text-cyan-700">•</span>
                        <span className="text-cyan-400/60">{item.source}</span>
                      </div>
                      <span className="px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                        {item.relevance}
                      </span>
                    </div>

                    <h4 className="text-sm font-bold font-mono text-white mb-1.5">{item.headline}</h4>
                    <p className="text-xs text-cyan-200/70 line-clamp-2 mb-2">{item.summary}</p>

                    <div className="flex items-center justify-between text-[9px] font-mono text-cyan-500/60 pt-2 border-t border-cyan-500/10">
                      <span>{item.timestamp}</span>
                      <span className="text-cyan-300">DEMO ARTICLE</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* RIGHT 5 COLS: AI CONTEXT & STORY ANALYSIS PANEL */}
          <div className="lg:col-span-5 space-y-6">
            {/* AI CONTEXT PANEL */}
            <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md space-y-4">
              <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">AI CONTEXT</h3>
                <span className="text-[9px] font-mono text-cyan-400/60">RELATIONAL MAPPING</span>
              </div>

              <div className="space-y-3 text-xs font-mono">
                <div>
                  <span className="text-[10px] text-cyan-400/60 font-bold block mb-1">WHY IT MATTERS</span>
                  <p className="text-cyan-200 leading-relaxed font-sans text-xs">
                    {selectedStory.fullAnalysis.context}
                  </p>
                </div>

                <div className="pt-2 border-t border-cyan-500/10">
                  <span className="text-[10px] text-cyan-400/60 font-bold block mb-1.5">RELATED TOPICS</span>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedStory.fullAnalysis.relatedTopics.map((topic) => (
                      <span
                        key={topic}
                        className="px-2 py-0.5 text-[9px] font-mono rounded bg-cyan-950/60 text-cyan-300 border border-cyan-500/30"
                      >
                        {topic}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="pt-2 border-t border-cyan-500/10">
                  <span className="text-[10px] text-cyan-400/60 font-bold block mb-1">AI INTERPRETATION</span>
                  <p className="text-cyan-300 italic text-[11px]">
                    "{selectedStory.fullAnalysis.aiInterpretation}"
                  </p>
                </div>
              </div>
            </div>

            {/* STORY ANALYSIS & KEY POINTS */}
            <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md space-y-3">
              <div className="flex items-center justify-between border-b border-cyan-500/15 pb-2">
                <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">STORY ANALYSIS</h3>
                <span className="text-[9px] font-mono text-cyan-400/60">KEY POINTS</span>
              </div>

              <ul className="space-y-2 text-xs text-cyan-200">
                {selectedStory.fullAnalysis.keyPoints.map((pt, idx) => (
                  <li key={idx} className="flex items-start space-x-2 font-mono">
                    <span className="text-cyan-400 mt-0.5">▸</span>
                    <span>{pt}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* TRENDING INTELLIGENCE NODES */}
        <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md space-y-4">
          <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
            <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">TRENDING INTELLIGENCE</h3>
            <span className="text-[9px] font-mono text-cyan-400/60">ACTIVE NODES</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            {trendingNodes.map((node) => (
              <div
                key={node}
                className="p-3 rounded-xl border border-cyan-500/20 bg-cyan-950/20 text-center flex flex-col justify-center items-center hover:bg-cyan-500/15 transition cursor-pointer"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mb-1.5 animate-pulse" />
                <span className="text-[10px] font-mono font-bold text-cyan-100 tracking-wider">{node}</span>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
