"use client";

import { useEffect, useRef, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import AICore from "@/components/AICore";
import LinkifiedText from "@/components/LinkifiedText";
import { useChat } from "@/hooks/useChat";
import { useAuth } from "@/hooks/useAuth";

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
  const { messages, sending, error, send } = useChat();
  const [input, setInput] = useState("");
  const [capability, setCapability] = useState("AI");
  const [coreState, setCoreState] = useState<CoreState>("idle");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [attached, setAttached] = useState<AttachedImage | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setCoreState(sending ? "thinking" : "idle");
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
      // revoke previous preview if user replaces the file
      if (attached?.previewUrl) URL.revokeObjectURL(attached.previewUrl);
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

  // `revoke` = true only when user manually clears or replaces.
  // When sending, keep the blob URL alive so the picture stays in chat history.
  const clearAttachment = (revoke = true) => {
    if (revoke && attached?.previewUrl) URL.revokeObjectURL(attached.previewUrl);
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
    clearAttachment(false); // don't revoke — keep the preview alive in chat

    const effectiveText =
      text || (hasImage ? "What do you see in this image?" : "");
    await send(effectiveText, capability, payloadImage);
  };

  return (
    <ProtectedRoute>
      <div className="flex flex-col h-screen">
        {/* Top bar */}
        <div className="border-b border-cyan-500/10 px-6 py-3 flex items-center justify-between bg-[#020914]/60 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen((v) => !v)}
              className="xl:hidden w-8 h-8 flex items-center justify-center rounded-md border border-cyan-500/30 text-cyan-300 text-xs"
              aria-label="Toggle modules"
            >
              ≡
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
          {/* Module sidebar */}
          <div
            className={`${
              sidebarOpen ? "flex" : "hidden"
            } xl:flex w-52 flex-col border-r border-cyan-500/10 p-3 overflow-y-auto kz-scroll absolute xl:relative inset-y-0 left-0 z-20 bg-[#020914] xl:bg-transparent`}
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
                <p className="font-mono-tech text-[10px] tracking-widest">
                  {cap.name}
                </p>
                <p className="font-mono-tech text-[9px] tracking-wider text-cyan-400/30">
                  {cap.desc}
                </p>
              </button>
            ))}
          </div>

          {/* Chat area */}
          <div className="flex-1 flex flex-col min-w-0">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto kz-scroll px-6 py-6 space-y-5">
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <AICore state="idle" size={180} />
                  <p className="mt-12 font-mono-tech text-[10px] tracking-[0.4em] text-cyan-400/40">
                    AWAITING INPUT
                  </p>
                </div>
              )}

              {messages.map((m) => (
                <div
                  key={m.id}
                  className={`flex ${
                    m.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[80%] rounded-xl px-4 py-3 ${
                      m.role === "user"
                        ? "bg-cyan-500/15 border border-cyan-500/30"
                        : m.id.startsWith("error")
                        ? "bg-red-500/10 border border-red-500/30"
                        : "kz-glass"
                    }`}
                  >
                    {m.status && (
                      <p className="font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/40 mb-1.5">
                        {m.status}
                      </p>
                    )}

                    {/* NEW: show attached image inside the bubble */}
                    {m.imagePreviewUrl && (
                      <div className="mb-2">
                        <a
                          href={m.imagePreviewUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-block"
                        >
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={m.imagePreviewUrl}
                            alt={m.imageName || "attachment"}
                            className="rounded-lg border border-cyan-500/20 max-w-full max-h-[300px] object-contain hover:border-cyan-400 transition-colors"
                          />
                        </a>
                        {m.imageName && (
                          <p className="mt-1 font-mono-tech text-[9px] tracking-widest text-cyan-400/40 truncate max-w-[280px]">
                            📎 {m.imageName}
                          </p>
                        )}
                      </div>
                    )}

                    {/* NEW: render text with clickable links & inline images */}
                    <p className="text-sm text-white/90 whitespace-pre-wrap leading-relaxed">
                      <LinkifiedText text={m.text} />
                    </p>

                    <div className="flex items-center justify-between mt-2 gap-4">
                      {m.capability && (
                        <span className="font-mono-tech text-[9px] tracking-widest text-cyan-400/30">
                          {m.capability}
                        </span>
                      )}
                      <span className="font-mono-tech text-[9px] tracking-widest text-cyan-400/30">
                        {m.timestamp}
                      </span>
                    </div>
                  </div>
                </div>
              ))}

              {sending && (
                <div className="flex justify-start">
                  <div className="kz-glass rounded-xl px-5 py-4 flex items-center gap-2">
                    <span className="kz-typing-dot w-1.5 h-1.5 rounded-full bg-cyan-400" />
                    <span className="kz-typing-dot w-1.5 h-1.5 rounded-full bg-cyan-400" />
                    <span className="kz-typing-dot w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  </div>
                </div>
              )}

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

            {/* Pending attachment preview */}
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
                    <span className="font-mono-tech text-[9px] tracking-widest text-cyan-400/40">
                      {attached.mime}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => clearAttachment(true)}
                    className="ml-2 w-6 h-6 flex items-center justify-center rounded-md border border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/40 text-xs"
                    aria-label="Remove attachment"
                  >
                    ✕
                  </button>
                </div>
              </div>
            )}

            {/* Input */}
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
                  className="w-11 h-11 flex items-center justify-center rounded-lg border border-cyan-500/25 text-cyan-300 hover:border-cyan-400 hover:bg-cyan-950/40 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
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
                  placeholder={`Message KING ZARRY AI [${capability}]...`}
                  disabled={sending}
                  className="flex-1 bg-black/40 border border-cyan-500/25 focus:border-cyan-400 rounded-lg px-4 py-3 text-sm text-white placeholder-cyan-400/30 outline-none transition-colors disabled:opacity-50 font-mono-tech tracking-wider"
                />
                <button
                  type="submit"
                  disabled={sending || (!input.trim() && !attached)}
                  className="px-5 py-3 rounded-lg bg-cyan-400 text-black font-display text-xs font-bold tracking-[0.2em] hover:bg-cyan-300 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  SEND
                </button>
              </div>
              <p className="mt-2 font-mono-tech text-[9px] tracking-widest text-cyan-400/30">
                Tip: paste an image (Ctrl+V) or click 📎 to attach. Max 8 MB.
              </p>
            </form>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
