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

export default function ChatWorkspace({ fullScreen = true }: { fullScreen?: boolean }) {
  const { user } = useAuth();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(min-width: 768px)");
    const apply = () => setHistoryOpen(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

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
    } catch {
      /* API may not be ready */
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
      <div className={`flex flex-col min-h-0 overflow-hidden bg-[#212121] text-zinc-100 ${fullScreen ? "h-[100dvh]" : "h-[min(760px,calc(100dvh-2rem))] rounded-2xl border border-zinc-800 shadow-2xl"}`}>
        {!isVip && membership && (
          <div className="border-b border-zinc-800 bg-[#212121] px-4 py-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <p className="text-xs tracking-wider text-zinc-300">
              FREE TIER · Normal chat allowed · Signals / plans / alerts require
              VIP · {membership.freeMessagesRemaining}/
              {membership.freeDailyLimit} messages left today
            </p>
            <Link
              href="/pricing"
              className="text-xs tracking-normal text-zinc-300 hover:text-white underline underline-offset-2 shrink-0"
            >
              UPGRADE →
            </Link>
          </div>
        )}
        {isVip && (
          <div className="border-b border-zinc-800 bg-[#212121] px-4 py-2">
            <p className="text-xs tracking-wider text-zinc-300">
              VIP ACTIVE
              {membership?.plan || user?.plan
                ? ` · ${String(membership?.plan || user?.plan).toUpperCase()}`
                : ""}{" "}
              · Unlimited chat & signals
            </p>
          </div>
        )}

        <div className="border-b border-zinc-800 px-4 sm:px-6 py-3 flex items-center justify-between bg-[#212121] backdrop-blur-xl shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setHistoryOpen((v) => !v)}
              className="md:hidden w-8 h-8 flex items-center justify-center rounded-md border border-zinc-700 text-zinc-300 text-xs"
              aria-label="Toggle history"
              title="Chat history"
            >
              ☰
            </button>
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs tracking-normal text-zinc-300">
              AI CORE {coreState.toUpperCase()}
              {coreState === "thinking"
                ? thinkingPhase === "reading"
                  ? " · READING"
                  : thinkingPhase === "responding"
                    ? " · RESPONDING"
                    : " · THINKING"
                : ""}
            </span>
          </div>
          <div className="hidden sm:flex items-center gap-4 text-xs tracking-normal text-zinc-500">
            <span>AI memory</span>
            {user?.email && <span>{user.email}</span>}
          </div>
        </div>

        <div className="flex flex-1 min-h-0 overflow-hidden">
          <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
          {/* AI MODULES — hidden */}
          <div className="hidden" aria-hidden="true">
            {capabilities.map((cap) => (
              <span key={cap.name}>{cap.name}</span>
            ))}
          </div>

            <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain kz-scroll px-4 sm:px-6 py-4 sm:py-6 space-y-5">
              {messages.length === 0 && !historyLoading && (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <AICore state="idle" size={180} />
                  <p className="mt-12 text-xs tracking-normal text-zinc-500">
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
                      ? () =>
                          isSpeaking ? stopSpeaking() : speak(m.text || "")
                      : undefined
                  }
                />
              ))}

              {historyLoading && (
                <p className="text-sm text-zinc-400">
                  Loading chat…
                </p>
              )}
              {sending && <ThinkingIndicator phase={thinkingPhase} />}
              <div ref={endRef} />
            </div>

            {error && (
              <div className="px-6 pb-2">
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-2 text-xs text-red-300 font-sans">
                  {error}
                </div>
              </div>
            )}

            {attachError && (
              <div className="px-6 pb-2">
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-2 text-xs text-amber-300 font-sans">
                  {attachError}
                </div>
              </div>
            )}

            {attached && (
              <div className="px-6 pb-2">
                <div className="inline-flex items-center gap-3 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={attached.previewUrl}
                    alt="attachment preview"
                    className="w-12 h-12 object-cover rounded-md border border-zinc-700"
                  />
                  <div className="flex flex-col min-w-0">
                    <span className="text-xs tracking-normal text-zinc-200 truncate max-w-[200px]">
                      {attached.name}
                    </span>
                    <span className="text-xs tracking-normal text-zinc-500">
                      {attached.mime}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={clearAttachment}
                    className="ml-2 w-6 h-6 flex items-center justify-center rounded-md border border-zinc-700 text-zinc-300 hover:bg-zinc-900 text-xs"
                    aria-label="Remove attachment"
                  >
                    ×
                  </button>
                </div>
              </div>
            )}

            <form
              onSubmit={handleSubmit}
              className="border-t border-zinc-800 px-4 sm:px-6 py-4 bg-[#212121]"
            >
              <div className="flex flex-wrap items-center gap-2 mb-3">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-3 py-1.5 rounded-md border border-zinc-700 text-xs tracking-normal text-zinc-300 hover:bg-zinc-800"
                >
                  📎
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleFileInputChange}
                />
                {voiceSupported && (
                  <>
                    <button
                      type="button"
                      onClick={() =>
                        listening ? stopListening() : listen((t) => setInput(t))
                      }
                      className={`px-3 py-1.5 rounded-md border text-xs tracking-normal ${
                        listening
                          ? "border-red-400/50 text-red-300 bg-red-500/10"
                          : "border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                      }`}
                    >
                      {listening ? "STOP MIC" : "MIC"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setVoicePanelOpen((v) => !v)}
                      className="px-3 py-1.5 rounded-md border border-zinc-700 text-xs tracking-normal text-zinc-300 hover:bg-zinc-800"
                    >
                      VOICE
                    </button>
                    <button
                      type="button"
                      onClick={() => setAutoSpeak((v) => !v)}
                      className={`px-3 py-1.5 rounded-md border text-xs tracking-normal ${
                        autoSpeak
                          ? "border-zinc-500/50 text-zinc-200 bg-zinc-800"
                          : "border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                      }`}
                    >
                      AUTO {autoSpeak ? "ON" : "OFF"}
                    </button>
                  </>
                )}
              </div>

              {voicePanelOpen && (
                <div className="mb-3 p-3 rounded-lg border border-zinc-700 bg-[#2a2a2a] space-y-2">
                  <p className="text-xs tracking-normal text-zinc-500">
                    CHARACTER
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {(["bella", "male"] as const).map((v) => (
                      <button
                        key={v}
                        type="button"
                        onClick={() => setVoice(v)}
                        className={`px-2.5 py-1 rounded-md text-[9px] font-sans tracking-normal border ${
                          voiceCharacter === v
                            ? "border-zinc-500 text-zinc-200 bg-zinc-800"
                            : "border-zinc-700 text-zinc-400"
                        }`}
                      >
                        {v.toUpperCase()}
                      </button>
                    ))}
                  </div>
                  <p className="text-xs tracking-normal text-zinc-500">
                    SPEED
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {(["slow", "normal", "human", "fast"] as VoiceStyle[]).map(
                      (s) => (
                        <button
                          key={s}
                          type="button"
                          onClick={() => setVoiceStyle(s)}
                          className={`px-2.5 py-1 rounded-md text-[9px] font-sans tracking-normal border ${
                            voiceStyle === s
                              ? "border-zinc-500 text-zinc-200 bg-zinc-800"
                              : "border-zinc-700 text-zinc-400"
                          }`}
                        >
                          {s.toUpperCase()}
                        </button>
                      )
                    )}
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onPaste={handlePaste}
                  placeholder="Message KING ZARRY AI..."
                  disabled={sending}
                  className="flex-1 bg-[#2a2a2a] border border-zinc-700 focus:border-zinc-500 rounded-lg px-4 py-3 text-sm text-white placeholder-zinc-500 outline-none transition-colors disabled:opacity-50 tracking-normal"
                />
                <button
                  type="submit"
                  disabled={sending || (!input.trim() && !attached)}
                  className="px-5 py-3 rounded-lg bg-white text-black font-display text-xs font-bold tracking-normal hover:bg-zinc-200 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  SEND
                </button>
              </div>
              <p className="mt-2 text-xs tracking-normal text-zinc-500 text-center">
                Tip: paste an image (Ctrl+V) or click 📎 to attach. Max 8 MB.
              </p>
            </form>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
