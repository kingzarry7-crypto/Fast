import React, { useRef, useEffect } from "react";
import { ChatMessage, ChatMessageProps } from "./ChatMessage";
import { ChatInput, ChatInputProps } from "./ChatInput";

export interface ChatMessageItem extends ChatMessageProps {
  id: string;
}

export interface ChatWindowProps {
  messages?: ChatMessageItem[];
  isLoading?: boolean;
  isStreaming?: boolean;
  inputValue?: string;
  inputPlaceholder?: string;
  isListening?: boolean;
  onInputChange?: (value: string) => void;
  onSubmitMessage?: (value: string) => void;
  onStopGeneration?: () => void;
  onAttachFile?: () => void;
  onVoiceToggle?: () => void;
  onCopyMessage?: (content: string) => void;
  onRegenerateMessage?: () => void;
  onSpeakMessage?: () => void;
  onSelectPrompt?: (prompt: string) => void;
  suggestedPrompts?: string[];
  className?: string;
}

export function ChatWindow({
  messages = [],
  isLoading = false,
  isStreaming = false,
  inputValue = "",
  inputPlaceholder = "Ask KING ZARRY AI anything...",
  isListening = false,
  onInputChange,
  onSubmitMessage,
  onStopGeneration,
  onAttachFile,
  onVoiceToggle,
  onCopyMessage,
  onRegenerateMessage,
  onSpeakMessage,
  onSelectPrompt,
  suggestedPrompts = [
    "ANALYZE MARKET: BTC/USD",
    "REVIEW RECENT INTELLIGENCE ALERTS",
    "SYSTEM HEALTH DIAGNOSTIC",
    "EXECUTE AGENT PROTOCOL",
  ],
  className = "",
}: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div
      className={`kz-panel kz-bracket relative flex flex-col h-full w-full max-w-5xl mx-auto bg-black/60 backdrop-blur-md border border-cyan-500/30 shadow-[0_0_35px_rgba(6,182,212,0.15)] rounded-lg overflow-hidden ${className}`}
    >
      {/* HUD Corner Accents */}
      <div className="kz-hud-corner kz-hud-corner-tl" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-tr" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-bl" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-br" aria-hidden="true" />

      {/* Chat Window Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-cyan-500/20 bg-black/80 z-10">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-3 h-3">
            <span className="absolute w-3 h-3 rounded-full bg-cyan-400 animate-ping opacity-75" aria-hidden="true" />
            <span className="relative w-2 h-2 rounded-full bg-cyan-300" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white tracking-wider flex items-center gap-2">
              KING ZARRY AI
            </h2>
            <p className="text-[10px] font-mono text-cyan-400/70 tracking-widest uppercase">
              INTELLIGENCE COMMUNICATION CHAMBER
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 px-3 py-1 bg-cyan-950/60 border border-cyan-500/30 rounded text-[10px] font-mono text-cyan-300">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" aria-hidden="true" />
          <span>SESSION ONLINE</span>
        </div>
      </div>

      {/* Conversation Scroll Area */}
      <div
        className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4"
        role="log"
        aria-live="polite"
      >
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-6 my-auto">
            <div className="relative flex items-center justify-center w-16 h-16 rounded-full bg-cyan-500/10 border border-cyan-500/30 shadow-[0_0_25px_rgba(6,182,212,0.2)]">
              <span className="w-4 h-4 rounded-full bg-cyan-400 animate-pulse" aria-hidden="true" />
            </div>

            <div className="space-y-2 max-w-md">
              <h3 className="text-base font-bold text-white tracking-wider">
                KING ZARRY AI INTELLIGENCE CORE
              </h3>
              <p className="text-xs font-mono text-cyan-400/80 leading-relaxed">
                Secure communication channel established. Ask anything across markets, vision, memory, or active agent protocols.
              </p>
            </div>

            {/* Suggested Prompts */}
            {suggestedPrompts && suggestedPrompts.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-lg pt-4">
                {suggestedPrompts.map((prompt, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      if (onSelectPrompt) {
                        onSelectPrompt(prompt);
                      } else if (onSubmitMessage) {
                        onSubmitMessage(prompt);
                      }
                    }}
                    className="p-3 text-left bg-black/40 hover:bg-cyan-500/15 border border-cyan-500/20 hover:border-cyan-400 rounded text-xs font-mono text-cyan-200 transition-all shadow-[0_0_10px_rgba(6,182,212,0.05)]"
                  >
                    <span className="text-cyan-400 mr-2">▸</span>
                    {prompt}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                {...msg}
                onCopy={onCopyMessage ? () => onCopyMessage(msg.content) : msg.onCopy}
                onRegenerate={onRegenerateMessage}
                onSpeak={onSpeakMessage}
              />
            ))}

            {/* Loading / Processing Indicator */}
            {isLoading && !isStreaming && (
              <div className="flex items-center space-x-3 p-4 my-2 kz-panel bg-black/50 border border-cyan-500/20 rounded max-w-sm">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" aria-hidden="true" />
                <span className="text-xs font-mono text-cyan-300 uppercase tracking-widest animate-pulse">
                  PROCESSING INTELLIGENCE...
                </span>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Bottom Command Input Console Area */}
      <div className="p-4 border-t border-cyan-500/20 bg-black/90">
        <ChatInput
          value={inputValue}
          onChange={onInputChange}
          onSubmit={onSubmitMessage}
          onStop={onStopGeneration}
          onAttach={onAttachFile}
          onVoiceToggle={onVoiceToggle}
          isLoading={isLoading || isStreaming}
          isListening={isListening}
          placeholder={inputPlaceholder}
        />
      </div>
    </div>
  );
}
