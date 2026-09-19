import React from "react";

export type AlertType = "MARKET" | "AI" | "NEWS" | "SYSTEM" | "AGENT" | "SECURITY";
export type AlertSeverity = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

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
  const normalizedType = type.toUpperCase();
  const normalizedSeverity = severity.toUpperCase();

  // Severity-based styling and indicators
  const getSeverityStyles = () => {
    switch (normalizedSeverity) {
      case "CRITICAL":
        return {
          border: "border-red-500/50 hover:border-red-500",
          glow: "shadow-[0_0_25px_rgba(239,68,68,0.25)]",
          badge: "bg-red-500/15 text-red-400 border-red-500/40",
          pulse: "animate-pulse",
        };
      case "HIGH":
        return {
          border: "border-amber-500/40 hover:border-amber-500/70",
          glow: "shadow-[0_0_20px_rgba(245,158,11,0.2)]",
          badge: "bg-amber-500/15 text-amber-300 border-amber-500/40",
          pulse: "",
        };
      case "MEDIUM":
        return {
          border: "border-cyan-400/30 hover:border-cyan-400/60",
          glow: "kz-glow",
          badge: "bg-cyan-500/15 text-cyan-200 border-cyan-400/30",
          pulse: "",
        };
      case "LOW":
      case "INFO":
      default:
        return {
          border: "border-cyan-500/20 hover:border-cyan-500/40",
          glow: "",
          badge: "bg-cyan-950/65 text-cyan-300 border-cyan-500/20",
          pulse: "",
        };
    }
  };

  const sevStyle = getSeverityStyles();

  // Category Icon SVG renderer
  const renderCategoryIcon = () => {
    switch (normalizedType) {
      case "MARKET":
        return (
          <svg className="w-4 h-4 text-cyan-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
        );
      case "AI":
        return (
          <svg className="w-4 h-4 text-cyan-300 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        );
      case "NEWS":
        return (
          <svg className="w-4 h-4 text-cyan-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
          </svg>
        );
      case "AGENT":
        return (
          <svg className="w-4 h-4 text-purple-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z" />
          </svg>
        );
      case "SECURITY":
        return (
          <svg className="w-4 h-4 text-red-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        );
      case "SYSTEM":
      default:
        return (
          <svg className="w-4 h-4 text-cyan-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        );
    }
  };

  return (
    <div
      className={`kz-panel kz-bracket relative p-5 transition-all duration-300 ${sevStyle.border} ${sevStyle.glow} ${className}`}
    >
      {/* HUD Corner Accents */}
      <div className="kz-hud-corner kz-hud-corner-tl" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-tr" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-bl" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-br" aria-hidden="true" />

      {/* Card Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          {renderCategoryIcon()}
          <span className="kz-hud-label text-cyan-300 tracking-wider">
            {normalizedType} INTELLIGENCE
          </span>
        </div>

        <div className="flex items-center gap-2">
          {timestamp && (
            <span className="text-[11px] font-mono text-cyan-400/60 uppercase">
              {timestamp}
            </span>
          )}
          <span className={`px-2 py-0.5 text-[10px] font-mono font-bold tracking-wider uppercase border rounded-sm ${sevStyle.badge} ${sevStyle.pulse}`}>
            {normalizedSeverity}
          </span>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="mb-4">
        <h3 className="text-base font-bold text-white tracking-wide mb-1.5 line-clamp-2">
          {title}
        </h3>
        <p className="text-sm text-cyan-100/80 leading-relaxed font-sans line-clamp-3">
          {description}
        </p>
      </div>

      {/* Intelligence Metadata Grid (Optional fields rendered dynamically) */}
      {(asset || timeframe || confidence || source || agent || signal || status) && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 py-2.5 my-3 border-t border-b border-cyan-500/15 bg-black/20 px-3 rounded-sm">
          {status && (
            <div>
              <div className="text-[9px] font-mono text-cyan-400/60 uppercase tracking-widest">Status</div>
              <div className="text-xs font-mono text-cyan-200 font-semibold uppercase">{status}</div>
            </div>
          )}
          {asset && (
            <div>
              <div className="text-[9px] font-mono text-cyan-400/60 uppercase tracking-widest">Asset</div>
              <div className="text-xs font-mono text-cyan-200 font-semibold">{asset}</div>
            </div>
          )}
          {timeframe && (
            <div>
              <div className="text-[9px] font-mono text-cyan-400/60 uppercase tracking-widest">Timeframe</div>
              <div className="text-xs font-mono text-cyan-200 font-semibold">{timeframe}</div>
            </div>
          )}
          {signal && (
            <div>
              <div className="text-[9px] font-mono text-cyan-400/60 uppercase tracking-widest">Signal</div>
              <div className="text-xs font-mono text-cyan-200 font-semibold">{signal}</div>
            </div>
          )}
          {confidence && (
            <div>
              <div className="text-[9px] font-mono text-cyan-400/60 uppercase tracking-widest">Confidence</div>
              <div className="text-xs font-mono text-cyan-200 font-semibold">{confidence}</div>
            </div>
          )}
          {agent && (
            <div>
              <div className="text-[9px] font-mono text-cyan-400/60 uppercase tracking-widest">Agent</div>
              <div className="text-xs font-mono text-purple-300 font-semibold truncate">{agent}</div>
            </div>
          )}
          {source && (!agent || source !== agent) && (
            <div>
              <div className="text-[9px] font-mono text-cyan-400/60 uppercase tracking-widest">Source</div>
              <div className="text-xs font-mono text-cyan-200 font-semibold truncate">{source}</div>
            </div>
          )}
        </div>
      )}

      {/* Footer / Action */}
      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" aria-hidden="true" />
          <span className="text-[10px] font-mono text-cyan-400/70 tracking-widest uppercase">
            KING ZARRY AI
          </span>
        </div>

        {onAction && (
          <button
            type="button"
            onClick={onAction}
            className="kz-button kz-button-primary text-[11px] px-3 py-1.5"
          >
            {actionLabel}
          </button>
        )}
      </div>
    </div>
  );
}
