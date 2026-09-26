"use client";

import Link from "next/link";
import AICore from "@/components/AICore";

export default function LandingPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6 py-16 bg-[#020914]">
      <div className="max-w-3xl w-full text-center">
        <AICore state="idle" size={200} />
        <h1 className="mt-10 font-display text-4xl md:text-6xl font-bold tracking-wider text-white">
          KING ZARRY <span className="text-cyan-400">AI</span>
        </h1>
        <p className="mt-6 text-base md:text-lg text-cyan-200/70 leading-relaxed">
          Multi-timeframe trading intelligence, persistent memory, live web
          search, and generative media — one AI core.
        </p>
        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/chat"
            className="px-8 py-3 rounded-lg bg-cyan-400 text-black font-display text-sm font-bold tracking-[0.2em] hover:bg-cyan-300 transition-all"
          >
            OPEN CHAT
          </Link>
          <Link
            href="/login"
            className="px-8 py-3 rounded-lg border border-cyan-500/30 text-cyan-300 font-mono-tech text-sm tracking-widest hover:bg-cyan-950/40 transition-all"
          >
            SIGN IN
          </Link>
        </div>
      </div>
    </main>
  );
}
