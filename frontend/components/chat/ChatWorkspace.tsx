"use client";

import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import ChatMessage from "@/components/chat/ChatMessage";
import RobotHead from "@/components/RobotHead";
import VoiceCallUI from "@/components/chat/VoiceCallUI";
import { useChat } from "@/hooks/useChat";
import { useVoice, type VoiceStyle } from "@/hooks/useVoice";
import { useRealtimeVoice } from "@/hooks/useRealtimeVoice";
import { api, type ConversationItem } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import Link from "next/link";
import {
  getMembershipSnapshot,
  type MembershipSnapshot,
} from "@/lib/membership";

interface AttachedImage {
  base64: string;
  mime: string;
  previewUrl: string;
  name: string;
}

const MAX_IMAGE_BYTES = 8 * 1024 * 1024;

const STARTER_SUGGESTIONS = [
  "Give me a signal",
  "What is moving today?",
  "Explain it simply",
  "Plan my day",
] as const;

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
  const { messages, setMessages, sending, error, send, decideApproval, stop: stopChat, clear } = useChat(
    user?.id,
    user?.is_subscribed,
    conversationId
  );
  const [membership, setMembership] = useState<MembershipSnapshot | null>(null);
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [capability] = useState("AI");
  const [attached, setAttached] = useState<AttachedImage | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [voicePanelOpen, setVoicePanelOpen] = useState(false);
  const [callMode, setCallMode] = useState(false);
  const [callMuted, setCallMuted] = useState(false);
  const [callStartedAt, setCallStartedAt] = useState<number | null>(null);
  const [callElapsed, setCallElapsed] = useState(0);
  const callModeRef = useRef(false);
  const callMutedRef = useRef(false);
  const lastVoiceResponseRef = useRef<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const shouldAutoScrollRef = useRef(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const {
    speak,
    speakInstant,
    stop: stopSpeaking,
    speaking: isSpeaking,
    listening,
    listen,
    listenContinuous,
    stopListening,
    error: voiceError,
    supported: voiceSupported,
    style: voiceStyle,
    setVoiceStyle,
    voiceCharacter,
    setVoice,
  } = useVoice();

  const {
    supported: realtimeSupported,
    enabled: realtimeEnabled,
    active: realtimeActive,
    muted: realtimeMuted,
    speaking: realtimeSpeaking,
    listening: realtimeListening,
    start: startRealtime,
    stop: stopRealtime,
    toggleMute: toggleRealtimeMute,
  } = useRealtimeVoice();

  const voiceCallSupported = voiceSupported || (realtimeSupported && realtimeEnabled);

  const refreshConversations = async () => {
    try {
      const list = await api.listConversations();
      setConversations(list);
      onConversationsRefresh?.(list);
    } catch {
      /* ignore */
    }
  };

  // Keep the latest send callback without tying the one-time dashboard handoff
  // to its identity. useChat.send changes as sending/messages state changes; the
  // old [send] effect could cancel its timer after consuming sessionStorage,
  // causing the user's prompt to disappear without ever reaching the API.
  const sendRef = useRef(send);
  useEffect(() => {
    sendRef.current = send;
  }, [send]);

  useEffect(() => {
    const prompt = sessionStorage.getItem("kz-dashboard-prompt");
    if (!prompt) return;
    sessionStorage.removeItem("kz-dashboard-prompt");
    setInput(prompt);
    const timer = window.setTimeout(() => {
      window.dispatchEvent(new CustomEvent("kz-core-state", {
        detail: { state: "thinking", title: "Sending request", detail: prompt.slice(0, 90) },
      }));
      void sendRef.current(prompt).then((result) => {
        const failed = !result;
        window.dispatchEvent(new CustomEvent("kz-core-state", {
          detail: {
            state: failed ? "error" : "idle",
            title: failed ? "Request needs attention" : "Response received",
            detail: failed ? "Open chat to see the error and retry." : "King Zarry AI finished responding.",
          },
        }));
      }).catch(() => {
        window.dispatchEvent(new CustomEvent("kz-core-state", {
          detail: { state: "error", title: "Request failed", detail: "Open chat to see the error and retry." },
        }));
      });
      setInput("");
    }, 120);
    return () => window.clearTimeout(timer);
    // This handoff must run once per ChatWorkspace mount, not whenever send changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    if (!callMode || realtimeActive || sending || !messages.length) return;
    const last = messages[messages.length - 1];
    if (
      last?.role === "assistant" &&
      last.text &&
      !String(last.id || "").startsWith("error") &&
      String(last.id || "") !== lastVoiceResponseRef.current
    ) {
      lastVoiceResponseRef.current = String(last.id || "");
      speakInstant(last.text);
    }
  }, [callMode, messages, sending, speakInstant]);

  useEffect(() => {
    if (!callMode || realtimeActive || callMuted || sending || isSpeaking || listening) return;
    const last = messages[messages.length - 1];
    if (!last || last.role !== "assistant" || !last.text) return;

    const timer = window.setTimeout(() => {
      if (!callMode) return;
      listenContinuous((text) => {
        stopListening();
        void sendVoiceText(text);
      });
    }, 350);

    return () => window.clearTimeout(timer);
  }, [callMode, callMuted, sending, isSpeaking, listening, messages, listenContinuous]);

  useEffect(() => {
    if (!input && inputRef.current) inputRef.current.style.height = "auto";
  }, [input]);

  useEffect(() => {
    if (!autoSpeak || realtimeActive || sending || !messages.length) return;
    const last = messages[messages.length - 1];
    if (last?.role === "assistant" && last.text && !String(last.id || "").startsWith("error")) {
      speak(last.text);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, sending, autoSpeak]);

  useEffect(() => {
    if (!callMode || !callStartedAt) {
      setCallElapsed(0);
      return;
    }
    const tick = () => setCallElapsed(Math.max(0, Math.floor((Date.now() - callStartedAt) / 1000)));
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [callMode, callStartedAt]);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    const updateScrollIntent = () => {
      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      shouldAutoScrollRef.current = distanceFromBottom < 96;
    };
    el.addEventListener("scroll", updateScrollIntent, { passive: true });
    updateScrollIntent();
    return () => el.removeEventListener("scroll", updateScrollIntent);
  }, []);

  useEffect(() => {
    const el = listRef.current;
    if (!el || !shouldAutoScrollRef.current) return;
    const frame = window.requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
    return () => window.cancelAnimationFrame(frame);
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

  const handlePaste: React.ClipboardEventHandler<HTMLTextAreaElement> = (e) => {
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

  const sendVoiceText = async (text: string) => {
    const spokenText = text.trim();
    if (!spokenText || sending || !callModeRef.current) return;
    const res = await send(spokenText, capability);
    if (res && (res as { conversation_id?: string }).conversation_id) {
      const cid = (res as { conversation_id: string }).conversation_id;
      setConversationId(cid);
      refreshConversations();
    }
  };

  const saveRealtimeTranscript = useCallback(async (
    role: "user" | "assistant",
    text: string
  ) => {
    try {
      const saved = await api.saveRealtimeTranscript(conversationId, role, text);
      if (saved.conversation_id && saved.conversation_id !== conversationId) {
        setConversationId(saved.conversation_id);
        void refreshConversations();
      }
    } catch {
      // Audio continues even if transcript persistence is temporarily unavailable.
    }
  }, [conversationId]);

  const playCallStartSound = () => {
    try {
      const AudioContextCtor = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioContextCtor) return;
      const ctx = new AudioContextCtor();
      const now = ctx.currentTime;
      const notes = [
        { frequency: 880, start: 0, duration: 0.16 },
        { frequency: 1174.66, start: 0.2, duration: 0.16 },
        { frequency: 880, start: 0.4, duration: 0.22 },
      ];
      for (const note of notes) {
        const oscillator = ctx.createOscillator();
        const gain = ctx.createGain();
        oscillator.type = "sine";
        oscillator.frequency.setValueAtTime(note.frequency, now + note.start);
        gain.gain.setValueAtTime(0.0001, now + note.start);
        gain.gain.exponentialRampToValueAtTime(0.12, now + note.start + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + note.start + note.duration);
        oscillator.connect(gain);
        gain.connect(ctx.destination);
        oscillator.start(now + note.start);
        oscillator.stop(now + note.start + note.duration + 0.02);
      }
      window.setTimeout(() => void ctx.close(), 1000);
    } catch {
      // Some browsers may block Web Audio; the voice call still starts normally.
    }
  };

  const playCallEndSound = () => {
    try {
      const AudioContextCtor =
        window.AudioContext ||
        (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioContextCtor) return;
      const ctx = new AudioContextCtor();
      const now = ctx.currentTime;
      const notes = [
        { frequency: 659.25, start: 0, duration: 0.16 },
        { frequency: 523.25, start: 0.18, duration: 0.16 },
        { frequency: 392, start: 0.36, duration: 0.28 },
      ];

      for (const note of notes) {
        const oscillator = ctx.createOscillator();
        const gain = ctx.createGain();
        oscillator.type = "sine";
        oscillator.frequency.setValueAtTime(note.frequency, now + note.start);
        gain.gain.setValueAtTime(0.0001, now + note.start);
        gain.gain.exponentialRampToValueAtTime(0.12, now + note.start + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + note.start + note.duration);
        oscillator.connect(gain);
        gain.connect(ctx.destination);
        oscillator.start(now + note.start);
        oscillator.stop(now + note.start + note.duration + 0.02);
      }

      window.setTimeout(() => void ctx.close(), 1000);
    } catch {
      // Some browsers may block Web Audio; ending the call still works normally.
    }
  };

  const startVoiceCall = () => {
    if (!voiceCallSupported || callMode) return;
    playCallStartSound();
    stopSpeaking();
    stopListening();

    const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
    lastVoiceResponseRef.current = lastAssistant?.id ? String(lastAssistant.id) : null;
    callModeRef.current = true;
    callMutedRef.current = false;
    setCallMuted(false);
    setCallStartedAt(Date.now());
    setCallElapsed(0);
    setCallMode(true);

    if (realtimeSupported && realtimeEnabled) {
      void startRealtime(conversationId, (role, text) => {
        void saveRealtimeTranscript(role, text);
      }).then((started) => {
        if (started || !callModeRef.current) return;
        setTimeout(() => {
          if (!callModeRef.current) return;
          listen((text) => { void sendVoiceText(text); });
        }, 150);
      });
      return;
    }

    setTimeout(() => {
      listen((text) => {
        void sendVoiceText(text);
      });
    }, 150);
  };

  const endVoiceCall = () => {
    playCallEndSound();
    callModeRef.current = false;
    callMutedRef.current = false;
    setCallMuted(false);
    setCallStartedAt(null);
    setCallElapsed(0);
    setCallMode(false);
    stopRealtime();
    stopListening();
    stopSpeaking();
  };

  const toggleCallMute = () => {
    if (realtimeActive) {
      toggleRealtimeMute();
      return;
    }
    const next = !callMutedRef.current;
    callMutedRef.current = next;
    setCallMuted(next);
    if (next) {
      stopListening();
      return;
    }
    if (!callModeRef.current || sending || isSpeaking) return;
    window.setTimeout(() => {
      if (!callModeRef.current || callMutedRef.current || sending || isSpeaking) return;
      listenContinuous((text) => { void sendVoiceText(text); });
    }, 120);
  };

  const handleStarterSuggestion = async (suggestion: string) => {
    if (sending) return;
    const res = await send(suggestion, capability);
    if (res && (res as { conversation_id?: string }).conversation_id) {
      const cid = (res as { conversation_id: string }).conversation_id;
      setConversationId(cid);
      void refreshConversations();
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

  useEffect(() => {
    return () => {
      stopRealtime();
      stopListening();
      stopSpeaking();
    };
  }, [stopRealtime, stopListening, stopSpeaking]);

  const isVip = Boolean(user?.is_subscribed || membership?.isVip);
  const callIsMuted = realtimeActive ? realtimeMuted : callMuted;
  const callIsSpeaking = realtimeActive ? realtimeSpeaking : isSpeaking;
  const callIsListening = realtimeActive ? realtimeListening : listening;
  const showSideHistory = !embedMode;
  const callStatus = callIsMuted
    ? "MIC MUTED"
    : callIsSpeaking
      ? "SPEAKING"
      : callIsListening
        ? "LISTENING..."
        : sending
          ? "THINKING..."
          : "READY";
  const callPrompt = [...messages]
    .reverse()
    .find((message) => message.role === "user")
    ?.text?.trim()
    .slice(0, 64);

  // Preserve repeated messages: identical consecutive questions or answers are valid conversation history.
  const visibleMessages = messages;
  const lastAssistantId = [...messages].reverse().find((message) => message.role === "assistant")?.id;

  return (
    <div
      className={
        "relative flex w-full flex-col overflow-hidden text-zinc-100 bg-transparent " +
        (fullScreen ? "h-[100dvh] max-h-[100dvh]" : "h-full min-h-0")
      }
    >
      <div className="relative flex min-h-0 flex-1 overflow-hidden">
        {showSideHistory && historyOpen && (
          <button
            type="button"
            aria-label="Close chat history"
            onClick={() => setHistoryOpen(false)}
            className="absolute inset-0 z-30 bg-black/55 backdrop-blur-[2px] lg:hidden"
          />
        )}
        {showSideHistory && (
          <aside
            aria-label="Chat history"
            className={
              "absolute inset-y-0 left-0 z-40 flex w-[min(84vw,18rem)] flex-col border-r border-cyan-300/10 bg-[#06101b]/[0.98] shadow-2xl backdrop-blur-xl transition-transform lg:relative lg:inset-auto lg:z-auto lg:w-64 lg:shrink-0 lg:translate-x-0 lg:shadow-none " +
              (historyOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0")
            }
          >
            <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-300/20 bg-cyan-300/[0.08] text-lg text-cyan-200 shadow-[0_0_24px_rgba(34,211,238,0.08)]">✦</div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold tracking-wide text-slate-100">King Zarry AI</p>
                  <p className="mt-0.5 text-[9px] uppercase tracking-[0.2em] text-cyan-200/50">Personal AI workspace</p>
                </div>
              </div>
              <button type="button" onClick={() => setHistoryOpen(false)} className="rounded-lg px-2 py-1 text-sm text-slate-400 hover:bg-white/5 hover:text-white lg:hidden" aria-label="Close history">×</button>
            </div>
            <button
              type="button"
              onClick={() => { void handleNewChat(); setHistoryOpen(false); }}
              disabled={sending || callMode}
              className="mx-3 mt-4 flex items-center gap-2 rounded-xl border border-cyan-300/20 bg-cyan-300/[0.07] px-3 py-3 text-left text-sm text-cyan-50 transition hover:border-cyan-200/40 hover:bg-cyan-300/[0.12] disabled:opacity-40"
            >
              <span className="text-lg leading-none">＋</span>
              <span>New conversation</span>
            </button>
            <div className="px-4 pb-2 pt-5 text-[9px] font-semibold uppercase tracking-[0.2em] text-slate-500">Recent conversations</div>
            <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-4">
              {conversations.length ? conversations.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => { void handleOpenConversation(item.id); setHistoryOpen(false); }}
                  className={
                    "mb-1 w-full rounded-lg border px-3 py-2.5 text-left transition " +
                    (item.id === conversationId
                      ? "border-cyan-300/20 bg-cyan-300/[0.08] text-slate-100"
                      : "border-transparent text-slate-400 hover:border-white/[0.06] hover:bg-white/[0.035] hover:text-slate-200")
                  }
                >
                  <span className="block truncate text-xs">{item.title || "Untitled conversation"}</span>
                </button>
              )) : (
                <p className="px-3 py-3 text-xs leading-5 text-slate-500">Your saved conversations will appear here.</p>
              )}
            </div>
            <div className="border-t border-white/[0.06] px-4 py-3 text-[9px] uppercase tracking-[0.16em] text-slate-600">Private workspace</div>
          </aside>
        )}
        <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
      <div aria-hidden="true" className="kz-chat-cosmic-backdrop" />
      <div className="relative inset-x-0 z-10 shrink-0">
        {!isVip && membership && (
          <div className="border-b border-white/5 bg-[#05080f]/90 px-3 py-1.5 flex items-center justify-between gap-2">
            <p className="text-[11px] tracking-wider text-cyan-200/70">
              FREE · {membership.freeMessagesRemaining}/{membership.freeDailyLimit} left today
            </p>
            <Link href="/pricing" className="text-[11px] text-cyan-300 hover:text-white underline underline-offset-2 shrink-0">
              UPGRADE →
            </Link>
          </div>
        )}
        {showSideHistory && (
          <div className="border-b border-white/5 px-3 py-1.5 flex items-center justify-between bg-[#05080f]/40">
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => setHistoryOpen((v) => !v)} className="w-7 h-7 flex items-center justify-center rounded-md border border-cyan-500/20 text-cyan-300/80 text-xs" title="Chats">
                ☰
              </button>
              
            </div>
            <div className="flex items-center gap-1.5">
              {voiceCallSupported && (
                <button
                  type="button"
                  onClick={callMode ? endVoiceCall : startVoiceCall}
                  disabled={sending && !callMode}
                  className={
                    "px-2.5 py-1 rounded-full border text-[9px] tracking-widest transition " +
                    (callMode
                      ? "border-red-400/50 bg-red-500/10 text-red-200"
                      : "border-cyan-400/30 bg-cyan-500/5 text-cyan-200 hover:bg-cyan-500/10")
                  }
                  title={callMode ? "End AI voice call" : "Start AI voice call"}
                >
                  {callMode ? "● END CALL" : "☎ CALL AI"}
                </button>
              )}
              <button type="button" onClick={handleNewChat} disabled={sending || callMode} className="px-2 py-0.5 rounded-md border border-cyan-500/25 text-[9px] tracking-widest text-cyan-200 disabled:opacity-40">
                + NEW
              </button>
            </div>
          </div>
        )}
      </div>

      {embedMode && (
        <div className="absolute inset-x-0 top-0 z-20 flex items-center justify-end border-b border-white/5 bg-[#05080f]/70 px-3 py-1.5 backdrop-blur-sm">
          {voiceCallSupported && (
            <button
              type="button"
              onClick={callMode ? endVoiceCall : startVoiceCall}
              disabled={sending && !callMode}
              className={
                "rounded-full border px-3 py-1.5 text-[9px] tracking-[0.18em] transition " +
                (callMode
                  ? "border-red-400/50 bg-red-500/10 text-red-200"
                  : "border-cyan-400/30 bg-cyan-500/10 text-cyan-200 hover:bg-cyan-500/20")
              }
              title={callMode ? "End AI voice call" : "Start AI voice call"}
            >
              {callMode ? "● END CALL" : "☎ CALL AI"}
            </button>
          )}
        </div>
      )}

      <div
        ref={listRef}
        className="relative z-10 min-h-0 flex-1 overflow-y-auto overscroll-y-none kz-scroll px-3 sm:px-4"
      >
        <div className="mx-auto w-full max-w-2xl space-y-2.5 py-4 pb-28">
          {messages.length === 0 && !historyLoading && (
            <div className="flex flex-col items-center justify-center min-h-[200px] text-center py-8">
              <div className="relative flex h-[124px] w-[124px] items-center justify-center" aria-hidden="true">
                <div className="absolute inset-2 rounded-full border border-cyan-300/20 bg-cyan-400/[0.025] shadow-[0_0_32px_rgba(0,190,255,.12)] animate-[kz-cosmic-ai-wave_5.2s_ease-in-out_infinite]" />
                <div className="absolute inset-0 rounded-full border border-cyan-300/10" />
                {/* Reuse the same King Zarry AI head portrait as the dashboard AI core. */}
                <img src="/human-ai-core.webp" alt="" className="relative z-10 h-[112px] w-[112px] object-contain drop-shadow-[0_0_16px_rgba(0,210,255,.35)]" draggable={false} />
              </div>
              <p className="mt-4 text-lg font-medium tracking-tight text-slate-100">What can I help you with?</p>
              <p className="mt-1 max-w-sm text-sm leading-6 text-slate-400">Ask a question or choose a starting point.</p>
              <div className="mt-5 flex max-w-xl flex-wrap justify-center gap-2">
                {STARTER_SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => void handleStarterSuggestion(suggestion)}
                    disabled={sending}
                    className="rounded-full border border-cyan-300/15 bg-white/[0.025] px-3.5 py-2 text-xs text-slate-300 transition hover:border-cyan-300/35 hover:bg-cyan-300/[0.07] hover:text-white disabled:opacity-40"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {visibleMessages.map((m) => (
            <Fragment key={m.id}>
              {m.role === "assistant" && m.id === lastAssistantId && (sending || Boolean(m.activitySteps?.length)) && (() => {
                const steps = m.activitySteps || [];
                const hasStartedReply = Boolean(m.text?.trim());
                const visibleSteps = steps.slice(-6);
                return (
                  <div className="mb-3 max-w-2xl px-0.5 pt-0.5" role="status" aria-live="polite" aria-label="King Zarry AI activity timeline">
                    <div className="flex items-start gap-3">
                      <RobotHead size={48} className="mt-1" />
                      <div className="min-w-0 flex-1 pt-1">
                        <div className="mb-1.5 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.16em] text-zinc-500">
                          <span className="h-1.5 w-1.5 rounded-full bg-cyan-300 shadow-[0_0_8px_rgba(103,232,249,.5)]" />
                          King Zarry AI · Live activity
                        </div>
                        <div className="space-y-1.5">
                          {visibleSteps.map((step, index) => {
                            const done = step.done;
                            return (
                              <div key={step.label + index} className="flex min-w-0 items-center gap-2 text-xs text-zinc-400">
                                <span className={"flex h-4 w-4 shrink-0 items-center justify-center " + (done ? "text-emerald-300" : "text-cyan-200")} aria-hidden="true">
                                  {done ? <span className="text-[12px] leading-none">✓</span> : <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/15 border-t-cyan-200" />}
                                </span>
                                <span className={"min-w-0 truncate " + (done ? "text-zinc-500" : "text-zinc-300")}>{step.label}</span>
                              </div>
                            );
                          })}
                          {hasStartedReply && !visibleSteps.some((step) => step.label.toLowerCase() === "writing response") ? (
                            <div className="flex items-center gap-2 text-xs text-zinc-300">
                              <span className="h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-white/15 border-t-cyan-200" aria-hidden="true" />
                              <span>Writing response</span>
                            </div>
                          ) : !hasStartedReply && visibleSteps.length === 0 ? (
                            <div className="flex items-center gap-2 text-xs text-zinc-400">
                              <span className="h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-white/15 border-t-cyan-200" aria-hidden="true" />
                              <span>{m.status?.startsWith("KZ AGENT •") ? m.status.slice("KZ AGENT •".length).trim() : "Thinking through your request"}</span>
                            </div>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}
              <ChatMessage
              key={m.id}
              id={m.id}
              role={m.role}
              content={m.text}
              timestamp={m.timestamp}
              status={m.status}
              isError={String(m.id || "").startsWith("error")}
              isStreaming={sending && m.role === "assistant" && m.id === lastAssistantId}
              imagePreviewUrl={m.imagePreviewUrl}
              suggestions={m.suggestions}
              onSpeak={
                m.role === "assistant"
                  ? () => (isSpeaking ? stopSpeaking() : speak(m.text || ""))
                  : undefined
              }
              onSuggestion={
                m.role === "assistant"
                  ? (suggestion) => {
                      setInput(suggestion);
                      void send(suggestion);
                    }
                  : undefined
              }
            />
            {m.role === "assistant" && m.approval && (
              <div className="mt-2 ml-0 max-w-[min(100%,34rem)] rounded-2xl border border-cyan-400/20 bg-[#11161f]/95 p-3 shadow-[0_8px_28px_rgba(0,0,0,.28)]">
                <div className="flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-cyan-400/10 text-cyan-300">✓</span>
                  <div>
                    <div className="text-xs font-medium text-white">Allow King Zarry AI to do this?</div>
                    <div className="mt-0.5 text-[10px] text-zinc-500">
                      {m.approval.operation === "send_gmail" ? "Send this Gmail message" : m.approval.operation === "create_calendar_event" ? "Create this Calendar event" : "Perform this connected-account action"}
                    </div>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" onClick={() => void decideApproval(m.id, "once")} className="rounded-xl border border-cyan-400/25 bg-cyan-400/10 px-3 py-2 text-[10px] font-medium text-cyan-100 transition hover:bg-cyan-400/20 active:scale-95">
                    Allow once
                  </button>
                  <button type="button" onClick={() => void decideApproval(m.id, "always")} className="rounded-xl border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-[10px] font-medium text-emerald-100 transition hover:bg-emerald-400/20 active:scale-95">
                    Allow always
                  </button>
                  <button type="button" onClick={() => void decideApproval(m.id, "reject")} className="rounded-xl border border-red-400/20 bg-red-400/5 px-3 py-2 text-[10px] font-medium text-red-200 transition hover:bg-red-400/10 active:scale-95">
                    Reject
                  </button>
                </div>
                <div className="mt-2 text-[9px] leading-relaxed text-zinc-600">
                  Allow once applies only to this exact action. Allow always saves permission for this type of Google action until you revoke it.
                </div>
              </div>
            )}
            </Fragment>
          ))}

          {historyLoading && <p className="text-xs text-zinc-500">Loading…</p>}
          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</div>
          )}
          {attachError && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">{attachError}</div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      {callMode && (
        <VoiceCallUI
          status={callStatus}
          prompt={callPrompt}
          elapsed={callElapsed}
          muted={callIsMuted}
          speaking={callIsSpeaking}
          listening={callIsListening}
          onMute={toggleCallMute}
          onEnd={endVoiceCall}
          onStopSpeaking={stopSpeaking}
        />
      )}

      <form
        onSubmit={handleSubmit}
        className="relative inset-x-0 z-30 shrink-0 border-t border-white/[0.06] bg-[#0b0b0c]/95 px-3 sm:px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] [transform:translateZ(0)]"
      >
        <div className="mx-auto w-full max-w-2xl">
          {attached && (
            <div className="mb-2 flex items-center gap-2 rounded-lg border border-cyan-500/20 bg-black/40 px-2 py-1.5">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={attached.previewUrl} alt="" className="h-8 w-8 rounded object-cover" />
              <span className="truncate text-xs text-zinc-300">{attached.name}</span>
              <button type="button" onClick={clearAttachment} className="ml-auto text-zinc-400 hover:text-white text-sm">×</button>
            </div>
          )}
          {voiceError && (
            <p role="status" className="mb-2 px-2 text-xs leading-5 text-amber-200/90">{voiceError}</p>
          )}



          {voicePanelOpen && (
            <div className="mb-2 rounded-lg border border-cyan-500/15 bg-black/40 p-2">
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

          {!callMode && (
          <div className="rounded-[26px] border border-white/[0.12] bg-[#1b1b1d] px-3 py-2 shadow-[0_8px_30px_rgba(0,0,0,0.22)] transition-colors focus-within:border-white/20">
            <div className="flex items-end gap-2">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="mb-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/[0.08] text-zinc-300 transition hover:border-cyan-300/40 hover:bg-cyan-300/[0.08] hover:text-cyan-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300"
              title="Upload an image"
              aria-label="Upload an image"
            >
              <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="m12.5 6.5-6.8 6.8a4 4 0 0 0 5.7 5.7l7.1-7.1a5.5 5.5 0 0 0-7.8-7.8l-7.1 7.1" />
              </svg>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileInputChange}
              aria-label="Choose an image to upload"
            />

            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                e.currentTarget.style.height = "auto";
                e.currentTarget.style.height = `${Math.min(e.currentTarget.scrollHeight, 144)}px`;
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  e.currentTarget.form?.requestSubmit();
                }
              }}
              onPaste={handlePaste}
              placeholder="Message King Zarry AI…"
              disabled={sending || callMode}
              aria-label="Message King Zarry AI"
              className="max-h-36 min-w-0 flex-1 resize-none bg-transparent px-1 py-2 text-[15px] leading-6 text-white placeholder-zinc-500 outline-none disabled:opacity-50"
            />

            {voiceSupported && (
              <>
                {!callMode && (
                  <button
                    type="button"
                    onClick={() => (listening ? stopListening() : listen((t) => setInput(t)))}
                    className={"flex h-10 w-10 shrink-0 items-center justify-center rounded-full border transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300 " + (listening ? "border-red-400/40 bg-red-400/10 text-red-300 shadow-[0_0_16px_rgba(248,113,113,.15)]" : "border-white/[0.08] text-zinc-300 hover:border-cyan-300/40 hover:bg-cyan-300/[0.08] hover:text-cyan-100")}
                    title={listening ? "Stop recording" : "Record a voice message"}
                    aria-label={listening ? "Stop recording" : "Record a voice message"}
                    aria-pressed={listening}
                  >
                    {listening ? (
                      <span className="h-3.5 w-3.5 rounded-[3px] bg-current" aria-hidden="true" />
                    ) : (
                      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="9" y="3" width="6" height="12" rx="3" />
                        <path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 18v3m-4 0h8" />
                      </svg>
                    )}
                  </button>
                )}
                <button type="button" onClick={() => setVoicePanelOpen((v) => !v)} className="hidden sm:flex h-8 shrink-0 items-center justify-center rounded-full px-2 text-[9px] tracking-widest text-zinc-500 hover:text-cyan-300" title="Voice">VOICE</button>
              </>
            )}

            {sending ? (
              <button
                type="button"
                onClick={stopChat}
                aria-label="Stop King Zarry AI"
                title="Stop King Zarry AI"
                className="flex h-8 shrink-0 items-center justify-center gap-1.5 rounded-full border border-white/10 bg-[#1d1d1f] px-3 text-[10px] font-medium text-white shadow-[0_4px_14px_rgba(0,0,0,.28)] transition hover:bg-[#29292c] active:scale-95"
              >
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-cyan-500 shadow-[0_0_12px_rgba(34,211,238,.28)]" aria-hidden="true">
                  <span className="h-2 w-2 rounded-[2px] bg-white" />
                </span>
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim() && !attached}
                className="mb-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-30 disabled:bg-zinc-600 disabled:text-zinc-300"
                title="Send"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M12 19V5M12 5l-6 6M12 5l6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            )}
            </div>
          </div>
          )}
        </div>
      </form>
        </div>
      </div>
    </div>
  );
}
