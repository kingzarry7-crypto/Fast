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

export default function SignalsPage() {
  const [rows, setRows] = useState<MarketSnapshot[]>([]);
  const [actionable, setActionable] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSignals();
      setRows(data.signals || []);
      setActionable(data.actionable_count || 0);
    } catch (e) {
      setError(e instanceof ApiError ? e.detail || e.message : "Failed to load signals");
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
              Signals
            </h1>
            <p className="font-mono-tech text-[10px] tracking-[0.4em] text-cyan-400/40 mt-1">
              MTF PACKAGE · {actionable} ACTIONABLE
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
          <p className="font-mono-tech text-xs text-cyan-400/50">Building signals…</p>
        )}
        {error && (
          <div className="kz-panel p-4 text-sm text-amber-200 mb-6">{error}</div>
        )}

        <div className="space-y-4">
          {rows.map((s) => {
            const reasons = Array.isArray(s.reasons) ? s.reasons : [];
            return (
              <div key={String(s.symbol || "")} className="kz-panel p-5">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                  <p className="font-display text-lg text-white tracking-wider">
                    {String(s.symbol || "—")}
                  </p>
                  <span
                    className={`px-2.5 py-1 rounded-md border text-[10px] font-mono-tech tracking-widest ${badge(
                      s.signal
                    )}`}
                  >
                    {String(s.signal || "WAIT").toUpperCase()}
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono-tech text-[10px] text-cyan-300/70 mb-3">
                  <span>Price {s.price != null ? String(s.price) : "—"}</span>
                  <span>Conf {s.confidence != null ? String(s.confidence) : "—"}</span>
                  <span>Entry {s.entry != null ? String(s.entry) : "—"}</span>
                  <span>SL {s.stop_loss != null ? String(s.stop_loss) : "—"}</span>
                  <span>TP1 {s.tp1 != null ? String(s.tp1) : "—"}</span>
                  <span>TP2 {s.tp2 != null ? String(s.tp2) : "—"}</span>
                  <span>TP3 {s.tp3 != null ? String(s.tp3) : "—"}</span>
                  <span>Trend {String(s.trend || "—")}</span>
                </div>
                {reasons.length > 0 && (
                  <ul className="text-xs text-cyan-200/50 space-y-1 list-disc list-inside">
                    {reasons.slice(0, 5).map((r, i) => (
                      <li key={i}>{String(r)}</li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>

        <p className="mt-8 text-[10px] font-mono-tech text-cyan-400/30 tracking-wider">
          Not financial advice. Trading involves risk.
        </p>
      </div>
    </ProtectedRoute>
  );
}
