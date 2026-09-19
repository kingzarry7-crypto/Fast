"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

type MessageRole = "ai" | "user" | "system";

interface Message {
  id: string;
  role: MessageRole;
  text: string;
  timestamp: string;
  status?: string;
  capability?: string;
}

interface ChatResponse {
  reply?: string;
  response?: string;
  message?: string;
  detail?: string;
}

interface AuthResponse {
  user?: {
    id?: string;
    email?: string;
    name?: string;
  };
  authenticated?: boolean;
  detail?: string;
}

type AICoreState =
  | "connecting"
  | "idle"
  | "thinking"
  | "speaking"
  | "listening"
  | "error";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://fast-production-0eba.up.railway.app";

export default function KingZarryChatPage() {
  const router = useRouter();

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [coreState, setCoreState] =
    useState<AICoreState>("connecting");

  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [activeCapability, setActiveCapability] =
    useState<string>("AI");

  const [mobileMenuOpen, setMobileMenuOpen] =
    useState(false);

  const [connectionError, setConnectionError] =
    useState<string | null>(null);

  const [currentUser, setCurrentUser] = useState<{
    name?: string;
    email?: string;
  } | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  /*
   * REAL SESSION CHECK
   *
   * The chat requires the real backend session cookie.
   */
  useEffect(() => {
    let cancelled = false;

    const checkSession = async () => {
      try {
        setCoreState("connecting");

        const response = await fetch(
          `${API_BASE_URL}/api/auth/me`,
          {
            method: "GET",
            credentials: "include",
            cache: "no-store",
          }
        );

        let data: AuthResponse = {};

        try {
          data = await response.json();
        } catch {
          data = {};
        }

        if (cancelled) return;

        if (response.status === 401) {
          router.replace("/login");
          return;
        }

        if (!response.ok) {
          throw new Error(
            data.detail ||
              "Unable to verify KING ZARRY AI session."
          );
        }

        setCurrentUser(data.user || null);
        setConnectionError(null);
        setCoreState("idle");
      } catch (error) {
        if (cancelled) return;

        console.error(
          "KING ZARRY AI session error:",
          error
        );

        setConnectionError(
          error instanceof Error
            ? error.message
            : "Unable to connect to KING ZARRY AI backend."
        );

        setCoreState("error");
      }
    };

    checkSession();

    return () => {
      cancelled = true;
    };
  }, [router]);

  /*
   * AUTO SCROLL
   */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
    });
  }, [messages, coreState]);

  /*
   * TIME
   */
  const getCurrentTime = () => {
    const now = new Date();

    return `${now
      .getHours()
      .toString()
      .padStart(2, "0")}:${now
      .getMinutes()
      .toString()
      .padStart(2, "0")}:${now
      .getSeconds()
      .toString()
      .padStart(2, "0")}`;
  };

  /*
   * REAL AI CHAT
   */
  const handleSend = async (
    e?: React.FormEvent<HTMLFormElement>
  ) => {
    e?.preventDefault();

    const userMsgText = input.trim();

    if (
      !userMsgText ||
      coreState === "thinking" ||
      coreState === "connecting"
    ) {
      return;
    }

    const timeStr = getCurrentTime();

    const newUserMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      text: userMsgText,
      timestamp: timeStr,
    };

    setMessages((prev) => [...prev, newUserMsg]);
    setInput("");
    setConnectionError(null);
    setCoreState("thinking");

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/chat`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            message: userMsgText,
          }),
        }
      );

      let data: ChatResponse = {};

      try {
        data = await response.json();
      } catch {
        data = {};
      }

      /*
       * AUTHENTICATION
       */
      if (response.status === 401) {
        setCoreState("error");

        setMessages((prev) => [
          ...prev,
          {
            id: `auth-${Date.now()}`,
            role: "ai",
            text:
              "Your KING ZARRY AI session has expired. Please sign in again.",
            timestamp: getCurrentTime(),
            status:
              "SECURITY MODULE • AUTHENTICATION REQUIRED",
            capability: "SECURITY",
          },
        ]);

        setTimeout(() => {
          router.replace("/login");
        }, 800);

        return;
      }

      /*
       * FORBIDDEN
       */
      if (response.status === 403) {
        throw new Error(
          data.detail ||
            "Access denied by KING ZARRY AI security."
        );
      }

      /*
       * SERVER / API ERROR
       */
      if (!response.ok) {
        throw new Error(
          data.detail ||
            data.reply ||
            data.response ||
            data.message ||
            `KING ZARRY AI backend returned HTTP ${response.status}.`
        );
      }

      /*
       * REAL RESPONSE
       */
      const reply =
        data.reply ||
        data.response ||
        data.message;

      if (!reply) {
        throw new Error(
          "The KING ZARRY AI backend returned an empty response."
        );
      }

      setCoreState("speaking");

      setMessages((prev) => [
        ...prev,
        {
          id: `ai-${Date.now()}`,
          role: "ai",
          text: reply,
          timestamp: getCurrentTime(),
          status: "AI CORE • RESPONSE RECEIVED",
          capability: activeCapability || "AI",
        },
      ]);

      setConnectionError(null);

      window.setTimeout(() => {
        setCoreState("idle");
      }, 900);
    } catch (error) {
      console.error(
        "KING ZARRY AI chat error:",
        error
      );

      const errorMessage =
        error instanceof Error
          ? error.message
          : "Unable to reach KING ZARRY AI backend.";

      setConnectionError(errorMessage);
      setCoreState("error");

      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "ai",
          text: errorMessage,
          timestamp: getCurrentTime(),
          status: "AI CORE • BACKEND ERROR",
          capability: "SYSTEM",
        },
      ]);
    }
  };

  /*
   * VOICE UI
   *
   * This only activates the voice interface.
   * It does not pretend an audio stream was transmitted.
   */
  const toggleVoiceMode = () => {
    if (isVoiceActive) {
      setIsVoiceActive(false);
      setCoreState("idle");
      return;
    }

    setIsVoiceActive(true);
    setCoreState("listening");
  };

  /*
   * CAPABILITIES
   */
  const capabilities = [
    { name: "AI", desc: "Core Intelligence" },
    { name: "VISION", desc: "Spatial Analysis" },
    { name: "VOICE", desc: "Acoustic Interface" },
    { name: "MEMORY", desc: "Neural Context" },
    { name: "REASONING", desc: "Cognitive Processing" },
    { name: "AGENTS", desc: "Autonomous Units" },
    { name: "TOOLS", desc: "System Integrations" },
    { name: "MARKETS", desc: "Market Data" },
    { name: "SIGNALS", desc: "Pattern Detection" },
    { name: "NEWS", desc: "External Information" },
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
    "MEMORY",
  ];

  /*
   * CORE LABEL
   */
  const coreStatusLabel = {
    connecting: "CONNECTING",
    idle: "READY",
    thinking: "THINKING",
    speaking: "RESPONDING",
    listening: "LISTENING",
    error: "ERROR",
  }[coreState];

  return (
    <div className="relative w-full h-screen bg-[#03060a] text-cyan-100 font-sans overflow-hidden flex flex-col selection:bg-cyan-500 selection:text-black">

      {/* BACKGROUND */}

      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#072438] via-[#020b14] to-[#010408] pointer-events-none" />

      <div className="absolute inset-0 bg-[linear-gradient(to_right,#091a2815_1px,transparent_1px),linear-gradient(to_bottom,#091a2815_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />

      <div className="absolute inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,240,255,0.015)_3px,transparent_4px)] pointer-events-none z-10" />

      <div className="absolute top-[-10%] left-[20%] w-[500px] h-[500px] bg-cyan-600/10 rounded-full blur-[120px] pointer-events-none" />

      <div className="absolute bottom-[-10%] right-[20%] w-[600px] h-[600px] bg-indigo-600/10 rounded-full blur-[140px] pointer-events-none" />

      {/* HEADER */}

      <header className="relative z-20 flex items-center justify-between px-6 py-4 border-b border-cyan-500/15 bg-[#030810]/70 backdrop-blur-md">

        <div className="flex items-center space-x-4">

          <div className="relative flex items-center justify-center w-10 h-10 rounded-lg border border-cyan-500/40 bg-cyan-950/30 text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.2)]">

            <span className="font-extrabold text-lg tracking-wider">
              KZ
            </span>

            <span className="absolute -top-1 -right-1 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500" />
            </span>

          </div>

          <div>

            <div className="flex items-center space-x-2">

              <h1 className="text-base font-bold tracking-widest text-white uppercase">
                KING ZARRY AI
              </h1>

              <span className="px-1.5 py-0.5 text-[9px] font-mono tracking-wider text-cyan-400 border border-cyan-500/30 bg-cyan-950/40 rounded">
                CORE
              </span>

            </div>

            <div className="flex items-center space-x-3 text-[10px] font-mono text-cyan-400/70">

              <span className="flex items-center space-x-1">

                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    coreState === "error"
                      ? "bg-red-400"
                      : coreState === "thinking"
                      ? "bg-purple-400 animate-pulse"
                      : "bg-cyan-400 animate-pulse"
                  }`}
                />

                <span>
                  AI CORE {coreStatusLabel}
                </span>

              </span>

              <span className="hidden sm:inline-block border-r border-cyan-800/50 h-2.5" />

              <span className="hidden sm:inline-block">
                REAL BACKEND
              </span>

              <span className="hidden md:inline-block border-r border-cyan-800/50 h-2.5" />

              <span className="hidden md:inline-block">
                NEON MEMORY
              </span>

              {currentUser?.email && (
                <>
                  <span className="hidden lg:inline-block border-r border-cyan-800/50 h-2.5" />

                  <span className="hidden lg:inline-block">
                    {currentUser.email}
                  </span>
                </>
              )}

            </div>

          </div>

        </div>

        {/* DESKTOP NAV */}

        <nav className="hidden lg:flex items-center space-x-1 bg-cyan-950/20 p-1 rounded-lg border border-cyan-500/10">

          {navItems.map((item) => {

            const isActive = item === "CHAT";

            return (
              <button
                key={item}
                onClick={() => {
                  if (item === "HOME") {
                    router.push("/");
                  }

                  if (item !== "HOME" && item !== "CHAT") {
                    setActiveCapability(item);
                  }
                }}
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

        {/* MOBILE BUTTON */}

        <button
          onClick={() =>
            setMobileMenuOpen(!mobileMenuOpen)
          }
          className="lg:hidden p-2 rounded border border-cyan-500/30 text-cyan-400 bg-cyan-950/40 hover:bg-cyan-500/20"
        >
          <svg
            className="w-5 h-5"
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

      {/* MOBILE MENU */}

      {mobileMenuOpen && (
        <div className="lg:hidden absolute top-[65px] inset-x-0 z-40 bg-[#040c16]/95 border-b border-cyan-500/30 p-4 backdrop-blur-xl">

          <div className="grid grid-cols-3 gap-2">

            {navItems.map((item) => (

              <button
                key={item}
                onClick={() => {
                  if (item === "HOME") {
                    router.push("/");
                  }

                  if (item !== "HOME" && item !== "CHAT") {
                    setActiveCapability(item);
                  }

                  setMobileMenuOpen(false);
                }}
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

      {/* MAIN */}

      <div className="relative z-20 flex-1 flex overflow-hidden">

        {/* LEFT MODULE BAR */}

        <aside className="hidden xl:flex flex-col w-64 border-r border-cyan-500/15 bg-[#020710]/50 backdrop-blur-sm p-4 justify-between">

          <div>

            <div className="flex items-center justify-between mb-4 pb-2 border-b border-cyan-500/15">

              <span className="text-[11px] font-mono tracking-widest text-cyan-400/80 uppercase">
                AI MODULES
              </span>

              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  coreState === "error"
                    ? "bg-red-400"
                    : "bg-cyan-400 animate-pulse"
                }`}
              />

            </div>

            <div className="space-y-1.5">

              {capabilities.map((cap) => {

                const isSelected =
                  activeCapability === cap.name;

                return (
                  <button
                    key={cap.name}
                    onClick={() =>
                      setActiveCapability(cap.name)
                    }
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-xs font-mono transition-all duration-200 group text-left ${
                      isSelected
                        ? "bg-cyan-500/15 border border-cyan-500/40 text-white shadow-[0_0_12px_rgba(0,240,255,0.15)]"
                        : "border border-transparent text-cyan-400/60 hover:border-cyan-500/20 hover:text-cyan-200 hover:bg-cyan-950/30"
                    }`}
                  >

                    <div className="flex items-center space-x-2">

                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          isSelected
                            ? "bg-cyan-400 shadow-[0_0_8px_#00f0ff]"
                            : "bg-cyan-900 group-hover:bg-cyan-500"
                        }`}
                      />

                      <span className="font-semibold tracking-wider">
                        {cap.name}
                      </span>

                    </div>

                    <span className="text-[9px] text-cyan-500/40 group-hover:text-cyan-400/70">
                      {cap.desc}
                    </span>

                  </button>
                );
              })}

            </div>

          </div>

          {/* REAL STATUS */}

          <div className="p-3 rounded-lg border border-cyan-500/15 bg-cyan-950/20 text-[10px] font-mono text-cyan-400/70 space-y-2">

            <div className="flex justify-between border-b border-cyan-500/10 pb-1">
              <span>BACKEND</span>

              <span
                className={
                  coreState === "error"
                    ? "text-red-400"
                    : "text-emerald-400"
                }
              >
                {coreState === "error"
                  ? "ERROR"
                  : "CONNECTED"}
              </span>
            </div>

            <div className="flex justify-between border-b border-cyan-500/10 pb-1">
              <span>DATABASE</span>

              <span className="text-cyan-300">
                NEON
              </span>
            </div>

            <div className="flex justify-between">
              <span>SESSION</span>

              <span className="text-cyan-300">
                {currentUser ? "AUTHENTICATED" : "CHECKING"}
              </span>
            </div>

          </div>

        </aside>

        {/* CHAT */}

        <main className="flex-1 flex flex-col relative overflow-hidden bg-gradient-to-b from-transparent via-[#020812]/40 to-transparent">

          {/* AI CORE */}

          <div className="relative flex flex-col items-center justify-center pt-6 pb-2 px-4 border-b border-cyan-500/10 bg-[#020810]/40 backdrop-blur-sm">

            <div className="relative w-28 h-28 flex items-center justify-center my-1">

              <div className="absolute inset-0 rounded-full border border-dashed border-cyan-500/30 animate-[spin_20s_linear_infinite]" />

              <div className="absolute inset-2 rounded-full border border-cyan-400/20 border-t-cyan-400 animate-[spin_12s_linear_infinite_reverse]" />

              <div
                className={`absolute inset-4 rounded-full bg-cyan-500/10 blur-md transition-all duration-500 ${
                  coreState === "thinking"
                    ? "scale-125 bg-purple-500/20 shadow-[0_0_30px_rgba(168,85,247,0.4)]"
                    : coreState === "speaking"
                    ? "scale-110 bg-cyan-400/30 shadow-[0_0_35px_rgba(0,240,255,0.5)] animate-pulse"
                    : coreState === "listening"
                    ? "scale-115 bg-emerald-500/30 shadow-[0_0_30px_rgba(16,185,129,0.4)]"
                    : coreState === "error"
                    ? "scale-110 bg-red-500/20 shadow-[0_0_30px_rgba(239,68,68,0.3)]"
                    : "scale-100 shadow-[0_0_20px_rgba(0,240,255,0.2)]"
                }`}
              />

              <div className="relative z-10 flex flex-col items-center justify-center w-16 h-16 rounded-full bg-[#031322] border border-cyan-400/60 shadow-[inset_0_0_15px_rgba(0,240,255,0.3)]">

                <span className="font-extrabold text-xl tracking-tighter text-white drop-shadow-[0_0_8px_rgba(0,240,255,0.8)]">
                  KZ
                </span>

                <span className="text-[8px] font-mono tracking-widest text-cyan-400/80 -mt-1">
                  AI
                </span>

              </div>

              <div className="absolute w-full h-full animate-[spin_8s_linear_infinite]">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-300 shadow-[0_0_8px_#00f0ff] absolute top-0 left-1/2 -translate-x-1/2" />
              </div>

              <div className="absolute w-full h-full animate-[spin_14s_linear_infinite_reverse]">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 shadow-[0_0_8px_#818cf8] absolute bottom-1 left-1/2 -translate-x-1/2" />
              </div>

            </div>

            <div className="flex items-center space-x-2 mt-1">

              <span className="text-xs font-mono font-bold tracking-widest text-cyan-200 uppercase">
                KING ZARRY AI CORE
              </span>

              <span
                className={`px-2 py-0.5 text-[9px] font-mono rounded-full border ${
                  coreState === "thinking"
                    ? "bg-purple-950/60 text-purple-300 border-purple-500/50"
                    : coreState === "speaking"
                    ? "bg-cyan-950/60 text-cyan-300 border-cyan-500/50"
                    : coreState === "listening"
                    ? "bg-emerald-950/60 text-emerald-300 border-emerald-500/50"
                    : coreState === "error"
                    ? "bg-red-950/60 text-red-300 border-red-500/50"
                    : "bg-cyan-950/30 text-cyan-400/70 border-cyan-500/20"
                }`}
              >
                ● {coreStatusLabel}
              </span>

            </div>

          </div>

          {/* MESSAGES */}

          <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 scrollbar-thin scrollbar-thumb-cyan-500/20 scrollbar-track-transparent">

            {/* EMPTY STATE */}

            {messages.length === 0 &&
              coreState === "idle" && (
                <div className="h-full flex items-center justify-center">

                  <div className="text-center max-w-md px-6">

                    <div className="text-cyan-400/40 font-mono text-xs tracking-[0.35em] mb-4">
                      KZ AI CORE
                    </div>

                    <h2 className="text-white text-xl font-semibold tracking-wider mb-3">
                      READY
                    </h2>

                    <p className="text-cyan-400/50 text-sm leading-relaxed">
                      KING ZARRY AI is connected to the live
                      backend. Send a message to begin a real
                      conversation.
                    </p>

                  </div>

                </div>
              )}

            {messages.map((msg) => {

              const isAI = msg.role === "ai";

              return (
                <div
                  key={msg.id}
                  className={`flex flex-col ${
                    isAI
                      ? "items-start"
                      : "items-end"
                  } space-y-1`}
                >

                  <div className="flex items-center space-x-2 text-[10px] font-mono text-cyan-400/60 px-1">

                    <span>
                      {isAI
                        ? "KING ZARRY AI"
                        : "KING ZARRY"}
                    </span>

                    <span>•</span>

                    <span>{msg.timestamp}</span>

                  </div>

                  <div
                    className={`relative max-w-2xl rounded-xl p-4 transition-all duration-300 backdrop-blur-md ${
                      isAI
                        ? "bg-[#041220]/80 border border-cyan-500/30 text-cyan-50 shadow-[0_4px_20px_rgba(0,240,255,0.08)] rounded-tl-none"
                        : "bg-[#0b1929]/70 border border-cyan-400/20 text-white shadow-[0_4px_15px_rgba(0,0,0,0.3)] rounded-tr-none"
                    }`}
                  >

                    {isAI && (
                      <>
                        <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-cyan-400" />
                        <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-cyan-400" />
                        <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-cyan-400" />
                        <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-cyan-400" />
                      </>
                    )}

                    <p className="text-sm sm:text-base leading-relaxed tracking-wide whitespace-pre-wrap">
                      {msg.text}
                    </p>

                    {isAI && msg.status && (
                      <div className="mt-3 pt-2 border-t border-cyan-500/10 flex items-center justify-between text-[9px] font-mono text-cyan-400/60">

                        <span className="tracking-widest">
                          {msg.status}
                        </span>

                        <span className="px-1.5 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/20 text-cyan-300">
                          {msg.capability || "KZ AI"}
                        </span>

                      </div>
                    )}

                  </div>

                </div>
              );
            })}

            {/* THINKING */}

            {coreState === "thinking" && (
              <div className="flex items-center space-x-3 text-xs font-mono text-purple-300/80 bg-purple-950/20 border border-purple-500/30 p-3 rounded-lg w-fit animate-pulse">

                <div className="w-2 h-2 rounded-full bg-purple-400 animate-ping" />

                <span>
                  KING ZARRY AI IS THINKING...
                </span>

              </div>
            )}

            {/* CONNECTING */}

            {coreState === "connecting" && (
              <div className="h-full flex items-center justify-center">

                <div className="text-center">

                  <div className="w-3 h-3 rounded-full bg-cyan-400 animate-ping mx-auto mb-4" />

                  <div className="text-xs font-mono text-cyan-400/70 tracking-widest">
                    VERIFYING AI CORE CONNECTION...
                  </div>

                </div>

              </div>
            )}

            {/* ERROR */}

            {connectionError && (
              <div className="mx-2 p-3 rounded-lg border border-red-500/20 bg-red-950/20">

                <div className="text-[10px] font-mono text-red-400 tracking-wider">
                  CONNECTION STATUS • BACKEND RESPONSE ERROR
                </div>

                <div className="mt-1 text-xs text-red-300/70 break-words">
                  {connectionError}
                </div>

              </div>
            )}

            <div ref={chatEndRef} />

          </div>

          {/* COMPOSER */}

          <div className="relative z-20 p-4 border-t border-cyan-500/15 bg-[#020710]/80 backdrop-blur-md">

            {isVoiceActive ? (

              <div className="flex flex-col items-center justify-center p-4 rounded-xl border border-emerald-500/40 bg-emerald-950/20 shadow-[0_0_25px_rgba(16,185,129,0.15)] space-y-3">

                <div className="flex items-center space-x-3 text-emerald-400 font-mono text-xs tracking-widest">

                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />

                  <span>
                    VOICE INTERFACE • LISTENING
                  </span>

                </div>

                <div className="flex items-center justify-center space-x-1.5 h-10 w-full max-w-xs">

                  {[...Array(16)].map((_, i) => (

                    <div
                      key={i}
                      className="w-1.5 bg-emerald-400/80 rounded-full animate-pulse"
                      style={{
                        height: `${40 + ((i * 17) % 55)}%`,
                        animationDuration: `${0.4 + (i % 5) * 0.2}s`,
                      }}
                    />

                  ))}

                </div>

                <button
                  onClick={toggleVoiceMode}
                  className="px-4 py-1.5 rounded-md text-xs font-mono text-red-400 border border-red-500/30 bg-red-950/30 hover:bg-red-900/40 transition"
                >
                  CANCEL VOICE
                </button>

              </div>

            ) : (

              <form
                onSubmit={handleSend}
                className="relative flex items-center space-x-2"
              >

                <div className="relative flex-1 flex items-center bg-[#051322]/80 rounded-xl border border-cyan-500/30 focus-within:border-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.05)] transition-all">

                  <input
                    type="text"
                    value={input}
                    onChange={(e) =>
                      setInput(e.target.value)
                    }
                    placeholder={
                      coreState === "connecting"
                        ? "Connecting to KING ZARRY AI..."
                        : "Talk to KING ZARRY AI..."
                    }
                    disabled={
                      coreState === "thinking" ||
                      coreState === "connecting"
                    }
                    className="w-full py-3.5 px-4 bg-transparent text-sm text-white placeholder-cyan-500/40 focus:outline-none font-sans disabled:opacity-50"
                  />

                  <div className="flex items-center space-x-1 pr-2">

                    {/* IMAGE PLACEHOLDER */}

                    <button
                      type="button"
                      title="Vision input"
                      onClick={() =>
                        setActiveCapability("VISION")
                      }
                      className="p-2 text-cyan-400/60 hover:text-cyan-200 transition"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                        />
                      </svg>
                    </button>

                    {/* FILE */}

                    <button
                      type="button"
                      title="Tools"
                      onClick={() =>
                        setActiveCapability("TOOLS")
                      }
                      className="p-2 text-cyan-400/60 hover:text-cyan-200 transition"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                        />
                      </svg>
                    </button>

                    {/* MIC */}

                    <button
                      type="button"
                      onClick={toggleVoiceMode}
                      title="Voice Mode"
                      className="p-2 text-cyan-400 hover:text-emerald-300 transition"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
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

                {/* SEND */}

                <button
                  type="submit"
                  disabled={
                    !input.trim() ||
                    coreState === "thinking" ||
                    coreState === "connecting"
                  }
                  className={`px-5 py-3.5 rounded-xl text-xs font-mono font-bold tracking-wider transition-all duration-300 flex items-center justify-center space-x-1 ${
                    input.trim() &&
                    coreState !== "thinking" &&
                    coreState !== "connecting"
                      ? "bg-cyan-500 text-black shadow-[0_0_20px_rgba(0,240,255,0.4)] hover:bg-cyan-400 active:scale-95"
                      : "bg-cyan-950/40 text-cyan-500/30 border border-cyan-500/10 cursor-not-allowed"
                  }`}
                >

                  <span>
                    {coreState === "thinking"
                      ? "PROCESSING"
                      : "EXECUTE"}
                  </span>

                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M14 5l7 7m0 0l-7 7m7-7H3"
                    />
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
