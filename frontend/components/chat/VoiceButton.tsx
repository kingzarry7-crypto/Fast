import React from "react";

export interface VoiceButtonProps {
  isListening?: boolean;
  isLoading?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  className?: string;
  title?: string;
  ariaLabel?: string;
}

export function VoiceButton({
  isListening = false,
  isLoading = false,
  disabled = false,
  onClick,
  className = "",
  title = "Voice Input",
  ariaLabel = "Toggle voice input",
}: VoiceButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      title={title}
      className={`relative group flex items-center justify-center p-2.5 rounded-lg border transition-all duration-300 shrink-0 ${
        isListening
          ? "bg-red-500/25 border-red-400 text-red-200 shadow-[0_0_20px_rgba(239,68,68,0.5)] animate-pulse"
          : isLoading
          ? "bg-amber-500/20 border-amber-400/80 text-amber-200 shadow-[0_0_15px_rgba(245,158,11,0.3)] animate-pulse"
          : "bg-black/60 backdrop-blur-md border-cyan-500/30 text-cyan-400 hover:text-white hover:border-cyan-400 hover:shadow-[0_0_15px_rgba(6,182,212,0.3)]"
      } disabled:opacity-40 disabled:cursor-not-allowed ${className}`}
    >
      {/* HUD Corner Accents for Cinematic Tech Feel */}
      <div className="absolute -top-0.5 -left-0.5 w-1 h-1 border-t border-l border-cyan-400 pointer-events-none opacity-60 group-hover:opacity-100 transition-opacity" aria-hidden="true" />
      <div className="absolute -top-0.5 -right-0.5 w-1 h-1 border-t border-r border-cyan-400 pointer-events-none opacity-60 group-hover:opacity-100 transition-opacity" aria-hidden="true" />
      <div className="absolute -bottom-0.5 -left-0.5 w-1 h-1 border-b border-l border-cyan-400 pointer-events-none opacity-60 group-hover:opacity-100 transition-opacity" aria-hidden="true" />
      <div className="absolute -bottom-0.5 -right-0.5 w-1 h-1 border-b border-r border-cyan-400 pointer-events-none opacity-60 group-hover:opacity-100 transition-opacity" aria-hidden="true" />

      {/* Active Listening Pulse Halo */}
      {isListening && (
        <span
          className="absolute inset-0 rounded-lg border border-red-400 animate-ping opacity-50 pointer-events-none"
          aria-hidden="true"
        />
      )}

      {/* Loading Spin Halo */}
      {isLoading && (
        <span
          className="absolute inset-0 rounded-lg border border-amber-400/50 animate-spin pointer-events-none"
          aria-hidden="true"
        />
      )}

      {/* Microphone Icon & Mini Core Dot */}
      <div className="relative flex items-center justify-center">
        <svg
          className={`w-4 h-4 transition-transform duration-300 ${isListening ? "scale-110 text-red-300" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.75}
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z"
          />
        </svg>

        {/* Tiny AI Core Indicator */}
        <span
          className={`absolute -bottom-1 -right-1 w-1.5 h-1.5 rounded-full transition-colors ${
            isListening
              ? "bg-red-400 animate-pulse"
              : isLoading
              ? "bg-amber-400 animate-ping"
              : "bg-cyan-400 shadow-[0_0_6px_rgba(6,182,212,0.8)]"
          }`}
          aria-hidden="true"
        />
      </div>
    </button>
  );
}
