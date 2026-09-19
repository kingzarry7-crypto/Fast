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
  const endRef = useRef<HTMLDivElement>(null);

  // Sync core state with sending
  useEffect(() => {
    if (sending) setCoreState("thinking");
    else setCoreState("idle");
  }, [sending]);

  // Auto-scroll
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
        {/* Header */}
        <div className="border-b border-cyan-500/10 px-6 py-3 flex items-center justify-between bg-[#020914]/60 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-mono text-cyan-400/80 tracking-widest">
              AI CORE {coreState.toUpperCase()}
            </span>
          </div>
          <div className="flex items-center gap-4 text-[10px] font-mono text-cyan-400/40 tracking-widest">
            <span>NEON MEMORY</span>
            {user?.email && <span>{user.email}</span>}
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Capability bar */}
          <div className="hidden xl:flex w-52 flex-col border-r border-cyan-500/10 p-3 overflow-y-auto kz-scroll">
            <p className="text-[9px] font-mono text-cyan-400/30 tracking-[0.3em] px-2 mb-2">
              AI MODULES
            </p>
            {capabilities.map((cap) => (
              <button
                key={cap.name}
                onClick={() => setCapability(cap.name)}
                className={`text-left px-3 py-2 rounded-md mb-0.5 transition-all ${
                  capability === cap.name
                    ? "bg-cyan-500/15 border border-cyan-500/40 text-white"
                    : "border border-transparent text-cyan-400/50 hover:text-cyan-200 hover:bg-cyan-950/30"
                }`}
              >
                <p className="text-[11px] font-mono tracking-wider">
                  {cap.name}
                </p>
                <p className="text-[9px] text-cyan-400/30">{cap.desc}</p>
              </button>
            ))}
          </div>

          {/* Chat area */}
          <div className="flex-1 flex flex-col min-w-0">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto kz-scroll px-6 py-6 space-y-5">
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <AICore state="idle" size={140} />
                  <p className="mt-10 text-xs font-mono text-cyan-400/40 tracking-widest">
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
                    className={`max-w-[75%] rounded-xl px-4 py-3 ${
                      m.role === "user"
                        ? "bg-cyan-500/15 border border-cyan-500/30"
                        : m.id.startsWith("error")
                        ? "bg-red-500/10 border border-red-500/30"
                        : "bg-[#031322]/80 border border-cyan-500/15"
                    }`}
                  >
                    {m.status && (
                      <p className="text-[9px] font-mono text-cyan-400/40 tracking-widest mb-1.5">
                        {m.status}
                      </p>
                    )}
                    <p className="text-sm text-white/90 whitespace-pre-wrap leading-relaxed">
                      {m.text}
                    </p>
                    <div className="flex items-center justify-between mt-2 gap-4">
                      {m.capability && (
                        <span className="text-[9px] font-mono text-cyan-400/30">
                          {m.capability}
                        </span>
                      )}
                      <span className="text-[9px] font-mono text-cyan-400/30">
                        {m.timestamp}
                      </span>
                    </div>
                  </div>
                </div>
              ))}

              {sending && (
                <div className="flex justify-start">
                  <div className="bg-[#031322]/80 border border-cyan-500/15 rounded-xl px-5 py-4 flex items-center gap-2">
                    <span className="kz-typing-dot w-1.5 h-1.5 rounded-full bg-cyan-400" />
                    <span className="kz-typing-dot w-1.5 h-1.5 rounded-full bg-cyan-400" />
                    <span className="kz-typing-dot w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  </div>
                </div>
              )}

              <div ref={endRef} />
            </div>

            {/* Error banner */}
            {error && (
              <div className="px-6 pb-2">
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-2 text-xs text-red-300 font-mono">
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
                  className="flex-1 bg-[#031322]/80 border border-cyan-500/20 focus:border-cyan-500/50 rounded-lg px-4 py-3 text-sm text-white placeholder-cyan-400/30 outline-none transition-colors disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={sending || !input.trim()}
                  className="px-5 py-3 rounded-lg bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 text-xs font-mono tracking-widest hover:bg-cyan-500/30 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
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
