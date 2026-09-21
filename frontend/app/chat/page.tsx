"use client";

import { useEffect, useRef, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import AICore from "@/components/AICore";
import { useChat } from "@/hooks/useChat";
import { useAuth } from "@/hooks/useAuth";

type CoreState = "idle" | "thinking" | "speaking" | "listening" | "error";

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

export default function ChatPage() {
  const { user } = useAuth();
  const { messages, sending, error, send } = useChat();
  const [input, setInput] = useState("");
  const [capability, setCapability] = useState("AI");
  const [coreState, setCoreState] = useState<CoreState>("idle");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setCoreState(sending ? "thinking" : "idle");
  }, [sending]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    await send(text, capability);
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
                    <p className="text-sm text-white/90 whitespace-pre-wrap leading-relaxed">
                      {m.text}
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

            {/* Input */}
            <form
              onSubmit={handleSubmit}
              className="border-t border-cyan-500/10 p-4 bg-[#020914]/60 backdrop-blur-xl"
            >
              <div className="flex items-center gap-2">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={`Message KING ZARRY AI [${capability}]...`}
                  disabled={sending}
                  className="flex-1 bg-black/40 border border-cyan-500/25 focus:border-cyan-400 rounded-lg px-4 py-3 text-sm text-white placeholder-cyan-400/30 outline-none transition-colors disabled:opacity-50 font-mono-tech tracking-wider"
                />
                <button
                  type="submit"
                  disabled={sending || !input.trim()}
                  className="px-5 py-3 rounded-lg bg-cyan-400 text-black font-display text-xs font-bold tracking-[0.2em] hover:bg-cyan-300 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
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
