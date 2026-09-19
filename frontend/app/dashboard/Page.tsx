"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://fast-production-0eba.up.railway.app";

type Message = {
  sender: "AI" | "USER";
  text: string;
};

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState("Dashboard");
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const [messages, setMessages] = useState<Message[]>([
    {
      sender: "AI",
      text: "Greetings, King Zarry. I am online and ready. What system or market segment shall we analyze today?",
    },
  ]);

  const [inputVal, setInputVal] = useState("");
  const [time, setTime] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [authError, setAuthError] = useState(false);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();

      setTime(
        now.toLocaleTimeString("en-US", {
          hour12: false,
        })
      );
    };

    updateTime();

    const timer = setInterval(updateTime, 1000);

    return () => clearInterval(timer);
  }, []);

  const handleNavigation = (label: string) => {
    setActiveTab(label);
    setIsMobileMenuOpen(false);
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();

    const userMessage = inputVal.trim();

    if (!userMessage || isSending) return;

    setInputVal("");
    setAuthError(false);
    setIsSending(true);

    setMessages((prev) => [
      ...prev,
      {
        sender: "USER",
        text: userMessage,
      },
    ]);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (response.status === 401) {
        setAuthError(true);

        setMessages((prev) => [
          ...prev,
          {
            sender: "AI",
            text: "SECURE SESSION REQUIRED. Please sign in before using KING ZARRY AI.",
          },
        ]);

        return;
      }

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            data?.error ||
            data?.message ||
            "AI CORE REQUEST FAILED"
        );
      }

      const aiReply =
        data?.reply ??
        data?.response ??
        data?.message ??
        "AI CORE returned no response.";

      setMessages((prev) => [
        ...prev,
        {
          sender: "AI",
          text:
            typeof aiReply === "string"
              ? aiReply
              : JSON.stringify(aiReply),
        },
      ]);
    } catch (error) {
      console.error("Dashboard AI error:", error);

      setMessages((prev) => [
        ...prev,
        {
          sender: "AI",
          text:
            error instanceof Error
              ? `AI CORE ERROR: ${error.message}`
              : "AI CORE CONNECTION FAILED. Please try again.",
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const navigationItems = [
    { label: "Dashboard", icon: "⌂", href: "/dashboard" },
    { label: "AI Chat", icon: "◉", href: "/chat" },
    { label: "Signals", icon: "◈", href: "/signals" },
    { label: "Markets", icon: "◌", href: "/markets" },
    { label: "News", icon: "◇", href: "/news" },
    { label: "Alerts", icon: "◉", href: "/alerts" },
    { label: "History", icon: "▣", href: "/history" },
  ];

  return (
    <div className="min-h-screen bg-[#05070c] text-[#c0e0ff] font-sans selection:bg-[#00f0ff]/30 selection:text-white relative overflow-x-hidden">
      {/* Background Grid */}
      <div
        className="fixed inset-0 pointer-events-none opacity-20"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(0, 240, 255, 0.08) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(0, 240, 255, 0.08) 1px, transparent 1px)
          `,
          backgroundSize: "40px 40px",
        }}
      />

      <div className="fixed -top-40 -left-40 w-96 h-96 bg-[#00f0ff]/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="fixed -bottom-40 -right-40 w-96 h-96 bg-[#7000ff]/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="flex h-screen overflow-hidden relative z-10">

        {/* LEFT SIDEBAR */}
        <aside
          className={`
            fixed md:relative z-30 h-full w-64 bg-[#080c14]/80 backdrop-blur-md
            border-r border-[#00f0ff]/20 flex flex-col justify-between
            transition-transform duration-300 ease-in-out
            ${
              isMobileMenuOpen
                ? "translate-x-0"
                : "-translate-x-full md:translate-x-0"
            }
          `}
        >
          {/* Header */}
          <div className="p-5 border-b border-[#00f0ff]/15">
            <div className="flex items-center justify-between">
              <h1 className="font-extrabold tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-white via-[#00f0ff] to-[#0099ff] text-lg">
                KING ZARRY AI
              </h1>

              <button
                onClick={() => setIsMobileMenuOpen(false)}
                className="md:hidden text-[#00f0ff] hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="flex items-center gap-2 mt-2 text-[10px] tracking-widest text-[#00f0ff] uppercase">
              <span className="w-2 h-2 rounded-full bg-[#00f0ff] animate-pulse shadow-[0_0_8px_#00f0ff]" />
              SYSTEM ONLINE
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navigationItems.map((item) => {
              const active = activeTab === item.label;

              if (item.label === "Dashboard") {
                return (
                  <button
                    key={item.label}
                    onClick={() => handleNavigation(item.label)}
                    className={`
                      w-full flex items-center gap-3 px-4 py-2.5 rounded
                      text-xs font-mono tracking-wider transition-all
                      ${
                        active
                          ? "bg-[#00f0ff]/10 text-[#00f0ff] border-l-2 border-[#00f0ff] shadow-[inset_0_0_15px_rgba(0,240,255,0.15)]"
                          : "text-[#88a0c0] hover:text-[#00f0ff] hover:bg-[#00f0ff]/5"
                      }
                    `}
                  >
                    <span className="text-sm">{item.icon}</span>
                    {item.label}
                  </button>
                );
              }

              return (
                <Link
                  key={item.label}
                  href={item.href}
                  onClick={() => handleNavigation(item.label)}
                  className={`
                    w-full flex items-center gap-3 px-4 py-2.5 rounded
                    text-xs font-mono tracking-wider transition-all
                    ${
                      active
                        ? "bg-[#00f0ff]/10 text-[#00f0ff] border-l-2 border-[#00f0ff] shadow-[inset_0_0_15px_rgba(0,240,255,0.15)]"
                        : "text-[#88a0c0] hover:text-[#00f0ff] hover:bg-[#00f0ff]/5"
                    }
                  `}
                >
                  <span className="text-sm">{item.icon}</span>
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-[#00f0ff]/15">
            <Link
              href="/settings"
              className="w-full flex items-center gap-3 px-4 py-2 text-xs font-mono text-[#88a0c0] hover:text-[#00f0ff] transition-colors"
            >
              <span>⚙</span>
              Settings
            </Link>
          </div>
        </aside>

        {/* MAIN CONTENT */}
        <div className="flex-1 flex flex-col h-full overflow-y-auto relative">

          {/* TOP BAR */}
          <header className="sticky top-0 z-20 bg-[#05070c]/90 backdrop-blur-md border-b border-[#00f0ff]/15 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setIsMobileMenuOpen(true)}
                className="md:hidden text-[#00f0ff] focus:outline-none"
              >
                ☰
              </button>

              <div>
                <h2 className="text-sm md:text-base font-bold tracking-widest text-white">
                  GOOD EVENING,{" "}
                  <span className="text-[#00f0ff]">KING ZARRY</span>
                </h2>

                <p className="text-[10px] font-mono text-[#00f0ff]/70 tracking-wider">
                  AI CORE ONLINE • {time || "SYS_CLK"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">

              <div className="hidden sm:flex items-center gap-2 px-3 py-1 bg-[#00f0ff]/5 border border-[#00f0ff]/20 rounded text-[11px] font-mono text-[#00f0ff]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#00f0ff] animate-ping" />
                SECURE CONNECTION
              </div>

              <button className="relative p-2 bg-[#00f0ff]/5 border border-[#00f0ff]/20 rounded hover:border-[#00f0ff] transition-all text-[#00f0ff]">
                🔔
                <span className="absolute top-1 right-1 w-2 h-2 bg-[#00f0ff] rounded-full" />
              </button>

              <div className="w-8 h-8 rounded border border-[#00f0ff] bg-gradient-to-br from-[#00f0ff]/30 to-transparent flex items-center justify-center font-mono font-bold text-xs text-[#00f0ff] shadow-[0_0_10px_rgba(0,240,255,0.3)]">
                KZ
              </div>
            </div>
          </header>

          {/* DASHBOARD BODY */}
          <main className="p-4 md:p-6 space-y-6 max-w-[1600px] mx-auto w-full">

            {/* TOP ROW */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">

              {/* CENTRAL AI CORE */}
              <div className="lg:col-span-7 bg-[#080c14]/60 backdrop-blur-md border border-[#00f0ff]/20 rounded-lg p-6 relative overflow-hidden flex flex-col justify-between group shadow-[0_0_20px_rgba(0,0,0,0.5)]">

                <div className="flex justify-between items-start z-10">
                  <div>
                    <span className="text-[10px] font-mono tracking-widest text-[#00f0ff] bg-[#00f0ff]/10 px-2 py-0.5 rounded border border-[#00f0ff]/30">
                      PRIMARY NODE
                    </span>

                    <h3 className="text-lg font-bold text-white mt-1">
                      NEXUS AI CORE
                    </h3>
                  </div>

                  <span className="text-xs font-mono text-[#00f0ff]/60">
                    SYS_VER 4.0.9
                  </span>
                </div>

                {/* CORE VISUALIZER */}
                <div className="relative my-8 flex items-center justify-center">
                  <div className="relative w-64 h-64 md:w-80 md:h-80 flex items-center justify-center">

                    <svg
                      className="absolute inset-0 w-full h-full animate-[spin_20s_linear_infinite]"
                      viewBox="0 0 200 200"
                    >
                      <circle
                        cx="100"
                        cy="100"
                        r="90"
                        fill="none"
                        stroke="#00f0ff"
                        strokeWidth="0.5"
                        strokeDasharray="4 8"
                        opacity="0.4"
                      />

                      <circle
                        cx="100"
                        cy="100"
                        r="75"
                        fill="none"
                        stroke="#00f0ff"
                        strokeWidth="1"
                        strokeDasharray="40 10 5 10"
                        opacity="0.6"
                      />
                    </svg>

                    <svg
                      className="absolute inset-0 w-full h-full animate-[spin_12s_linear_infinite_reverse]"
                      viewBox="0 0 200 200"
                    >
                      <circle
                        cx="100"
                        cy="100"
                        r="60"
                        fill="none"
                        stroke="#00f0ff"
                        strokeWidth="1.5"
                        strokeDasharray="15 30 45 10"
                        opacity="0.8"
                      />

                      <circle
                        cx="100"
                        cy="100"
                        r="45"
                        fill="none"
                        stroke="#7000ff"
                        strokeWidth="1"
                        strokeDasharray="10 15"
                        opacity="0.5"
                      />
                    </svg>

                    <svg
                      className="absolute inset-0 w-full h-full animate-[spin_6s_linear_infinite]"
                      viewBox="0 0 200 200"
                    >
                      <line
                        x1="10"
                        y1="100"
                        x2="190"
                        y2="100"
                        stroke="#00f0ff"
                        strokeWidth="0.5"
                        opacity="0.2"
                      />

                      <line
                        x1="100"
                        y1="10"
                        x2="100"
                        y2="190"
                        stroke="#00f0ff"
                        strokeWidth="0.5"
                        opacity="0.2"
                      />
                    </svg>

                    <div className="relative z-10 w-28 h-28 md:w-32 md:h-32 rounded-full bg-gradient-to-br from-[#00f0ff]/20 via-[#05070c] to-[#7000ff]/30 border border-[#00f0ff] flex flex-col items-center justify-center shadow-[0_0_30px_rgba(0,240,255,0.4)] animate-pulse">
                      <span className="text-2xl md:text-3xl font-black tracking-tighter text-white drop-shadow-[0_0_10px_#00f0ff]">
                        KZ
                      </span>

                      <span className="text-[9px] font-mono text-[#00f0ff] tracking-widest mt-1">
                        AI CORE
                      </span>
                    </div>
                  </div>
                </div>

                {/* TELEMETRY */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 z-10 border-t border-[#00f0ff]/15 pt-4">
                  {[
                    {
                      label: "NEURAL ENGINE",
                      status: "ONLINE",
                    },
                    {
                      label: "MEMORY",
                      status: "READY",
                    },
                    {
                      label: "ANALYSIS",
                      status: "ACTIVE",
                    },
                    {
                      label: "SIGNAL ENGINE",
                      status: "READY",
                    },
                  ].map((item, idx) => (
                    <div
                      key={idx}
                      className="bg-[#00f0ff]/5 border border-[#00f0ff]/10 p-2 rounded text-center"
                    >
                      <div className="text-[9px] font-mono text-[#88a0c0] tracking-wider">
                        {item.label}
                      </div>

                      <div className="text-xs font-mono font-bold text-[#00f0ff] mt-0.5">
                        {item.status}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* AI ASSISTANT */}
              <div className="lg:col-span-5 bg-[#080c14]/60 backdrop-blur-md border border-[#00f0ff]/20 rounded-lg p-5 flex flex-col justify-between relative shadow-[0_0_20px_rgba(0,0,0,0.5)]">

                <div className="flex items-center justify-between border-b border-[#00f0ff]/15 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[#00f0ff] animate-ping" />

                    <h3 className="font-bold text-white text-sm tracking-wider">
                      KING ZARRY AI
                    </h3>
                  </div>

                  <span className="text-[10px] font-mono text-[#00f0ff] bg-[#00f0ff]/10 px-2 py-0.5 rounded border border-[#00f0ff]/20">
                    {isSending ? "● THINKING" : "● LISTENING"}
                  </span>
                </div>

                {/* MESSAGE LOG */}
                <div className="flex-1 my-4 space-y-3 overflow-y-auto max-h-[280px] pr-2 font-mono text-xs">

                  {messages.map((msg, index) => (
                    <div
                      key={index}
                      className={`p-3 rounded border ${
                        msg.sender === "AI"
                          ? "bg-[#00f0ff]/5 border-[#00f0ff]/20 text-[#c0e0ff]"
                          : "bg-[#7000ff]/10 border-[#7000ff]/30 text-white ml-6"
                      }`}
                    >
                      <div className="text-[9px] text-[#00f0ff]/70 mb-1 font-bold">
                        {msg.sender === "AI"
                          ? "⚡ KING ZARRY AI"
                          : "👤 USER"}
                      </div>

                      <div className="whitespace-pre-wrap break-words">
                        {msg.text}
                      </div>
                    </div>
                  ))}

                  {isSending && (
                    <div className="p-3 rounded border bg-[#00f0ff]/5 border-[#00f0ff]/20 text-[#00f0ff]">
                      <div className="text-[9px] mb-1 font-bold">
                        ⚡ KING ZARRY AI
                      </div>

                      <div className="flex items-center gap-1">
                        <span className="animate-pulse">●</span>
                        <span
                          className="animate-pulse"
                          style={{ animationDelay: "150ms" }}
                        >
                          ●
                        </span>
                        <span
                          className="animate-pulse"
                          style={{ animationDelay: "300ms" }}
                        >
                          ●
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* AUTH WARNING */}
                {authError && (
                  <div className="mb-3 rounded border border-red-400/30 bg-red-400/5 p-3 text-[10px] font-mono text-red-300">
                    <div className="mb-2">
                      🔐 AUTHENTICATION REQUIRED
                    </div>

                    <Link
                      href="/login"
                      className="inline-block border border-[#00f0ff]/40 bg-[#00f0ff]/10 px-3 py-1.5 text-[#00f0ff] hover:bg-[#00f0ff]/20 transition-all"
                    >
                      SIGN IN TO SYSTEM
                    </Link>
                  </div>
                )}

                {/* INPUT */}
                <form
                  onSubmit={handleSendMessage}
                  className="flex gap-2 pt-2 border-t border-[#00f0ff]/15"
                >
                  <input
                    type="text"
                    value={inputVal}
                    onChange={(e) => setInputVal(e.target.value)}
                    disabled={isSending}
                    placeholder={
                      isSending
                        ? "AI CORE PROCESSING..."
                        : "Ask your AI anything..."
                    }
                    className="flex-1 bg-[#00f0ff]/5 border border-[#00f0ff]/20 rounded px-3 py-2 text-xs font-mono text-white placeholder-[#88a0c0]/50 focus:outline-none focus:border-[#00f0ff] disabled:opacity-50"
                  />

                  <button
                    type="submit"
                    disabled={isSending || !inputVal.trim()}
                    className="bg-[#00f0ff]/20 hover:bg-[#00f0ff]/30 border border-[#00f0ff] text-[#00f0ff] px-4 py-2 rounded text-xs font-mono font-bold transition-all shadow-[0_0_10px_rgba(0,240,255,0.2)] disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {isSending ? "..." : "SEND"}
                  </button>
                </form>
              </div>
            </div>

            {/* MARKET INTELLIGENCE */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

              <div className="lg:col-span-8 bg-[#080c14]/60 backdrop-blur-md border border-[#00f0ff]/20 rounded-lg p-5">

                <div className="flex justify-between items-center mb-4 pb-2 border-b border-[#00f0ff]/15">
                  <h3 className="text-sm font-bold tracking-widest text-white">
                    MARKET INTELLIGENCE
                  </h3>

                  <span className="text-[10px] font-mono text-[#88a0c0]">
                    DEMO MODE ONLY
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

                  {[
                    {
                      pair: "BTC/USD",
                      structure: "BULLISH BREAKOUT",
                      momentum: "HIGH (+8.4)",
                      volatility: "EXPANDING",
                      status: "OPTIMAL",
                    },
                    {
                      pair: "ETH/USD",
                      structure: "CONSOLIDATION",
                      momentum: "NEUTRAL (0.0)",
                      volatility: "COMPRESSED",
                      status: "WATCHING",
                    },
                    {
                      pair: "SOL/USD",
                      structure: "IMPULSE WAVE",
                      momentum: "STRONG (+12.1)",
                      volatility: "HIGH",
                      status: "ACTIVE",
                    },
                    {
                      pair: "XAU/USD",
                      structure: "RANGE BOUND",
                      momentum: "SLIGHT BEAR (-1.2)",
                      volatility: "LOW",
                      status: "STABLE",
                    },
                  ].map((item, idx) => (
                    <div
                      key={idx}
                      className="bg-[#00f0ff]/5 border border-[#00f0ff]/15 p-4 rounded hover:border-[#00f0ff]/40 transition-all"
                    >
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-mono font-bold text-sm text-white">
                          {item.pair}
                        </span>

                        <span className="text-[10px] font-mono text-[#00f0ff] px-1.5 py-0.5 bg-[#00f0ff]/10 rounded border border-[#00f0ff]/30">
                          {item.status}
                        </span>
                      </div>

                      <div className="space-y-1 font-mono text-[11px]">
                        <div className="flex justify-between text-[#88a0c0]">
                          <span>STRUCTURE:</span>
                          <span className="text-white">
                            {item.structure}
                          </span>
                        </div>

                        <div className="flex justify-between text-[#88a0c0]">
                          <span>MOMENTUM:</span>
                          <span className="text-[#00f0ff]">
                            {item.momentum}
                          </span>
                        </div>

                        <div className="flex justify-between text-[#88a0c0]">
                          <span>VOLATILITY:</span>
                          <span className="text-white">
                            {item.volatility}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}

                </div>
              </div>

              {/* SIGNAL ENGINE */}
              <div className="lg:col-span-4 bg-[#080c14]/60 backdrop-blur-md border border-[#00f0ff]/20 rounded-lg p-5 flex flex-col justify-between">

                <div>
                  <div className="flex justify-between items-center mb-4 pb-2 border-b border-[#00f0ff]/15">
                    <h3 className="text-sm font-bold tracking-widest text-white">
                      AI SIGNAL ENGINE
                    </h3>

                    <span className="text-[10px] font-mono text-[#00f0ff] animate-pulse">
                      DEMO
                    </span>
                  </div>

                  <div className="bg-[#00f0ff]/5 border border-[#00f0ff]/30 p-4 rounded space-y-3 font-mono text-xs">

                    <div className="flex justify-between items-center">
                      <span className="text-base font-bold text-white">
                        BTC/USD
                      </span>

                      <span className="text-[10px] text-[#88a0c0]">
                        TIMEFRAME: 15M
                      </span>
                    </div>

                    <div className="flex items-center justify-between py-1 px-3 bg-[#00f0ff]/10 rounded border border-[#00f0ff]/40">
                      <span className="text-[#88a0c0]">
                        ACTION:
                      </span>

                      <span className="text-sm font-bold text-[#00f0ff]">
                        DEMO SIGNAL
                      </span>
                    </div>

                    <div className="space-y-1 text-[11px]">
                      <div className="flex justify-between">
                        <span className="text-[#88a0c0]">
                          ENTRY ZONE:
                        </span>

                        <span className="text-white">
                          DEMO DATA
                        </span>
                      </div>

                      <div className="flex justify-between">
                        <span className="text-[#88a0c0]">
                          STOP LOSS:
                        </span>

                        <span className="text-red-400">
                          DEMO DATA
                        </span>
                      </div>

                      <div className="flex justify-between">
                        <span className="text-[#88a0c0]">
                          TARGETS:
                        </span>

                        <span className="text-[#00f0ff]">
                          DEMO DATA
                        </span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-[#00f0ff]/15">

                      <div className="flex justify-between text-[10px] mb-1">
                        <span className="text-[#88a0c0]">
                          AI STATUS
                        </span>

                        <span className="text-[#00f0ff]">
                          READY
                        </span>
                      </div>

                      <div className="w-full bg-[#00f0ff]/10 rounded-full h-1.5 overflow-hidden">
                        <div className="bg-[#00f0ff] h-full rounded-full w-full shadow-[0_0_8px_#00f0ff]" />
                      </div>

                    </div>
                  </div>
                </div>

                <div className="mt-4 text-[9px] font-mono text-[#88a0c0]/60 text-center tracking-wider uppercase">
                  Demonstration Data Only • Not Financial Advice
                </div>
              </div>
            </div>

            {/* ACTIVITY LOG */}
            <div className="bg-[#080c14]/60 backdrop-blur-md border border-[#00f0ff]/20 rounded-lg p-5">

              <h3 className="text-sm font-bold tracking-widest text-white mb-3">
                SYSTEM ACTIVITY LOG
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 font-mono text-xs">

                {[
                  {
                    module: "AI CORE",
                    log: "Dashboard initialized",
                    time: "LIVE",
                  },
                  {
                    module: "MEMORY",
                    log: "Web session ready",
                    time: "LIVE",
                  },
                  {
                    module: "AI CHAT",
                    log: "Secure API available",
                    time: "READY",
                  },
                  {
                    module: "SYSTEM",
                    log: "All parameters operational",
                    time: "STABLE",
                  },
                ].map((act, i) => (
                  <div
                    key={i}
                    className="bg-[#00f0ff]/5 border border-[#00f0ff]/10 p-2.5 rounded flex items-center justify-between"
                  >
                    <div>
                      <span className="text-[10px] text-[#00f0ff] font-bold block">
                        {act.module}
                      </span>

                      <span className="text-white text-[11px]">
                        {act.log}
                      </span>
                    </div>

                    <span className="text-[9px] text-[#88a0c0]">
                      {act.time}
                    </span>
                  </div>
                ))}

              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
