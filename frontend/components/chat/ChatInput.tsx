"use client";

import React, { useState, useRef, useEffect } from "react";

export interface ChatInputProps {
  value?: string;
  onChange?: (value: string) => void;
  onSubmit?: (value: string) => void;
  onStop?: () => void;
  onAttach?: () => void;
  onVoiceToggle?: () => void;
  isLoading?: boolean;
  isListening?: boolean;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function ChatInput({
  value: externalValue,
  onChange,
  onSubmit,
  onStop,
  onAttach,
  onVoiceToggle,
  isLoading = false,
  isListening = false,
  placeholder = "Ask KING ZARRY AI anything...",
  disabled = false,
  className = "",
}: ChatInputProps) {
  const [internalValue, setInternalValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isControlled = externalValue !== undefined;
  const value = isControlled ? externalValue : internalValue;

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    if (!isControlled) {
      setInternalValue(newValue);
    }
    if (onChange) {
      onChange(newValue);
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
    }
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled && !isLoading && onSubmit) {
        onSubmit(value);
        if (!isControlled) {
          setInternalValue("");
        }
      }
    }
  };

  const handleSubmitClick = () => {
    if (isLoading && onStop) {
      onStop();
    } else if (value.trim() && !disabled && onSubmit) {
      onSubmit(value);
      if (!isControlled) {
        setInternalValue("");
      }
    }
  };

  return (
    <div className={`w-full max-w-4xl mx-auto px-4 ${className}`}>
      {/* Holographic Input Shell */}
      <div className="kz-panel kz-bracket relative bg-black/70 backdrop-blur-md border border-cyan-500/30 shadow-[0_0_30px_rgba(6,182,212,0.15)] rounded-lg p-3 transition-all duration-300 focus-within:border-cyan-400 focus-within:shadow-[0_0_35px_rgba(6,182,212,0.3)]">
        {/* HUD Corner Accents */}
        <div className="kz-hud-corner kz-hud-corner-tl" aria-hidden="true" />
        <div className="kz-hud-corner kz-hud-corner-tr" aria-hidden="true" />
        <div className="kz-hud-corner kz-hud-corner-bl" aria-hidden="true" />
        <div className="kz-hud-corner kz-hud-corner-br" aria-hidden="true" />

        {/* Top Status & AI Core Bar */}
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-cyan-500/15 text-[10px] font-mono">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                isLoading
                  ? "bg-amber-400 animate-ping"
                  : isListening
                  ? "bg-red-400 animate-pulse"
                  : "bg-cyan-400 animate-pulse"
              }`}
              aria-hidden="true"
            />
            <span className="text-cyan-300 uppercase tracking-widest font-semibold">
              KING ZARRY AI CORE
            </span>
          </div>

          <div className="flex items-center gap-2 text-cyan-400/70">
            <span>
              {isLoading ? "THINKING..." : isListening ? "LISTENING..." : "READY"}
            </span>
          </div>
        </div>

        {/* Main Input Field Area */}
        <div className="flex items-end gap-2">
          {/* Attachment / Vision Button */}
          {onAttach && (
            <button
              type="button"
              onClick={onAttach}
              disabled={disabled}
              aria-label="Add visual input or attachment"
              className="p-2 mb-1 rounded bg-black/40 border border-cyan-500/30 text-cyan-400 hover:text-white hover:border-cyan-400 transition-all disabled:opacity-50 shrink-0"
              title="Add Visual Input"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M12 4v16m8-8H4" />
              </svg>
            </button>
          )}

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="flex-1 bg-transparent text-white placeholder-cyan-500/50 text-sm font-sans focus:outline-none resize-none max-h-40 py-2 px-1 leading-relaxed"
          />

          {/* Voice Control Button */}
          {onVoiceToggle && (
            <button
              type="button"
              onClick={onVoiceToggle}
              disabled={disabled}
              aria-label="Toggle voice input"
              className={`p-2 mb-1 rounded border transition-all shrink-0 ${
                isListening
                  ? "bg-red-500/20 border-red-500 text-red-300 shadow-[0_0_15px_rgba(239,68,68,0.4)] animate-pulse"
                  : "bg-black/40 border-cyan-500/30 text-cyan-400 hover:text-white hover:border-cyan-400"
              } disabled:opacity-50`}
              title="Voice Input"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.75}
                  d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z"
                />
              </svg>
            </button>
          )}

          {/* Send / Stop Button */}
          <button
            type="button"
            onClick={handleSubmitClick}
            disabled={disabled || (!isLoading && !value.trim())}
            aria-label={isLoading ? "Stop generation" : "Send message"}
            className={`p-2 mb-1 rounded border transition-all shrink-0 flex items-center justify-center ${
              isLoading
                ? "bg-amber-500/20 border-amber-500 text-amber-300 hover:bg-amber-500/30 shadow-[0_0_15px_rgba(245,158,11,0.3)]"
                : value.trim() && !disabled
                ? "kz-button kz-button-primary bg-cyan-500/20 border-cyan-400 text-cyan-100 hover:bg-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.3)]"
                : "bg-black/30 border-cyan-500/20 text-cyan-500/40 cursor-not-allowed"
            }`}
          >
            {isLoading ? (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            )}
          </button>
        </div>

        {/* Ecosystem Capability Strip */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 mt-2 border-t border-cyan-500/10 text-[9px] font-mono text-cyan-400/60 uppercase">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1 hover:text-cyan-300 transition-colors">
              <span className="w-1 h-1 rounded-full bg-cyan-400" aria-hidden="true" />
              AI
            </span>
            <span className="flex items-center gap-1 hover:text-cyan-300 transition-colors">
              <span className="w-1 h-1 rounded-full bg-cyan-400" aria-hidden="true" />
              VISION
            </span>
            <span className="flex items-center gap-1 hover:text-cyan-300 transition-colors">
              <span className="w-1 h-1 rounded-full bg-cyan-400" aria-hidden="true" />
              VOICE
            </span>
            <span className="flex items-center gap-1 hover:text-cyan-300 transition-colors">
              <span className="w-1 h-1 rounded-full bg-cyan-400" aria-hidden="true" />
              MEMORY
            </span>
            <span className="flex items-center gap-1 hover:text-cyan-300 transition-colors">
              <span className="w-1 h-1 rounded-full bg-cyan-400" aria-hidden="true" />
              AGENTS
            </span>
            <span className="flex items-center gap-1 hover:text-cyan-300 transition-colors">
              <span className="w-1 h-1 rounded-full bg-cyan-400" aria-hidden="true" />
              TOOLS
            </span>
          </div>

          <div className="hidden sm:block text-cyan-400/40">
            SECURE NEURAL LINK
          </div>
        </div>
      </div>
    </div>
  );
}
