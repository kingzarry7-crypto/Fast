import React, { useState } from "react";

export interface ChatMessageProps {
  id?: string;
  role: "user" | "assistant" | "system" | string;
  content: string;
  timestamp?: string;
  model?: string;
  status?: string;
  isStreaming?: boolean;
  isError?: boolean;
  onCopy?: (content: string) => void;
  onRegenerate?: () => void;
  onSpeak?: () => void;
  className?: string;
}

export function ChatMessage({
  role,
  content,
  timestamp,
  model,
  status,
  isStreaming = false,
  isError = false,
  onCopy,
  onRegenerate,
  onSpeak,
  className = "",
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const normalizedRole = role.toLowerCase();
  const isUser = normalizedRole === "user";
  const isSystem = normalizedRole === "system";

  const handleCopy = () => {
    if (onCopy) {
      onCopy(content);
    } else {
      navigator.clipboard.writeText(content);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`flex flex-col w-full my-4 transition-all duration-300 ${
        isUser ? "items-end" : isSystem ? "items-center" : "items-start"
      } ${className}`}
    >
      {/* System Message Treatment */}
      {isSystem ? (
        <div className="w-full max-w-lg px-4 py-2 my-2 text-center kz-panel bg-black/50 border border-cyan-500/20 rounded text-[11px] font-mono text-cyan-400 uppercase tracking-widest">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 inline-block mr-2 animate-pulse" aria-hidden="true" />
          {content}
        </div>
      ) : (
        <div
          className={`relative max-w-3xl w-full p-4 md:p-5 rounded-lg border ${
            isUser
              ? "bg-cyan-950/20 border-cyan-500/30 text-cyan-100 shadow-[0_0_20px_rgba(6,182,212,0.1)] ml-auto"
              : isError
              ? "bg-red-950/30 border-red-500/50 text-red-100 shadow-[0_0_25px_rgba(239,68,68,0.2)]"
              : "kz-panel kz-bracket bg-black/70 backdrop-blur-md border-cyan-500/30 text-white shadow-[0_0_25px_rgba(6,182,212,0.15)]"
          }`}
        >
          {/* HUD Corner Accents for AI Messages */}
          {!isUser && !isError && (
            <>
              <div className="kz-hud-corner kz-hud-corner-tl" aria-hidden="true" />
              <div className="kz-hud-corner kz-hud-corner-tr" aria-hidden="true" />
              <div className="kz-hud-corner kz-hud-corner-bl" aria-hidden="true" />
              <div className="kz-hud-corner kz-hud-corner-br" aria-hidden="true" />
            </>
          )}

          {/* Message Header / Role Indicator */}
          <div className="flex items-center justify-between pb-2 mb-3 border-b border-cyan-500/15 text-[10px] font-mono">
            <div className="flex items-center gap-2">
              {isUser ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-cyan-300" aria-hidden="true" />
                  <span className="text-cyan-200 uppercase tracking-widest font-semibold">
                    OPERATOR
                  </span>
                </>
              ) : (
                <>
                  <span
                    className={`w-2 h-2 rounded-full ${
                      isStreaming ? "bg-amber-400 animate-ping" : "bg-cyan-400 animate-pulse"
                    }`}
                    aria-hidden="true"
                  />
                  <span className="text-cyan-300 uppercase tracking-widest font-semibold">
                    KING ZARRY AI {model ? `[${model}]` : "INTELLIGENCE CORE"}
                  </span>
                </>
              )}
            </div>

            <div className="flex items-center gap-3 text-cyan-400/60">
              {status && <span className="uppercase">{status}</span>}
              {timestamp && <span>{timestamp}</span>}
            </div>
          </div>

          {/* Message Body Content */}
          <div className="text-sm font-sans leading-relaxed whitespace-pre-wrap break-words">
            {content}
            {isStreaming && (
              <span className="inline-block w-2 h-4 ml-1 bg-cyan-400 animate-pulse align-middle" aria-hidden="true" />
            )}
          </div>

          {/* Action Footer for AI Messages */}
          {!isUser && (
            <div className="flex items-center justify-between pt-3 mt-4 border-t border-cyan-500/10 text-[11px] font-mono">
              <div className="flex items-center gap-1.5 text-cyan-400/50">
                <span className="w-1 h-1 rounded-full bg-cyan-400" aria-hidden="true" />
                <span>SECURE PROTOCOL</span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleCopy}
                  className="px-2.5 py-1 bg-black/40 hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 hover:text-white rounded transition-all flex items-center gap-1"
                  title="Copy response"
                >
                  <span>{copied ? "COPIED" : "COPY"}</span>
                </button>

                {onRegenerate && (
                  <button
                    type="button"
                    onClick={onRegenerate}
                    className="px-2.5 py-1 bg-black/40 hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 hover:text-white rounded transition-all"
                    title="Regenerate intelligence output"
                  >
                    REGENERATE
                  </button>
                )}

                {onSpeak && (
                  <button
                    type="button"
                    onClick={onSpeak}
                    className="px-2.5 py-1 bg-black/40 hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 hover:text-white rounded transition-all"
                    title="Synthesize voice output"
                  >
                    SPEAK
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
