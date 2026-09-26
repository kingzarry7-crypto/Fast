"use client";

import { useEffect, useRef, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
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

const capabilities = [
  { name: "AI", desc: "Core Intelligence" },
  { name: "VISION", desc: "Spatial Analysis" },
  { name: "VOICE", desc: "Acoustic Interface" },
  { name: "MEMORY", desc: "Neural Context" },
  { name: "REASONING", desc: "Cognitive Processing" },
  { name: "AGENTS", desc: "Autonomous Units" },
  { name: "TOOLS", desc: "System Integrations" },
  { name: "MARKETS", desc: "Market Data" },
  { name: "SIGNALS", desc: "Pattern Detection" },
  { name: "NEWS", desc: "External Information" },
];

const MAX_IMAGE_BYTES = 8 * 1024 * 1024;

export default function ChatPage() {
  const { user } = useAuth();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const { messages, setMessages, sending, error, send, clear } = useChat(
    user?.id,
    user?.is_subscribed,
    conversationId
  );
  const [membership, setMembership] = useState<MembershipSnapshot | null>(null);
  const [input, setInput] = useState("");
  const [capability, setCapability] = useState("AI");
  const [coreState, setCoreState] = useState<CoreState>("idle");
  const [thinkingPhase, setThinkingPhase] = useState<
    "reading" | "thinking" | "responding"
  >("thinking");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [attached, setAttached] = useState<AttachedImage | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const [autoSpeak, setAutoSpeak] = useState(false);
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
  } = useVoice();

  const refreshConversations = async () => {
    try {
      const list = await api.listConversations();
      setConversations(list);
    } catch {
      /* API may not be ready */
    }
  };

  useEffect(() => {
    const refresh = () => setMembership(getMembershipSnapshot(user?.id));
    refresh();
    window.addEventListener("kz-membership-change", refresh);
    window.addEventListener("storage", refresh);
    return () => {
      window.removeEventListener("kz-membership-change", refresh);
      window.removeEventListener("storage", refresh);
    };
  }, [user?.id]);

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
    if (
      last?.role === "assistant" &&
      last.text &&
      !String(last.id || "").startsWith("error")
    ) {
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
          role: (m.role === "user" ? "user" : "assistant") as
            | "user"
            | "assistant",
          text: m.content || "",
          timestamp: m.created_at
            ? String(m.created_at).slice(11, 19) || ""
            : "",
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
      ? {
          base64: attached.base64,
          mime: attached.mime,
          previewUrl: attached.previewUrl,
          name: attached.name,
        }
      : undefined;

    setInput("");
    clearAttachment();

    const effectiveText =
      text || (hasImage ? "What do you see in this image?" : "");
    const res = await send(effectiveText, capability, payloadImage);
    if (res && (res as { conversation_id?: string }).conversation_id) {
      const cid = (res as { conversation_id: string }).conversation_id;
      setConversationId(cid);
      refreshConversations();
    }
  };

  const isVip = Boolean(user?.is_subscribed || membership?.isVip);

  return (
    <ProtectedRoute>
      <div className="flex flex-col h-screen">
        {!isVip && membership && (
          <div className="border-b border-amber-500/20 bg-amber-950/30 px-4 py-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <p className="font-mono-tech text-[10px] tracking-wider text-amber-200/90">
              FREE TIER · Normal chat allowed · Signals require VIP ·{" "}
              {membership.freeMessagesRemaining}/{membership.freeDailyLimit} left today
            </p>
            <Link
              href="/pricing"
              className="font-mono-tech text-[10px] tracking-widest text-cyan-300 hover:text-cyan-200 underline underline-offset-2 shrink-0"
            >
              UPGRADE →
            </Link>
          </div>
        )}
        {isVip && (
          <div className="border-b border-cyan-500/20 bg-cyan-950/20 px-4 py-2">
            <p className="font-mono-tech text-[10px] tracking-wider text-cyan-300/90">
              VIP ACTIVE
              {membership?.plan || user?.plan
                ? ` · ${String(membership?.plan || user?.plan).toUpperCase()}`
                : ""}{" "}
              · Unlimited chat & signals
            </p>
          </div>
        )}

        <div className="border-b border-cyan-500/10 px-6 py-3 flex items-center justify-between bg-[#020914]/60 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setHistoryOpen((v) => !v)}
              className="md:hidden w-8 h-8 flex items-center justify-center rounded-md border border-cyan-500/30 text-cyan-300 text-xs"
              aria-label="Toggle history"
            >
              ☰
            </button>
            <button
              onClick={() => setSidebarOpen((v) => !v)}
              className="xl:hidden w-8 h-8 flex items-center justify-center rounded-md border border-cyan-500/30 text-cyan-300 text-xs"
              aria-label="Toggle modules"
            >
              ≡
            </button>
            <button
              type="button"
              onClick={handleNewChat}
              className="hidden sm:inline-flex px-3 py-1.5 rounded-md font-mono-tech text-[10px] tracking-widest text-cyan-300 border border-cyan-500/30 hover:bg-cyan-500/10"
            >
              + NEW
            </button>
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/80">
              AI CORE {coreState.toUpperCase()}
            </span>
          </div>
          <div className="hidden sm:flex items-center gap-4 font-mono-tech text-[9px] tracking-widest text-cyan-400/40">
            <span>NEON MEMORY</span>
            {user?.email && <span>{user.email}</span>}
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          <div
            className={`${
              historyOpen ? "flex" : "hidden"
            } md:flex w-56 flex-col border-r border-cyan-500/10 bg-[#020914] shrink-0 z-30`}
          >
            <div className="p-3 border-b border-cyan-500/10 space-y-2">
              <button
                type="button"
                onClick={handleNewChat}
                disabled={sending}
                className="w-full rounded-lg bg-cyan-400 text-black font-display text-xs font-bold tracking-widest py-2.5 hover:bg-cyan-300 disabled:opacity-40"
              >
                + NEW CHAT
              </button>
            </div>
            <div className="flex-1 overflow-y-auto kz-scroll p-2 space-y-0.5">
              <p className="px-2 py-1 font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/30">
                HISTORY
              </p>
              {conversations.length === 0 && (
                <p className="px-2 py-3 text-xs text-cyan-400/40">No past chats yet.</p>
              )}
              {conversations.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => handleOpenConversation(c.id)}
                  className={`w-full text-left rounded-lg px-3 py-2.5 transition-all ${
                    conversationId === c.id
                      ? "bg-cyan-500/15 border border-cyan-500/40 text-white"
                      : "border border-transparent text-cyan-400/60 hover:bg-cyan-950/40 hover:text-cyan-200"
                  }`}
                >
                  <p className="font-mono-tech text-[11px] tracking-wide truncate">{c.title || "Chat"}</p>
                  {c.preview && (
                    <p className="text-[10px] text-cyan-400/35 truncate mt-0.5">{c.preview}</p>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div
            className={`${
              sidebarOpen ? "flex" : "hidden"
            } xl:flex w-44 flex-col border-r border-cyan-500/10 p-3 overflow-y-auto kz-scroll absolute xl:relative inset-y-0 left-0 z-20 bg-[#020914] xl:bg-transparent`}
          >
            <p className="font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/30 px-2 mb-2">
              AI MODULES
            </p>
            {capabilities.map((cap) => (
              <button
                key={cap.name}
                onClick={() => {
                  setCapability(cap.name);
                  setSidebarOpen(false);
                }}
                className={`text-left px-3 py-2 rounded-md mb-0.5 transition-all ${
                  capability === cap.name
                    ? "bg-cyan-500/15 border border-cyan-500/40 text-white"
                    : "border border-transparent text-cyan-400/50 hover:text-cyan-200 hover:bg-cyan-950/30"
                }`}
              >
                <p className="font-mono-tech text-[10px] tracking-widest">{cap.name}</p>
                <p className="font-mono-tech text-[9px] tracking-wider text-cyan-400/30">{cap.desc}</p>
              </button>
            ))}
          </div>

          <div className="flex-1 flex flex-col min-w-0">
            <div className="flex-1 overflow-y-auto kz-scroll px-6 py-6 space-y-5">
              {messages.length === 0 && !historyLoading && (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <AICore state="idle" size={180} />
                  <p className="mt-12 font-mono-tech text-[10px] tracking-[0.4em] text-cyan-400/40">
                    AWAITING INPUT
                  </p>
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

              {historyLoading && (
                <p className="font-mono-tech text-xs text-cyan-400/50">Loading chat…</p>
              )}
              {sending && <ThinkingIndicator phase={thinkingPhase} />}
              <div ref={endRef} />
            </div>

            {error && (
              <div className="px-6 pb-2">
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-2 text-xs text-red-300 font-mono-tech">
                  {error}
                </div>
              </div>
            )}

            {attachError && (
              <div className="px-6 pb-2">
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-2 text-xs text-amber-300 font-mono-tech">
                  {attachError}
                </div>
              </div>
            )}

            {attached && (
              <div className="px-6 pb-2">
                <div className="inline-flex items-center gap-3 bg-cyan-500/10 border border-cyan-500/30 rounded-lg px-3 py-2">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={attached.previewUrl}
                    alt="attachment preview"
                    className="w-12 h-12 object-cover rounded-md border border-cyan-500/20"
                  />
                  <div className="flex flex-col min-w-0">
                    <span className="font-mono-tech text-[10px] tracking-widest text-cyan-200 truncate max-w-[200px]">
                      {attached.name}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={clearAttachment}
                    className="ml-2 w-6 h-6 flex items-center justify-center rounded-md border border-cyan-500/30 text-cyan-300 text-xs"
                    aria-label="Remove attachment"
                  >
                    ✕
                  </button>
                </div>
              </div>
            )}

            {voiceSupported && (
              <div className="px-4 pb-2 flex flex-wrap items-center gap-2">
                <span className="text-[10px] tracking-widest text-cyan-400/50 font-mono-tech uppercase">
                  Voice
                </span>
                {(["slow", "normal", "human", "fast"] as VoiceStyle[]).map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setVoiceStyle(s)}
                    className={`px-2.5 py-1 rounded-md text-[10px] font-mono-tech tracking-wider border ${
                      voiceStyle === s
                        ? "border-cyan-400 bg-cyan-500/15 text-cyan-200"
                        : "border-cyan-500/20 text-cyan-400/50"
                    }`}
                  >
                    {s.toUpperCase()}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => setAutoSpeak((v) => !v)}
                  className={`px-2.5 py-1 rounded-md text-[10px] font-mono-tech tracking-wider border ${
                    autoSpeak
                      ? "border-emerald-400/50 text-emerald-300"
                      : "border-cyan-500/20 text-cyan-400/50"
                  }`}
                >
                  {autoSpeak ? "AUTO ON" : "AUTO OFF"}
                </button>
                {isSpeaking && (
                  <button
                    type="button"
                    onClick={stopSpeaking}
                    className="px-2.5 py-1 rounded-md text-[10px] font-mono-tech border border-red-500/40 text-red-300"
                  >
                    STOP
                  </button>
                )}
              </div>
            )}

            <form
              onSubmit={handleSubmit}
              className="border-t border-cyan-500/10 p-4 bg-[#020914]/60 backdrop-blur-xl"
            >
              <div className="flex items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileInputChange}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={sending}
                  className="w-11 h-11 flex items-center justify-center rounded-lg border border-cyan-500/25 text-cyan-300 disabled:opacity-30"
                  aria-label="Attach image"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                  </svg>
                </button>

                {voiceSupported && (
                  <button
                    type="button"
                    onClick={() => {
                      if (listening) stopListening();
                      else
                        listen((text) => {
                          setInput((prev) => (prev ? `${prev} ${text}` : text));
                        });
                    }}
                    disabled={sending}
                    className={`w-11 h-11 flex items-center justify-center rounded-lg border disabled:opacity-30 ${
                      listening
                        ? "border-emerald-400 bg-emerald-500/20 text-emerald-300"
                        : "border-cyan-500/25 text-cyan-300"
                    }`}
                    aria-label="Voice input"
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8" />
                    </svg>
                  </button>
                )}

                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onPaste={handlePaste}
                  placeholder={`Message KING ZARRY AI [${capability}]...`}
                  disabled={sending}
                  className="flex-1 bg-black/40 border border-cyan-500/25 focus:border-cyan-400 rounded-lg px-4 py-3 text-sm text-white placeholder-cyan-400/30 outline-none disabled:opacity-50 font-mono-tech tracking-wider"
                />
                <button
                  type="submit"
                  disabled={sending || (!input.trim() && !attached)}
                  className="px-5 py-3 rounded-lg bg-cyan-400 text-black font-display text-xs font-bold tracking-[0.2em] hover:bg-cyan-300 disabled:opacity-30"
                >
                  SEND
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
