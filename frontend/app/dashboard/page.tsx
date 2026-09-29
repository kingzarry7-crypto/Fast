"use client";

import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
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
      if (marketResult.status === "fulfilled") {
        setMarkets(marketResult.value.symbols || []);
      }
      if (signalResult.status === "fulfilled") {
        setSignals(signalResult.value.signals || []);
      }
      if (chatResult.status === "fulfilled") {
        setConversations(chatResult.value || []);
      }
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
    { label: "Agent", href: "/agent", desc: "Autonomous market watch" },
    { label: "Settings", href: "/settings", desc: "Account & preferences" },
  ];

  return (
    <ProtectedRoute>
      <div className="min-h-screen">
        <div className="mx-auto max-w-6xl p-6 lg:p-10">
          <div className="mb-10">
            <p className="mb-2 font-mono-tech text-[10px] tracking-[0.4em] text-cyan-400/50">
              SYSTEM ONLINE
            </p>
            <h1 className="font-display text-3xl font-bold tracking-wider text-white kz-glow-text">
              Command Centre
            </h1>
            <p className="mt-2 font-mono-tech text-sm text-cyan-200/50">
              Welcome back{user?.email ? `, ${user.email}` : ""}.
              {syncing ? " · Syncing…" : ""}
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link
                href="/chat"
                className="inline-flex items-center rounded-lg bg-cyan-400 px-4 py-2 font-display text-xs font-bold tracking-widest text-black hover:bg-cyan-300"
              >
                OPEN CHAT
              </Link>
              <Link
                href="/agent"
                className="inline-flex items-center rounded-lg border border-cyan-500/40 px-4 py-2 font-mono-tech text-[10px] tracking-widest text-cyan-300 hover:bg-cyan-500/10"
              >
                AGENT
              </Link>
              <button
                type="button"
                onClick={syncDashboard}
                disabled={syncing}
                className="inline-flex items-center rounded-lg border border-cyan-500/20 px-4 py-2 font-mono-tech text-[10px] tracking-widest text-cyan-400/70 hover:text-cyan-200 disabled:opacity-40"
              >
                {syncing ? "SYNCING…" : "SYNC DATA"}
              </button>
            </div>
          </div>

          <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
            {[
              { label: "MARKETS", value: String(markets.length || "—"), href: "/markets" },
              { label: "SIGNALS", value: String(actionableSignals), href: "/signals" },
              { label: "CHATS", value: String(conversations.length || "—"), href: "/chat" },
              {
                label: "PLAN",
                value: user?.is_subscribed ? "VIP" : "FREE",
                href: "/pricing",
              },
            ].map((s) => (
              <Link
                key={s.label}
                href={s.href}
                className="kz-panel p-4 transition-colors hover:border-cyan-400/40"
              >
                <p className="mb-1 font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/40">
                  {s.label}
                </p>
                <p className="font-display text-xl font-bold text-white">{s.value}</p>
              </Link>
            ))}
          </div>

          <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="kz-panel p-5">
              <div className="mb-4 flex items-center justify-between">
                <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/50">
                  LIVE MARKETS
                </p>
                <Link
                  href="/markets"
                  className="font-mono-tech text-[9px] text-cyan-400/60 hover:text-cyan-300"
                >
                  VIEW ALL
                </Link>
              </div>
              <div className="space-y-2">
                {markets.slice(0, 6).map((market) => {
                  const signal = String(market.signal || "WAIT").toUpperCase();
                  const signalClass =
                    signal === "BUY"
                      ? "text-emerald-400"
                      : signal === "SELL"
                        ? "text-red-400"
                        : "text-cyan-400/50";
                  return (
                    <div
                      key={market.symbol}
                      className="flex items-center justify-between rounded-lg border border-cyan-500/10 bg-black/25 px-3 py-3"
                    >
                      <div>
                        <div className="font-display text-[10px] font-bold text-white">
                          {market.symbol}
                        </div>
                        <div className="mt-1 font-mono-tech text-[9px] text-cyan-200/60">
                          {market.price != null ? String(market.price) : "—"}
                        </div>
                      </div>
                      <div
                        className={`font-mono-tech text-[8px] tracking-widest ${signalClass}`}
                      >
                        {signal}
                      </div>
                    </div>
                  );
                })}
                {!markets.length && (
                  <p className="py-5 text-center font-mono-tech text-[9px] tracking-widest text-cyan-400/30">
                    NO MARKET DATA
                  </p>
                )}
              </div>
            </div>

            <div className="kz-panel p-5">
              <div className="mb-4 flex items-center justify-between">
                <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/50">
                  SIGNALS
                </p>
                <Link
                  href="/signals"
                  className="font-mono-tech text-[9px] text-cyan-400/60 hover:text-cyan-300"
                >
                  VIEW ALL
                </Link>
              </div>
              <div className="space-y-2">
                {signals.slice(0, 6).map((signal) => (
                  <Link
                    key={signal.symbol}
                    href="/signals"
                    className="flex items-center justify-between rounded-lg border border-cyan-500/10 bg-black/25 px-3 py-3 hover:border-cyan-400/30 hover:bg-cyan-400/5"
                  >
                    <div>
                      <span className="font-display text-[10px] font-bold text-white">
                        {signal.symbol}
                      </span>
                      <span className="block font-mono-tech text-[8px] text-cyan-400/40">
                        {String(signal.trend || "SCANNING").toUpperCase()}
                      </span>
                    </div>
                    <span className="font-mono-tech text-[9px] tracking-widest text-cyan-300">
                      {String(signal.signal || "WAIT").toUpperCase()}
                    </span>
                  </Link>
                ))}
                {!signals.length && (
                  <p className="py-5 text-center font-mono-tech text-[9px] tracking-widest text-cyan-400/30">
                    NO ACTIVE SIGNALS
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-3">
            {[
              { label: "COMMAND CENTRE", value: "ACTIVE", color: "text-emerald-400" },
              { label: "DATABASE", value: "NEON", color: "text-cyan-400" },
              {
                label: "SESSION",
                value: user ? "AUTHENTICATED" : "—",
                color: "text-cyan-400",
              },
            ].map((s) => (
              <div key={s.label} className="kz-panel p-5">
                <p className="mb-2 font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40">
                  {s.label}
                </p>
                <p className={`font-display text-lg font-bold ${s.color}`}>{s.value}</p>
              </div>
            ))}
          </div>

          <div>
            <p className="mb-3 font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40">
              QUICK ACCESS
            </p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {quickLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="kz-panel group relative overflow-hidden p-5 transition-all hover:border-cyan-400/60 hover:bg-cyan-400/[0.03]"
                >
                  <p className="font-display text-sm font-bold tracking-wider text-white transition-colors group-hover:text-cyan-300">
                    {link.label}
                  </p>
                  <p className="mt-2 font-mono-tech text-[10px] tracking-widest text-cyan-200/40">
                    {link.desc}
                  </p>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
