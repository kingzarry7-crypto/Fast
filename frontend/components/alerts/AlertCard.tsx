import React from "react";
export type AlertType =
  | "MARKET"
  | "AI"
  | "NEWS"
  | "SYSTEM"
  | "AGENT"
  | "SECURITY";
export type AlertSeverity =
  | "INFO"
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL";
export interface AlertCardProps {
  id?: string;
  type?: AlertType | string;
  severity?: AlertSeverity | string;
  title: string;
  description: string;
  timestamp?: string;
  status?: string;
  asset?: string;
  timeframe?: string;
  confidence?: string | number;
  source?: string;
  agent?: string;
  signal?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}
interface SeverityStyle {
  border: string;
  glow: string;
  badge: string;
  pulse: string;
}
export function AlertCard({
  type = "SYSTEM",
  severity = "INFO",
  title,
  description,
  timestamp,
  status = "ACTIVE",
  asset,
  timeframe,
  confidence,
  source,
  agent,
  signal,
  actionLabel = "VIEW INTELLIGENCE",
  onAction,
  className = "",
}: AlertCardProps) {
  const normalizedType = String(type).toUpperCase();
  const normalizedSeverity = String(severity).toUpperCase();
  function getSeverityStyles(): SeverityStyle {
    switch (normalizedSeverity) {
      case "CRITICAL":
        return {
          border:
            "border-red-500/50 hover:border-red-500",
          glow:
            "shadow-[0_0_25px_rgba(239,68,68,0.25)]",
          badge:
            "bg-red-500/15 text-red-400 border-red-500/40",
          pulse: "animate-pulse",
        };
      case "HIGH":
        return {
          border:
            "border-amber-500/40 hover:border-amber-500/70",
          glow:
            "shadow-[0_0_20px_rgba(245,158,11,0.2)]",
          badge:
            "bg-amber-500/15 text-amber-300 border-amber-500/40",
          pulse: "",
        };
      case "MEDIUM":
        return {
          border:
            "border-cyan-400/30 hover:border-cyan-400/60",
          glow: "kz-glow",
          badge:
            "bg-cyan-500/15 text-cyan-200 border-cyan-400/30",
          pulse: "",
        };
      case "LOW":
      case "INFO":
      default:
        return {
          border:
            "border-cyan-500/20 hover:border-cyan-500/40",
          glow: "",
          badge:
            "bg-cyan-950/65 text-cyan-300 border-cyan-500/20",
          pulse: "",
        };
    }
  }
  const severityStyle = getSeverityStyles();
  function renderCategoryIcon() {
    switch (normalizedType) {
      case "MARKET":
        return (
          <svg
            className="h-4 w-4 shrink-0 text-cyan-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.75}
              d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
            />
          </svg>
        );
      case "AI":
        return (
          <svg
            className="h-4 w-4 shrink-0 text-cyan-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.75}
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          </svg>
        );
      case "NEWS":
        return (
          <svg
            className="h-4 w-4 shrink-0 text-cyan-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.75}
              d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"
            />
          </svg>
        );
      case "AGENT":
        return (
          <svg
            className="h-4 w-4 shrink-0 text-purple-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.75}
              d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z"
            />
          </svg>
        );
      case "SECURITY":
        return (
          <svg
            className="h-4 w-4 shrink-0 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.75}
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
            />
          </svg>
        );
      case "SYSTEM":
      default:
        return (
          <svg
            className="h-4 w-4 shrink-0 text-cyan-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.75}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.75}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
        );
    }
  }
  const hasMetadata =
    Boolean(
      status ||
        asset ||
        timeframe ||
        confidence ||
        source ||
        agent ||
        signal
    );
  return (
    <article
      className={`kz-panel kz-bracket relative p-5 transition-all duration-300 ${severityStyle.border} ${severityStyle.glow} ${className}`}
      aria-label={`${normalizedSeverity} ${normalizedType} alert: ${title}`}
    >
      {/* HUD CORNERS */}
      <div
        className="kz-hud-corner kz-hud-corner-tl"
        aria-hidden="true"
      />
      <div
        className="kz-hud-corner kz-hud-corner-tr"
        aria-hidden="true"
      />
      <div
        className="kz-hud-corner kz-hud-corner-bl"
        aria-hidden="true"
      />
      <div
        className="kz-hud-corner kz-hud-corner-br"
        aria-hidden="true"
      />
      {/* HEADER */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          {renderCategoryIcon()}
          <span className="kz-hud-label tracking-wider text-cyan-300">
            {normalizedType} INTELLIGENCE
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {timestamp && (
            <span className="text-[11px] font-mono uppercase text-cyan-400/60">
              {timestamp}
            </span>
          )}
          <span
            className={`rounded-sm border px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${severityStyle.badge} ${severityStyle.pulse}`}
          >
            {normalizedSeverity}
          </span>
        </div>
      </div>
      {/* MAIN CONTENT */}
      <div className="mb-4">
        <h3 className="mb-1.5 line-clamp-2 text-base font-bold tracking-wide text-white">
          {title}
        </h3>
        <p className="line-clamp-3 text-sm font-sans leading-relaxed text-cyan-100/80">
          {description}
        </p>
      </div>
      {/* METADATA */}
      {hasMetadata && (
        <div className="my-3 grid grid-cols-2 gap-2 rounded-sm border-y border-cyan-500/15 bg-black/20 px-3 py-2.5 sm:grid-cols-3">
          {status && (
            <div className="min-w-0">
              <div className="text-[9px] font-mono uppercase tracking-widest text-cyan-400/60">
                Status
              </div>
              <div className="truncate text-xs font-mono font-semibold uppercase text-cyan-200">
                {status}
              </div>
            </div>
          )}
          {asset && (
            <div className="min-w-0">
              <div className="text-[9px] font-mono uppercase tracking-widest text-cyan-400/60">
                Asset
              </div>
              <div className="truncate text-xs font-mono font-semibold text-cyan-200">
                {asset}
              </div>
            </div>
          )}
          {timeframe && (
            <div className="min-w-0">
              <div className="text-[9px] font-mono uppercase tracking-widest text-cyan-400/60">
                Timeframe
              </div>
              <div className="truncate text-xs font-mono font-semibold text-cyan-200">
                {timeframe}
              </div>
            </div>
          )}
          {signal && (
            <div className="min-w-0">
              <div className="text-[9px] font-mono uppercase tracking-widest text-cyan-400/60">
                Signal
              </div>
              <div className="truncate text-xs font-mono font-semibold text-cyan-200">
                {signal}
              </div>
            </div>
          )}
          {confidence !== undefined &&
            confidence !== null &&
            String(confidence).trim() !== "" && (
              <div className="min-w-0">
                <div className="text-[9px] font-mono uppercase tracking-widest text-cyan-400/60">
                  Confidence
                </div>
                <div className="truncate text-xs font-mono font-semibold text-cyan-200">
                  {confidence}
                </div>
              </div>
            )}
          {agent && (
            <div className="min-w-0">
              <div className="text-[9px] font-mono uppercase tracking-widest text-cyan-400/60">
                Agent
              </div>
              <div className="truncate text-xs font-mono font-semibold text-purple-300">
                {agent}
              </div>
            </div>
          )}
          {source &&
            (!agent || source !== agent) && (
              <div className="min-w-0">
                <div className="text-[9px] font-mono uppercase tracking-widest text-cyan-400/60">
                  Source
                </div>
                <div className="truncate text-xs font-mono font-semibold text-cyan-200">
                  {source}
                </div>
              </div>
            )}
        </div>
      )}
      {/* FOOTER */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        <div className="flex items-center gap-1.5">
          <span
            className="h-1.5 w-1.5 animate-ping rounded-full bg-cyan-400"
            aria-hidden="true"
          />
          <span className="text-[10px] font-mono uppercase tracking-widest text-cyan-400/70">
            KING ZARRY AI
          </span>
        </div>
        {onAction && (
          <button
            type="button"
            onClick={onAction}
            className="kz-button kz-button-primary px-3 py-1.5 text-[11px]"
          >
            {actionLabel}
          </button>
        )}
      </div>
    </article>
  );
}
