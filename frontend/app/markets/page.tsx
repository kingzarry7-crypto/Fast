"use client";

import { useCallback, useEffect, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import { api, ApiError, type MarketSnapshot } from "@/lib/api";

function badge(signal?: string) {
  const s = String(signal || "WAIT").toUpperCase();
  if (s === "BUY") return "text-emerald-300 border-emerald-500/40 bg-emerald-500/10";
  if (s === "SELL") return "text-red-300 border-red-500/40 bg-red-500/10";
  return "text-cyan-300/80 border-cyan-500/30 bg-cyan-500/5";
}

export default function MarketsPage() {
  const [rows, setRows] = useState<MarketSnapshot[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMarkets();
      setRows(data.symbols || []);
    } catch (e) {
      setError(e instanceof ApiError ? e.detail || e.message : "Failed to load markets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <ProtectedRoute>
      <div className="p-6 lg:p-10 max-w-6xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-8">
          <div>
            <h1 className="font-display text-2xl font-bold text-white kz-glow-text tracking-wider">
              Markets
            </h1>
            <p className="font-mono-tech text-[10px] tracking-[0.4em] text-cyan-400/40 mt-1">
              LIVE MTF SNAPSHOT · BTC ETH SOL XAU
            </p>
          </div>
          <button
            type="button"
            onClick={load}
            className="px-3 py-1.5 rounded-md border border-cyan-500/30 font-mono-tech text-[10px] tracking-widest text-cyan-300 hover:bg-cyan-500/10"
          >
            REFRESH
          </button>
        </div>

        {loading && (
          <p className="font-mono-tech text-xs text-cyan-400/50">Scanning markets…</p>
        )}
        {error && (
          <div className="kz-panel p-4 text-sm text-amber-200 mb-6">{error}</div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {rows.map((m) => (
            <div key={m.symbol} className="kz-panel p-5 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-display text-lg text-white tracking-wider">
                    {m.symbol}
                  </p>
                  <p className="font-mono-tech text-xs text-cyan-400/60">
                    {m.price != null ? String(m.price) : "—"}
                  </p>
                </div>
                <span
                  className={`px-2.5 py-1 rounded-md border text-[10px] font-mono-tech tracking-widest ${badge(
                    m.signal
                  )}`}
                >
                  {String(m.signal || "WAIT").toUpperCase()}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 font-mono-tech text-[10px] text-cyan-300/70">
                <span>Trend: {String(m.trend || "—")}</span>
                <span>RSI: {m.rsi != null ? Number(m.rsi).toFixed(1) : "—"}</span>
                <span>Support: {m.support != null ? String(m.support) : "—"}</span>
                <span>Resist: {m.resistance != null ? String(m.resistance) : "—"}</span>
              </div>
              {m.news && (
                <p className="font-mono-tech text-[10px] text-cyan-400/50">
                  News risk: {String((m.news as { news_risk?: string }).news_risk || "—")}
                </p>
              )}
              {m.error && (
                <p className="text-xs text-amber-300/80">Error: {m.error}</p>
              )}
            </div>
          ))}
        </div>

        {!loading && rows.length === 0 && !error && (
          <p className="text-sm text-cyan-400/50">No market data returned.</p>
        )}

        <p className="mt-8 text-[10px] font-mono-tech text-cyan-400/30 tracking-wider">
          Not financial advice. Trading involves risk.
        </p>
      </div>
    </ProtectedRoute>
  );
}
