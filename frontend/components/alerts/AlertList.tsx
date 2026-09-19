"use client";
import { useMemo, useState } from "react";
import {
  AlertCard,
  type AlertCardProps,
  type AlertSeverity,
  type AlertType,
} from "./AlertCard";
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
  live?: boolean;
}
type SortMode = "newest" | "severity";
const CATEGORIES: Array<"ALL" | AlertType> = [
  "ALL",
  "MARKET",
  "AI",
  "NEWS",
  "SYSTEM",
  "AGENT",
  "SECURITY",
];
const SEVERITY_RANK: Record<string, number> = {
  CRITICAL: 5,
  HIGH: 4,
  MEDIUM: 3,
  LOW: 2,
  INFO: 1,
};
function normalize(value?: string | null) {
  return String(value ?? "").trim().toUpperCase();
}
function getTimestampValue(timestamp?: string) {
  if (!timestamp) {
    return 0;
  }
  const parsed = Date.parse(timestamp);
  return Number.isNaN(parsed) ? 0 : parsed;
}
export function AlertList({
  alerts = [],
  isLoading = false,
  error = null,
  onRetry,
  onAction,
  onConfigureNew,
  className = "",
  live = false,
}: AlertListProps) {
  const [selectedFilter, setSelectedFilter] =
    useState<"ALL" | AlertType>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSort, setSelectedSort] =
    useState<SortMode>("newest");
  const filteredAndSortedAlerts = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    const filtered = alerts.filter((alert) => {
      const alertType = normalize(alert.type);
      const matchesCategory =
        selectedFilter === "ALL" ||
        alertType === selectedFilter;
      if (!matchesCategory) {
        return false;
      }
      if (!query) {
        return true;
      }
      const searchableText = [
        alert.title,
        alert.description,
        alert.asset,
        alert.timeframe,
        alert.source,
        alert.agent,
        alert.signal,
        alert.confidence,
        alert.status,
        alert.type,
        alert.severity,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return searchableText.includes(query);
    });
    return [...filtered].sort((a, b) => {
      if (selectedSort === "severity") {
        const rankA =
          SEVERITY_RANK[normalize(a.severity)] ?? 0;
        const rankB =
          SEVERITY_RANK[normalize(b.severity)] ?? 0;
        if (rankB !== rankA) {
          return rankB - rankA;
        }
      }
      const timestampA = getTimestampValue(a.timestamp);
      const timestampB = getTimestampValue(b.timestamp);
      return timestampB - timestampA;
    });
  }, [
    alerts,
    searchQuery,
    selectedFilter,
    selectedSort,
  ]);
  const hasFilters =
    selectedFilter !== "ALL" ||
    searchQuery.trim() !== "";
  function clearFilters() {
    setSelectedFilter("ALL");
    setSearchQuery("");
    setSelectedSort("newest");
  }
  return (
    <section
      className={`space-y-6 ${className}`}
      aria-label="KING ZARRY AI alert intelligence"
    >
      {/* STREAM HEADER */}
      <div className="kz-panel kz-bracket relative border border-cyan-500/30 bg-black/40 p-5">
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
        <div className="mb-4 flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <div className="flex items-center gap-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  live
                    ? "animate-pulse bg-cyan-400"
                    : "bg-cyan-500/50"
                }`}
                aria-hidden="true"
              />
              <h2 className="text-base font-bold tracking-wider text-white">
                INTELLIGENCE STREAM
              </h2>
            </div>
            <p className="mt-1 text-xs font-mono uppercase tracking-widest text-cyan-400/70">
              {live
                ? "LIVE AI MONITORING & PROTOCOL DISPATCH"
                : "ALERT INTELLIGENCE & PROTOCOL DISPATCH"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 rounded border border-cyan-500/30 bg-cyan-950/60 px-3 py-1 text-xs font-mono text-cyan-300">
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  live
                    ? "animate-ping bg-cyan-400"
                    : "bg-cyan-500/50"
                }`}
                aria-hidden="true"
              />
              <span>
                {live
                  ? "AI MONITORING ACTIVE"
                  : "AI MONITORING READY"}
              </span>
            </div>
          </div>
        </div>
        {/* CONTROLS */}
        <div className="flex flex-col items-stretch justify-between gap-3 border-t border-cyan-500/20 pt-3 lg:flex-row lg:items-center">
          {/* CATEGORY FILTERS */}
          <div
            className="flex flex-wrap items-center gap-1.5"
            aria-label="Alert categories"
          >
            {CATEGORIES.map((category) => {
              const isActive =
                selectedFilter === category;
              return (
                <button
                  key={category}
                  type="button"
                  aria-pressed={isActive}
                  onClick={() =>
                    setSelectedFilter(category)
                  }
                  className={`rounded border px-3 py-1.5 text-[11px] font-mono font-semibold tracking-wider transition-all ${
                    isActive
                      ? "border-cyan-300 bg-cyan-500/25 text-white shadow-[0_0_12px_rgba(6,182,212,0.2)]"
                      : "border-cyan-500/20 bg-black/30 text-cyan-400/80 hover:border-cyan-500/40 hover:text-cyan-200"
                  }`}
                >
                  {category}
                </button>
              );
            })}
          </div>
          {/* SEARCH + SORT */}
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="relative min-w-0 flex-1 sm:w-60 sm:flex-none">
              <span
                className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-xs font-mono text-cyan-400/60"
                aria-hidden="true"
              >
                ⌕
              </span>
              <input
                type="search"
                value={searchQuery}
                onChange={(event) =>
                  setSearchQuery(event.target.value)
                }
                placeholder="Search intelligence..."
                aria-label="Search alerts"
                className="kz-input w-full rounded border border-cyan-500/30 bg-black/50 py-1.5 pl-8 pr-3 text-xs font-mono text-cyan-100 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400/50"
              />
            </div>
            <select
              value={selectedSort}
              onChange={(event) =>
                setSelectedSort(
                  event.target.value as SortMode
                )
              }
              aria-label="Sort intelligence stream"
              className="kz-select cursor-pointer rounded border border-cyan-500/30 bg-black/50 px-3 py-1.5 text-xs font-mono text-cyan-200 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400/50"
            >
              <option
                value="newest"
                className="bg-slate-950"
              >
                SORT: NEWEST
              </option>
              <option
                value="severity"
                className="bg-slate-950"
              >
                SORT: SEVERITY
              </option>
            </select>
          </div>
        </div>
        {/* RESULT COUNT */}
        {!isLoading && !error && (
          <div className="mt-4 flex items-center justify-between border-t border-cyan-500/10 pt-3">
            <span className="text-[10px] font-mono uppercase tracking-widest text-cyan-400/50">
              {filteredAndSortedAlerts.length}{" "}
              {filteredAndSortedAlerts.length === 1
                ? "ALERT"
                : "ALERTS"}{" "}
              DISPLAYED
            </span>
            {hasFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="text-[10px] font-mono uppercase tracking-widest text-cyan-400 transition-colors hover:text-white"
              >
                CLEAR FILTERS
              </button>
            )}
          </div>
        )}
      </div>
      {/* LOADING */}
      {isLoading && (
        <div className="kz-panel kz-bracket border border-cyan-500/20 bg-black/30 p-12 text-center">
          <div className="flex flex-col items-center justify-center space-y-4">
            <div
              className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent"
              aria-hidden="true"
            />
            <div className="animate-pulse text-xs font-mono uppercase tracking-widest text-cyan-300">
              INITIALIZING INTELLIGENCE STREAM...
            </div>
            <div
              className="h-0.5 w-48 bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-60"
              aria-hidden="true"
            />
          </div>
        </div>
      )}
      {/* ERROR */}
      {!isLoading && error && (
        <div
          className="kz-panel kz-bracket border border-red-500/40 bg-red-950/20 p-8 text-center"
          role="alert"
        >
          <div className="flex flex-col items-center justify-center space-y-3">
            <span
              className="text-2xl text-red-400"
              aria-hidden="true"
            >
              ⚠
            </span>
            <div className="text-sm font-bold tracking-wide text-red-200">
              INTELLIGENCE STREAM ERROR
            </div>
            <p className="max-w-md text-xs font-mono text-red-300/80">
              {error}
            </p>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="mt-2 rounded border border-red-500/50 bg-red-500/20 px-4 py-2 text-xs font-mono tracking-wider text-red-200 transition-all hover:bg-red-500/30"
              >
                RETRY STREAM
              </button>
            )}
          </div>
        </div>
      )}
      {/* EMPTY */}
      {!isLoading &&
        !error &&
        filteredAndSortedAlerts.length === 0 && (
          <div className="kz-panel kz-bracket border border-cyan-500/20 bg-black/30 p-12 text-center">
            <div className="flex flex-col items-center justify-center space-y-3">
              <span
                className="text-3xl text-cyan-400/50"
                aria-hidden="true"
              >
                ◎
              </span>
              <div className="text-sm font-bold tracking-wide text-white">
                {hasFilters
                  ? "NO MATCHING INTELLIGENCE"
                  : "NO ACTIVE INTELLIGENCE"}
              </div>
              <p className="max-w-sm text-xs font-mono text-cyan-400/70">
                {hasFilters
                  ? "NO ALERTS MATCH THE CURRENT SEARCH OR CATEGORY FILTER."
                  : "KING ZARRY AI CURRENTLY HAS NO ALERTS FOR THIS STREAM."}
              </p>
              {hasFilters ? (
                <button
                  type="button"
                  onClick={clearFilters}
                  className="kz-button mt-3 px-4 py-2 text-xs"
                >
                  CLEAR FILTERS
                </button>
              ) : (
                onConfigureNew && (
                  <button
                    type="button"
                    onClick={onConfigureNew}
                    className="kz-button kz-button-primary mt-3 px-4 py-2 text-xs"
                  >
                    CONFIGURE ALERT PROTOCOL
                  </button>
                )
              )}
            </div>
          </div>
        )}
      {/* ALERT STREAM */}
      {!isLoading &&
        !error &&
        filteredAndSortedAlerts.length > 0 && (
          <div className="relative space-y-4">
            {/* TIMELINE */}
            <div
              className="pointer-events-none absolute bottom-4 left-3.5 top-4 hidden w-px bg-cyan-500/15 sm:block"
              aria-hidden="true"
            />
            {filteredAndSortedAlerts.map((alert) => (
              <div
                key={alert.id}
                className="relative sm:pl-8"
              >
                {/* TIMELINE NODE */}
                <div
                  className="absolute left-2.5 top-6 z-10 hidden h-2.5 w-2.5 rounded-full border border-cyan-400 bg-black shadow-[0_0_8px_rgba(6,182,212,0.5)] sm:block"
                  aria-hidden="true"
                />
                <AlertCard
                  {...alert}
                  onAction={
                    onAction
                      ? () => onAction(alert)
                      : alert.onAction
                  }
                />
              </div>
            ))}
          </div>
        )}
    </section>
  );
}
export default AlertList;
