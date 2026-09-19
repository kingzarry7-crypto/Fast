"use client";

import React, { useState } from "react";

// Types
type PlanId = "monthly" | "quarterly" | "yearly";

export default function KingZarryPricingPage() {
  const [selectedPlan, setSelectedPlan] = useState<PlanId>("quarterly");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeFaq, setActiveFaq] = useState<number | null>(null);

  // Navigation Items matching standard King Zarry AI HUD
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
  ];

  // Core Capabilities linked around AI Core
  const coreCapabilities = [
    { label: "AI", status: "ONLINE" },
    { label: "VISION", status: "ACTIVE" },
    { label: "VOICE", status: "READY" },
    { label: "MEMORY", status: "SYNCED" },
    { label: "REASONING", status: "MAX" },
    { label: "AGENTS", status: "DEPLOYED" },
    { label: "TOOLS", status: "STANDBY" },
    { label: "MARKETS", status: "LIVE" },
    { label: "SIGNALS", status: "MONITOR" },
    { label: "NEWS", status: "STREAM" },
  ];

  // Membership Plans matching requested exact Stars & Duration values
  const plans = [
    {
      id: "monthly" as PlanId,
      name: "MONTHLY ACCESS",
      duration: "30 DAYS",
      stars: "150",
      description: "Standard personal AI system access for standard operational cycles.",
      features: [
        "Full AI Chat & Reasoning Engine",
        "Memory & Context Retention",
        "Standard Vision & Voice Processing",
        "Core Agent & Tool Execution",
        "Real-time Market Intelligence",
      ],
      tag: "FLEXIBLE",
    },
    {
      id: "quarterly" as PlanId,
      name: "90-DAY EXTENDED ACCESS",
      duration: "90 DAYS",
      stars: "500",
      description: "Extended operational access with priority neural bandwidth allocation.",
      features: [
        "All Monthly System Features",
        "Priority AI Agent Execution",
        "Advanced Market Signal Telemetry",
        "Extended Long-Term Memory Indexing",
        "Deep Contextual News Synthesis",
      ],
      tag: "RECOMMENDED",
    },
    {
      id: "yearly" as PlanId,
      name: "LONG-TERM ACCESS",
      duration: "365 DAYS",
      stars: "2500",
      description: "Uninterrupted annual membership with maximum neural priority and compute allocation.",
      features: [
        "Unrestricted System Access (365 Days)",
        "Maximum Priority Neural Processing",
        "Full Suite: Agents, Vision, Tools & Markets",
        "Advanced Telegram & Discord Bridge Integration",
        "Permanent Extended Memory Architecture",
      ],
      tag: "EXTENDED ACCESS",
    },
  ];

  const faqs = [
    {
      q: "What does AI access include?",
      a: "Membership grants full access to the KING ZARRY AI environment, including conversational reasoning, vision, voice synthesis, memory indexing, autonomous agents, and real-time market/news intelligence."
    },
    {
      q: "Can I change my plan?",
      a: "Yes, you can select and activate any access tier when required. New activations securely extend your active membership duration."
    },
    {
      q: "How does Stars payment work?",
      a: "Payments are securely processed via Telegram Stars. Select your access tier and complete the prompt through the authorized Telegram payment interface."
    },
    {
      q: "What happens when access expires?",
      a: "When your access period concludes, your personal AI environment returns to standby mode. Your encrypted memory and configurations remain safely stored for your next activation."
    },
    {
      q: "Can I use KING ZARRY AI on multiple devices?",
      a: "Yes. Your personal AI access is synchronized across your authorized account session, allowing seamless transition between web and supported messaging environments."
    },
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
                ACCESS CONTROL
              </span>
            </div>
            <div className="flex items-center space-x-2 text-[10px] font-mono text-cyan-400/70">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span>SYSTEM READY</span>
              <span className="text-cyan-700">•</span>
              <span>TELEMETRY: SYNCHRONIZED</span>
            </div>
          </div>
        </div>

        {/* Navigation - Desktop */}
        <nav className="hidden lg:flex items-center space-x-1 bg-cyan-950/20 p-1 rounded-lg border border-cyan-500/10">
          {navItems.map((item) => {
            const isActive = item === "PRICING";
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
                  item === "PRICING"
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
      <main className="relative z-20 flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-8">
        {/* TOP TITLE SUB HEADER */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-cyan-500/10 pb-6 text-center md:text-left">
          <div>
            <h2 className="text-2xl md:text-3xl font-bold tracking-widest text-white uppercase flex items-center justify-center md:justify-start space-x-3">
              <span>CHOOSE YOUR ACCESS</span>
            </h2>
            <p className="text-xs font-mono text-cyan-400/60 mt-1">
              Unlock the intelligence capabilities you want from your personal AI system.
            </p>
          </div>

          {/* CURRENT ACCESS STATUS PANEL */}
          <div className="p-3 rounded-lg border border-cyan-500/20 bg-cyan-950/20 backdrop-blur-md max-w-xs mx-auto md:mx-0">
            <div className="flex items-center justify-between text-[10px] font-mono text-cyan-400/80 mb-1">
              <span className="font-bold tracking-wider">CURRENT ACCESS</span>
              <span className="text-cyan-400">STANDBY</span>
            </div>
            <div className="text-xs text-cyan-200 font-mono">
              STATUS: <strong className="text-cyan-400">NOT CONNECTED</strong>
            </div>
          </div>
        </div>

        {/* CENTRAL AI ACCESS CORE HUD */}
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
              <span className="text-xs font-mono font-bold tracking-widest text-cyan-200 uppercase">ONE AI CORE</span>
              <div className="text-[9px] font-mono text-cyan-500/70">ONE AI CORE → MANY CAPABILITIES</div>
            </div>
          </div>

          {/* Capability Nodes */}
          <div className="relative z-10 grid grid-cols-2 sm:grid-cols-5 gap-2.5 w-full md:w-2/3">
            {coreCapabilities.map((cap) => (
              <div key={cap.label} className="p-2.5 rounded-xl border border-cyan-500/15 bg-cyan-950/20 flex flex-col justify-between items-center text-center">
                <span className="text-xs font-mono font-bold text-white mb-1">{cap.label}</span>
                <span className="px-1.5 py-0.5 text-[8px] font-mono rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  {cap.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* PRICING MODULES / MEMBERSHIP OPTIONS */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((plan) => {
            const isSelected = selectedPlan === plan.id;
            const isYearly = plan.id === "yearly";

            return (
              <div
                key={plan.id}
                onClick={() => setSelectedPlan(plan.id)}
                className={`relative rounded-2xl border p-6 backdrop-blur-md cursor-pointer transition-all duration-300 flex flex-col justify-between ${
                  isYearly
                    ? "bg-cyan-950/30 border-cyan-400 shadow-[0_0_25px_rgba(0,240,255,0.25)]"
                    : isSelected
                    ? "bg-cyan-950/25 border-cyan-500/60 shadow-[0_0_15px_rgba(0,240,255,0.15)]"
                    : "bg-[#020914]/90 border-cyan-500/20 hover:border-cyan-500/40"
                }`}
              >
                {/* Holographic corner accents */}
                <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-cyan-400 pointer-events-none" />
                <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-cyan-400 pointer-events-none" />

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-cyan-300 tracking-wider uppercase">
                      {plan.name}
                    </span>
                    <span className="px-2 py-0.5 text-[9px] font-mono rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                      {plan.tag}
                    </span>
                  </div>

                  {/* Stars Pricing Display */}
                  <div className="py-3 border-y border-cyan-500/15">
                    <div className="text-3xl md:text-4xl font-extrabold font-mono text-white tracking-tight flex items-baseline space-x-2">
                      <span>{plan.stars}</span>
                      <span className="text-xs font-normal text-cyan-400 tracking-widest uppercase">STARS</span>
                    </div>
                    <div className="text-[10px] font-mono text-cyan-400/70 mt-1">
                      DURATION: <strong className="text-cyan-200">{plan.duration}</strong>
                    </div>
                  </div>

                  <p className="text-xs text-cyan-200/80 leading-relaxed font-sans">
                    {plan.description}
                  </p>

                  <div className="space-y-2 pt-2">
                    <span className="text-[10px] font-mono text-cyan-400/60 tracking-wider block uppercase">INCLUDED CAPABILITIES</span>
                    <ul className="space-y-1.5 text-xs text-cyan-200 font-mono">
                      {plan.features.map((feat, idx) => (
                        <li key={idx} className="flex items-center space-x-2">
                          <span className="text-cyan-400">▸</span>
                          <span>{feat}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="pt-6 mt-6 border-t border-cyan-500/15">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedPlan(plan.id);
                    }}
                    className={`w-full py-2.5 rounded-lg text-xs font-mono font-bold tracking-widest uppercase transition shadow-[0_0_15px_rgba(0,240,255,0.2)] ${
                      isYearly
                        ? "bg-cyan-400 text-black hover:bg-cyan-300"
                        : "bg-cyan-500/20 text-cyan-200 border border-cyan-500/50 hover:bg-cyan-500/30 hover:text-white"
                    }`}
                  >
                    {isSelected ? "SELECTED ACCESS" : "ACTIVATE ACCESS"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* AI ACCESS MATRIX VISUALIZATION */}
        <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md space-y-4">
          <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
            <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">AI ACCESS MATRIX</h3>
            <span className="text-[9px] font-mono text-cyan-400/60">CONNECTED TO KZ AI CORE</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-9 gap-2 text-center font-mono text-xs">
            {["CONVERSATION", "VISION", "MEMORY", "VOICE", "AGENTS", "TOOLS", "MARKETS", "SIGNALS", "NEWS"].map((mod) => (
              <div key={mod} className="p-2.5 rounded-lg border border-cyan-500/20 bg-cyan-950/20 flex flex-col items-center justify-center space-y-1">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                <span className="text-[10px] text-cyan-100 font-bold">{mod}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ONE SYSTEM. MANY CAPABILITIES. */}
        <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md space-y-3">
          <h3 className="text-sm font-mono font-bold tracking-widest text-white uppercase">ONE SYSTEM. MANY CAPABILITIES.</h3>
          <p className="text-xs md:text-sm text-cyan-200/90 leading-relaxed font-sans">
            KING ZARRY AI brings conversation, reasoning, memory, vision, voice, agents, tools and market intelligence into one personal AI environment. Select your access tier to activate the complete intelligence suite.
          </p>
        </div>

        {/* FAQ / ACCESS INFORMATION */}
        <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6 backdrop-blur-md space-y-4">
          <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
            <h3 className="text-xs font-mono font-bold tracking-widest text-white uppercase">ACCESS INFORMATION & FAQ</h3>
            <span className="text-[9px] font-mono text-cyan-400/60">KNOWLEDGE BASE</span>
          </div>

          <div className="space-y-3">
            {faqs.map((faq, idx) => {
              const isOpen = activeFaq === idx;
              return (
                <div
                  key={idx}
                  onClick={() => setActiveFaq(isOpen ? null : idx)}
                  className="p-3.5 rounded-xl border border-cyan-500/20 bg-cyan-950/20 cursor-pointer transition"
                >
                  <div className="flex items-center justify-between font-mono text-xs text-white">
                    <span className="font-bold">{faq.q}</span>
                    <span className="text-cyan-400">{isOpen ? "[-]" : "[+]"}</span>
                  </div>
                  {isOpen && (
                    <p className="text-xs text-cyan-200/80 mt-2 pt-2 border-t border-cyan-500/10 font-sans leading-relaxed">
                      {faq.a}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}
