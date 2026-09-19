"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";

// ============================================================
// TYPES
// ============================================================

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

type FilterMode =
  | "LATEST"
  | "MOST RELEVANT"
  | "MARKETS"
  | "AI"
  | "TECH"
  | "WORLD"
  | "BUSINESS";

interface NewsItem {
  id: string;
  category: CategoryType;
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

// ============================================================
// DEMO NEWS DATA
// ============================================================
// This is intentionally labelled DEMO.
// Connect the Railway news endpoint here when the live
// intelligence feed is implemented.
// ============================================================

const newsItems: NewsItem[] = [
  {
    id: "story-1",
    category: "AI",
    headline:
      "AI SYSTEMS CONTINUE TO TRANSFORM HOW INFORMATION IS ANALYZED",
    summary:
      "A demonstration intelligence summary showing how KING ZARRY AI could organize and interpret information across multiple information streams.",
    source: "DEMO SOURCE",
    timestamp: "24 MIN AGO",
    relevance: "CRITICAL",
    fullAnalysis: {
      summary:
        "This demonstration shows how an AI system could combine multiple information streams and organize them into structured intelligence.",
      keyPoints: [
        "Cross-source information aggregation.",
        "Automated filtering of irrelevant information.",
        "Contextual relationships between information streams.",
      ],
      context:
        "The concept connects AI-assisted research, automated monitoring and information organization.",
      relatedTopics: ["AI", "TECH", "MARKETS", "BUSINESS"],
      aiInterpretation:
        "The intelligence layer could help transform large volumes of information into structured context for further analysis.",
    },
  },

  {
    id: "story-2",
    category: "MARKETS",
    headline: "GLOBAL MARKET CONDITIONS UNDER REVIEW",
    summary:
      "Demonstration intelligence describing how market information, volatility metrics and liquidity data could be organized.",
    source: "DEMO SOURCE",
    timestamp: "1 HR AGO",
    relevance: "HIGH",
    fullAnalysis: {
      summary:
        "A demonstration of how market information could be grouped around price structure, volatility and liquidity conditions.",
      keyPoints: [
        "Market structure can be monitored across multiple instruments.",
        "Volatility can be incorporated into market context.",
        "Liquidity information can provide additional analytical context.",
      ],
      context:
        "Market intelligence becomes more useful when price information is combined with broader economic and liquidity context.",
      relatedTopics: ["MARKETS", "BUSINESS", "ECONOMY"],
      aiInterpretation:
        "A connected market intelligence layer could combine multiple market variables before presenting an analytical summary.",
    },
  },

  {
    id: "story-3",
    category: "TECH",
    headline:
      "EMERGING TECHNOLOGY TRENDS AND INFRASTRUCTURE SCALING",
    summary:
      "Demonstration technology intelligence covering distributed infrastructure, computing and hardware acceleration.",
    source: "DEMO SOURCE",
    timestamp: "2 HR AGO",
    relevance: "MEDIUM",
    fullAnalysis: {
      summary:
        "A demonstration story showing how technology developments could be grouped around computing infrastructure and system performance.",
      keyPoints: [
        "Distributed infrastructure can increase system capacity.",
        "Hardware acceleration can improve AI workloads.",
        "Infrastructure remains important for large-scale AI systems.",
      ],
      context:
        "Technology infrastructure is a major component of modern AI and information systems.",
      relatedTopics: ["TECH", "SECURITY", "AI"],
      aiInterpretation:
        "Technology infrastructure determines how efficiently advanced information systems can process increasing workloads.",
    },
  },

  {
    id: "story-4",
    category: "WORLD",
    headline: "GLOBAL POLICY FRAMEWORKS FOR AUTONOMOUS SYSTEMS",
    summary:
      "Demonstration report covering international coordination, safety frameworks and governance considerations.",
    source: "DEMO SOURCE",
    timestamp: "3 HR AGO",
    relevance: "HIGH",
    fullAnalysis: {
      summary:
        "A demonstration of how policy developments surrounding autonomous systems could be organized and analyzed.",
      keyPoints: [
        "Governance frameworks can influence technology deployment.",
        "Transparency requirements may affect automated systems.",
        "Cross-border technology rules can create operational requirements.",
      ],
      context:
        "Policy and regulation can influence how AI and autonomous technologies are developed and deployed.",
      relatedTopics: ["WORLD", "SECURITY", "BUSINESS"],
      aiInterpretation:
        "Policy developments should be interpreted alongside the technical and commercial environment surrounding autonomous systems.",
    },
  },

  {
    id: "story-5",
    category: "CRYPTO",
    headline:
      "DECENTRALIZED SETTLEMENT LAYERS AND PROTOCOL UPGRADES",
    summary:
      "Demonstration intelligence examining blockchain infrastructure, cryptographic verification and protocol development.",
    source: "DEMO SOURCE",
    timestamp: "4 HR AGO",
    relevance: "MEDIUM",
    fullAnalysis: {
      summary:
        "A demonstration of how blockchain infrastructure developments could be organized into structured intelligence.",
      keyPoints: [
        "Protocol upgrades can affect network functionality.",
        "Cryptographic verification supports transaction integrity.",
        "Interoperability remains an important blockchain infrastructure issue.",
      ],
      context:
        "Blockchain development combines cryptography, distributed systems and economic incentives.",
      relatedTopics: ["CRYPTO", "TECH", "SECURITY"],
      aiInterpretation:
        "Blockchain intelligence benefits from separating protocol developments from market speculation and broader narratives.",
    },
  },

  {
    id: "story-6",
    category: "SECURITY",
    headline:
      "CYBERSECURITY AND DIGITAL INFRASTRUCTURE MONITORING",
    summary:
      "Demonstration security intelligence covering digital infrastructure, defensive systems and emerging cyber risks.",
    source: "DEMO SOURCE",
    timestamp: "5 HR AGO",
    relevance: "HIGH",
    fullAnalysis: {
      summary:
        "A demonstration of how cybersecurity information could be grouped into infrastructure, threat and defensive categories.",
      keyPoints: [
        "Security monitoring can combine multiple information sources.",
        "Infrastructure protection requires continuous observation.",
        "Threat intelligence benefits from contextual analysis.",
      ],
      context:
        "Cybersecurity information changes rapidly and requires reliable sources before conclusions are drawn.",
      relatedTopics: ["SECURITY", "TECH", "AI"],
      aiInterpretation:
        "A security intelligence layer should distinguish verified events from unconfirmed reports before producing conclusions.",
    },
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

const filterModes: FilterMode[] = [
  "LATEST",
  "MOST RELEVANT",
  "MARKETS",
  "AI",
  "TECH",
  "WORLD",
  "BUSINESS",
];

// ============================================================
// NEWS PAGE
// ============================================================

export default function KingZarryNewsPage() {
  const [activeCategory, setActiveCategory] =
    useState<CategoryType>("ALL");

  const [searchQuery, setSearchQuery] =
    useState("");

  const [filterMode, setFilterMode] =
    useState<FilterMode>("LATEST");

  const [mobileMenuOpen, setMobileMenuOpen] =
    useState(false);

  const [selectedStoryId, setSelectedStoryId] =
    useState("story-1");

  const [showDemoNotice, setShowDemoNotice] =
    useState(false);

  // ==========================================================
  // INFORMATION NODES
  // ==========================================================

  const newsNodes = [
    { label: "GLOBAL", status: "READY" },
    { label: "MARKETS", status: "READY" },
    { label: "TECH", status: "READY" },
    { label: "AI", status: "READY" },
    { label: "CRYPTO", status: "READY" },
    { label: "BUSINESS", status: "READY" },
    { label: "SCIENCE", status: "READY" },
    { label: "WORLD", status: "READY" },
  ];

  // ==========================================================
  // TRENDING
  // ==========================================================

  const trendingNodes = [
    "ARTIFICIAL INTELLIGENCE",
    "BITCOIN",
    "GLOBAL MARKETS",
    "TECHNOLOGY",
    "ENERGY",
    "CYBERSECURITY",
    "ECONOMY",
  ];

  // ==========================================================
  // FILTERED NEWS
  // ==========================================================

  const filteredNews = useMemo(() => {
    let results = [...newsItems];

    // Category filter

    if (activeCategory !== "ALL") {
      if (activeCategory === "TRENDING") {
        const trendingCategories: CategoryType[] = [
          "AI",
          "CRYPTO",
          "MARKETS",
          "TECH",
        ];

        results = results.filter((item) =>
          trendingCategories.includes(item.category)
        );
      } else {
        results = results.filter(
          (item) => item.category === activeCategory
        );
      }
    }

    // Search

    const query = searchQuery.trim().toLowerCase();

    if (query) {
      results = results.filter((item) => {
        return (
          item.headline.toLowerCase().includes(query) ||
          item.summary.toLowerCase().includes(query) ||
          item.category.toLowerCase().includes(query) ||
          item.source.toLowerCase().includes(query) ||
          item.fullAnalysis.context
            .toLowerCase()
            .includes(query) ||
          item.fullAnalysis.relatedTopics.some((topic) =>
            topic.toLowerCase().includes(query)
          )
        );
      });
    }

    // Filter mode

    if (filterMode === "MOST RELEVANT") {
      const relevanceWeight: Record<
        RelevanceType,
        number
      > = {
        CRITICAL: 4,
        HIGH: 3,
        MEDIUM: 2,
        LOW: 1,
      };

      results.sort(
        (a, b) =>
          relevanceWeight[b.relevance] -
          relevanceWeight[a.relevance]
      );
    }

    if (filterMode !== "LATEST" && filterMode !== "MOST RELEVANT") {
      results = results.filter(
        (item) => item.category === filterMode
      );
    }

    return results;
  }, [
    activeCategory,
    searchQuery,
    filterMode,
  ]);

  // ==========================================================
  // SELECTED STORY
  // ==========================================================

  const selectedStory =
    newsItems.find(
      (story) => story.id === selectedStoryId
    ) ?? newsItems[0];

  // ==========================================================
  // DEMO NOTICE
  // ==========================================================

  const handleDemoAction = () => {
    setShowDemoNotice(true);

    window.setTimeout(() => {
      setShowDemoNotice(false);
    }, 3500);
  };

  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div className="relative flex min-h-screen w-full flex-col overflow-x-hidden bg-[#03060a] font-sans text-cyan-100 selection:bg-cyan-500 selection:text-black">

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
                INTELLIGENCE NEWS
              </span>
            </div>

            <div className="mt-0.5 flex items-center gap-2 font-mono text-[9px] text-cyan-400/70 md:text-[10px]">

              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />

              <span>
                NEWS INTELLIGENCE READY
              </span>

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

            const active =
              item.href === "/news";

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded px-3 py-1.5 font-mono text-xs tracking-wider transition ${
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

        {/* Mobile navigation */}

        <button
          type="button"
          onClick={() =>
            setMobileMenuOpen(
              (open) => !open
            )
          }
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
          MOBILE NAV DRAWER
      ====================================================== */}

      {mobileMenuOpen && (
        <div className="relative z-30 border-b border-cyan-500/30 bg-[#040c16]/95 p-4 backdrop-blur-xl lg:hidden">

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">

            {navItems.map((item) => {

              const active =
                item.href === "/news";

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() =>
                    setMobileMenuOpen(false)
                  }
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

            <span className="text-yellow-300">
              ⚠
            </span>

            <div>

              <div className="font-mono text-xs font-bold tracking-wider text-yellow-300">
                DEMO FUNCTION
              </div>

              <p className="mt-1 font-mono text-[10px] leading-relaxed text-yellow-100/70">
                Live news ingestion will be enabled when the
                intelligence feed is connected to the backend.
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

            <div className="flex flex-wrap items-center gap-3">

              <h2 className="text-xl font-bold uppercase tracking-widest text-white md:text-2xl">
                INTELLIGENCE NEWS
              </h2>

              <span className="rounded border border-yellow-500/30 bg-yellow-500/10 px-2 py-1 font-mono text-[8px] text-yellow-300">
                DEMO DATA
              </span>
            </div>

            <p className="mt-1 font-mono text-xs text-cyan-400/60">
              Organize, search and interpret information through KING ZARRY AI.
            </p>
          </div>

          {/* AI brief */}

          <div className="max-w-md rounded-lg border border-cyan-500/20 bg-cyan-950/20 p-3 backdrop-blur-md">

            <div className="mb-1 flex items-center justify-between font-mono text-[10px] text-cyan-400/80">

              <span className="font-bold tracking-wider">
                AI NEWS BRIEF
              </span>

              <span className="text-yellow-300">
                PREVIEW
              </span>
            </div>

            <p className="text-xs leading-relaxed text-cyan-200/80">
              Select a story to inspect its context, key points,
              related topics and AI interpretation.
            </p>
          </div>
        </div>

        {/* ====================================================
            NEWS CORE
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
                NEWS INTELLIGENCE CORE
              </span>

              <div className="font-mono text-[9px] text-cyan-500/70">
                INFORMATION → AI → CONTEXT → UNDERSTANDING
              </div>
            </div>
          </div>

          {/* Nodes */}

          <div className="relative z-10 grid w-full grid-cols-2 gap-3 sm:grid-cols-4 md:w-2/3">

            {newsNodes.map((node) => (

              <div
                key={node.label}
                className="flex items-center justify-between rounded-xl border border-cyan-500/15 bg-cyan-950/20 p-3"
              >

                <div>

                  <span className="block font-mono text-xs font-bold text-white">
                    {node.label}
                  </span>

                  <span className="block font-mono text-[8px] text-cyan-400/60">
                    MODULE READY
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
            SEARCH + FILTER
        ==================================================== */}

        <section className="flex flex-col items-center justify-between gap-4 rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-4 backdrop-blur-md lg:flex-row">

          {/* Search */}

          <div className="relative w-full lg:w-96">

            <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-cyan-400/60">

              <svg
                className="h-4 w-4"
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
            </span>

            <input
              type="text"
              value={searchQuery}
              onChange={(event) =>
                setSearchQuery(event.target.value)
              }
              placeholder="Search intelligence..."
              className="w-full rounded-lg border border-cyan-500/30 bg-cyan-950/30 py-2 pl-9 pr-4 font-mono text-xs text-cyan-100 placeholder-cyan-500/50 transition focus:border-cyan-400 focus:outline-none focus:shadow-[0_0_10px_rgba(0,240,255,0.2)]"
            />
          </div>

          {/* Filter modes */}

          <div className="flex w-full items-center space-x-1 overflow-x-auto pb-1 lg:w-auto lg:pb-0">

            {filterModes.map((mode) => (

              <button
                key={mode}
                type="button"
                onClick={() =>
                  setFilterMode(mode)
                }
                className={`whitespace-nowrap rounded px-3 py-1.5 font-mono text-xs transition ${
                  filterMode === mode
                    ? "border border-cyan-500/40 bg-cyan-500/20 text-cyan-300"
                    : "text-cyan-400/60 hover:bg-cyan-500/10 hover:text-cyan-200"
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
        </section>

        {/* ====================================================
            CATEGORY CHANNELS
        ==================================================== */}

        <div className="flex items-center gap-2 overflow-x-auto border-b border-cyan-500/10 pb-2">

          {categories.map((category) => {

            const active =
              activeCategory === category;

            return (
              <button
                key={category}
                type="button"
                onClick={() =>
                  setActiveCategory(category)
                }
                className={`whitespace-nowrap rounded-lg border px-3 py-1.5 font-mono text-xs tracking-wider transition ${
                  active
                    ? "border-cyan-400 bg-cyan-500/20 text-cyan-300 shadow-[0_0_12px_rgba(0,240,255,0.25)]"
                    : "border-cyan-500/15 bg-cyan-950/20 text-cyan-400/70 hover:bg-cyan-500/10 hover:text-cyan-200"
                }`}
              >
                {category}
              </button>
            );
          })}
        </div>

        {/* ====================================================
            FEATURED STORY + SUMMARY
        ==================================================== */}

        <section className="grid grid-cols-1 gap-6 lg:grid-cols-12">

          {/* Featured */}

          <div className="relative space-y-4 overflow-hidden rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md lg:col-span-8">

            <div className="pointer-events-none absolute right-0 top-0 h-48 w-48 rounded-full bg-cyan-500/5 blur-3xl" />

            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">

              <div className="flex items-center gap-2">

                <span className="h-2 w-2 animate-ping rounded-full bg-cyan-400" />

                <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
                  FEATURED INTELLIGENCE
                </h3>
              </div>

              <span className="rounded border border-yellow-500/30 bg-yellow-500/10 px-2 py-0.5 font-mono text-[9px] text-yellow-300">
                DEMO ARTICLE
              </span>
            </div>

            <div className="space-y-3">

              <span className="block font-mono text-[10px] tracking-wider text-cyan-400/70">
                {selectedStory.category} • {selectedStory.source} •{" "}
                {selectedStory.timestamp}
              </span>

              <h2 className="font-mono text-lg font-bold tracking-wide text-white md:text-xl">
                {selectedStory.headline}
              </h2>

              <p className="font-sans text-xs leading-relaxed text-cyan-200/80">
                {selectedStory.summary}
              </p>
            </div>

            <div className="flex items-center justify-between border-t border-cyan-500/10 pt-2 font-mono text-xs">

              <span className="text-cyan-400/60">
                RELEVANCE:{" "}
                <strong className="text-cyan-300">
                  {selectedStory.relevance}
                </strong>
              </span>

              <button
                type="button"
                onClick={() =>
                  setSelectedStoryId(
                    selectedStory.id
                  )
                }
                className="rounded border border-cyan-500/40 bg-cyan-500/20 px-3 py-1 text-cyan-300 transition hover:bg-cyan-500/30"
              >
                CONTEXT ACTIVE →
              </button>
            </div>
          </div>

          {/* AI Summary */}

          <div className="space-y-4 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md lg:col-span-4">

            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">

              <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
                AI SUMMARY
              </h3>

              <span className="font-mono text-[9px] text-yellow-300">
                PREVIEW
              </span>
            </div>

            <p className="text-xs leading-relaxed text-cyan-200">
              {selectedStory.fullAnalysis.summary}
            </p>

            <div className="space-y-2 pt-2 font-mono text-xs">

              <div className="flex justify-between border-b border-cyan-500/10 py-1">

                <span className="text-cyan-500/70">
                  RELEVANCE
                </span>

                <span className="text-cyan-300">
                  {selectedStory.relevance}
                </span>
              </div>

              <div className="flex justify-between border-b border-cyan-500/10 py-1">

                <span className="text-cyan-500/70">
                  SOURCE
                </span>

                <span className="text-yellow-300">
                  DEMO
                </span>
              </div>

              <div className="flex justify-between border-b border-cyan-500/10 py-1">

                <span className="text-cyan-500/70">
                  CONTEXT
                </span>

                <span className="text-cyan-200">
                  AVAILABLE
                </span>
              </div>

              <div className="flex justify-between py-1">

                <span className="text-cyan-500/70">
                  LIVE FEED
                </span>

                <span className="text-yellow-300">
                  OFFLINE
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* ====================================================
            FEED + CONTEXT
        ==================================================== */}

        <section className="grid grid-cols-1 gap-6 lg:grid-cols-12">

          {/* Feed */}

          <div className="space-y-4 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md lg:col-span-7">

            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">

              <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
                INTELLIGENCE FEED
              </h3>

              <span className="font-mono text-[9px] text-cyan-400/60">
                {filteredNews.length} RESULTS
              </span>
            </div>

            {filteredNews.length === 0 ? (

              <div className="rounded-xl border border-cyan-500/15 bg-cyan-950/20 p-8 text-center">

                <div className="font-mono text-sm font-bold text-cyan-300">
                  NO INTELLIGENCE FOUND
                </div>

                <p className="mt-2 font-mono text-[10px] text-cyan-500/60">
                  Try another search term or category.
                </p>

                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery("");
                    setActiveCategory("ALL");
                    setFilterMode("LATEST");
                  }}
                  className="mt-4 rounded border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 font-mono text-[10px] text-cyan-300 hover:bg-cyan-500/20"
                >
                  RESET FILTERS
                </button>
              </div>
            ) : (

              <div className="space-y-3">

                {filteredNews.map((item) => {

                  const selected =
                    item.id === selectedStoryId;

                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() =>
                        setSelectedStoryId(
                          item.id
                        )
                      }
                      className={`w-full rounded-xl border p-4 text-left transition-all duration-200 ${
                        selected
                          ? "border-cyan-400 bg-cyan-950/40 shadow-[0_0_15px_rgba(0,240,255,0.2)]"
                          : "border-cyan-500/15 bg-cyan-950/20 hover:border-cyan-500/30 hover:bg-cyan-950/30"
                      }`}
                    >

                      <div className="mb-1.5 flex items-center justify-between gap-3 font-mono text-[10px]">

                        <div className="flex min-w-0 items-center gap-2">

                          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-400" />

                          <span className="font-bold text-cyan-300">
                            {item.category}
                          </span>

                          <span className="text-cyan-700">
                            •
                          </span>

                          <span className="truncate text-cyan-400/60">
                            {item.source}
                          </span>
                        </div>

                        <span className="shrink-0 rounded border border-cyan-500/20 bg-cyan-500/10 px-1.5 py-0.5 text-cyan-300">
                          {item.relevance}
                        </span>
                      </div>

                      <h4 className="mb-1.5 font-mono text-sm font-bold text-white">
                        {item.headline}
                      </h4>

                      <p className="mb-2 line-clamp-2 text-xs text-cyan-200/70">
                        {item.summary}
                      </p>

                      <div className="flex items-center justify-between border-t border-cyan-500/10 pt-2 font-mono text-[9px] text-cyan-500/60">

                        <span>
                          {item.timestamp}
                        </span>

                        <span className="text-yellow-300">
                          DEMO
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Context */}

          <div className="space-y-6 lg:col-span-5">

            {/* AI context */}

            <div className="space-y-4 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md">

              <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">

                <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
                  AI CONTEXT
                </h3>

                <span className="font-mono text-[9px] text-cyan-400/60">
                  RELATIONAL MAPPING
                </span>
              </div>

              <div className="space-y-3 font-mono text-xs">

                <div>

                  <span className="mb-1 block font-mono text-[10px] font-bold text-cyan-400/60">
                    WHY IT MATTERS
                  </span>

                  <p className="font-sans text-xs leading-relaxed text-cyan-200">
                    {selectedStory.fullAnalysis.context}
                  </p>
                </div>

                <div className="border-t border-cyan-500/10 pt-2">

                  <span className="mb-1.5 block font-mono text-[10px] font-bold text-cyan-400/60">
                    RELATED TOPICS
                  </span>

                  <div className="flex flex-wrap gap-1.5">

                    {selectedStory.fullAnalysis.relatedTopics.map(
                      (topic) => (
                        <button
                          key={topic}
                          type="button"
                          onClick={() => {
                            if (
                              categories.includes(
                                topic as CategoryType
                              )
                            ) {
                              setActiveCategory(
                                topic as CategoryType
                              );
                            }
                          }}
                          className="rounded border border-cyan-500/30 bg-cyan-950/60 px-2 py-0.5 font-mono text-[9px] text-cyan-300 transition hover:bg-cyan-500/20"
                        >
                          {topic}
                        </button>
                      )
                    )}
                  </div>
                </div>

                <div className="border-t border-cyan-500/10 pt-2">

                  <span className="mb-1 block font-mono text-[10px] font-bold text-cyan-400/60">
                    AI INTERPRETATION
                  </span>

                  <p className="text-[11px] italic text-cyan-300">
                    "{selectedStory.fullAnalysis.aiInterpretation}"
                  </p>
                </div>
              </div>
            </div>

            {/* Key points */}

            <div className="space-y-3 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md">

              <div className="flex items-center justify-between border-b border-cyan-500/15 pb-2">

                <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
                  STORY ANALYSIS
                </h3>

                <span className="font-mono text-[9px] text-cyan-400/60">
                  KEY POINTS
                </span>
              </div>

              <ul className="space-y-2 text-xs text-cyan-200">

                {selectedStory.fullAnalysis.keyPoints.map(
                  (point, index) => (
                    <li
                      key={`${selectedStory.id}-${index}`}
                      className="flex items-start gap-2 font-mono"
                    >
                      <span className="mt-0.5 text-cyan-400">
                        ▸
                      </span>

                      <span>
                        {point}
                      </span>
                    </li>
                  )
                )}
              </ul>
            </div>
          </div>
        </section>

        {/* ====================================================
            TRENDING
        ==================================================== */}

        <section className="space-y-4 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md">

          <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">

            <h3 className="font-mono text-xs font-bold uppercase tracking-widest text-white">
              TRENDING INTELLIGENCE
            </h3>

            <span className="font-mono text-[9px] text-yellow-300">
              DEMO TOPICS
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">

            {trendingNodes.map((node) => (

              <button
                key={node}
                type="button"
                onClick={() =>
                  setSearchQuery(node)
                }
                className="flex min-h-[70px] flex-col items-center justify-center rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-3 text-center transition hover:bg-cyan-500/15"
              >

                <span className="mb-1.5 h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />

                <span className="font-mono text-[9px] font-bold tracking-wider text-cyan-100">
                  {node}
                </span>
              </button>
            ))}
          </div>
        </section>

        {/* ====================================================
            FOOTER STATUS
        ==================================================== */}

        <section className="flex flex-col justify-between gap-3 border-t border-cyan-500/10 pt-4 font-mono text-[9px] text-cyan-500/50 sm:flex-row">

          <span>
            KING ZARRY AI • INTELLIGENCE NEWS
          </span>

          <span>
            LIVE NEWS FEED: NOT CONNECTED
          </span>

          <span>
            DATASET: DEMONSTRATION
          </span>
        </section>
      </main>
    </div>
  );
}
