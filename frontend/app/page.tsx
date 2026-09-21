"use client";

import Link from "next/link";
import AICore from "@/components/AICore";
import HeroRings from "@/components/HeroRings";
import StatCard from "@/components/StatCard";

export default function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Background decor */}
      <HeroRings size={720} />

      {/* Navbar */}
      <nav className="relative z-10 flex items-center justify-between px-6 lg:px-10 py-5 border-b border-cyan-500/10 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shadow-[0_0_20px_rgba(0,240,255,0.4)]">
            <span className="font-bold text-black text-xs">KZ</span>
          </div>
          <p className="font-display font-bold text-white text-sm tracking-wider">
            KING ZARRY{" "}
            <span className="text-cyan-400 kz-glow-soft">AI</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="text-[10px] font-mono-tech tracking-widest text-cyan-400/70 hover:text-cyan-300 px-3 py-2"
          >
            SIGN IN
          </Link>
          <Link
            href="/register"
            className="text-[10px] font-mono-tech tracking-widest text-black bg-cyan-400 hover:bg-cyan-300 px-4 py-2 rounded-md shadow-[0_0_20px_rgba(0,240,255,0.4)] transition-all"
          >
            ENTER
          </Link>
        </div>
      </nav>

      {/* Floating panels — desktop only */}
      <div className="hidden lg:block">
        <StatCard
          title="INTELLIGENCE CORE"
          value="ONLINE"
          sub="Neural links stable"
          className="absolute top-32 left-10 w-56 kz-slow-pulse"
        />
        <StatCard
          title="HUMAN INTELLIGENCE CORE"
          value="SYSTEM ACTIVE"
          sub="MARKET ANALYSIS"
          color="#10b981"
          showChart
          className="absolute top-1/2 left-10 -translate-y-1/2 w-64"
        />
        <StatCard
          title="NEURAL NETWORK"
          value="42 NODES"
          sub="Live wireframe"
          color="#8b5cf6"
          showChart
          className="absolute top-1/2 right-10 -translate-y-1/2 w-64"
        />
      </div>

      {/* Hero */}
      <main className="relative z-10 flex flex-col items-center justify-center px-6 pt-10 pb-24 min-h-[calc(100vh-80px)]">
        <div className="flex flex-col items-center">
          <AICore state="idle" size={320} />
        </div>

        <div className="mt-24 text-center">
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold text-white kz-glow-text tracking-wider">
            KING ZARRY AI
          </h1>
          <p className="font-mono-tech text-[11px] sm:text-xs tracking-[0.5em] text-cyan-400/70 mt-4">
            YOUR INTELLIGENCE. AMPLIFIED.
          </p>
        </div>

        <div className="mt-10 flex flex-col sm:flex-row items-center gap-4">
          <Link
            href="/login"
            className="w-64 sm:w-auto px-8 py-4 rounded-md bg-cyan-400 text-black font-display font-bold text-xs tracking-[0.3em] text-center shadow-[0_0_30px_rgba(0,240,255,0.5)] hover:shadow-[0_0_50px_rgba(0,240,255,0.8)] hover:bg-cyan-300 transition-all kz-slow-pulse"
          >
            ENTER SYSTEM
          </Link>
          <Link
            href="/register"
            className="w-64 sm:w-auto px-8 py-4 rounded-md border border-cyan-400/60 text-cyan-300 font-display font-bold text-xs tracking-[0.3em] text-center hover:bg-cyan-500/10 hover:border-cyan-300 transition-all"
          >
            EXPLORE INTELLIGENCE
          </Link>
        </div>

        {/* Mobile-only stat cards */}
        <div className="lg:hidden w-full max-w-sm mt-14 grid grid-cols-2 gap-3">
          <StatCard title="CORE" value="ONLINE" />
          <StatCard title="DATABASE" value="NEON" />
          <StatCard title="SIGNALS" value="LIVE" color="#10b981" />
          <StatCard title="AI MODEL" value="v2.5" color="#8b5cf6" />
        </div>
      </main>
    </div>
  );
}
