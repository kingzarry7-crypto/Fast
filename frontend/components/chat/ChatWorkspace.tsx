"use client";

import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import ChatMessage from "@/components/chat/ChatMessage";
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
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="font-mono-tech text-[9px] tracking-[0.2em] text-cyan-300/70">
                {sending ? "WORKING" : "READY"}
              </span>
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
        className="relative min-h-0 flex-1 overflow-y-auto overscroll-y-none kz-scroll px-3 sm:px-4"
      >
        <div className="mx-auto w-full max-w-2xl space-y-2.5 py-4 pb-28">
          {showSideHistory && historyOpen && (
            <div className="mb-3 rounded-xl border border-cyan-500/15 bg-black/40 p-2 max-h-40 overflow-y-auto">
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
          )}

          {messages.length === 0 && !historyLoading && (
            <div className="flex flex-col items-center justify-center min-h-[200px] text-center py-8">
              <div className="flex h-[100px] w-[100px] items-center justify-center rounded-full border border-cyan-400/15 bg-cyan-400/[0.03]" aria-hidden="true">
                <span className="h-3 w-3 rounded-full bg-cyan-300/80 shadow-[0_0_18px_rgba(0,240,255,.55)]" />
              </div>
              <p className="mt-4 font-mono-tech text-[10px] tracking-[0.3em] text-cyan-300/70">READY</p>
              <p className="mt-1 text-xs text-zinc-500">Type a message below</p>
            </div>
          )}

          {visibleMessages.map((m) => (
            <Fragment key={m.id}>
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

          {sending && (() => {
            const latestAssistant = [...messages].reverse().find((message) => message.role === "assistant" && message.status);
            const rawStatus = latestAssistant?.status || "";
            const label = rawStatus.startsWith("KZ AGENT •")
              ? `King Zarry AI agent: ${rawStatus.slice("KZ AGENT •".length).trim()}`
              : "King Zarry AI is processing your message…";
            return (
              <div className="flex items-center gap-3 px-1 py-3" aria-live="polite">
                <div className="flex min-w-0 flex-1 items-center gap-2.5">
                  <span className="flex items-center gap-1.5" aria-hidden="true">
                    <span className="h-1.5 w-1.5 rounded-full bg-cyan-300 animate-pulse" />
                    <span className="h-1.5 w-1.5 rounded-full bg-cyan-300 animate-pulse [animation-delay:150ms]" />
                    <span className="h-1.5 w-1.5 rounded-full bg-cyan-300 animate-pulse [animation-delay:300ms]" />
                  </span>
                  <span className="truncate text-xs font-medium tracking-wide text-cyan-200/80">{label}</span>
                </div>
                <button
                  type="button"
                  onClick={stopChat}
                  className="flex h-9 shrink-0 items-center gap-2 rounded-full border border-white/10 bg-[#1d1d1f] px-3.5 text-xs font-medium text-white shadow-[0_4px_14px_rgba(0,0,0,.28)] transition hover:bg-[#29292c] active:scale-95"
                  aria-label="Stop King Zarry AI"
                  title="Stop King Zarry AI"
                >
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-cyan-500 text-white shadow-[0_0_12px_rgba(34,211,238,.28)]">
                    <span className="h-2 w-2 rounded-[2px] bg-white" />
                  </span>
                  <span>Stop</span>
                </button>
              </div>
            );
          })()}

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
        className="relative inset-x-0 z-30 shrink-0 border-t border-white/10 bg-[#05080f]/95 backdrop-blur-md px-3 sm:px-4 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] [transform:translateZ(0)]"
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
          <div className="flex items-center gap-2 rounded-full border border-zinc-600/60 bg-zinc-900/90 px-2 py-1.5 shadow-lg shadow-black/40">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-zinc-400 hover:bg-zinc-800 hover:text-white"
              title="Attach"
            >
              +
            </button>
            <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileInputChange} />

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
              className="max-h-36 min-w-0 flex-1 resize-none bg-transparent px-1 py-1.5 text-sm leading-6 text-white placeholder-zinc-500 outline-none disabled:opacity-50"
            />

            {voiceSupported && (
              <>
                {!callMode && <button type="button" onClick={() => (listening ? stopListening() : listen((t) => setInput(t)))} className={"hidden sm:flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[10px] " + (listening ? "text-red-300" : "text-zinc-500 hover:text-cyan-300")} title="Mic">{listening ? "■" : "🎤"}</button>}
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
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-cyan-500 shadow-[0_0_12px_rgba(34,211,238,.28)]">
                  <span className="h-2 w-2 rounded-[2px] bg-white" />
                </span>
                <span className="hidden sm:inline">Stop</span>
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim() && !attached}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-cyan-400/25 bg-[#07111d] text-cyan-200 shadow-[0_0_14px_rgba(0,240,255,0.08)] hover:bg-cyan-500/10 hover:border-cyan-300/50 disabled:opacity-30 disabled:bg-zinc-800 disabled:text-zinc-500"
                title="Send"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M12 19V5M12 5l-6 6M12 5l6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            )}
          </div>
          )}
        </div>
      </form>
    </div>
  );
}
