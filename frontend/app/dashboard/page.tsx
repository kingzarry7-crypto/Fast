"use client";

import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import ChatWorkspace from "@/components/chat/ChatWorkspace";
import { useAuth } from "@/hooks/useAuth";
import { useCallback, useEffect, useState } from "react";
import { api, type ConversationItem, type MarketSnapshot } from "@/lib/api";

export default function DashboardPage() {
  const { user } = useAuth();
  const [markets, setMarkets] = useState<MarketSnapshot[]>([]);
  const [signals, setSignals] = useState<MarketSnapshot[]>([]);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [syncing, setSyncing] = useState(false);

  const syncDashboard = useCallback(async () => {
    setSyncing(true);
    try {
      const [marketResult, signalResult, chatResult] = await Promise.allSettled([
        api.getMarkets(),
        api.getSignals(),
        api.listConversations(),
      ]);
      if (marketResult.status === "fulfilled") setMarkets(marketResult.value.symbols || []);
      if (signalResult.status === "fulfilled") setSignals(signalResult.value.signals || []);
      if (chatResult.status === "fulfilled") setConversations(chatResult.value || []);
    } finally {
      setSyncing(false);
    }
  }, []);

  useEffect(() => {
    syncDashboard();
    const timer = window.setInterval(syncDashboard, 60000);
    return () => window.clearInterval(timer);
  }, [syncDashboard]);

  const actionableSignals = signals.filter((item) => {
    const signal = String(item.signal || "").toUpperCase();
    return signal === "BUY" || signal === "SELL";
  }).length;

  const quickLinks = [
    { label: "Chat", href: "/chat", desc: "Ask the AI anything" },
    { label: "Signals", href: "/signals", desc: "Live MTF trading signals" },
    { label: "Markets", href: "/markets", desc: "BTC • ETH • SOL • XAU" },
    { label: "News", href: "/news", desc: "Economic calendar & headlines" },
    { label: "Settings", href: "/settings", desc: "Account & preferences" },
  ];

  return (
    <ProtectedRoute>
      <div className="min-h-screen">
        <div className="p-4 sm:p-6 lg:p-8"><ChatWorkspace fullScreen={false} /></div>
        <div className="p-6 lg:p-10 max-w-6xl mx-auto">
        <div className="mb-10">
          <p className="font-mono-tech text-[10px] tracking-[0.4em] text-cyan-400/50 mb-2">
            SYSTEM ONLINE
          </p>
          <h1 className="font-display text-3xl font-bold text-white kz-glow-text tracking-wider">
            Command Centre
          </h1>
          <p className="font-mono-tech text-xs tracking-widest text-cyan-200/50 mt-2">
            WELCOME BACK{user?.display_name ? `, ${user.display_name.toUpperCase()}` : ""}
          </p>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
          {[
            ["MARKETS", markets.length, "LIVE"],
            ["SIGNALS", actionableSignals, "ACTIONABLE"],
            ["CHATS", conversations.length, "HISTORY"],
            ["MEMORY", "AUTO", "LEARNING"],
          ].map(([label, value, detail]) => (
            <div key={String(label)} className="kz-panel p-4 relative overflow-hidden">
              <div className="absolute right-0 top-0 h-12 w-12 rounded-full bg-cyan-400/5 blur-xl" />
              <p className="font-mono-tech text-[8px] tracking-[0.25em] text-cyan-400/40">{label}</p>
              <p className="mt-1 font-display text-lg font-bold tracking-wider text-white">{value}</p>
              <p className="font-mono-tech text-[8px] tracking-widest text-cyan-300/35">{detail}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1.25fr_.75fr] gap-4 mb-8">
          <div className="kz-panel p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/40">MARKET INTELLIGENCE</p>
                <h2 className="font-display text-sm font-bold tracking-widest text-white">LIVE TREND MATRIX</h2>
              </div>
              <button type="button" onClick={syncDashboard} disabled={syncing} className="font-mono-tech text-[9px] tracking-widest text-cyan-300 hover:text-white disabled:opacity-40">
                {syncing ? "SYNCING..." : "SYNC →"}
              </button>
            </div>
            <div className="relative h-36 overflow-hidden rounded-xl border border-cyan-500/15 bg-black/30 mb-4">
              <div className="absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(0,240,255,.08)_1px,transparent_1px),linear-gradient(90deg,rgba(0,240,255,.08)_1px,transparent_1px)] [background-size:36px_28px]" />
              <svg viewBox="0 0 400 140" preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
                <polygon points="0,115 45,105 90,110 130,78 175,88 220,58 260,67 300,38 345,48 400,20 400,140 0,140" fill="rgba(0,240,255,.06)" />
                <polyline points="0,115 45,105 90,110 130,78 175,88 220,58 260,67 300,38 345,48 400,20" fill="none" stroke="rgba(0,240,255,.95)" strokeWidth="2" />
                <circle cx="400" cy="20" r="4" fill="#fff" />
              </svg>
              <span className="absolute bottom-2 left-3 font-mono-tech text-[8px] tracking-widest text-cyan-400/35">4H · 1H · 15M · 5M</span>
              <span className="absolute right-3 top-2 font-mono-tech text-[8px] tracking-widest text-emerald-300/60">LIVE</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {markets.slice(0, 4).map((market) => {
                const signal = String(market.signal || "WAIT").toUpperCase();
                const signalClass = signal === "BUY" ? "text-emerald-300" : signal === "SELL" ? "text-red-300" : "text-cyan-200";
                return (
                  <div key={market.symbol} className="rounded-lg border border-cyan-500/10 bg-black/25 p-3">
                    <div className="font-display text-[10px] font-bold text-white">{market.symbol}</div>
                    <div className="mt-1 font-mono-tech text-[9px] text-cyan-200/60">{market.price != null ? String(market.price) : "—"}</div>
                    <div className={`mt-2 font-mono-tech text-[8px] tracking-widest ${signalClass}`}>{signal}</div>
                  </div>
                );
              })}
              {!markets.length && <p className="col-span-full py-4 text-center font-mono-tech text-[9px] tracking-widest text-cyan-400/30">MARKET FEED STANDING BY</p>}
            </div>
          </div>

          <div className="kz-panel p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/40">INTELLIGENCE FEED</p>
                <h2 className="font-display text-sm font-bold tracking-widest text-white">RECENT SIGNALS</h2>
              </div>
              <Link href="/signals" className="font-mono-tech text-[9px] tracking-widest text-cyan-300 hover:text-white">OPEN →</Link>
            </div>
            <div className="space-y-2">
              {signals.slice(0, 5).map((signal) => (
                <Link key={signal.symbol} href="/signals" className="flex items-center justify-between rounded-lg border border-cyan-500/10 bg-black/25 px-3 py-3 hover:border-cyan-400/30 hover:bg-cyan-400/5">
                  <div>
                    <span className="font-display text-[10px] font-bold text-white">{signal.symbol}</span>
                    <span className="block font-mono-tech text-[8px] text-cyan-400/40">{String(signal.trend || "SCANNING").toUpperCase()}</span>
                  </div>
                  <span className="font-mono-tech text-[9px] tracking-widest text-cyan-300">{String(signal.signal || "WAIT").toUpperCase()}</span>
                </Link>
              ))}
              {!signals.length && <p className="py-5 text-center font-mono-tech text-[9px] tracking-widest text-cyan-400/30">NO ACTIVE SIGNALS</p>}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {[
            { label: "AI CORE", value: "ACTIVE", color: "text-emerald-400" },
            { label: "DATABASE", value: "NEON", color: "text-cyan-400" },
            { label: "SESSION", value: user ? "AUTHENTICATED" : "—", color: "text-cyan-400" },
          ].map((s) => (
            <div key={s.label} className="kz-panel p-5">
              <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40 mb-2">
                {s.label}
              </p>
              <p className={`font-display text-lg font-bold ${s.color}`}>
                {s.value}
              </p>
            </div>
          ))}
        </div>

        <div>
          <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40 mb-3">
            QUICK ACCESS
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {quickLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="kz-panel p-5 hover:border-cyan-400/60 hover:bg-cyan-400/[0.03] transition-all group relative overflow-hidden"
              >
                <p className="font-display text-sm font-bold text-white group-hover:text-cyan-300 transition-colors tracking-wider">
                  {link.label}
                </p>
                <p className="font-mono-tech text-[10px] tracking-widest text-cyan-200/40 mt-2">
                  {link.desc}
                </p>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
