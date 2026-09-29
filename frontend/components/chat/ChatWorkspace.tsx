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
  const listRef = useRef<HTMLDivElement>(null);
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
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
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
        "flex min-h-0 max-h-full flex-col overflow-hidden text-zinc-100 bg-transparent " +
        (fullScreen ? "h-[100dvh] max-h-[100dvh]" : "h-full")
      }
    >
      {!isVip && membership && (
        <div className="border-b border-white/5 bg-[#05080f]/80 px-3 py-1 flex items-center justify-between gap-2 shrink-0">
          <p className="text-[11px] tracking-wider text-cyan-200/70">
            FREE · {membership.freeMessagesRemaining}/{membership.freeDailyLimit} left today
          </p>
          <Link href="/pricing" className="text-[11px] text-cyan-300 hover:text-white underline underline-offset-2 shrink-0">
            UPGRADE →
          </Link>
        </div>
      )}

      {showSideHistory && (
        <div className="border-b border-white/5 px-3 py-1.5 flex items-center justify-between bg-[#05080f]/40 shrink-0">
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => setHistoryOpen((v) => !v)} className="w-7 h-7 flex items-center justify-center rounded-md border border-cyan-500/20 text-cyan-300/80 text-xs" title="Chats">
              ☰
            </button>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-mono-tech text-[9px] tracking-[0.2em] text-cyan-300/70">
              {coreState === "idle" ? "READY" : coreState.toUpperCase()}
            </span>
          </div>
          <button type="button" onClick={handleNewChat} disabled={sending} className="px-2 py-0.5 rounded-md border border-cyan-500/25 text-[9px] tracking-widest text-cyan-200 disabled:opacity-40">
            + NEW
          </button>
        </div>
      )}

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {showSideHistory && historyOpen && (
          <aside className="flex w-52 shrink-0 flex-col border-r border-white/5 bg-[#05080f]/95">
            <div className="flex-1 overflow-y-auto kz-scroll p-2">
              {conversations.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => handleOpenConversation(c.id)}
                  className={
                    "mb-1 w-full rounded-lg px-2 py-1.5 text-left text-xs " +
                    (c.id === conversationId
                      ? "bg-cyan-500/15 text-cyan-100 border border-cyan-500/30"
                      : "text-zinc-400 hover:bg-white/5 border border-transparent")
                  }
                >
                  <span className="block truncate">{c.title || "Untitled"}</span>
                </button>
              ))}
            </div>
          </aside>
        )}

        <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
          <div
            ref={listRef}
            className="flex-1 min-h-0 overflow-y-auto overscroll-y-contain kz-scroll px-3 sm:px-4 py-2 [overflow-anchor:none]"
          >
            <div className="mx-auto w-full max-w-xl space-y-1.5">
              {messages.length === 0 && !historyLoading && (
                <div className="flex flex-col items-center justify-center min-h-[120px] text-center py-4">
                  <AICore state={coreState === "idle" ? "idle" : coreState} size={64} />
                  <p className="mt-2 font-mono-tech text-[9px] tracking-[0.25em] text-cyan-300/60">READY</p>
                  <p className="mt-1 text-[11px] text-zinc-500">Type a message below</p>
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

              {historyLoading && <p className="text-xs text-zinc-500">Loading…</p>}
              {sending && <ThinkingIndicator phase={thinkingPhase} />}
              <div ref={endRef} />
            </div>
          </div>

          {error && (
            <div className="px-3 pb-1 shrink-0">
              <div className="mx-auto max-w-xl rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs text-red-300">{error}</div>
            </div>
          )}
          {attachError && (
            <div className="px-3 pb-1 shrink-0">
              <div className="mx-auto max-w-xl rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-300">{attachError}</div>
            </div>
          )}
          {attached && (
            <div className="px-3 pb-1 shrink-0">
              <div className="mx-auto max-w-xl flex items-center gap-2 rounded-lg border border-cyan-500/20 bg-black/40 px-2 py-1.5">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={attached.previewUrl} alt="" className="h-8 w-8 rounded object-cover" />
                <span className="truncate text-xs text-zinc-300">{attached.name}</span>
                <button type="button" onClick={clearAttachment} className="ml-auto text-zinc-400 hover:text-white text-sm">×</button>
              </div>
            </div>
          )}

          <form
            onSubmit={handleSubmit}
            className="shrink-0 border-t border-white/10 bg-[#05080f] px-3 sm:px-4 py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] z-20"
          >
            <div className="mx-auto w-full max-w-xl">
              <div className="mb-1.5 flex flex-wrap items-center gap-1">
                <button type="button" onClick={() => fileInputRef.current?.click()} className="rounded-md border border-cyan-500/20 px-2 py-0.5 text-[10px] text-cyan-300/80">📎</button>
                <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileInputChange} />
                {voiceSupported && (
                  <>
                    <button type="button" onClick={() => (listening ? stopListening() : listen((t) => setInput(t)))} className={"rounded-md border px-2 py-0.5 text-[10px] " + (listening ? "border-red-400/40 text-red-300" : "border-cyan-500/20 text-cyan-300/80")}>{listening ? "STOP" : "MIC"}</button>
                    <button type="button" onClick={() => setVoicePanelOpen((v) => !v)} className="rounded-md border border-cyan-500/20 px-2 py-0.5 text-[10px] text-cyan-300/80">VOICE</button>
                    <button type="button" onClick={() => setAutoSpeak((v) => !v)} className={"rounded-md border px-2 py-0.5 text-[10px] " + (autoSpeak ? "border-cyan-400/40 text-cyan-200" : "border-cyan-500/20 text-cyan-300/80")}>AUTO {autoSpeak ? "ON" : "OFF"}</button>
                  </>
                )}
              </div>

              {voicePanelOpen && (
                <div className="mb-1.5 rounded-lg border border-cyan-500/15 bg-black/40 p-2 space-y-1.5">
                  <div className="flex flex-wrap gap-1">
                    {(["bella", "male"] as const).map((v) => (
                      <button key={v} type="button" onClick={() => setVoice(v)} className={"rounded border px-2 py-0.5 text-[9px] " + (voiceCharacter === v ? "border-cyan-400/50 text-cyan-100" : "border-zinc-700 text-zinc-500")}>{v.toUpperCase()}</button>
                    ))}
                    {(["slow", "normal", "human", "fast"] as VoiceStyle[]).map((s) => (
                      <button key={s} type="button" onClick={() => setVoiceStyle(s)} className={"rounded border px-2 py-0.5 text-[9px] " + (voiceStyle === s ? "border-cyan-400/50 text-cyan-100" : "border-zinc-700 text-zinc-500")}>{s.toUpperCase()}</button>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-2 items-center">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onPaste={handlePaste}
                  placeholder="Message King Zarry AI…"
                  disabled={sending}
                  className="flex-1 rounded-xl border border-cyan-500/20 bg-black/50 px-3 py-2 text-[13px] text-white placeholder-zinc-600 outline-none focus:border-cyan-400/40 disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={sending || (!input.trim() && !attached)}
                  className="rounded-xl bg-cyan-400 px-3.5 py-2 text-xs font-semibold tracking-wide text-black hover:bg-cyan-300 disabled:opacity-30 shrink-0"
                >
                  SEND
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
