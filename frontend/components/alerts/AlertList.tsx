import React, { useState } from "react";
import { AlertCard, AlertCardProps, AlertType, AlertSeverity } from "./AlertCard";

export interface AlertItem extends AlertCardProps {
  id: string;
}

export interface AlertListProps {
  alerts?: AlertItem[];
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onAction?: (alert: AlertItem) => void;
  onConfigureNew?: () => void;
  className?: string;
}

export function AlertList({
  alerts = [],
  isLoading = false,
  error = null,
  onRetry,
  onAction,
  onConfigureNew,
  className = "",
}: AlertListProps) {
  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedSort, setSelectedSort] = useState<string>("newest");

  const categories = ["ALL", "MARKET", "AI", "NEWS", "SYSTEM", "AGENT", "SECURITY"];

  // Filter and search logic
  const filteredAlerts = alerts.filter((alert) => {
    const matchesCategory =
      selectedFilter === "ALL" || (alert.type && alert.type.toUpperCase() === selectedFilter);
    const matchesSearch =
      searchQuery.trim() === "" ||
      alert.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      alert.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (alert.asset && alert.asset.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  // Sort logic
  const sortedAlerts = [...filteredAlerts].sort((a, b) => {
    if (selectedSort === "severity") {
      const severityRank: Record<string, number> = {
        CRITICAL: 5,
        HIGH: 4,
        MEDIUM: 3,
        LOW: 2,
        INFO: 1,
      };
      const rankA = severityRank[(a.severity || "INFO").toUpperCase()] || 0;
      const rankB = severityRank[(b.severity || "INFO").toUpperCase()] || 0;
      return rankB - rankA;
    }
    // Default or 'newest' sorting order (preserving array order or timestamp approximation)
    return 0;
  });

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Stream Header & Controls Panel */}
      <div className="kz-panel kz-bracket relative p-5 border border-cyan-500/30 bg-black/40">
        <div className="kz-hud-corner kz-hud-corner-tl" aria-hidden="true" />
        <div className="kz-hud-corner kz-hud-corner-tr" aria-hidden="true" />
        <div className="kz-hud-corner kz-hud-corner-bl" aria-hidden="true" />
        <div className="kz-hud-corner kz-hud-corner-br" aria-hidden="true" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" aria-hidden="true" />
              <h2 className="text-base font-bold text-white tracking-wider">INTELLIGENCE STREAM</h2>
            </div>
            <p className="text-xs font-mono text-cyan-400/70 tracking-widest uppercase mt-1">
              REAL-TIME AI MONITORING &amp; PROTOCOL DISPATCH
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-3 py-1 bg-cyan-950/60 border border-cyan-500/30 rounded text-xs font-mono text-cyan-300">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" aria-hidden="true" />
              <span>AI MONITORING ACTIVE</span>
            </div>
          </div>
        </div>

        {/* Filter Pills & Search Bar */}
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 pt-3 border-t border-cyan-500/20">
          {/* Category Filters */}
          <div className="flex flex-wrap items-center gap-1.5">
            {categories.map((cat) => {
              const isActive = selectedFilter === cat;
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setSelectedFilter(cat)}
                  className={`px-3 py-1.5 text-[11px] font-mono font-semibold tracking-wider rounded transition-all border ${
                    isActive
                      ? "bg-cyan-500/25 border-cyan-300 text-white shadow-[0_0_12px_rgba(6,182,212,0.2)]"
                      : "bg-black/30 border-cyan-500/20 text-cyan-400/80 hover:border-cyan-500/40 hover:text-cyan-200"
                  }`}
                >
                  {cat}
                </button>
              );
            })}
          </div>

          {/* Search & Sort Controls */}
          <div className="flex items-center gap-2">
            <div className="relative flex-1 sm:w-60">
              <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-cyan-400/60 text-xs font-mono">
                ⌕
              </span>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search intelligence..."
                className="w-full kz-input bg-black/50 border border-cyan-500/30 focus:border-cyan-400 pl-8 pr-3 py-1.5 text-xs font-mono text-cyan-100 rounded focus:outline-none focus:ring-1 focus:ring-cyan-400/50"
              />
            </div>

            <select
              value={selectedSort}
              onChange={(e) => setSelectedSort(e.target.value)}
              aria-label="Sort intelligence stream"
              className="kz-select bg-black/50 border border-cyan-500/30 focus:border-cyan-400 px-3 py-1.5 text-xs font-mono text-cyan-200 rounded focus:outline-none focus:ring-1 focus:ring-cyan-400/50 cursor-pointer"
            >
              <option value="newest">SORT: NEWEST</option>
              <option value="severity">SORT: SEVERITY</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Stream Content */}
      {isLoading ? (
        <div className="kz-panel kz-bracket p-12 text-center border border-cyan-500/20 bg-black/30">
          <div className="flex flex-col items-center justify-center space-y-4">
            <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" aria-hidden="true" />
            <div className="text-xs font-mono text-cyan-300 tracking-widest uppercase animate-pulse">
              INITIALIZING INTELLIGENCE STREAM...
            </div>
            <div className="w-48 h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-60" />
          </div>
        </div>
      ) : error ? (
        <div className="kz-panel kz-bracket p-8 text-center border border-red-500/40 bg-red-950/20">
          <div className="flex flex-col items-center justify-center space-y-3">
            <span className="text-2xl text-red-400">⚠</span>
            <div className="text-sm font-bold text-red-200 tracking-wide">
              INTELLIGENCE STREAM ERROR
            </div>
            <p className="text-xs font-mono text-red-300/80 max-w-md">
              {error}
            </p>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="mt-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-200 text-xs font-mono tracking-wider rounded transition-all"
              >
                RETRY STREAM
              </button>
            )}
          </div>
        </div>
      ) : sortedAlerts.length === 0 ? (
        <div className="kz-panel kz-bracket p-12 text-center border border-cyan-500/20 bg-black/30">
          <div className="flex flex-col items-center justify-center space-y-3">
            <span className="text-3xl text-cyan-400/50">◎</span>
            <div className="text-sm font-bold text-white tracking-wide">
              NO ACTIVE INTELLIGENCE
            </div>
            <p className="text-xs font-mono text-cyan-400/70 max-w-sm">
              KING ZARRY AI IS CURRENTLY NOT REPORTING ANY ALERTS FOR THIS STREAM.
            </p>
            {onConfigureNew && (
              <button
                type="button"
                onClick={onConfigureNew}
                className="mt-3 kz-button kz-button-primary text-xs px-4 py-2"
              >
                CONFIGURE ALERT PROTOCOL
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="relative space-y-4">
          {/* Subtle vertical timeline trace */}
          <div className="absolute left-3.5 top-4 bottom-4 w-px bg-cyan-500/15 pointer-events-none hidden sm:block" aria-hidden="true" />

          {sortedAlerts.map((alert) => (
            <div key={alert.id || alert.title} className="relative sm:pl-8">
              {/* Timeline Node Marker */}
              <div className="absolute left-2.5 top-6 w-2.5 h-2.5 rounded-full border border-cyan-400 bg-black shadow-[0_0_8px_rgba(6,182,212,0.5)] z-10 hidden sm:block" aria-hidden="true" />

              <AlertCard
                {...alert}
                onAction={onAction ? () => onAction(alert) : alert.onAction}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
