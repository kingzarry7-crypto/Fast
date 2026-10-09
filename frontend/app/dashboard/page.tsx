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

const EXPLORE = [
  { href: "/agent", label: "AI Agent", detail: "Delegate tasks to King Zarry", icon: "✦" },
  { href: "/markets", label: "Markets", detail: "Market data and watchlists", icon: "↗" },
  { href: "/signals", label: "Signals", detail: "Trading signals and analysis", icon: "⌁" },
  { href: "/news", label: "News & research", detail: "Discover current opportunities", icon: "⌕" },
  { href: "/plugins", label: "Explore tools", detail: "Tools and integrations", icon: "◇" },
  { href: "/history", label: "Chat history", detail: "Find previous conversations", icon: "◷" },
  { href: "/settings", label: "Settings", detail: "Account and preferences", icon: "⚙" },
  { href: "/pricing", label: "Plans", detail: "View plan options", icon: "☆" },
];

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [markets, setMarkets] = useState<MarketSnapshot[]>([]);
  const [signals, setSignals] = useState<MarketSnapshot[]>([]);
  const [chatsOpen, setChatsOpen] = useState(false);
  const [exploreOpen, setExploreOpen] = useState(false);

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
    setConversationId(null);
    setChatsOpen(false);
    setExploreOpen(false);
  };

  const openChat = (id: string) => {
    window.dispatchEvent(new CustomEvent("kz-open-chat", { detail: id }));
    setConversationId(id);
    setChatsOpen(false);
  };

  return (
    <ProtectedRoute>
      <div className="kz-command-shell fixed inset-0 flex h-[100dvh] max-h-[100dvh] w-full flex-col overflow-hidden">
        <div className="pointer-events-none absolute inset-0 -z-10 bg-[#05080f]" aria-hidden="true">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-10%,rgba(0,180,220,0.12),transparent_55%)]" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_80%_100%,rgba(30,60,120,0.08),transparent_50%)]" />
          <div className="absolute inset-0 opacity-[0.35]" style={{ backgroundImage: "linear-gradient(rgba(0,200,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,200,255,0.03) 1px, transparent 1px)", backgroundSize: "48px 48px" }} />
        </div>

        <header className="relative z-30 shrink-0 border-b border-white/[0.07] bg-[#05080f]/95 backdrop-blur-xl">
          <div className="flex w-full items-center gap-3 px-3 py-2.5 sm:px-5">
            <Link href="/dashboard" aria-label="King Zarry AI home" className="flex shrink-0 items-center gap-2.5">
              <RobotHead size={34} />
              <span className="hidden sm:block">
                <span className="block font-display text-[11px] font-bold tracking-wider text-white">KING ZARRY</span>
                <span className="block font-mono-tech text-[8px] tracking-[0.22em] text-cyan-400/50">AI ASSISTANT</span>
              </span>
            </Link>

            <div className="mx-1 hidden h-7 w-px bg-white/10 sm:block" />
            <button type="button" onClick={newChat} className="inline-flex shrink-0 items-center gap-2 rounded-full bg-cyan-300 px-3.5 py-2 text-xs font-semibold text-[#041019] transition hover:bg-cyan-200">
              <span className="text-base leading-none">+</span><span>New chat</span>
            </button>

            <div className="relative shrink-0">
              <button type="button" onClick={() => { setChatsOpen(v => !v); setExploreOpen(false); }} aria-expanded={chatsOpen}
                className={"rounded-full px-3 py-2 text-xs transition " + (chatsOpen ? "bg-white/10 text-white" : "text-zinc-400 hover:bg-white/[0.06] hover:text-white")}>
                <span className="sm:hidden">Chats</span><span className="hidden sm:inline">History</span>
                {conversations.length > 0 && <span className="ml-1.5 text-[10px] text-cyan-300">{conversations.length}</span>}
              </button>
              {chatsOpen && <>
                <button type="button" className="fixed inset-0 z-40 cursor-default" aria-label="Close history" onClick={() => setChatsOpen(false)} />
                <div className="absolute left-0 top-full z-50 mt-2 w-[min(86vw,320px)] max-h-[65vh] overflow-y-auto rounded-2xl border border-white/10 bg-[#0b1019] p-2 shadow-2xl">
                  <div className="px-3 py-2 text-[10px] font-medium uppercase tracking-[0.18em] text-zinc-500">Recent conversations</div>
                  {!conversations.length && <p className="px-3 py-6 text-center text-xs text-zinc-500">Your chats will appear here.</p>}
                  {conversations.slice(0, 30).map(c => <button key={c.id} type="button" onClick={() => openChat(c.id)}
                    className={"mb-0.5 w-full rounded-xl px-3 py-2.5 text-left text-sm transition " + (c.id === conversationId ? "bg-cyan-400/10 text-white" : "text-zinc-300 hover:bg-white/[0.06]")}>
                    <span className="block truncate">{c.title || "Untitled chat"}</span>
                  </button>)}
                  <Link href="/history" onClick={() => setChatsOpen(false)} className="mt-1 block rounded-xl px-3 py-2.5 text-xs text-cyan-300 hover:bg-white/[0.05]">View all history →</Link>
                </div>
              </>}
            </div>

            <div className="relative shrink-0">
              <button type="button" onClick={() => { setExploreOpen(v => !v); setChatsOpen(false); }} aria-expanded={exploreOpen}
                className={"inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs transition " + (exploreOpen ? "border-cyan-300/30 bg-cyan-300/10 text-cyan-100" : "border-white/10 text-zinc-300 hover:border-white/20 hover:bg-white/[0.05]")}>
                <span>Explore</span><span className="text-sm leading-none">···</span>
              </button>
              {exploreOpen && <>
                <button type="button" className="fixed inset-0 z-40 cursor-default" aria-label="Close Explore menu" onClick={() => setExploreOpen(false)} />
                <section className="absolute left-0 top-full z-50 mt-2 w-[min(92vw,390px)] max-h-[78vh] overflow-y-auto rounded-2xl border border-white/10 bg-[#0b1019] p-3 shadow-2xl shadow-black/50">
                  <div className="px-2 pb-3 pt-1">
                    <div className="text-sm font-semibold text-white">Explore King Zarry</div>
                    <p className="mt-1 text-xs leading-relaxed text-zinc-500">Your tools and workspace, kept out of the way until you need them.</p>
                  </div>
                  <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
                    {EXPLORE.map(item => <Link key={item.href} href={item.href} onClick={() => setExploreOpen(false)}
                      className="flex items-start gap-3 rounded-xl p-3 transition hover:bg-white/[0.06]">
                      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-white/[0.08] bg-white/[0.04] text-base text-cyan-200">{item.icon}</span>
                      <span className="min-w-0"><span className="block text-sm font-medium text-zinc-100">{item.label}</span><span className="mt-1 block text-[11px] leading-relaxed text-zinc-500">{item.detail}</span></span>
                    </Link>)}
                  </div>
                  <div className="mx-2 my-3 border-t border-white/[0.08]" />
                  <div className="px-2 pb-2 text-[10px] font-medium uppercase tracking-[0.18em] text-zinc-500">Quick controls</div>
                  <div className="flex flex-wrap items-center gap-2 px-1 pb-1">
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
                  </div>
                </section>
              </>}
            </div>

            <div className="ml-auto flex min-w-0 shrink-0 items-center gap-2">
              <span className="hidden xl:inline text-[10px] text-zinc-600">{markets.length || "—"} markets · {actionable} signals</span>
              <span className="hidden sm:inline rounded-full border border-white/[0.08] px-2.5 py-1 text-[10px] text-zinc-400">{user?.is_subscribed ? "VIP" : "Free"}</span>
              <Link href="/settings" aria-label="Settings" title="Settings" className="grid h-9 w-9 place-items-center rounded-full text-zinc-400 transition hover:bg-white/[0.06] hover:text-white">⚙</Link>
              <button type="button" onClick={logout} className="rounded-full px-2.5 py-2 text-xs text-zinc-500 transition hover:bg-red-400/10 hover:text-red-300">Sign out</button>
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
