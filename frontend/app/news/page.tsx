"use client";

import { useCallback, useEffect, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import { api, ApiError } from "@/lib/api";

type AssetNews = {
  symbol?: string;
  news_risk?: string;
  news_summary?: string;
  news_headlines?: unknown[];
  news_events?: unknown[];
  news_available?: boolean;
};

export default function NewsPage() {
  const [assets, setAssets] = useState<AssetNews[]>([]);
  const [headlines, setHeadlines] = useState<unknown[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getNews();
      setAssets((data.assets || []) as AssetNews[]);
      setHeadlines(data.global_headlines || []);
    } catch (e) {
      setError(e instanceof ApiError ? e.detail || e.message : "Failed to load news");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const riskClass = (r?: string) => {
    const x = String(r || "").toUpperCase();
    if (x === "HIGH") return "text-red-300";
    if (x === "MEDIUM" || x === "MED") return "text-amber-300";
    if (x === "LOW") return "text-emerald-300";
    return "text-cyan-300/70";
  };

  return (
    <ProtectedRoute>
      <div className="p-6 lg:p-10 max-w-6xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-8">
          <div>
            <h1 className="font-display text-2xl font-bold text-white kz-glow-text tracking-wider">
              News
            </h1>
            <p className="font-mono-tech text-[10px] tracking-[0.4em] text-cyan-400/40 mt-1">
              RISK · HEADLINES · CALENDAR CONTEXT
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
          <p className="font-mono-tech text-xs text-cyan-400/50">Fetching news…</p>
        )}
        {error && (
          <div className="kz-panel p-4 text-sm text-amber-200 mb-6">{error}</div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {assets.map((a) => (
            <div key={String(a.symbol)} className="kz-panel p-5 space-y-2">
              <div className="flex justify-between gap-2">
                <p className="font-display text-white tracking-wider">{a.symbol}</p>
                <span className={`font-mono-tech text-[10px] tracking-widest ${riskClass(a.news_risk)}`}>
                  RISK {String(a.news_risk || "—").toUpperCase()}
                </span>
              </div>
              <p className="text-sm text-cyan-200/60">
                {a.news_summary || "No summary"}
              </p>
              {(a.news_headlines || []).slice(0, 3).map((h, i) => (
                <p key={i} className="text-xs text-cyan-400/50 border-l border-cyan-500/20 pl-2">
                  {typeof h === "string" ? h : JSON.stringify(h).slice(0, 160)}
                </p>
              ))}
            </div>
          ))}
        </div>

        {headlines.length > 0 && (
          <section className="kz-panel p-6">
            <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40 mb-4">
              GLOBAL HEADLINES
            </p>
            <ul className="space-y-2">
              {headlines.slice(0, 12).map((h, i) => (
                <li key={i} className="text-sm text-cyan-100/70 border-b border-cyan-500/10 pb-2">
                  {typeof h === "string"
                    ? h
                    : typeof h === "object" && h && "title" in (h as object)
                      ? String((h as { title: string }).title)
                      : JSON.stringify(h).slice(0, 200)}
                </li>
              ))}
            </ul>
          </section>
        )}

        <p className="mt-8 text-[10px] font-mono-tech text-cyan-400/30 tracking-wider">
          Informational only. Not financial advice.
        </p>
      </div>
    </ProtectedRoute>
  );
}
