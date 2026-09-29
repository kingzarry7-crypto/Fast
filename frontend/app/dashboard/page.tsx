"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import ChatWorkspace from "@/components/chat/ChatWorkspace";
import { useAuth } from "@/hooks/useAuth";
import { api, type ConversationItem, type MarketSnapshot } from "@/lib/api";

export default function DashboardPage() {
  const { user } = useAuth();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [markets, setMarkets] = useState<MarketSnapshot[]>([]);
  const [signals, setSignals] = useState<MarketSnapshot[]>([]);
  const [railOpen, setRailOpen] = useState(true);

  const loadSide = useCallback(async () => {
    const [m, s, c] = await Promise.allSettled([
      api.getMarkets(),
      api.getSignals(),
      api.listConversations(),
    ]);
    if (m.status === "fulfilled") setMarkets(m.value.symbols || []);
    if (s.status === "fulfilled") setSignals(s.value.signals || []);
    if (c.status === "fulfilled") setConversations(c.value || []);
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
  };

  const openChat = (id: string) => {
    window.dispatchEvent(new CustomEvent("kz-open-chat", { detail: id }));
    setConversationId(id);
  };

  return (
    <ProtectedRoute>
      <div className="flex h-[100dvh] min-h-0 w-full overflow-hidden">
        <div className="relative flex min-w-0 flex-1 flex-col">
          <div className="relative z-10 flex min-h-0 flex-1 flex-col border-r border-cyan-500/10 bg-[#020914]/40">
            <ChatWorkspace
              fullScreen
              embedMode
              conversationId={conversationId}
              onConversationChange={setConversationId}
              onConversationsRefresh={setConversations}
            />
          </div>
        </div>

        <aside
          className={
            (railOpen ? "flex" : "hidden") +
            " w-[min(100%,300px)] shrink-0 flex-col border-l border-cyan-500/10 bg-[#020914]/95 backdrop-blur-xl xl:flex"
          }
        >
          <div className="flex items-center justify-between border-b border-cyan-500/10 px-4 py-3">
            <div>
              <p className="font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/50">DASHBOARD</p>
              <p className="font-display text-xs font-bold tracking-wider text-white">Command side</p>
            </div>
            <button
              type="button"
              onClick={newChat}
              className="rounded-lg border border-cyan-400/40 bg-cyan-400/10 px-3 py-1.5 font-mono-tech text-[10px] tracking-widest text-cyan-200 hover:bg-cyan-400/20"
            >
              + NEW CHAT
            </button>
          </div>

          <div className="border-b border-cyan-500/10 px-4 py-3">
            <p className="mb-2 font-mono-tech text-[9px] tracking-[0.25em] text-cyan-400/40">SESSION</p>
            <p className="truncate text-xs text-zinc-300">{user?.email || "—"}</p>
            <p className="mt-1 font-mono-tech text-[10px] text-cyan-300/60">
              {user?.is_subscribed ? "VIP ACTIVE" : "FREE PLAN"}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-2 border-b border-cyan-500/10 px-3 py-3">
            {[
              { l: "MKT", v: String(markets.length || "—"), href: "/markets" },
              { l: "SIG", v: String(actionable), href: "/signals" },
              { l: "CHATS", v: String(conversations.length || "—"), href: "/chat" },
            ].map((x) => (
              <Link
                key={x.l}
                href={x.href}
                className="rounded-lg border border-cyan-500/15 bg-black/30 px-2 py-2 text-center hover:border-cyan-400/40"
              >
                <p className="font-mono-tech text-[8px] tracking-widest text-cyan-400/40">{x.l}</p>
                <p className="font-display text-sm font-bold text-white">{x.v}</p>
              </Link>
            ))}
          </div>

          <div className="flex min-h-0 flex-1 flex-col">
            <div className="flex items-center justify-between px-4 py-2">
              <p className="font-mono-tech text-[9px] tracking-[0.25em] text-cyan-400/40">RECENT CHATS</p>
            </div>
            <div className="flex-1 overflow-y-auto kz-scroll px-2 pb-3">
              {conversations.slice(0, 20).map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => openChat(c.id)}
                  className={
                    "mb-1 w-full rounded-lg px-3 py-2.5 text-left transition-colors " +
                    (c.id === conversationId
                      ? "border border-cyan-500/35 bg-cyan-500/15 text-white"
                      : "border border-transparent text-zinc-400 hover:bg-white/5 hover:text-zinc-200")
                  }
                >
                  <span className="block truncate text-xs">{c.title || "Untitled conversation"}</span>
                  <span className="mt-0.5 block truncate font-mono-tech text-[9px] text-zinc-600">
                    {c.updated_at || c.created_at
                      ? String(c.updated_at || c.created_at).slice(0, 16).replace("T", " ")
                      : ""}
                  </span>
                </button>
              ))}
              {!conversations.length && (
                <p className="px-2 py-6 text-center font-mono-tech text-[10px] text-zinc-600">
                  No chats yet — start with + NEW CHAT
                </p>
              )}
            </div>
          </div>

          <div className="border-t border-cyan-500/10 p-3 space-y-1.5">
            {[
              { href: "/markets", label: "Markets" },
              { href: "/signals", label: "Signals" },
              { href: "/agent", label: "Agent" },
              { href: "/pricing", label: "Pricing" },
            ].map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="block rounded-lg px-3 py-2 font-mono-tech text-[10px] tracking-widest text-cyan-300/70 hover:bg-cyan-500/10 hover:text-cyan-100"
              >
                {l.label.toUpperCase()} →
              </Link>
            ))}
          </div>
        </aside>

        <button
          type="button"
          onClick={() => setRailOpen((v) => !v)}
          className="fixed bottom-4 right-4 z-40 rounded-full border border-cyan-500/40 bg-[#020914]/95 px-4 py-2 font-mono-tech text-[10px] tracking-widest text-cyan-200 shadow-lg xl:hidden"
        >
          {railOpen ? "HIDE PANEL" : "DASHBOARD"}
        </button>
      </div>
    </ProtectedRoute>
  );
}
