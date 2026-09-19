import React, { useState } from "react";

export interface SignalItem {
  id: string | number;
  symbol: string;
  direction?: "BUY" | "SELL" | "LONG" | "SHORT" | "NEUTRAL" | string;
  timeframe?: string;
  status?: "ACTIVE" | "PENDING" | "HIT" | "COMPLETED" | "CANCELLED" | "EXPIRED" | string;
  entry?: string | number;
  stopLoss?: string | number;
  tp1?: string | number;
  tp2?: string | number;
  tp3?: string | number;
  confidence?: string | number;
  timestamp?: string;
  reasoning?: string;
}

export interface RecentSignalsProps {
  signals?: SignalItem[];
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  onSelectSignal?: (signal: SignalItem) => void;
  className?: string;
}

export function RecentSignals({
  signals = [],
  isLoading = false,
  error = null,
  onRefresh,
  onSelectSignal,
  className = "",
}: RecentSignalsProps) {
  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");

  const filteredSignals = signals.filter((sig) => {
    if (selectedFilter === "ALL") return true;
    const dir = String(sig.direction || "").toUpperCase();
    return dir.includes(selectedFilter);
  });

  return (
    <div
      className={`kz-panel kz-bracket relative p-6 md:p-8 bg-black/75 backdrop-blur-md border border-cyan-500/30 shadow-[0_0_40px_rgba(6,182,212,0.15)] rounded-lg overflow-hidden space-y-6 ${className}`}
    >
      {/* HUD Corner Accents */}
      <div className="kz-hud-corner kz-hud-corner-tl" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-tr" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-bl" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-br" aria-hidden="true" />

      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-5 border-b border-cyan-500/20">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono text-cyan-400/70 tracking-widest uppercase">
              KING ZARRY AI // INTELLIGENCE FEED
            </span>
            <span className="text-cyan-500/40">/</span>
            <span className="text-[10px] font-mono text-cyan-300 uppercase">
              SIGNAL INTELLIGENCE
            </span>
          </div>
          <h1 className="text-xl md:text-2xl font-bold text-white tracking-wide flex items-center gap-3">
            RECENT MARKET SIGNALS <span className="text-cyan-400 font-mono text-xs px-2 py-0.5 bg-cyan-950/60 border border-cyan-500/30 rounded">{signals.length} ACTIVE</span>
          </h1>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              className="px-3 py-1.5 bg-black/50 hover:bg-cyan-500/20 border border-cyan-500/30 rounded text-xs font-mono text-cyan-300 transition-colors"
            >
              SYNC FEED
            </button>
          )}

          <div className="flex items-center gap-2 px-3.5 py-1.5 bg-cyan-950/60 border border-cyan-500/30 rounded text-xs font-mono text-cyan-300">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_rgba(6,182,212,0.8)]" aria-hidden="true" />
            <span className="uppercase font-bold tracking-wider">ONLINE</span>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 pb-2">
        {["ALL", "BUY", "SELL", "LONG", "SHORT"].map((filter) => {
          const isActive = selectedFilter === filter;
          return (
            <button
              key={filter}
              type="button"
              onClick={() => setSelectedFilter(filter)}
              className={`px-3 py-1 rounded text-[10px] font-mono transition-all border ${
                isActive
                  ? "bg-cyan-500/20 border-cyan-400 text-white font-bold"
                  : "bg-black/40 border-cyan-500/20 text-cyan-400/70 hover:bg-cyan-500/10 hover:text-cyan-300"
              }`}
            >
              {filter}
            </button>
          );
        })}
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 bg-red-950/40 border border-red-500/40 rounded-lg text-red-200 text-xs font-mono">
          <span className="font-bold block mb-1">SIGNAL STREAM UNAVAILABLE</span>
          {error}
        </div>
      )}

      {/* Loading State */}
      {isLoading ? (
        <div className="space-y-4 py-8">
          {[1, 2, 3].map((n) => (
            <div key={n} className="p-4 bg-black/40 border border-cyan-500/20 rounded-xl animate-pulse space-y-3">
              <div className="flex justify-between">
                <div className="w-24 h-4 bg-cyan-500/20 rounded" />
                <div className="w-16 h-4 bg-cyan-500/20 rounded" />
              </div>
              <div className="w-full h-12 bg-cyan-500/10 rounded" />
            </div>
          ))}
        </div>
      ) : filteredSignals.length > 0 ? (
        <div className="space-y-4 max-h-[500px] overflow-y-auto pr-1">
          {filteredSignals.map((signal) => {
            const dir = String(signal.direction || "").toUpperCase();
            const status = String(signal.status || "ACTIVE").toUpperCase();
            const isBuy = dir.includes("BUY") || dir.includes("LONG");
            const isSell = dir.includes("SELL") || dir.includes("SHORT");

            return (
              <div
                key={signal.id}
                onClick={() => onSelectSignal && onSelectSignal(signal)}
                className="p-4 md:p-5 bg-black/50 hover:bg-cyan-500/10 border border-cyan-500/25 hover:border-cyan-400/60 rounded-xl transition-all group cursor-pointer relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/5 rounded-full blur-2xl pointer-events-none" aria-hidden="true" />

                {/* Signal Header Info */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 mb-3 border-b border-cyan-500/15">
                  <div className="flex items-center gap-3">
                    <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" aria-hidden="true" />
                    <span className="text-sm font-mono font-bold text-white tracking-wide">
                      {signal.symbol}
                    </span>
                    {signal.timeframe && (
                      <span className="px-2 py-0.5 bg-black/60 border border-cyan-500/30 text-cyan-300 rounded text-[10px] font-mono">
                        {signal.timeframe}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {signal.direction && (
                      <span
                        className={`px-2.5 py-0.5 rounded border text-[10px] font-mono font-bold ${
                          isBuy
                            ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-300"
                            : isSell
                            ? "bg-red-950/60 border-red-500/40 text-red-300"
                            : "bg-cyan-950/60 border-cyan-500/30 text-cyan-300"
                        }`}
                      >
                        {signal.direction}
                      </span>
                    )}
                    <span className="px-2 py-0.5 bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 rounded text-[10px] font-mono uppercase">
                      {status}
                    </span>
                  </div>
                </div>

                {/* Levels Grid if provided */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 mb-3">
                  {signal.entry !== undefined && (
                    <div className="p-2.5 bg-black/40 border border-cyan-500/15 rounded">
                      <span className="text-[9px] font-mono text-cyan-400/60 uppercase block mb-0.5">ENTRY</span>
                      <span className="text-xs font-mono font-bold text-white">{signal.entry}</span>
                    </div>
                  )}
                  {signal.stopLoss !== undefined && (
                    <div className="p-2.5 bg-black/40 border border-cyan-500/15 rounded">
                      <span className="text-[9px] font-mono text-cyan-400/60 uppercase block mb-0.5">STOP LOSS</span>
                      <span className="text-xs font-mono font-bold text-red-300">{signal.stopLoss}</span>
                    </div>
                  )}
                  {signal.tp1 !== undefined && (
                    <div className="p-2.5 bg-black/40 border border-cyan-500/15 rounded">
                      <span className="text-[9px] font-mono text-cyan-400/60 uppercase block mb-0.5">TP 1</span>
                      <span className="text-xs font-mono font-bold text-emerald-300">{signal.tp1}</span>
                    </div>
                  )}
                  {signal.tp2 !== undefined && (
                    <div className="p-2.5 bg-black/40 border border-cyan-500/15 rounded">
                      <span className="text-[9px] font-mono text-cyan-400/60 uppercase block mb-0.5">TP 2</span>
                      <span className="text-xs font-mono font-bold text-emerald-300">{signal.tp2}</span>
                    </div>
                  )}
                  {signal.tp3 !== undefined && (
                    <div className="p-2.5 bg-black/40 border border-cyan-500/15 rounded">
                      <span className="text-[9px] font-mono text-cyan-400/60 uppercase block mb-0.5">TP 3</span>
                      <span className="text-xs font-mono font-bold text-emerald-300">{signal.tp3}</span>
                    </div>
                  )}
                </div>

                {/* Reasoning & Confidence Footer */}
                {(signal.reasoning || signal.confidence || signal.timestamp) && (
                  <div className="pt-3 mt-3 border-t border-cyan-500/15 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono">
                    {signal.reasoning ? (
                      <p className="text-cyan-300/80 text-[11px] line-clamp-1">
                        <span className="text-cyan-400 font-bold uppercase mr-1.5">AI REASONING:</span>
                        {signal.reasoning}
                      </p>
                    ) : (
                      <span className="text-cyan-400/50 text-[10px]">KING ZARRY AI INTELLIGENCE STREAM</span>
                    )}

                    <div className="flex items-center gap-3 shrink-0">
                      {signal.confidence && (
                        <span className="text-[10px] text-cyan-200">
                          CONFIDENCE: <strong className="text-cyan-400">{signal.confidence}</strong>
                        </span>
                      )}
                      {signal.timestamp && (
                        <span className="text-[10px] text-cyan-400/60">
                          {signal.timestamp}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="py-16 flex flex-col items-center justify-center text-center space-y-3">
          <span className="w-2 h-2 rounded-full bg-cyan-400/60 animate-pulse" aria-hidden="true" />
          <p className="text-xs font-mono text-cyan-400/80 uppercase tracking-widest">
            NO RECENT SIGNALS
          </p>
          <p className="text-[10px] font-mono text-cyan-400/50 max-w-sm">
            Signal intelligence is standing by for the next neural market trigger.
          </p>
        </div>
      )}
    </div>
  );
}
