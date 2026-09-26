"use client";

import { useEffect, useRef, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import AICore from "@/components/AICore";
import ChatMessage, { ThinkingIndicator } from "@/components/chat/ChatMessage";
import { useChat } from "@/hooks/useChat";
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
  const { messages, sending, error, send } = useChat(
    user?.id,
    user?.is_subscribed
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
  const endRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refreshMembership = () =>
    setMembership(getMembershipSnapshot(user?.id));

  useEffect(() => {
    refreshMembership();
    window.addEventListener("kz-membership-change", refreshMembership);
    return () =>
      window.removeEventListener("kz-membership-change", refreshMembership);
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
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

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
    await send(effectiveText, capability, payloadImage);
  };

  const isVip = Boolean(user?.is_subscribed || membership?.isVip);

  return (
    <ProtectedRoute>
      <div className="flex flex-col h-screen bg-[#0a0a0b] text-zinc-100">
        <div className="border-b border-zinc-800/80 px-6 py-3 flex items-center justify-between bg-[#0a0a0b]/90 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen((v) => !v)}
              className="xl:hidden w-8 h-8 flex items-center justify-center rounded-md border border-zinc-700 text-zinc-300 text-xs"
              aria-label="Toggle modules"
            >
              ≡
            </button>
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[11px] tracking-wide text-zinc-400">
              {coreState === "thinking"
                ? thinkingPhase === "reading"
                  ? "Reading…"
                  : thinkingPhase === "responding"
                    ? "Responding…"
                    : "Thinking…"
                : "Ready"}
            </span>
          </div>
          <div className="hidden sm:flex items-center gap-4 text-[11px] text-zinc-500">
            {user?.email && <span>{user.email}</span>}
          </div>
        </div>

        {!isVip && membership && (
          <div className="px-6 py-2 border-b border-zinc-800/80 bg-zinc-900/40 flex flex-wrap items-center justify-between gap-2">
            <p className="text-[11px] text-zinc-400">
              Free · {membership.freeMessagesRemaining}/
              {membership.freeDailyLimit} messages left today · Signals need VIP
            </p>
            <Link
              href="/pricing"
              className="text-[11px] text-cyan-400 hover:text-cyan-300"
            >
              Upgrade →
            </Link>
          </div>
        )}

        {isVip && (
          <div className="px-6 py-2 border-b border-zinc-800/80 bg-zinc-900/20">
            <p className="text-[11px] text-zinc-400">
              VIP active
              {membership?.plan || user?.plan
                ? ` · ${String(membership?.plan || user?.plan)}`
                : ""}
            </p>
          </div>
        )}

        <div className="flex flex-1 overflow-hidden">
          <div
            className={`${
              sidebarOpen ? "flex" : "hidden"
            } xl:flex w-52 flex-col border-r border-zinc-800/80 p-3 overflow-y-auto absolute xl:relative inset-y-0 left-0 z-20 bg-[#0a0a0b] xl:bg-transparent`}
          >
            <p className="text-[10px] tracking-widest text-zinc-600 px-2 mb-2 uppercase">
              Modules
            </p>
            {capabilities.map((cap) => (
              <button
                key={cap.name}
                onClick={() => {
                  setCapability(cap.name);
                  setSidebarOpen(false);
                }}
                className={`text-left px-3 py-2 rounded-lg mb-0.5 transition-all text-sm ${
                  capability === cap.name
                    ? "bg-zinc-800 text-white"
                    : "text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900"
                }`}
              >
                <p className="font-medium">{cap.name}</p>
                <p className="text-[10px] text-zinc-600">{cap.desc}</p>
              </button>
            ))}
          </div>

          <div className="flex-1 flex flex-col min-w-0">
            <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-4">
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <AICore state="idle" size={180} />
                  <p className="mt-10 text-sm text-zinc-500">
                    How can King Zarry AI help you today?
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
                  isError={m.id.startsWith("error")}
                  imagePreviewUrl={m.imagePreviewUrl}
                />
              ))}

              {sending && <ThinkingIndicator phase={thinkingPhase} />}

              <div ref={endRef} />
            </div>

            {error && (
              <div className="px-6 pb-2">
                <div className="bg-red-950/40 border border-red-500/30 rounded-lg px-4 py-2 text-xs text-red-300">
                  {error}
                </div>
              </div>
            )}

            {attachError && (
              <div className="px-6 pb-2">
                <div className="bg-amber-950/30 border border-amber-500/30 rounded-lg px-4 py-2 text-xs text-amber-200">
                  {attachError}
                </div>
              </div>
            )}

            {attached && (
              <div className="px-6 pb-2">
                <div className="inline-flex items-center gap-3 bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={attached.previewUrl}
                    alt="attachment preview"
                    className="w-12 h-12 object-cover rounded-md"
                  />
                  <div className="flex flex-col min-w-0">
                    <span className="text-xs text-zinc-300 truncate max-w-[200px]">
                      {attached.name}
                    </span>
                    <span className="text-[10px] text-zinc-600">{attached.mime}</span>
                  </div>
                  <button
                    type="button"
                    onClick={clearAttachment}
                    className="ml-2 w-6 h-6 flex items-center justify-center rounded-md text-zinc-400 hover:bg-zinc-800 text-xs"
                    aria-label="Remove attachment"
                  >
                    ✕
                  </button>
                </div>
              </div>
            )}

            <form
              onSubmit={handleSubmit}
              className="border-t border-zinc-800/80 p-4 bg-[#0a0a0b]"
            >
              <div className="flex items-end gap-2 max-w-3xl mx-auto">
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
                  className="w-10 h-10 flex items-center justify-center rounded-xl border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900 disabled:opacity-30"
                  aria-label="Attach image"
                  title="Attach image"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                  </svg>
                </button>

                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onPaste={handlePaste}
                  placeholder="Message King Zarry AI…"
                  disabled={sending}
                  className="flex-1 bg-zinc-900 border border-zinc-700 focus:border-zinc-500 rounded-xl px-4 py-3 text-sm text-zinc-100 placeholder-zinc-600 outline-none disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={sending || (!input.trim() && !attached)}
                  className="px-4 py-3 rounded-xl bg-zinc-100 text-zinc-900 text-sm font-semibold hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  Send
                </button>
              </div>
              <p className="mt-2 text-center text-[10px] text-zinc-600">
                Paste an image or click 📎 · Max 8 MB
              </p>
            </form>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
