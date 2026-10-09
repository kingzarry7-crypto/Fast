"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import ChatWorkspace from "@/components/chat/ChatWorkspace";
import RobotHead from "@/components/RobotHead";
import WorkPanel from "@/components/dashboard/WorkPanel";
import RevenuePanel from "@/components/dashboard/RevenuePanel";
import OpportunityPanel from "@/components/dashboard/OpportunityPanel";
import KZWatchPanel from "@/components/dashboard/KZWatchPanel";
import DeliveryPanel from "@/components/dashboard/DeliveryPanel";
import BusinessPanel from "@/components/dashboard/BusinessPanel";
import WorkerPanel from "@/components/dashboard/WorkerPanel";
import LearningPanel from "@/components/dashboard/LearningPanel";
import CommandStatusPanel from "@/components/dashboard/CommandStatusPanel";
import ConnectionsPanel from "@/components/dashboard/ConnectionsPanel";
import PluginsPanel from "@/components/dashboard/PluginsPanel";
import { useAuth } from "@/hooks/useAuth";
import { api, type ConversationItem, type MarketSnapshot } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Chat" }, { href: "/markets", label: "Markets" },
  { href: "/signals", label: "Signals" }, { href: "/agent", label: "Agent" },
  { href: "/news", label: "News" }, { href: "/pricing", label: "Pricing" },
  { href: "/settings", label: "Settings" },
];

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [markets, setMarkets] = useState<MarketSnapshot[]>([]);
  const [signals, setSignals] = useState<MarketSnapshot[]>([]);
  const [chatsOpen, setChatsOpen] = useState(false);

  const loadSide = useCallback(async () => {
    const [m, s, c] = await Promise.allSettled([api.getMarkets(), api.getSignals(), api.listConversations()]);
    if (m.status === "fulfilled") setMarkets((m.value as { symbols?: MarketSnapshot[] }).symbols || []);
    if (s.status === "fulfilled") setSignals((s.value as { signals?: MarketSnapshot[] }).signals || []);
    if (c.status === "fulfilled") setConversations((c.value as ConversationItem[]) || []);
  }, []);

  useEffect(() => {
    loadSide();
    const t = window.setInterval(loadSide, 90000);
    return () => window.clearInterval(t);
  }, [loadSide]);

  const actionable = signals.filter((x) => {
    const s = String(x.signal || "").toUpperCase();
    return s === "BUY" || s === "SELL";
  }).length;

  const newChat = () => {
    window.dispatchEvent(new Event("kz-new-chat"));
    setConversationId(null); setChatsOpen(false);
  };

  const openChat = (id: string) => {
    window.dispatchEvent(new CustomEvent("kz-open-chat", { detail: id }));
    setConversationId(id); setChatsOpen(false);
  };

  return (
    <ProtectedRoute>
      <div className="kz-command-shell fixed inset-0 flex h-[100dvh] max-h-[100dvh] w-full flex-col overflow-hidden">
        <div className="pointer-events-none absolute inset-0 -z-10 bg-[#05080f]" aria-hidden="true">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-10%,rgba(0,180,220,0.12),transparent_55%)]" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_80%_100%,rgba(30,60,120,0.08),transparent_50%)]" />
          <div className="absolute inset-0 opacity-[0.35]" style={{ backgroundImage: "linear-gradient(rgba(0,200,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,200,255,0.03) 1px, transparent 1px)", backgroundSize: "48px 48px" }} />
        </div>

        <header className="relative z-30 shrink-0 overflow-hidden border-b border-white/5 bg-[#05080f]/95">
          <div className="flex min-w-max items-center gap-2 overflow-x-auto px-3 py-2 sm:px-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <Link href="/dashboard" className="flex items-center gap-2.5 shrink-0 mr-1">
              <RobotHead size={36} />
              <span className="hidden sm:block">
                <span className="block font-display text-[11px] font-bold tracking-wider text-white">KING ZARRY</span>
                <span className="block font-mono-tech text-[8px] tracking-[0.25em] text-cyan-400/50">COMMAND CENTRE</span>
              </span>
            </Link>

            <button type="button" onClick={newChat} className="rounded-md border border-cyan-400/40 bg-cyan-400/10 px-2.5 py-1.5 font-mono-tech text-[10px] tracking-widest text-cyan-200 hover:bg-cyan-400/20 shrink-0">+ NEW</button>
            <WorkPanel />
            <ConnectionsPanel />
            <PluginsPanel />
            <RevenuePanel />
            <OpportunityPanel />
            <KZWatchPanel />
            <DeliveryPanel />
            <BusinessPanel />
            <WorkerPanel />
            <LearningPanel />
            <CommandStatusPanel />

            <div className="relative shrink-0">
              <button type="button" onClick={() => setChatsOpen((v) => !v)} className="rounded-md border border-cyan-500/20 px-2.5 py-1.5 font-mono-tech text-[10px] tracking-widest text-cyan-300/80 hover:bg-cyan-500/10">
                CHATS {conversations.length ? `(${conversations.length})` : ""}
              </button>
              {chatsOpen && (
                <>
                  <button type="button" className="fixed inset-0 z-40 cursor-default" aria-label="Close chats" onClick={() => setChatsOpen(false)} />
                  <div className="absolute left-0 top-full z-50 mt-2 w-72 max-h-72 overflow-y-auto rounded-xl border border-cyan-500/20 bg-[#05080f] p-2 shadow-2xl">
                    {!conversations.length && <p className="px-2 py-4 text-center font-mono-tech text-[10px] text-zinc-600">No chats yet</p>}
                    {conversations.slice(0, 30).map((c) => (
                      <button key={c.id} type="button" onClick={() => openChat(c.id)}
                        className={"mb-1 w-full rounded-lg px-3 py-2 text-left text-xs " + (c.id === conversationId ? "bg-cyan-500/15 text-white border border-cyan-500/30" : "text-zinc-400 hover:bg-white/5 border border-transparent")}>
                        <span className="block truncate">{c.title || "Untitled"}</span>
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            <nav className="hidden md:flex items-center gap-0.5 ml-1 overflow-x-auto">
              {NAV.map((n) => (
                <Link key={n.href} href={n.href} className="rounded-md px-2 py-1 font-mono-tech text-[10px] tracking-widest text-cyan-300/60 hover:text-cyan-100 hover:bg-cyan-500/10 whitespace-nowrap">
                  {n.label.toUpperCase()}
                </Link>
              ))}
            </nav>

            <div className="ml-auto flex items-center gap-2 min-w-0">
              <span className="hidden lg:inline font-mono-tech text-[9px] text-cyan-400/40 tracking-widest">MKT {markets.length || "—"} · SIG {actionable}</span>
              <span className="font-mono-tech text-[9px] tracking-widest text-cyan-300/50">{user?.is_subscribed ? "VIP" : "FREE"}</span>
              <button type="button" onClick={logout} className="rounded-md border border-red-500/20 px-2 py-1 font-mono-tech text-[9px] tracking-widest text-red-400/70 hover:bg-red-500/10">EXIT</button>
            </div>
          </div>
        </header>

        <main className="relative z-10 min-h-0 flex-1 overflow-hidden">
          <div className="absolute inset-0">
            <ChatWorkspace fullScreen={false} embedMode conversationId={conversationId} onConversationChange={setConversationId} onConversationsRefresh={setConversations} />
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
