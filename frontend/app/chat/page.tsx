"use client";

import React, { useState, useEffect, useRef } from "react";

// Types
type MessageRole = "ai" | "user" | "system";

interface Message {
  id: string;
  role: MessageRole;
  text: string;
  timestamp: string;
  status?: string;
  capability?: string;
}

type AICoreState = "idle" | "thinking" | "speaking" | "listening";

export default function KingZarryChatPage() {
  // State
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "msg-1",
      role: "ai",
      text: "Good evening, King Zarry. All neural parameters are nominal. I am online and ready to assist you.",
      timestamp: "21:42:05",
      status: "KZ AI CORE • READY",
      capability: "SYSTEM",
    },
    {
      id: "msg-2",
      role: "user",
      text: "Initialize tactical situational overview and evaluate system readiness.",
      timestamp: "21:42:30",
    },
    {
      id: "msg-3",
      role: "ai",
      text: "Understood. Synthesizing real-time environment telemetry, memory threads, and active agent directives. Core reasoning operating at peak efficiency across all connected modules.",
      timestamp: "21:42:34",
      status: "REASONING MODULE • ACTIVE",
      capability: "REASONING",
    },
  ]);

  const [input, setInput] = useState("");
  const [coreState, setCoreState] = useState<AICoreState>("idle");
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [activeCapability, setActiveCapability] = useState<string | null>("REASONING");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [hudStats, setHudStats] = useState({
    fps: 60,
    latency: 12,
    memory: 34,
    nodes: 1024,
  });

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, coreState]);

  // Dynamic telemetry simulator
  useEffect(() => {
    const interval = setInterval(() => {
      setHudStats({
        fps: Math.floor(58 + Math.random() * 4),
        latency: Math.floor(10 + Math.random() * 5),
        memory: +(34 + Math.random() * 0.8).toFixed(1),
        nodes: 1024 + Math.floor(Math.random() * 16),
      });
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  // Send message simulator
  const handleSend = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim()) return;

    const userMsgText = input;
    const now = new Date();
    const timeStr = `${now.getHours().toString().padStart(2, "0")}:${now
      .getMinutes()
      .toString()
      .padStart(2, "0")}:${now.getSeconds().toString().padStart(2, "0")}`;

    const newUserMsg: Message = {
      id: `msg-${Date.now()}`,
      role: "user",
      text: userMsgText,
      timestamp: timeStr,
    };

    setMessages((prev) => [...prev, newUserMsg]);
    setInput("");
    setCoreState("thinking");

    // Dynamic AI response generation logic
    setTimeout(() => {
      setCoreState("speaking");
      const aiResponse: Message = {
        id: `msg-${Date.now() + 1}`,
        role: "ai",
        text: getSimulatedAIResponse(userMsgText),
        timestamp: timeStr,
        status: `${activeCapability || "AI CORE"} • ONLINE`,
        capability: activeCapability || "AI",
      };

      setMessages((prev) => [...prev, aiResponse]);

      setTimeout(() => {
        setCoreState("idle");
      }, 2500);
    }, 1500);
  };

  const getSimulatedAIResponse = (query: string): string => {
    const lower = query.toLowerCase();
    if (lower.includes("vision") || lower.includes("see") || lower.includes("image")) {
      return "Visual analysis sub-routine activated. Processing high-resolution visual input feeds through spatial-neural recognition vectors.";
    }
    if (lower.includes("voice") || lower.includes("listen") || lower.includes("speak")) {
      return "Acoustic audio stream locked. Neural speech synthesis and soundwave frequency isolation operational.";
    }
    if (lower.includes("market") || lower.includes("signal") || lower.includes("news")) {
      return "Monitoring active telemetry modules. Aggregating incoming external data matrices and structure patterns.";
    }
    return `Acknowledged, King Zarry. Executing analysis on "${query}". All system outputs remain stable and isolated within the primary environment.`;
  };

  const toggleVoiceMode = () => {
    if (isVoiceActive) {
      setIsVoiceActive(false);
      setCoreState("idle");
    } else {
      setIsVoiceActive(true);
      setCoreState("listening");
    }
  };

  const capabilities = [
    { name: "AI", desc: "Core Intelligence" },
    { name: "VISION", desc: "Spatial Analysis" },
    { name: "VOICE", desc: "Acoustic Synthesizer" },
    { name: "MEMORY", desc: "Neural Context vector" },
    { name: "REASONING", desc: "Cognitive Processing" },
    { name: "AGENTS", desc: "Autonomous Units" },
    { name: "TOOLS", desc: "System Integrations" },
    { name: "MARKETS", desc: "Data Stream Watch" },
    { name: "SIGNALS", desc: "Pattern Detection" },
    { name: "NEWS", desc: "External Information" },
  ];

  const navItems = ["HOME", "CHAT", "VISION", "AGENTS", "TOOLS", "MARKETS", "SIGNALS", "NEWS", "MEMORY"];

  return (
    <div className="relative w-full h-screen bg-[#03060a] text-cyan-100 font-sans overflow-hidden flex flex-col justify-between selection:bg-cyan-500 selection:text-black">
      {/* Background Holographic Atmosphere */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#072438] via-[#020b14] to-[#010408] pointer-events-none" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#091a2815_1px,transparent_1px),linear-gradient(to_bottom,#091a2815_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />

      {/* Subtle Scan Lines Overlay */}
      <div className="absolute inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,240,255,0.015)_3px,transparent_4px)] pointer-events-none z-10" />

      {/* Radial Soft Glowing Spheres */}
      <div className="absolute top-[-10%] left-[20%] w-[500px] h-[500px] bg-cyan-600/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[20%] w-[600px] h-[600px] bg-indigo-600/10 rounded-full blur-[140px] pointer-events-none" />

      {/* TOP HEADER / NAVIGATION HUD */}
      <header className="relative z-20 flex items-center justify-between px-6 py-4 border-b border-cyan-500/15 bg-[#030810]/70 backdrop-blur-md">
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
                HD v2.6
              </span>
            </div>
            <div className="flex items-center space-x-3 text-[10px] font-mono text-cyan-400/70">
              <span className="flex items-center space-x-1">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                <span>AI CORE ONLINE</span>
              </span>
              <span className="hidden sm:inline-block border-r border-cyan-800/50 h-2.5" />
              <span className="hidden sm:inline-block">NEURAL SYSTEM ACTIVE</span>
              <span className="hidden sm:inline-block border-r border-cyan-800/50 h-2.5" />
              <span className="hidden md:inline-block">MEMORY READY</span>
              <span className="hidden md:inline-block border-r border-cyan-800/50 h-2.5" />
              <span className="hidden lg:inline-block">VOICE READY</span>
            </div>
          </div>
        </div>

        {/* Navigation - Desktop */}
        <nav className="hidden lg:flex items-center space-x-1 bg-cyan-950/20 p-1 rounded-lg border border-cyan-500/10">
          {navItems.map((item) => {
            const isActive = item === "CHAT";
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

        {/* Telemetry Stats & Mobile Menu Toggle */}
        <div className="flex items-center space-x-4">
          <div className="hidden xl:flex items-center space-x-4 text-[10px] font-mono text-cyan-400/60 border-l border-cyan-500/15 pl-4">
            <div>
              FPS: <span className="text-cyan-300">{hudStats.fps}</span>
            </div>
            <div>
              LATENCY: <span className="text-cyan-300">{hudStats.latency}ms</span>
            </div>
            <div>
              NODES: <span className="text-cyan-300">{hudStats.nodes}</span>
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

      {/* MOBILE MENU DRAWER */}
      {mobileMenuOpen && (
        <div className="lg:hidden absolute top-[65px] inset-x-0 z-30 bg-[#040c16]/95 border-b border-cyan-500/30 p-4 backdrop-blur-xl transition-all">
          <div className="grid grid-cols-3 gap-2">
            {navItems.map((item) => (
              <button
                key={item}
                className={`p-2 text-xs font-mono text-center rounded border ${
                  item === "CHAT"
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

      {/* MAIN BODY AREA */}
      <div className="relative z-20 flex-1 flex overflow-hidden">
        {/* LEFT CAPABILITY BAR (DESKTOP) */}
        <aside className="hidden xl:flex flex-col w-64 border-r border-cyan-500/15 bg-[#020710]/50 backdrop-blur-sm p-4 justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-cyan-500/15">
              <span className="text-[11px] font-mono tracking-widest text-cyan-400/80 uppercase">AI MODULES</span>
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            </div>
            <div className="space-y-1.5">
              {capabilities.map((cap) => {
                const isSelected = activeCapability === cap.name;
                return (
                  <button
                    key={cap.name}
                    onClick={() => setActiveCapability(cap.name)}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-xs font-mono transition-all duration-200 group text-left ${
                      isSelected
                        ? "bg-cyan-500/15 border border-cyan-500/40 text-white shadow-[0_0_12px_rgba(0,240,255,0.15)]"
                        : "border border-transparent text-cyan-400/60 hover:border-cyan-500/20 hover:text-cyan-200 hover:bg-cyan-950/30"
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          isSelected ? "bg-cyan-400 shadow-[0_0_8px_#00f0ff]" : "bg-cyan-900 group-hover:bg-cyan-500"
                        }`}
                      />
                      <span className="font-semibold tracking-wider">{cap.name}</span>
                    </div>
                    <span className="text-[9px] text-cyan-500/40 group-hover:text-cyan-400/70">{cap.desc}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* TELEMETRY CORNER HUD */}
          <div className="p-3 rounded-lg border border-cyan-500/15 bg-cyan-950/20 text-[10px] font-mono text-cyan-400/70 space-y-2">
            <div className="flex justify-between border-b border-cyan-500/10 pb-1">
              <span>SYSTEM LATITUDE</span>
              <span className="text-cyan-300">34°12'N 118°14'W</span>
            </div>
            <div className="flex justify-between border-b border-cyan-500/10 pb-1">
              <span>SECURITY PROTOCOL</span>
              <span className="text-emerald-400">KZ-ALPHA-ENCRYPTED</span>
            </div>
            <div className="flex justify-between">
              <span>MEMORY ALLOC</span>
              <span className="text-cyan-300">{hudStats.memory}% / 100%</span>
            </div>
          </div>
        </aside>

        {/* CENTRAL CHAT ENVIRONMENT */}
        <main className="flex-1 flex flex-col relative overflow-hidden bg-gradient-to-b from-transparent via-[#020812]/40 to-transparent">
          {/* TOP ORB PRESENCE CONTAINER */}
          <div className="relative flex flex-col items-center justify-center pt-6 pb-2 px-4 border-b border-cyan-500/10 bg-[#020810]/40 backdrop-blur-sm">
            {/* HOLOGRAPHIC AI CORE ORB */}
            <div className="relative w-28 h-28 flex items-center justify-center my-1 group">
              {/* Outer Rotating HUD Ring 1 */}
              <div className="absolute inset-0 rounded-full border border-dashed border-cyan-500/30 animate-[spin_20s_linear_infinite]" />

              {/* Outer Ring 2 (Reverse Spin) */}
              <div className="absolute inset-2 rounded-full border border-cyan-400/20 border-t-cyan-400 animate-[spin_12s_linear_infinite_reverse]" />

              {/* Core Wave Pulse */}
              <div
                className={`absolute inset-4 rounded-full bg-cyan-500/10 blur-md transition-all duration-500 ${
                  coreState === "thinking"
                    ? "scale-125 bg-purple-500/20 shadow-[0_0_30px_rgba(168,85,247,0.4)]"
                    : coreState === "speaking"
                    ? "scale-110 bg-cyan-400/30 shadow-[0_0_35px_rgba(0,240,255,0.5)] animate-pulse"
                    : coreState === "listening"
                    ? "scale-115 bg-emerald-500/30 shadow-[0_0_30px_rgba(16,185,129,0.4)]"
                    : "scale-100 shadow-[0_0_20px_rgba(0,240,255,0.2)]"
                }`}
              />

              {/* Inner Glowing Core */}
              <div className="relative z-10 flex flex-col items-center justify-center w-16 h-16 rounded-full bg-[#031322] border border-cyan-400/60 shadow-[inset_0_0_15px_rgba(0,240,255,0.3)]">
                <span className="font-extrabold text-xl tracking-tighter text-white drop-shadow-[0_0_8px_rgba(0,240,255,0.8)]">
                  KZ
                </span>
                <span className="text-[8px] font-mono tracking-widest text-cyan-400/80 -mt-1">AI</span>
              </div>

              {/* Orbiting Orbital Dots */}
              <div className="absolute w-full h-full animate-[spin_8s_linear_infinite]">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-300 shadow-[0_0_8px_#00f0ff] absolute top-0 left-1/2 -translate-x-1/2" />
              </div>
              <div className="absolute w-full h-full animate-[spin_14s_linear_infinite_reverse]">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 shadow-[0_0_8px_#818cf8] absolute bottom-1 left-1/2 -translate-x-1/2" />
              </div>
            </div>

            {/* AI Core Status Label */}
            <div className="flex items-center space-x-2 mt-1">
              <span className="text-xs font-mono font-bold tracking-widest text-cyan-200 uppercase">
                KING ZARRY AI CORE
              </span>
              <span
                className={`px-2 py-0.5 text-[9px] font-mono rounded-full border transition-all duration-300 ${
                  coreState === "thinking"
                    ? "bg-purple-950/60 text-purple-300 border-purple-500/50 shadow-[0_0_10px_rgba(168,85,247,0.3)]"
                    : coreState === "speaking"
                    ? "bg-cyan-950/60 text-cyan-300 border-cyan-500/50 shadow-[0_0_10px_rgba(0,240,255,0.3)]"
                    : coreState === "listening"
                    ? "bg-emerald-950/60 text-emerald-300 border-emerald-500/50 shadow-[0_0_10px_rgba(16,185,129,0.3)]"
                    : "bg-cyan-950/30 text-cyan-400/70 border-cyan-500/20"
                }`}
              >
                ● {coreState.toUpperCase()}
              </span>
            </div>
          </div>

          {/* MESSAGES LIST AREA */}
          <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 scrollbar-thin scrollbar-thumb-cyan-500/20 scrollbar-track-transparent">
            {messages.map((msg) => {
              const isAI = msg.role === "ai";
              return (
                <div key={msg.id} className={`flex flex-col ${isAI ? "items-start" : "items-end"} space-y-1`}>
                  {/* Sender Badge */}
                  <div className="flex items-center space-x-2 text-[10px] font-mono text-cyan-400/60 px-1">
                    <span>{isAI ? "KING ZARRY AI" : "KING ZARRY"}</span>
                    <span>•</span>
                    <span>{msg.timestamp}</span>
                  </div>

                  {/* Message Hologram Container */}
                  <div
                    className={`relative max-w-2xl rounded-xl p-4 transition-all duration-300 backdrop-blur-md ${
                      isAI
                        ? "bg-[#041220]/80 border border-cyan-500/30 text-cyan-50 shadow-[0_4px_20px_rgba(0,240,255,0.08)] rounded-tl-none"
                        : "bg-[#0b1929]/70 border border-cyan-400/20 text-white shadow-[0_4px_15px_rgba(0,0,0,0.3)] rounded-tr-none"
                    }`}
                  >
                    {/* Corner HUD Accent Elements for AI */}
                    {isAI && (
                      <>
                        <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-cyan-400" />
                        <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-cyan-400" />
                        <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-cyan-400" />
                        <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-cyan-400" />
                      </>
                    )}

                    {/* Message Content */}
                    <p className="text-sm sm:text-base leading-relaxed tracking-wide font-sans">{msg.text}</p>

                    {/* AI Message Footer Tag */}
                    {isAI && msg.status && (
                      <div className="mt-3 pt-2 border-t border-cyan-500/10 flex items-center justify-between text-[9px] font-mono text-cyan-400/60">
                        <span className="tracking-widest">{msg.status}</span>
                        <span className="px-1.5 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/20 text-cyan-300">
                          {msg.capability || "KZ AI"}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Thinking / Processing Loading State */}
            {coreState === "thinking" && (
              <div className="flex items-center space-x-3 text-xs font-mono text-purple-300/80 bg-purple-950/20 border border-purple-500/30 p-3 rounded-lg w-fit animate-pulse">
                <div className="w-2 h-2 rounded-full bg-purple-400 animate-ping" />
                <span>NEURAL CORE ANALYZING QUERY & SYNTHESIZING DATA...</span>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* COMPOSER / VOICE INTERFACE */}
          <div className="relative z-20 p-4 border-t border-cyan-500/15 bg-[#020710]/80 backdrop-blur-md">
            {isVoiceActive ? (
              /* VOICE TRANSFORMED INTERFACE */
              <div className="flex flex-col items-center justify-center p-4 rounded-xl border border-emerald-500/40 bg-emerald-950/20 shadow-[0_0_25px_rgba(16,185,129,0.15)] space-y-3">
                <div className="flex items-center space-x-3 text-emerald-400 font-mono text-xs tracking-widest">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                  <span>ACOUSTIC SPEECH RECOGNITION ACTIVE • LISTENING...</span>
                </div>

                {/* Animated Waveform Bars */}
                <div className="flex items-center justify-center space-x-1.5 h-10 w-full max-w-xs">
                  {[...Array(16)].map((_, i) => (
                    <div
                      key={i}
                      className="w-1.5 bg-emerald-400/80 rounded-full animate-pulse"
                      style={{
                        height: `${Math.floor(20 + Math.random() * 80)}%`,
                        animationDuration: `${0.4 + (i % 5) * 0.2}s`,
                      }}
                    />
                  ))}
                </div>

                <div className="flex items-center space-x-4 pt-1">
                  <button
                    onClick={toggleVoiceMode}
                    className="px-4 py-1.5 rounded-md text-xs font-mono text-red-400 border border-red-500/30 bg-red-950/30 hover:bg-red-900/40 transition"
                  >
                    CANCEL VOICE
                  </button>
                  <button
                    onClick={() => {
                      setInput("Voice command captured and transmitted.");
                      setIsVoiceActive(false);
                      setCoreState("idle");
                    }}
                    className="px-4 py-1.5 rounded-md text-xs font-mono text-emerald-300 border border-emerald-500/50 bg-emerald-900/40 hover:bg-emerald-800/50 transition"
                  >
                    SEND AUDIO STREAM
                  </button>
                </div>
              </div>
            ) : (
              /* STANDARD COMMAND COMPOSER */
              <form onSubmit={handleSend} className="relative flex items-center space-x-2">
                <div className="relative flex-1 flex items-center bg-[#051322]/80 rounded-xl border border-cyan-500/30 focus-within:border-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.05)] transition-all">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Talk to KING ZARRY AI..."
                    className="w-full py-3.5 px-4 bg-transparent text-sm text-white placeholder-cyan-500/40 focus:outline-none font-sans"
                  />

                  {/* Quick Action Controls */}
                  <div className="flex items-center space-x-1 pr-2">
                    {/* Image Upload */}
                    <button
                      type="button"
                      title="Upload Image"
                      className="p-2 text-cyan-400/60 hover:text-cyan-200 transition"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                        />
                      </svg>
                    </button>

                    {/* File Attachment */}
                    <button
                      type="button"
                      title="Attach File"
                      className="p-2 text-cyan-400/60 hover:text-cyan-200 transition"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                        />
                      </svg>
                    </button>

                    {/* Mic Button */}
                    <button
                      type="button"
                      onClick={toggleVoiceMode}
                      title="Voice Mode"
                      className="p-2 text-cyan-400 hover:text-emerald-300 transition"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 016 0v6a3 3 0 01-3 3z"
                        />
                      </svg>
                    </button>
                  </div>
                </div>

                {/* Send Button */}
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className={`px-5 py-3.5 rounded-xl text-xs font-mono font-bold tracking-wider transition-all duration-300 flex items-center justify-center space-x-1 ${
                    input.trim()
                      ? "bg-cyan-500 text-black shadow-[0_0_20px_rgba(0,240,255,0.4)] hover:bg-cyan-400 active:scale-95"
                      : "bg-cyan-950/40 text-cyan-500/30 border border-cyan-500/10 cursor-not-allowed"
                  }`}
                >
                  <span>EXECUTE</span>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </button>
              </form>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
