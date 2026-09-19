import React, { useState } from "react";

export interface MarketAsset {
  symbol: string;
  name: string;
  price?: string | number;
  change?: string | number;
  trend?: "bullish" | "bearish" | "neutral" | string;
  volume?: string | number;
  high?: string | number;
  low?: string | number;
  marketCap?: string | number;
  rsi?: string | number;
  ema?: string | number;
  atr?: string | number;
}

export interface MarketOverviewProps {
  assets?: MarketAsset[];
  selectedSymbol?: string;
  onSelectAsset?: (symbol: string) => void;
  timeframe?: string;
  onChangeTimeframe?: (tf: string) => void;
  timeframes?: string[];
  chartData?: Array<{ timestamp?: string | number; price?: number; value?: number } | number>;
  aiAnalysis?: string;
  marketStatus?: string;
  watchlist?: MarketAsset[];
  onRefresh?: () => void;
  className?: string;
}

export function MarketOverview({
  assets = [],
  selectedSymbol,
  onSelectAsset,
  timeframe = "1H",
  onChangeTimeframe,
  timeframes = ["5M", "15M", "1H", "4H", "1D"],
  chartData = [],
  aiAnalysis,
  marketStatus = "LIVE",
  watchlist = [],
  onRefresh,
  className = "",
}: MarketOverviewProps) {
  const [activeTab, setActiveTab] = useState<"overview" | "watchlist">("overview");

  // Determine current active asset
  const currentAsset =
    assets.find((a) => a.symbol === selectedSymbol) ||
    assets[0] || {
      symbol: "BTC/USD",
      name: "Bitcoin / US Dollar",
      price: "$--",
      change: "0.00%",
      trend: "neutral",
    };

  const isLive = marketStatus.toUpperCase() === "LIVE" || marketStatus.toUpperCase() === "ACTIVE";
  const trendLower = String(currentAsset.trend || "").toLowerCase();
  const isBullish = trendLower.includes("bull") || trendLower.includes("up") || trendLower.includes("positive");
  const isBearish = trendLower.includes("bear") || trendLower.includes("down") || trendLower.includes("negative");

  return (
    <div
      className={`kz-panel kz-bracket relative p-6 md:p-8 bg-black/75 backdrop-blur-md border border-cyan-500/30 shadow-[0_0_40px_rgba(6,182,212,0.15)] rounded-lg overflow-hidden space-y-6 ${className}`}
    >
      {/* HUD Corner Accents */}
      <div className="kz-hud-corner kz-hud-corner-tl" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-tr" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-bl" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-br" aria-hidden="true" />

      {/* Market Intelligence Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-5 border-b border-cyan-500/20">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono text-cyan-400/70 tracking-widest uppercase">
              KING ZARRY AI // INTELLIGENCE MODULE
            </span>
            <span className="text-cyan-500/40">/</span>
            <span className="text-[10px] font-mono text-cyan-300 uppercase">
              MARKET ANALYTICS
            </span>
          </div>
          <h1 className="text-xl md:text-2xl font-bold text-white tracking-wide flex items-center gap-3">
            MARKET INTELLIGENCE <span className="text-cyan-400 font-mono text-sm px-2 py-0.5 bg-cyan-950/60 border border-cyan-500/30 rounded">{currentAsset.symbol}</span>
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
            <span
              className={`w-2 h-2 rounded-full ${
                isLive
                  ? "bg-cyan-400 animate-pulse shadow-[0_0_10px_rgba(6,182,212,0.8)]"
                  : "bg-amber-400"
              }`}
              aria-hidden="true"
            />
            <span className="uppercase font-bold tracking-wider">
              {marketStatus}
            </span>
          </div>
        </div>
      </div>

      {/* Asset Selector Bar if multiple assets exist */}
      {assets.length > 1 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
          {assets.map((asset) => {
            const isSelected = asset.symbol === currentAsset.symbol;
            return (
              <button
                key={asset.symbol}
                type="button"
                onClick={() => onSelectAsset && onSelectAsset(asset.symbol)}
                className={`px-3.5 py-2 rounded border text-xs font-mono transition-all shrink-0 flex items-center gap-2 ${
                  isSelected
                    ? "bg-cyan-500/20 border-cyan-400 text-white shadow-[0_0_15px_rgba(6,182,212,0.25)]"
                    : "bg-black/40 border-cyan-500/20 text-cyan-400/80 hover:bg-cyan-500/10 hover:text-cyan-300"
                }`}
              >
                <span className="font-bold">{asset.symbol}</span>
                {asset.price !== undefined && (
                  <span className="text-[10px] text-cyan-300/80">{asset.price}</span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Main Asset & Chart Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Primary Asset Card & Chart (Spans 2 cols) */}
        <div className="lg:col-span-2 p-5 bg-black/50 border border-cyan-500/25 rounded-xl flex flex-col justify-between space-y-6 relative overflow-hidden">
          <div className="absolute -right-12 -top-12 w-40 h-40 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" aria-hidden="true" />

          {/* Asset Price Banner & Timeframes */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span className="text-[10px] font-mono text-cyan-400/60 uppercase tracking-widest block mb-1">
                {currentAsset.name}
              </span>
              <div className="flex items-baseline gap-3">
                <span className="text-2xl md:text-3xl font-mono font-bold text-white tracking-tight">
                  {currentAsset.price ?? "$--"}
                </span>
                {currentAsset.change !== undefined && (
                  <span
                    className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${
                      isBullish
                        ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-300"
                        : isBearish
                        ? "bg-red-950/60 border-red-500/40 text-red-300"
                        : "bg-cyan-950/60 border-cyan-500/30 text-cyan-300"
                    }`}
                  >
                    {currentAsset.change}
                  </span>
                )}
              </div>
            </div>

            {/* Timeframe Selector */}
            {timeframes && timeframes.length > 0 && (
              <div className="flex items-center bg-black/60 border border-cyan-500/20 rounded p-1">
                {timeframes.map((tf) => {
                  const isActive = tf === timeframe;
                  return (
                    <button
                      key={tf}
                      type="button"
                      onClick={() => onChangeTimeframe && onChangeTimeframe(tf)}
                      className={`px-2.5 py-1 text-[10px] font-mono rounded transition-colors ${
                        isActive
                          ? "bg-cyan-500/30 text-white font-bold border border-cyan-400/40"
                          : "text-cyan-400/70 hover:text-cyan-200"
                      }`}
                    >
                      {tf}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Chart / Visualization Area */}
          <div className="relative h-48 bg-black/40 border border-cyan-500/20 rounded-lg p-4 flex flex-col justify-center items-center overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-cyan-500/5 via-transparent to-transparent pointer-events-none" aria-hidden="true" />
            
            {chartData && chartData.length > 0 ? (
              <div className="w-full h-full flex items-end justify-between gap-1 pt-4 relative z-10">
                {chartData.map((pt, idx) => {
                  const val = typeof pt === "number" ? pt : pt.price ?? pt.value ?? 50;
                  // Normalize height visually between 20% and 90%
                  const heightPct = Math.max(15, Math.min(95, val % 100));
                  return (
                    <div
                      key={idx}
                      className="flex-1 bg-cyan-500/20 hover:bg-cyan-400 border-t border-cyan-400/60 transition-all rounded-t"
                      style={{ height: `${heightPct}%` }}
                      title={`Point ${idx + 1}: ${val}`}
                    />
                  );
                })}
              </div>
            ) : (
              <div className="text-center space-y-2 z-10">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse inline-block" aria-hidden="true" />
                <p className="text-xs font-mono text-cyan-400/80 uppercase">
                  MARKET VISUALIZATION STANDBY
                </p>
                <p className="text-[10px] font-mono text-cyan-400/50">
                  Awaiting telemetry stream for {currentAsset.symbol} chart rendering.
                </p>
              </div>
            )}
          </div>

          {/* Market Diagnostics Readout / Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 bg-black/40 border border-cyan-500/15 rounded">
              <span className="text-[9px] font-mono text-cyan-400/60 uppercase block mb-1">VOLUME</span>
              <span className="text-xs font-mono font-bold text-white">{currentAsset.volume ?? "N/A"}</span>
            </div>
            <div className="p-3 bg-black/40 border border-cyan-500/15 rounded">
              <span className="text-[9px] font-mono text-cyan-400/60 uppercase block mb-1">24H HIGH</span>
              <span className="text-xs font-mono font-bold text-white">{currentAsset.high ?? "N/A"}</span>
            </div>
            <div className="p-3 bg-black/40 border border-cyan-500/15 rounded">
              <span className="text-[9px] font-mono text-cyan-400/60 uppercase block mb-1">24H LOW</span>
              <span className="text-xs font-mono font-bold text-white">{currentAsset.low ?? "N/A"}</span>
            </div>
            <div className="p-3 bg-black/40 border border-cyan-500/15 rounded">
              <span className="text-[9px] font-mono text-cyan-400/60 uppercase block mb-1">MARKET CAP</span>
              <span className="text-xs font-mono font-bold text-white">{currentAsset.marketCap ?? "N/A"}</span>
            </div>
          </div>
        </div>

        {/* Side Panel: AI Market Analysis & Watchlist */}
        <div className="flex flex-col space-y-6">
          {/* AI Market Analysis Console */}
          <div className="p-5 bg-black/50 border border-cyan-500/20 rounded-xl flex-1 flex flex-col">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-cyan-500/15">
              <h3 className="text-xs font-mono font-bold text-cyan-300 uppercase tracking-widest">
                AI MARKET READ
              </h3>
              <span className="text-[9px] font-mono text-cyan-400/60 uppercase">
                SYNTHESIS
              </span>
            </div>

            {aiAnalysis ? (
              <p className="text-xs font-mono text-cyan-100/90 leading-relaxed">
                {aiAnalysis}
              </p>
            ) : (
              <div className="py-6 flex flex-col items-center justify-center text-center space-y-2 my-auto">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400/60 animate-ping" aria-hidden="true" />
                <p className="text-xs font-mono text-cyan-400/70">
                  NO AI ANALYSIS SUPPLIED
                </p>
                <p className="text-[10px] font-mono text-cyan-400/40">
                  Neural market reasoning engine standing by.
                </p>
              </div>
            )}

            {/* Indicator Pills */}
            {(currentAsset.rsi !== undefined || currentAsset.ema !== undefined || currentAsset.atr !== undefined) && (
              <div className="grid grid-cols-3 gap-2 pt-4 mt-auto border-t border-cyan-500/15">
                {currentAsset.rsi !== undefined && (
                  <div className="p-2 bg-black/40 border border-cyan-500/15 rounded text-center">
                    <span className="text-[8px] font-mono text-cyan-400/60 block">RSI</span>
                    <span className="text-xs font-mono font-bold text-white">{currentAsset.rsi}</span>
                  </div>
                )}
                {currentAsset.ema !== undefined && (
                  <div className="p-2 bg-black/40 border border-cyan-500/15 rounded text-center">
                    <span className="text-[8px] font-mono text-cyan-400/60 block">EMA</span>
                    <span className="text-xs font-mono font-bold text-white">{currentAsset.ema}</span>
                  </div>
                )}
                {currentAsset.atr !== undefined && (
                  <div className="p-2 bg-black/40 border border-cyan-500/15 rounded text-center">
                    <span className="text-[8px] font-mono text-cyan-400/60 block">ATR</span>
                    <span className="text-xs font-mono font-bold text-white">{currentAsset.atr}</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Watchlist Rail if provided */}
          {watchlist && watchlist.length > 0 && (
            <div className="p-5 bg-black/50 border border-cyan-500/20 rounded-xl">
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-cyan-500/15">
                <h3 className="text-xs font-mono font-bold text-cyan-300 uppercase tracking-widest">
                  WATCHLIST RAIL
                </h3>
                <span className="text-[9px] font-mono text-cyan-400/60 uppercase">
                  {watchlist.length} ASSETS
                </span>
              </div>

              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {watchlist.map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => onSelectAsset && onSelectAsset(item.symbol)}
                    className="w-full p-2.5 bg-black/40 hover:bg-cyan-500/15 border border-cyan-500/15 rounded flex items-center justify-between text-left transition-colors"
                  >
                    <div>
                      <span className="text-xs font-mono font-bold text-white block">
                        {item.symbol}
                      </span>
                      <span className="text-[9px] font-mono text-cyan-400/60">
                        {item.name}
                      </span>
                    </div>
                    <div className="text-right">
                      {item.price !== undefined && (
                        <span className="text-xs font-mono text-cyan-200 font-bold block">
                          {item.price}
                        </span>
                      )}
                      {item.change !== undefined && (
                        <span className="text-[9px] font-mono text-cyan-400">
                          {item.change}
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
