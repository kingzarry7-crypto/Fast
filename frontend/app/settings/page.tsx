"use client";

import React, { useState } from "react";

// Types
type CategoryId =
  | "PROFILE"
  | "AI BEHAVIOUR"
  | "MEMORY"
  | "VOICE"
  | "VISION"
  | "NOTIFICATIONS"
  | "TRADING"
  | "AGENTS"
  | "APPEARANCE"
  | "SECURITY"
  | "PRIVACY"
  | "SUBSCRIPTION"
  | "SYSTEM";

export default function KingZarrySettingsPage() {
  const [activeTab, setActiveTab] = useState<CategoryId>("PROFILE");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"IDLE" | "SAVING" | "SAVED">("IDLE");

  // Interactive Settings State
  const [responseStyle, setResponseStyle] = useState<string>("BALANCED");
  const [proactiveSuggestions, setProactiveSuggestions] = useState<boolean>(true);
  const [contextAwareness, setContextAwareness] = useState<boolean>(true);
  
  // Memory
  const [saveConversations, setSaveConversations] = useState<boolean>(true);
  const [useRelevantMemory, setUseRelevantMemory] = useState<boolean>(true);
  const [personalContext, setPersonalContext] = useState<boolean>(true);

  // Voice
  const [voiceOutput, setVoiceOutput] = useState<boolean>(true);
  const [autoPlay, setAutoPlay] = useState<boolean>(false);
  const [voiceSpeed, setVoiceSpeed] = useState<string>("1.0x");

  // Vision
  const [imageAnalysis, setImageAnalysis] = useState<boolean>(true);
  const [docAnalysis, setDocAnalysis] = useState<boolean>(true);

  // Notifications
  const [notifAi, setNotifAi] = useState<boolean>(true);
  const [notifMarket, setNotifMarket] = useState<boolean>(true);
  const [notifNews, setNotifNews] = useState<boolean>(true);
  const [notifAgent, setNotifAgent] = useState<boolean>(true);
  const [notifSecurity, setNotifSecurity] = useState<boolean>(true);

  // Trading
  const [defaultMarket, setDefaultMarket] = useState<string>("BTC/USDT");
  const [defaultTimeframe, setDefaultTimeframe] = useState<string>("1H");
  const [riskPreference, setRiskPreference] = useState<string>("MODERATE");

  // Agents
  const [agentPermRead, setAgentPermRead] = useState<boolean>(true);
  const [agentPermAnalyze, setAgentPermAnalyze] = useState<boolean>(true);
  const [agentApproval, setAgentApproval] = useState<boolean>(true);

  // Appearance
  const [theme, setTheme] = useState<string>("DARK");
  const [hudIntensity, setHudIntensity] = useState<string>("HIGH");

  // Navigation Items
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

  const categories: CategoryId[] = [
    "PROFILE",
    "AI BEHAVIOUR",
    "MEMORY",
    "VOICE",
    "VISION",
    "NOTIFICATIONS",
    "TRADING",
    "AGENTS",
    "APPEARANCE",
    "SECURITY",
    "PRIVACY",
    "SUBSCRIPTION",
    "SYSTEM",
  ];

  const coreNodes = [
    { label: "IDENTITY", status: "SYNCED" },
    { label: "AI", status: "ACTIVE" },
    { label: "MEMORY", status: "READY" },
    { label: "VOICE", status: "ONLINE" },
    { label: "VISION", status: "STANDBY" },
    { label: "AGENTS", status: "DEPLOYED" },
    { label: "TOOLS", status: "SECURE" },
    { label: "SECURITY", status: "PROTECTED" },
  ];

  const handleSave = () => {
    setSaveStatus("SAVING");
    setTimeout(() => {
      setSaveStatus("SAVED");
      setTimeout(() => setSaveStatus("IDLE"), 2500);
    }, 1200);
  };

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
                SYSTEM CONTROL
              </span>
            </div>
            <div className="flex items-center space-x-2 text-[10px] font-mono text-cyan-400/70">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span>SYSTEM ONLINE</span>
              <span className="text-cyan-700">•</span>
              <span>AI CORE CONFIGURATION</span>
            </div>
          </div>
        </div>

        {/* Navigation - Desktop */}
        <nav className="hidden lg:flex items-center space-x-1 bg-cyan-950/20 p-1 rounded-lg border border-cyan-500/10">
          {navItems.map((item) => {
            const isActive = item === "SETTINGS";
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
                  item === "SETTINGS"
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
              <span>SYSTEM SETTINGS</span>
            </h2>
            <p className="text-xs font-mono text-cyan-400/60 mt-1">
              Configure your AI environment, identity, memory, notifications and system preferences.
            </p>
          </div>

          <div className="p-3 rounded-lg border border-cyan-500/20 bg-cyan-950/20 backdrop-blur-md max-w-xs">
            <div className="flex items-center justify-between text-[10px] font-mono text-cyan-400/80 mb-1">
              <span className="font-bold tracking-wider">AI CONFIGURATION</span>
              <span className="text-cyan-400">ACTIVE</span>
            </div>
            <div className="text-xs text-cyan-200 font-mono">
              STATUS: <strong className="text-cyan-400">ONLINE</strong>
            </div>
          </div>
        </div>

        {/* CENTRAL AI CONTROL CORE HUD */}
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
              <span className="text-xs font-mono font-bold tracking-widest text-cyan-200 uppercase">SYSTEM CONTROL CORE</span>
              <div className="text-[9px] font-mono text-cyan-500/70">ONE AI CORE → COMPLETE PERSONAL CONTROL</div>
            </div>
          </div>

          {/* Configuration Nodes */}
          <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 gap-3 w-full md:w-2/3">
            {coreNodes.map((node) => (
              <div key={node.label} className="p-3 rounded-xl border border-cyan-500/15 bg-cyan-950/20 flex items-center justify-between">
                <div>
                  <span className="text-xs font-mono font-bold text-white block">{node.label}</span>
                  <span className="text-[8px] font-mono text-cyan-400/60 block">NODE SECURE</span>
                </div>
                <span className="px-1.5 py-0.5 text-[9px] font-mono rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  {node.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* SETTINGS LAYOUT: SIDEBAR & MAIN PANEL */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* SETTINGS NAVIGATION CONSOLE (4 cols) */}
          <div className="lg:col-span-4 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-4 backdrop-blur-md space-y-2">
            <div className="text-[10px] font-mono font-bold tracking-widest text-cyan-400/70 px-3 py-1 border-b border-cyan-500/15 mb-2 uppercase">
              CONTROL CONSOLE
            </div>
            <div className="space-y-1 max-h-[500px] overflow-y-auto pr-1">
              {categories.map((cat) => {
                const isActive = activeTab === cat;
                return (
                  <button
                    key={cat}
                    onClick={() => setActiveTab(cat)}
                    className={`w-full text-left px-3.5 py-2.5 rounded-xl font-mono text-xs tracking-wider transition flex items-center justify-between border ${
                      isActive
                        ? "bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-[0_0_12px_rgba(0,240,255,0.2)]"
                        : "bg-cyan-950/20 text-cyan-400/70 border-cyan-500/10 hover:bg-cyan-500/10 hover:text-cyan-200"
                    }`}
                  >
                    <span>{cat}</span>
                    <span className={`w-1.5 h-1.5 rounded-full ${isActive ? "bg-cyan-400 animate-pulse" : "bg-cyan-900"}`} />
                  </button>
                );
              })}
            </div>
          </div>

          {/* SETTINGS CONTENT PANEL (8 cols) */}
          <div className="lg:col-span-8 rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md space-y-6">
            {/* PROFILE SETTINGS */}
            {activeTab === "PROFILE" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                  <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">AI USER IDENTITY</h3>
                  <span className="text-[9px] font-mono text-cyan-400/60">ACTIVE PROFILE</span>
                </div>

                <div className="flex items-center space-x-4 p-4 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                  <div className="w-16 h-16 rounded-xl border border-cyan-400 bg-cyan-950/40 flex items-center justify-center text-xl font-bold font-mono text-cyan-300 shadow-[0_0_15px_rgba(0,240,255,0.3)]">
                    KZ
                  </div>
                  <div>
                    <h4 className="text-sm font-bold font-mono text-white">KING ZARRY</h4>
                    <span className="text-xs font-mono text-cyan-400/70 block">@kingzarry • Primary System Owner</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                  <div className="space-y-1.5">
                    <label className="text-cyan-400/70 block">DISPLAY NAME</label>
                    <input
                      type="text"
                      defaultValue="KING ZARRY"
                      className="w-full px-3.5 py-2 rounded-lg bg-cyan-950/30 border border-cyan-500/30 text-cyan-100 focus:outline-none focus:border-cyan-400"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-cyan-400/70 block">SYSTEM USERNAME</label>
                    <input
                      type="text"
                      defaultValue="kingzarry"
                      className="w-full px-3.5 py-2 rounded-lg bg-cyan-950/30 border border-cyan-500/30 text-cyan-100 focus:outline-none focus:border-cyan-400"
                    />
                  </div>
                  <div className="space-y-1.5 md:col-span-2">
                    <label className="text-cyan-400/70 block">EMAIL / SECURE COMMUNICATIONS CHANNEL</label>
                    <input
                      type="email"
                      defaultValue="zarry@intelligence.core"
                      className="w-full px-3.5 py-2 rounded-lg bg-cyan-950/30 border border-cyan-500/30 text-cyan-100 focus:outline-none focus:border-cyan-400"
                    />
                  </div>
                </div>

                <div className="pt-2">
                  <button className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/30 transition">
                    EDIT PROFILE IDENTIFIERS
                  </button>
                </div>
              </div>
            )}

            {/* AI BEHAVIOUR */}
            {activeTab === "AI BEHAVIOUR" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                  <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">AI COMMUNICATION & BEHAVIOUR</h3>
                  <span className="text-[9px] font-mono text-cyan-400/60">REASONING ENGINE</span>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-mono text-cyan-400/70 block">RESPONSE STYLE</label>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                    {["CONCISE", "BALANCED", "DETAILED", "CREATIVE", "FORMAL"].map((style) => (
                      <button
                        key={style}
                        onClick={() => setResponseStyle(style)}
                        className={`p-2.5 rounded-lg text-xs font-mono border transition ${
                          responseStyle === style
                            ? "bg-cyan-500/25 text-cyan-300 border-cyan-400 shadow-[0_0_10px_rgba(0,240,255,0.2)]"
                            : "bg-cyan-950/20 text-cyan-400/70 border-cyan-500/15 hover:bg-cyan-500/10"
                        }`}
                      >
                        {style}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-4 pt-2 font-mono text-xs">
                  <div className="flex items-center justify-between p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                    <div>
                      <span className="text-white font-bold block">PROACTIVE SUGGESTIONS</span>
                      <span className="text-cyan-400/60 text-[10px]">Allow AI to offer contextual follow-up insights</span>
                    </div>
                    <button
                      onClick={() => setProactiveSuggestions(!proactiveSuggestions)}
                      className={`w-12 h-6 rounded-full p-1 transition ${proactiveSuggestions ? "bg-cyan-500" : "bg-cyan-950 border border-cyan-500/40"}`}
                    >
                      <div className={`w-4 h-4 rounded-full bg-black transition transform ${proactiveSuggestions ? "translate-x-6" : "translate-x-0"}`} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                    <div>
                      <span className="text-white font-bold block">CONTEXT AWARENESS</span>
                      <span className="text-cyan-400/60 text-[10px]">Retain active session context across queries</span>
                    </div>
                    <button
                      onClick={() => setContextAwareness(!contextAwareness)}
                      className={`w-12 h-6 rounded-full p-1 transition ${contextAwareness ? "bg-cyan-500" : "bg-cyan-950 border border-cyan-500/40"}`}
                    >
                      <div className={`w-4 h-4 rounded-full bg-black transition transform ${contextAwareness ? "translate-x-6" : "translate-x-0"}`} />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* MEMORY */}
            {activeTab === "MEMORY" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                  <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">MEMORY SYSTEM</h3>
                  <span className="text-[9px] font-mono text-cyan-400/60">STATUS: ACTIVE</span>
                </div>

                <div className="space-y-4 font-mono text-xs">
                  <div className="flex items-center justify-between p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                    <div>
                      <span className="text-white font-bold block">SAVE CONVERSATIONS</span>
                      <span className="text-cyan-400/60 text-[10px]">Index dialogue interactions into long-term memory</span>
                    </div>
                    <button
                      onClick={() => setSaveConversations(!saveConversations)}
                      className={`w-12 h-6 rounded-full p-1 transition ${saveConversations ? "bg-cyan-500" : "bg-cyan-950 border border-cyan-500/40"}`}
                    >
                      <div className={`w-4 h-4 rounded-full bg-black transition transform ${saveConversations ? "translate-x-6" : "translate-x-0"}`} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                    <div>
                      <span className="text-white font-bold block">USE RELEVANT MEMORY</span>
                      <span className="text-cyan-400/60 text-[10px]">Reference past context automatically</span>
                    </div>
                    <button
                      onClick={() => setUseRelevantMemory(!useRelevantMemory)}
                      className={`w-12 h-6 rounded-full p-1 transition ${useRelevantMemory ? "bg-cyan-500" : "bg-cyan-950 border border-cyan-500/40"}`}
                    >
                      <div className={`w-4 h-4 rounded-full bg-black transition transform ${useRelevantMemory ? "translate-x-6" : "translate-x-0"}`} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                    <div>
                      <span className="text-white font-bold block">PERSONAL CONTEXT</span>
                      <span className="text-cyan-400/60 text-[10px]">Incorporate user preferences into reasoning</span>
                    </div>
                    <button
                      onClick={() => setPersonalContext(!personalContext)}
                      className={`w-12 h-6 rounded-full p-1 transition ${personalContext ? "bg-cyan-500" : "bg-cyan-950 border border-cyan-500/40"}`}
                    >
                      <div className={`w-4 h-4 rounded-full bg-black transition transform ${personalContext ? "translate-x-6" : "translate-x-0"}`} />
                    </button>
                  </div>
                </div>

                <div className="pt-2 border-t border-red-500/20 p-4 rounded-xl bg-red-950/10 border">
                  <h4 className="text-xs font-mono font-bold text-red-400 mb-1">DESTRUCTIVE MEMORY ACTION</h4>
                  <p className="text-xs text-red-200/70 mb-3">Clear all stored memory indices from the neural database.</p>
                  <button className="px-3.5 py-1.5 rounded-lg text-xs font-mono bg-red-500/20 text-red-300 border border-red-500/40 hover:bg-red-500/30 transition">
                    CLEAR MEMORY
                  </button>
                </div>
              </div>
            )}

            {/* VOICE */}
            {activeTab === "VOICE" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                  <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">VOICE SYSTEM</h3>
                  <span className="text-[9px] font-mono text-cyan-400/60">SYNTHESIS READY</span>
                </div>

                {/* Waveform Visualization */}
                <div className="p-4 rounded-xl border border-cyan-500/30 bg-cyan-950/30 flex items-center justify-between">
                  <span className="text-xs font-mono text-cyan-300">VOICE TELEMETRY WAVEFORM</span>
                  <div className="flex items-center space-x-1">
                    {[40, 70, 30, 90, 50, 80, 20, 60, 100, 45].map((h, i) => (
                      <div
                        key={i}
                        style={{ height: `${h * 0.3}px` }}
                        className="w-1.5 bg-cyan-400 rounded-full animate-pulse"
                      />
                    ))}
                  </div>
                </div>

                <div className="space-y-4 font-mono text-xs">
                  <div className="flex items-center justify-between p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                    <div>
                      <span className="text-white font-bold block">VOICE OUTPUT</span>
                      <span className="text-cyan-400/60 text-[10px]">Enable audio response generation</span>
                    </div>
                    <button
                      onClick={() => setVoiceOutput(!voiceOutput)}
                      className={`w-12 h-6 rounded-full p-1 transition ${voiceOutput ? "bg-cyan-500" : "bg-cyan-950 border border-cyan-500/40"}`}
                    >
                      <div className={`w-4 h-4 rounded-full bg-black transition transform ${voiceOutput ? "translate-x-6" : "translate-x-0"}`} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                    <div>
                      <span className="text-white font-bold block">AUTO PLAY AUDIO</span>
                      <span className="text-cyan-400/60 text-[10px]">Automatically speak incoming AI responses</span>
                    </div>
                    <button
                      onClick={() => setAutoPlay(!autoPlay)}
                      className={`w-12 h-6 rounded-full p-1 transition ${autoPlay ? "bg-cyan-500" : "bg-cyan-950 border border-cyan-500/40"}`}
                    >
                      <div className={`w-4 h-4 rounded-full bg-black transition transform ${autoPlay ? "translate-x-6" : "translate-x-0"}`} />
                    </button>
                  </div>

                  <div className="space-y-2 pt-2">
                    <label className="text-cyan-400/70 block">VOICE SPEED</label>
                    <div className="flex space-x-2">
                      {["0.8x", "1.0x", "1.2x", "1.5x"].map((spd) => (
                        <button
                          key={spd}
                          onClick={() => setVoiceSpeed(spd)}
                          className={`px-3 py-1.5 rounded-lg border text-xs ${voiceSpeed === spd ? "bg-cyan-500/25 text-cyan-300 border-cyan-400" : "border-cyan-500/20 text-cyan-400/60"}`}
                        >
                          {spd}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* VISION */}
            {activeTab === "VISION" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                  <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">VISION SYSTEM</h3>
                  <span className="text-[9px] font-mono text-cyan-400/60">CAPABILITY ACTIVE</span>
                </div>

                <div className="space-y-4 font-mono text-xs">
                  <div className="flex items-center justify-between p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                    <div>
                      <span className="text-white font-bold block">IMAGE ANALYSIS</span>
                      <span className="text-cyan-400/60 text-[10px]">Process uploaded photographs and diagrams</span>
                    </div>
                    <button
                      onClick={() => setImageAnalysis(!imageAnalysis)}
                      className={`w-12 h-6 rounded-full p-1 transition ${imageAnalysis ? "bg-cyan-500" : "bg-cyan-950 border border-cyan-500/40"}`}
                    >
                      <div className={`w-4 h-4 rounded-full bg-black transition transform ${imageAnalysis ? "translate-x-6" : "translate-x-0"}`} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                    <div>
                      <span className="text-white font-bold block">DOCUMENT ANALYSIS</span>
                      <span className="text-cyan-400/60 text-[10px]">Extract semantic data from visual documents</span>
                    </div>
                    <button
                      onClick={() => setDocAnalysis(!docAnalysis)}
                      className={`w-12 h-6 rounded-full p-1 transition ${docAnalysis ? "bg-cyan-500" : "bg-cyan-950 border border-cyan-500/40"}`}
                    >
                      <div className={`w-4 h-4 rounded-full bg-black transition transform ${docAnalysis ? "translate-x-6" : "translate-x-0"}`} />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* NOTIFICATIONS */}
            {activeTab === "NOTIFICATIONS" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                  <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">INTELLIGENCE NOTIFICATIONS</h3>
                  <span className="text-[9px] font-mono text-cyan-400/60">ALERTS SYNCED</span>
                </div>

                <div className="space-y-3 font-mono text-xs">
                  {[
                    { label: "AI RESPONSES", val: notifAi, set: setNotifAi },
                    { label: "MARKET ALERTS", val: notifMarket, set: setNotifMarket },
                    { label: "NEWS ALERTS", val: notifNews, set: setNotifNews },
                    { label: "AGENT ACTIVITY", val: notifAgent, set: setNotifAgent },
                    { label: "SECURITY ALERTS", val: notifSecurity, set: setNotifSecurity },
                  ].map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                      <span className="text-white font-bold">{item.label}</span>
                      <button
                        onClick={() => item.set(!item.val)}
                        className={`w-12 h-6 rounded-full p-1 transition ${item.val ? "bg-cyan-500" : "bg-cyan-950 border border-cyan-500/40"}`}
                      >
                        <div className={`w-4 h-4 rounded-full bg-black transition transform ${item.val ? "translate-x-6" : "translate-x-0"}`} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TRADING */}
            {activeTab === "TRADING" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                  <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">MARKET INTELLIGENCE</h3>
                  <span className="text-[9px] font-mono text-cyan-400/60">CAPABILITY SETTING</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
                  <div className="space-y-1.5">
                    <label className="text-cyan-400/70 block">DEFAULT MARKET</label>
                    <select
                      value={defaultMarket}
                      onChange={(e) => setDefaultMarket(e.target.value)}
                      className="w-full px-3.5 py-2 rounded-lg bg-cyan-950/30 border border-cyan-500/30 text-cyan-100 focus:outline-none"
                    >
                      <option value="BTC/USDT">BTC/USDT</option>
                      <option value="ETH/USDT">ETH/USDT</option>
                      <option value="SOL/USDT">SOL/USDT</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-cyan-400/70 block">DEFAULT TIMEFRAME</label>
                    <select
                      value={defaultTimeframe}
                      onChange={(e) => setDefaultTimeframe(e.target.value)}
                      className="w-full px-3.5 py-2 rounded-lg bg-cyan-950/30 border border-cyan-500/30 text-cyan-100 focus:outline-none"
                    >
                      <option value="15M">15M</option>
                      <option value="1H">1H</option>
                      <option value="4H">4H</option>
                      <option value="1D">1D</option>
                    </select>
                  </div>

                  <div className="space-y-1.5 md:col-span-2">
                    <label className="text-cyan-400/70 block">RISK PREFERENCE</label>
                    <div className="grid grid-cols-3 gap-2">
                      {["CONSERVATIVE", "MODERATE", "AGGRESSIVE"].map((risk) => (
                        <button
                          key={risk}
                          onClick={() => setRiskPreference(risk)}
                          className={`p-2 rounded-lg border text-xs ${riskPreference === risk ? "bg-cyan-500/25 text-cyan-300 border-cyan-400" : "border-cyan-500/20 text-cyan-400/60"}`}
                        >
                          {risk}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* AGENTS */}
            {activeTab === "AGENTS" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                  <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">AI AGENT CONTROL</h3>
                  <span className="text-[9px] font-mono text-cyan-400/60">AUTONOMOUS AGENTS</span>
                </div>

                <div className="p-4 rounded-xl border border-cyan-500/20 bg-cyan-950/20 font-mono text-xs space-y-3">
                  <span className="text-cyan-300 font-bold block">PERMISSION TELEMETRY PIPELINE</span>
                  <div className="grid grid-cols-4 gap-2 text-center">
                    {["READ", "ANALYZE", "DRAFT", "ACTION"].map((step, idx) => (
                      <div key={step} className="p-2 rounded border border-cyan-500/30 bg-cyan-950/40">
                        <span className="text-[9px] text-cyan-400/60 block">STEP 0{idx + 1}</span>
                        <span className="text-cyan-100 font-bold">{step}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-4 font-mono text-xs">
                  <div className="flex items-center justify-between p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                    <div>
                      <span className="text-white font-bold block">AUTOMATIC ACTIONS</span>
                      <span className="text-cyan-400/60 text-[10px]">Allow background agents to execute routine tasks</span>
                    </div>
                    <button
                      onClick={() => setAgentPermRead(!agentPermRead)}
                      className={`w-12 h-6 rounded-full p-1 transition ${agentPermRead ? "bg-cyan-500" : "bg-cyan-950 border border-cyan-500/40"}`}
                    >
                      <div className={`w-4 h-4 rounded-full bg-black transition transform ${agentPermRead ? "translate-x-6" : "translate-x-0"}`} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                    <div>
                      <span className="text-white font-bold block">APPROVAL REQUIRED FOR CRITICAL TASKS</span>
                      <span className="text-cyan-400/60 text-[10px]">Mandate user authorization before major execution</span>
                    </div>
                    <button
                      onClick={() => setAgentApproval(!agentApproval)}
                      className={`w-12 h-6 rounded-full p-1 transition ${agentApproval ? "bg-cyan-500" : "bg-cyan-950 border border-cyan-500/40"}`}
                    >
                      <div className={`w-4 h-4 rounded-full bg-black transition transform ${agentApproval ? "translate-x-6" : "translate-x-0"}`} />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* APPEARANCE */}
            {activeTab === "APPEARANCE" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                  <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">INTERFACE APPEARANCE</h3>
                  <span className="text-[9px] font-mono text-cyan-400/60">HUD CONFIGURATION</span>
                </div>

                <div className="space-y-4 font-mono text-xs">
                  <div className="space-y-2">
                    <label className="text-cyan-400/70 block">THEME ENVIRONMENT</label>
                    <div className="grid grid-cols-3 gap-2">
                      {["DARK", "LIGHT", "SYSTEM"].map((t) => (
                        <button
                          key={t}
                          onClick={() => setTheme(t)}
                          className={`p-2.5 rounded-lg border text-xs ${theme === t ? "bg-cyan-500/25 text-cyan-300 border-cyan-400" : "border-cyan-500/20 text-cyan-400/60"}`}
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-2 pt-2">
                    <label className="text-cyan-400/70 block">HUD GLOW INTENSITY</label>
                    <div className="grid grid-cols-3 gap-2">
                      {["LOW", "BALANCED", "HIGH"].map((hi) => (
                        <button
                          key={hi}
                          onClick={() => setHudIntensity(hi)}
                          className={`p-2.5 rounded-lg border text-xs ${hudIntensity === hi ? "bg-cyan-500/25 text-cyan-300 border-cyan-400" : "border-cyan-500/20 text-cyan-400/60"}`}
                        >
                          {hi}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* SECURITY */}
            {activeTab === "SECURITY" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                  <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">SECURITY CONTROL</h3>
                  <span className="text-[9px] font-mono text-cyan-400/60">STATUS: PROTECTED</span>
                </div>

                <div className="space-y-3 font-mono text-xs">
                  <div className="p-4 rounded-xl border border-cyan-500/20 bg-cyan-950/20 flex items-center justify-between">
                    <div>
                      <span className="text-white font-bold block">CHANGE PASSWORD</span>
                      <span className="text-cyan-400/60 text-[10px]">Update your system security credentials</span>
                    </div>
                    <button className="px-3 py-1.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                      UPDATE
                    </button>
                  </div>

                  <div className="p-4 rounded-xl border border-cyan-500/20 bg-cyan-950/20 flex items-center justify-between">
                    <div>
                      <span className="text-white font-bold block">ACTIVE SESSIONS</span>
                      <span className="text-cyan-400/60 text-[10px]">1 active session connected securely</span>
                    </div>
                    <button className="px-3 py-1.5 rounded bg-red-500/20 text-red-300 border border-red-500/40">
                      LOG OUT ALL DEVICES
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* PRIVACY */}
            {activeTab === "PRIVACY" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                  <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">PRIVACY CONTROL</h3>
                  <span className="text-[9px] font-mono text-cyan-400/60">DATA GOVERNANCE</span>
                </div>

                <p className="text-xs text-cyan-200/80 font-sans leading-relaxed">
                  KING ZARRY AI enforces strict data compartmentalization. Your personal memory indices, conversational history, and telemetry tokens remain securely isolated within your designated environment.
                </p>

                <div className="space-y-3 font-mono text-xs">
                  {["MEMORY STORAGE ISOLATION", "ANALYTICS OPT-OUT", "LOCAL CONTEXT RETENTION"].map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                      <span className="text-white font-bold">{item}</span>
                      <span className="text-cyan-400">ENABLED</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* SUBSCRIPTION */}
            {activeTab === "SUBSCRIPTION" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                  <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">AI ACCESS</h3>
                  <span className="text-[9px] font-mono text-cyan-400/60">SUBSCRIPTION STATUS</span>
                </div>

                <div className="p-4 rounded-xl border border-cyan-500/30 bg-cyan-950/30 flex items-center justify-between font-mono">
                  <div>
                    <span className="text-cyan-400/70 text-[10px] block">CURRENT ACCESS STATUS</span>
                    <span className="text-white font-bold text-sm">LOGIN REQUIRED / STANDBY</span>
                  </div>
                  <span className="px-2.5 py-1 text-xs rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                    UNLINKED
                  </span>
                </div>

                <div className="pt-2 flex space-x-3">
                  <button className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-cyan-400 text-black hover:bg-cyan-300 transition">
                    VIEW PLANS
                  </button>
                  <button className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/30 transition">
                    MANAGE ACCESS
                  </button>
                </div>
              </div>
            )}

            {/* SYSTEM */}
            {activeTab === "SYSTEM" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
                  <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">SYSTEM DIAGNOSTICS & RESET</h3>
                  <span className="text-[9px] font-mono text-cyan-400/60">CORE 2.4.9</span>
                </div>

                <div className="space-y-3 font-mono text-xs">
                  <div className="flex justify-between p-3 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                    <span className="text-cyan-400/70">ENGINE LATENCY</span>
                    <span className="text-emerald-400">14ms (OPTIMAL)</span>
                  </div>
                  <div className="flex justify-between p-3 rounded-xl border border-cyan-500/20 bg-cyan-950/20">
                    <span className="text-cyan-400/70">NEURAL MESH SYNC</span>
                    <span className="text-cyan-300">100% SECURE</span>
                  </div>
                </div>

                <div className="pt-4 border-t border-red-500/20 p-4 rounded-xl bg-red-950/10 border space-y-3">
                  <h4 className="text-xs font-mono font-bold text-red-400">DANGER ZONE / SYSTEM RESET</h4>
                  <p className="text-xs text-red-200/70">Reset preferences or clear system parameters.</p>
                  <div className="flex space-x-2">
                    <button className="px-3 py-1.5 rounded text-xs font-mono bg-red-500/20 text-red-300 border border-red-500/40">
                      RESET PREFERENCES
                    </button>
                    <button className="px-3 py-1.5 rounded text-xs font-mono bg-red-600/30 text-red-200 border border-red-500/60">
                      DELETE ACCOUNT
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* SAVE SYSTEM BOTTOM BAR */}
            <div className="pt-6 mt-6 border-t border-cyan-500/15 flex items-center justify-between">
              <div className="text-xs font-mono text-cyan-400/70 flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                <span>
                  {saveStatus === "IDLE" && "CONFIGURATION READY"}
                  {saveStatus === "SAVING" && "SAVING CONFIGURATION..."}
                  {saveStatus === "SAVED" && "CONFIGURATION SAVED"}
                </span>
              </div>

              <div className="flex space-x-3">
                <button
                  onClick={() => setSaveStatus("IDLE")}
                  className="px-4 py-2 rounded-lg text-xs font-mono bg-cyan-950/40 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/10 transition"
                >
                  RESET
                </button>
                <button
                  onClick={handleSave}
                  className="px-5 py-2 rounded-lg text-xs font-mono font-bold tracking-widest bg-cyan-400 text-black hover:bg-cyan-300 transition shadow-[0_0_15px_rgba(0,240,255,0.3)]"
                >
                  SAVE CHANGES
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
