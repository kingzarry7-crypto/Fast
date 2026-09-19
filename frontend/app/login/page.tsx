"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";

type AuthState = "idle" | "authenticating" | "success" | "error";

interface LoginResponse {
  message?: string;
  detail?: string;
  user?: {
    id?: string;
    email?: string;
    username?: string;
    display_name?: string;
  };
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://fast-production-0eba.up.railway.app";

export default function KingZarryLoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [authState, setAuthState] = useState<AuthState>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const capabilities = [
    "AI",
    "VISION",
    "VOICE",
    "MEMORY",
    "REASONING",
    "AGENTS",
    "TOOLS",
    "MARKETS",
    "SIGNALS",
    "NEWS",
  ];

  async function handleLogin(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    const cleanEmail = email.trim();

    if (!cleanEmail || !password) {
      setErrorMessage("PLEASE ENTER ALL REQUIRED CREDENTIALS");
      setAuthState("error");
      return;
    }

    setErrorMessage("");
    setAuthState("authenticating");

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: cleanEmail,
          password,
        }),
      });

      let data: LoginResponse = {};

      try {
        data = await response.json();
      } catch {
        data = {};
      }

      if (!response.ok) {
        const detail =
          data.detail ||
          data.message ||
          "AUTHENTICATION FAILED • INVALID EMAIL OR PASSWORD";

        throw new Error(detail);
      }

      setAuthState("success");

      /*
       * Give the success animation a moment to display,
       * then enter the actual AI interface.
       */
      setTimeout(() => {
        router.push("/chat");
      }, 800);
    } catch (error) {
      setAuthState("error");

      setErrorMessage(
        error instanceof Error
          ? error.message
          : "AUTHENTICATION FAILED • PLEASE TRY AGAIN"
      );
    }
  }

  return (
    <div className="relative w-full min-h-screen bg-[#03060a] text-cyan-100 font-sans overflow-x-hidden flex flex-col justify-between selection:bg-cyan-500 selection:text-black">

      {/* BACKGROUND HOLOGRAPHIC ATMOSPHERE */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#072438] via-[#020b14] to-[#010408] pointer-events-none" />

      <div className="fixed inset-0 bg-[linear-gradient(to_right,#091a2815_1px,transparent_1px),linear-gradient(to_bottom,#091a2815_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />

      <div className="fixed inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,240,255,0.012)_3px,transparent_4px)] pointer-events-none z-10" />

      {/* SOFT AMBIENT GLOWS */}
      <div className="fixed top-[-10%] left-[30%] w-[600px] h-[600px] bg-cyan-600/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="fixed bottom-[-10%] right-[20%] w-[600px] h-[600px] bg-indigo-600/10 rounded-full blur-[140px] pointer-events-none" />

      {/* BACKGROUND HUD */}
      <div className="fixed inset-0 pointer-events-none hidden md:flex items-center justify-between px-12 z-0">
        <div className="space-y-8 text-[10px] font-mono text-cyan-500/20 tracking-widest">
          <div>// AI MODULES</div>
          <div>01. VISION MATRIX</div>
          <div>02. ACOUSTIC VOICE</div>
          <div>03. MEMORY VECTOR</div>
          <div>04. REASONING CORE</div>
        </div>

        <div className="space-y-8 text-[10px] font-mono text-cyan-500/20 tracking-widest text-right">
          <div>// CAPABILITIES</div>
          <div>05. AGENT NETWORK</div>
          <div>06. TOOL INTEGRATION</div>
          <div>07. MARKET TELEMETRY</div>
          <div>08. SIGNAL ENGINE</div>
        </div>
      </div>

      {/* TOP BRANDING */}
      <header className="relative z-20 flex items-center justify-between px-6 py-5 border-b border-cyan-500/15 bg-[#030810]/60 backdrop-blur-md">
        <div className="flex items-center space-x-3">
          <div className="relative flex items-center justify-center w-9 h-9 rounded-lg border border-cyan-500/40 bg-cyan-950/30 text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
            <span className="font-extrabold text-base tracking-wider">
              KZ
            </span>

            <span className="absolute -top-1 -right-1 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500" />
            </span>
          </div>

          <div>
            <h1 className="text-sm font-bold tracking-widest text-white uppercase">
              KING ZARRY AI
            </h1>

            <p className="text-[9px] font-mono tracking-wider text-cyan-400/60">
              PERSONAL AI INTELLIGENCE SYSTEM
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2 text-[10px] font-mono text-cyan-400/70 border border-cyan-500/20 px-3 py-1 rounded-full bg-cyan-950/30">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          <span>SECURE AI CORE</span>
        </div>
      </header>

      {/* MAIN */}
      <main className="relative z-20 flex-1 flex flex-col items-center justify-center px-4 py-8">

        {/* AI CORE */}
        <div className="relative w-36 h-36 md:w-40 md:h-40 flex items-center justify-center mb-6">

          <div className="absolute inset-0 rounded-full border border-cyan-500/30 animate-[spin_20s_linear_infinite]" />

          <div className="absolute inset-2 rounded-full border border-dashed border-cyan-400/20 animate-[spin_14s_linear_infinite_reverse]" />

          <div
            className={`absolute inset-4 rounded-full border-2 border-transparent border-t-cyan-400 transition-all duration-500 ${
              authState === "authenticating"
                ? "border-purple-400 animate-[spin_2s_linear_infinite]"
                : authState === "success"
                ? "border-emerald-400"
                : authState === "error"
                ? "border-red-400"
                : "animate-[spin_8s_linear_infinite]"
            }`}
          />

          <div
            className={`absolute inset-6 rounded-full blur-md transition-all duration-500 ${
              authState === "authenticating"
                ? "bg-purple-500/30 shadow-[0_0_30px_rgba(168,85,247,0.5)]"
                : authState === "success"
                ? "bg-emerald-500/30 shadow-[0_0_30px_rgba(16,185,129,0.5)]"
                : authState === "error"
                ? "bg-red-500/30 shadow-[0_0_30px_rgba(239,68,68,0.5)]"
                : "bg-cyan-500/20 shadow-[0_0_25px_rgba(0,240,255,0.3)] animate-pulse"
            }`}
          />

          <div className="relative z-10 flex flex-col items-center justify-center w-16 h-16 rounded-full bg-[#031322] border border-cyan-400/60 shadow-[inset_0_0_15px_rgba(0,240,255,0.4)]">
            <span className="font-extrabold text-xl tracking-tighter text-white">
              KZ
            </span>

            <span className="text-[8px] font-mono tracking-widest text-cyan-400/80 -mt-1">
              CORE
            </span>
          </div>

          <div className="absolute w-full h-full animate-[spin_10s_linear_infinite]">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-300 shadow-[0_0_8px_#00f0ff] absolute top-0 left-1/2 -translate-x-1/2" />
          </div>

          <div className="absolute w-full h-full animate-[spin_16s_linear_infinite_reverse]">
            <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 shadow-[0_0_8px_#818cf8] absolute bottom-0 left-1/2 -translate-x-1/2" />
          </div>
        </div>

        {/* AUTH PANEL */}
        <div className="relative w-full max-w-md rounded-2xl border border-cyan-500/30 bg-[#020914]/85 p-6 md:p-8 backdrop-blur-xl shadow-[0_0_40px_rgba(0,240,255,0.1)]">

          <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-cyan-400" />
          <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-cyan-400" />
          <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-cyan-400" />
          <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-cyan-400" />

          <div className="text-center space-y-1 mb-6">
            <h2 className="text-lg md:text-xl font-bold tracking-widest text-white uppercase">
              WELCOME BACK
            </h2>

            <p className="text-xs font-mono text-cyan-400/60">
              Authenticate to enter KING ZARRY AI.
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">

            {/* EMAIL */}
            <div className="space-y-1">
              <label className="text-[10px] font-mono tracking-widest text-cyan-400/80 uppercase block">
                SYSTEM IDENTIFIER / EMAIL
              </label>

              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="kingzarry@ai.core"
                autoComplete="email"
                required
                className="w-full py-3 px-4 bg-cyan-950/30 border border-cyan-500/30 focus:border-cyan-400 rounded-lg text-xs text-white placeholder-cyan-500/40 focus:outline-none transition shadow-[inset_0_0_10px_rgba(0,240,255,0.05)] font-mono"
                disabled={
                  authState === "authenticating" ||
                  authState === "success"
                }
              />
            </div>

            {/* PASSWORD */}
            <div className="space-y-1">

              <div className="flex justify-between items-center">
                <label className="text-[10px] font-mono tracking-widest text-cyan-400/80 uppercase block">
                  ACCESS KEY / PASSWORD
                </label>
              </div>

              <div className="relative flex items-center">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  autoComplete="current-password"
                  required
                  className="w-full py-3 pl-4 pr-10 bg-cyan-950/30 border border-cyan-500/30 focus:border-cyan-400 rounded-lg text-xs text-white placeholder-cyan-500/40 focus:outline-none transition shadow-[inset_0_0_10px_rgba(0,240,255,0.05)] font-mono"
                  disabled={
                    authState === "authenticating" ||
                    authState === "success"
                  }
                />

                <button
                  type="button"
                  onClick={() => setShowPassword((previous) => !previous)}
                  className="absolute right-3 text-cyan-400/60 hover:text-cyan-200 text-xs font-mono"
                >
                  {showPassword ? "HIDE" : "SHOW"}
                </button>
              </div>
            </div>

            {/* STATUS */}
            <div className="min-h-[20px] flex items-center justify-center text-center">

              {authState === "idle" && (
                <span className="text-[10px] font-mono text-cyan-500/60">
                  SYSTEM READY • AWAITING AUTHENTICATION
                </span>
              )}

              {authState === "authenticating" && (
                <span className="text-[10px] font-mono text-purple-300 animate-pulse flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-ping" />
                  <span>
                    AUTHENTICATING IDENTITY & VERIFYING KEYS...
                  </span>
                </span>
              )}

              {authState === "success" && (
                <span className="text-[10px] font-mono text-emerald-400 flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span>
                    IDENTITY VERIFIED • ACCESS GRANTED TO CORE
                  </span>
                </span>
              )}

              {authState === "error" && (
                <span className="text-[10px] font-mono text-red-400">
                  {errorMessage || "AUTHENTICATION FAILED"}
                </span>
              )}
            </div>

            {/* LOGIN */}
            <button
              type="submit"
              disabled={
                authState === "authenticating" ||
                authState === "success"
              }
              className={`w-full py-3.5 rounded-xl text-xs font-mono font-bold tracking-widest transition-all duration-300 shadow-[0_0_20px_rgba(0,240,255,0.2)] ${
                authState === "success"
                  ? "bg-emerald-500 text-black shadow-[0_0_25px_rgba(16,185,129,0.4)]"
                  : authState === "authenticating"
                  ? "bg-purple-600/50 text-purple-200 border border-purple-500/40 cursor-wait"
                  : "bg-cyan-500 text-black hover:bg-cyan-400 active:scale-[0.99]"
              }`}
            >
              {authState === "authenticating"
                ? "AUTHENTICATING..."
                : authState === "success"
                ? "ACCESS GRANTED"
                : "ENTER AI SYSTEM"}
            </button>
          </form>

          {/* CREATE ACCOUNT */}
          <div className="mt-6 pt-4 border-t border-cyan-500/15 flex items-center justify-between text-[10px] font-mono">
            <span className="text-cyan-400/50">
              NEW USER?
            </span>

            <button
              type="button"
              onClick={() => router.push("/register")}
              className="text-cyan-300 hover:text-white border-b border-cyan-500/40 pb-0.5 transition"
            >
              CREATE ACCOUNT
            </button>
          </div>
        </div>

        {/* CAPABILITIES */}
        <div className="mt-8 flex items-center space-x-2 text-[10px] font-mono text-cyan-400/40 overflow-hidden max-w-md">
          <span>CAPABILITIES:</span>

          <div className="flex items-center space-x-2">
            {capabilities.slice(0, 5).map((capability) => (
              <span
                key={capability}
                className="px-1.5 py-0.5 rounded bg-cyan-950/40 border border-cyan-500/10"
              >
                {capability}
              </span>
            ))}
          </div>
        </div>
      </main>

      {/* FOOTER */}
      <footer className="relative z-20 px-6 py-4 border-t border-cyan-500/10 bg-[#020710]/80 backdrop-blur-md flex flex-col sm:flex-row items-center justify-between text-[10px] font-mono text-cyan-400/50 gap-2">
        <div>
          <span>KING ZARRY AI</span>
          <span className="mx-2">•</span>
          <span>PERSONAL INTELLIGENCE SYSTEM</span>
        </div>

        <div className="flex items-center space-x-4">
          <button className="hover:text-cyan-200 transition">
            PRIVACY
          </button>

          <span>•</span>

          <button className="hover:text-cyan-200 transition">
            TERMS
          </button>
        </div>
      </footer>
    </div>
  );
}
