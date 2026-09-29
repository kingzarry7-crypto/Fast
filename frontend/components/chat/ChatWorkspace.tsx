"use client";

import { useEffect, useRef, useState } from "react";
import AICore from "@/components/AICore";
import ChatMessage, { ThinkingIndicator } from "@/components/chat/ChatMessage";
import { useChat } from "@/hooks/useChat";
import { useVoice, type VoiceStyle } from "@/hooks/useVoice";
import { api, type ConversationItem } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import Link from "next/link";
import {
  getMembershipSnapshot,
  type MembershipSnapshot,
} from "@/lib/membership";

type CoreState = "idle" | "thinking" | "speaking" | "listening" | "error";

interface AttachedImage {
  base64: string;
  mime: string;
  previewUrl: string;
  name: string;
}

const MAX_IMAGE_BYTES = 8 * 1024 * 1024;

export type ChatWorkspaceProps = {
  fullScreen?: boolean;
  embedMode?: boolean;
  conversationId?: string | null;
  onConversationChange?: (id: string | null) => void;
  onConversationsRefresh?: (list: ConversationItem[]) => void;
};

export default function ChatWorkspace({
  fullScreen = true,
  embedMode = false,
  conversationId: controlledId,
  onConversationChange,
  onConversationsRefresh,
}: ChatWorkspaceProps) {
  const { user } = useAuth();
  const [internalId, setInternalId] = useState<string | null>(null);
  const conversationId = controlledId !== undefined ? controlledId : internalId;
  const setConversationId = (id: string | null) => {
    if (controlledId === undefined) setInternalId(id);
    onConversationChange?.(id);
  };

  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const { messages, setMessages, sending, error, send, clear } = useChat(
    user?.id,
    user?.is_subscribed,
    conversationId
  );
  const [membership, setMembership] = useState<MembershipSnapshot | null>(null);
  const [input, setInput] = useState("");
  const [capability] = useState("AI");
  const [coreState, setCoreState] = useState<CoreState>("idle");
  const [thinkingPhase, setThinkingPhase] = useState<
    "reading" | "thinking" | "responding"
  >("thinking");
  const [attached, setAttached] = useState<AttachedImage | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [voicePanelOpen, setVoicePanelOpen] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const {
    speak,
    stop: stopSpeaking,
    speaking: isSpeaking,
    listening,
    listen,
    stopListening,
    supported: voiceSupported,
    style: voiceStyle,
    setVoiceStyle,
    voiceCharacter,
    setVoice,
  } = useVoice();

  const refreshConversations = async () => {
    try {
      const list = await api.listConversations();
      setConversations(list);
      onConversationsRefresh?.(list);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    const refresh = () =>
      setMembership(getMembershipSnapshot(user?.id, user?.is_subscribed));
    refresh();
    window.addEventListener("kz-membership-change", refresh);
    window.addEventListener("storage", refresh);
    return () => {
      window.removeEventListener("kz-membership-change", refresh);
      window.removeEventListener("storage", refresh);
    };
  }, [user?.id, user?.is_subscribed]);

  useEffect(() => {
    if (user?.id) refreshConversations();
  }, [user?.id]);

  useEffect(() => {
    if (!sending) {
      setCoreState("idle");
      return;
    }
    setCoreState("thinking");
    setThinkingPhase("reading");
    const t1 = setTimeout(() => setThinkingPhase("thinking"), 700);
    const t2 = setTimeout(() => setThinkingPhase("responding"), 2200);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [sending]);

  useEffect(() => {
    if (!autoSpeak || sending || !messages.length) return;
    const last = messages[messages.length - 1];
    if (last?.role === "assistant" && last.text && !String(last.id || "").startsWith("error")) {
      speak(last.text);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, sending, autoSpeak]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const handleNewChat = async () => {
    clear();
    setConversationId(null);
    try {
      const conv = await api.createConversation();
      setConversationId(conv.id);
      await refreshConversations();
    } catch {
      setConversationId(null);
    }
  };

  const handleOpenConversation = async (id: string) => {
    if (sending) return;
    setHistoryLoading(true);
    setConversationId(id);
    clear();
    try {
      const msgs = await api.getConversationMessages(id);
      setMessages(
        msgs.map((m, i) => ({
          id: m.id || `hist-${id}-${i}`,
          role: (m.role === "user" ? "user" : "assistant") as "user" | "assistant",
          text: m.content || "",
          timestamp: m.created_at ? String(m.created_at).slice(11, 19) || "" : "",
        }))
      );
    } catch {
      setMessages([
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          text: "Could not load this chat. Try again.",
          timestamp: "",
          status: "HISTORY ERROR",
        },
      ]);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    const onNew = () => {
      void handleNewChat();
    };
    const onOpen = (e: Event) => {
      const id = (e as CustomEvent<string>).detail;
      if (id) void handleOpenConversation(id);
    };
    window.addEventListener("kz-new-chat", onNew);
    window.addEventListener("kz-open-chat", onOpen as EventListener);
    return () => {
      window.removeEventListener("kz-new-chat", onNew);
      window.removeEventListener("kz-open-chat", onOpen as EventListener);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sending]);

  const handleFile = async (file: File) => {
    setAttachError(null);
    if (!file.type.startsWith("image/")) {
      setAttachError("Only image files are supported.");
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setAttachError("Image too large. Max 8 MB.");
      return;
    }
    try {
      const base64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = reader.result as string;
          const commaIdx = result.indexOf(",");
          resolve(commaIdx >= 0 ? result.slice(commaIdx + 1) : result);
        };
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(file);
      });
      setAttached({
        base64,
        mime: file.type || "image/jpeg",
        previewUrl: URL.createObjectURL(file),
        name: file.name,
      });
    } catch {
      setAttachError("Could not read that image. Try another file.");
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  };

  const clearAttachment = () => {
    if (attached?.previewUrl) URL.revokeObjectURL(attached.previewUrl);
    setAttached(null);
    setAttachError(null);
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) {
          e.preventDefault();
          handleFile(file);
          return;
        }
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    const hasImage = !!attached;
    if ((!text && !hasImage) || sending) return;
    const payloadImage = attached
      ? { base64: attached.base64, mime: attached.mime, previewUrl: attached.previewUrl, name: attached.name }
      : undefined;
    setInput("");
    clearAttachment();
    const effectiveText = text || (hasImage ? "What do you see in this image?" : "");
    const res = await send(effectiveText, capability, payloadImage);
    if (res && (res as { conversation_id?: string }).conversation_id) {
      const cid = (res as { conversation_id: string }).conversation_id;
      setConversationId(cid);
      refreshConversations();
    }
  };

  const isVip = Boolean(user?.is_subscribed || membership?.isVip);
  const showSideHistory = !embedMode;

  return (
    <div
      className={
        "flex flex-col min-h-0 overflow-hidden text-zinc-100 bg-transparent " +
        (fullScreen ? "h-[100dvh]" : "h-full min-h-[560px]")
      }
    >
      {!isVip && membership && (
        <div className="border-b border-cyan-500/10 bg-[#020914]/80 px-4 py-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 shrink-0">
          <p className="text-xs tracking-wider text-cyan-200/70">
            FREE · {membership.freeMessagesRemaining}/{membership.freeDailyLimit} messages left today
          </p>
          <Link href="/pricing" className="text-xs text-cyan-300 hover:text-white underline underline-offset-2 shrink-0">
            UPGRADE →
          </Link>
        </div>
      )}

      <div className="border-b border-cyan-500/10 px-4 py-2.5 flex items-center justify-between bg-[#020914]/50 backdrop-blur-md shrink-0">
        <div className="flex items-center gap-2.5">
          {showSideHistory && (
            <button
              type="button"
              onClick={() => setHistoryOpen((v) => !v)}
              className="w-8 h-8 flex items-center justify-center rounded-lg border border-cyan-500/20 text-cyan-300/80 text-xs hover:bg-cyan-500/10"
              title="Chats"
            >
              ☰
            </button>
          )}
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-mono-tech text-[10px] tracking-[0.25em] text-cyan-300/80">
            COMMAND CENTRE
            {coreState === "idle"
              ? " · IDLE"
              : coreState === "thinking"
                ? thinkingPhase === "reading"
                  ? " · READING"
                  : thinkingPhase === "responding"
                    ? " · RESPONDING"
                    : " · THINKING"
                : " · " + coreState.toUpperCase()}
          </span>
        </div>
        {showSideHistory && (
          <button
            type="button"
            onClick={handleNewChat}
            disabled={sending}
            className="px-2.5 py-1 rounded-lg border border-cyan-500/25 text-[10px] tracking-widest text-cyan-200 hover:bg-cyan-500/10 disabled:opacity-40"
          >
            + NEW
          </button>
        )}
      </div>

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {showSideHistory && historyOpen && (
          <aside className="flex w-60 shrink-0 flex-col border-r border-cyan-500/10 bg-[#020914]/90">
            <div className="flex items-center justify-between border-b border-cyan-500/10 px-3 py-3">
              <p className="text-[10px] tracking-widest text-cyan-400/50">CHATS</p>
              <button type="button" onClick={handleNewChat} disabled={sending} className="text-[10px] tracking-widest text-cyan-300 hover:text-white disabled:opacity-40">
                + NEW
              </button>
            </div>
            <div className="flex-1 overflow-y-auto kz-scroll p-2">
              {conversations.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => handleOpenConversation(c.id)}
                  className={
                    "mb-1 w-full rounded-lg px-3 py-2 text-left text-xs transition-colors " +
                    (c.id === conversationId
                      ? "bg-cyan-500/15 text-cyan-100 border border-cyan-500/30"
                      : "text-zinc-400 hover:bg-white/5 border border-transparent")
                  }
                >
                  <span className="block truncate">{c.title || "Untitled"}</span>
                </button>
              ))}
              {!conversations.length && <p className="px-2 py-4 text-[10px] text-zinc-500">No chats yet</p>}
            </div>
          </aside>
        )}

        <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
          <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain kz-scroll px-3 sm:px-6 py-4">
            <div className="mx-auto w-full max-w-2xl space-y-2.5">
              {messages.length === 0 && !historyLoading && (
                <div className="flex flex-col items-center justify-center min-h-[42vh] text-center py-10">
                  <AICore state={coreState === "idle" ? "idle" : coreState} size={110} />
                  <p className="mt-5 font-mono-tech text-[10px] tracking-[0.3em] text-cyan-300/70">COMMAND CENTRE</p>
                  <p className="mt-1.5 text-[11px] text-zinc-500">Ask anything about markets, signals, or strategy</p>
                </div>
              )}

              {messages.map((m) => (
                <ChatMessage
                  key={m.id}
                  id={m.id}
                  role={m.role}
                  content={m.text}
                  timestamp={m.timestamp}
                  status={m.status}
                  isError={String(m.id || "").startsWith("error")}
                  imagePreviewUrl={m.imagePreviewUrl}
                  onSpeak={
                    m.role === "assistant"
                      ? () => (isSpeaking ? stopSpeaking() : speak(m.text || ""))
                      : undefined
                  }
                />
              ))}

              {historyLoading && <p className="text-xs text-zinc-500">Loading chat…</p>}
              {sending && <ThinkingIndicator phase={thinkingPhase} />}
              <div ref={endRef} />
            </div>
          </div>

          {error && (
            <div className="px-4 pb-2">
              <div className="mx-auto max-w-2xl rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</div>
            </div>
          )}
          {attachError && (
            <div className="px-4 pb-2">
              <div className="mx-auto max-w-2xl rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">{attachError}</div>
            </div>
          )}
          {attached && (
            <div className="px-4 pb-2">
              <div className="mx-auto max-w-2xl flex items-center gap-3 rounded-lg border border-cyan-500/20 bg-black/40 px-3 py-2">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={attached.previewUrl} alt="" className="h-10 w-10 rounded object-cover" />
                <span className="truncate text-xs text-zinc-300">{attached.name}</span>
                <button type="button" onClick={clearAttachment} className="ml-auto text-zinc-400 hover:text-white text-sm">×</button>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="border-t border-cyan-500/10 bg-[#020914]/70 backdrop-blur-xl px-3 sm:px-6 py-3 shrink-0">
            <div className="mx-auto w-full max-w-2xl">
              <div className="mb-2 flex flex-wrap items-center gap-1.5">
                <button type="button" onClick={() => fileInputRef.current?.click()} className="rounded-lg border border-cyan-500/20 px-2.5 py-1 text-[10px] tracking-widest text-cyan-300/80 hover:bg-cyan-500/10">📎</button>
                <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileInputChange} />
                {voiceSupported && (
                  <>
                    <button type="button" onClick={() => (listening ? stopListening() : listen((t) => setInput(t)))} className={"rounded-lg border px-2.5 py-1 text-[10px] tracking-widest " + (listening ? "border-red-400/40 text-red-300 bg-red-500/10" : "border-cyan-500/20 text-cyan-300/80 hover:bg-cyan-500/10")}>{listening ? "STOP" : "MIC"}</button>
                    <button type="button" onClick={() => setVoicePanelOpen((v) => !v)} className="rounded-lg border border-cyan-500/20 px-2.5 py-1 text-[10px] tracking-widest text-cyan-300/80 hover:bg-cyan-500/10">VOICE</button>
                    <button type="button" onClick={() => setAutoSpeak((v) => !v)} className={"rounded-lg border px-2.5 py-1 text-[10px] tracking-widest " + (autoSpeak ? "border-cyan-400/40 text-cyan-200 bg-cyan-500/10" : "border-cyan-500/20 text-cyan-300/80")}>AUTO {autoSpeak ? "ON" : "OFF"}</button>
                  </>
                )}
              </div>

              {voicePanelOpen && (
                <div className="mb-2 rounded-xl border border-cyan-500/15 bg-black/40 p-3 space-y-2">
                  <p className="text-[9px] tracking-widest text-cyan-400/50">CHARACTER</p>
                  <div className="flex gap-2">
                    {(["bella", "male"] as const).map((v) => (
                      <button key={v} type="button" onClick={() => setVoice(v)} className={"rounded-md border px-2 py-1 text-[10px] tracking-widest " + (voiceCharacter === v ? "border-cyan-400/50 text-cyan-100" : "border-zinc-700 text-zinc-500")}>{v.toUpperCase()}</button>
                    ))}
                  </div>
                  <p className="text-[9px] tracking-widest text-cyan-400/50">SPEED</p>
                  <div className="flex flex-wrap gap-2">
                    {(["slow", "normal", "human", "fast"] as VoiceStyle[]).map((s) => (
                      <button key={s} type="button" onClick={() => setVoiceStyle(s)} className={"rounded-md border px-2 py-1 text-[10px] tracking-widest " + (voiceStyle === s ? "border-cyan-400/50 text-cyan-100" : "border-zinc-700 text-zinc-500")}>{s.toUpperCase()}</button>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-2 items-end">
                <input type="text" value={input} onChange={(e) => setInput(e.target.value)} onPaste={handlePaste} placeholder="Message King Zarry AI…" disabled={sending} className="flex-1 rounded-2xl border border-cyan-500/20 bg-black/40 px-4 py-2.5 text-[13px] text-white placeholder-zinc-600 outline-none focus:border-cyan-400/40 disabled:opacity-50" />
                <button type="submit" disabled={sending || (!input.trim() && !attached)} className="rounded-2xl bg-cyan-400 px-4 py-2.5 text-xs font-semibold tracking-wide text-black hover:bg-cyan-300 disabled:opacity-30">SEND</button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
