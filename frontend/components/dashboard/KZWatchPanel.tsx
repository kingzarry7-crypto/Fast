"use client";

import { useCallback, useEffect, useState } from "react";

type Finding = {
  id: string;
  category: string;
  title: string;
  summary?: string;
  url?: string;
  score?: number;
  confidence?: string;
  estimated_value?: number;
  source_kind?: string;
  status?: string;
  suggested_action?: string;
};

export default function KZWatchPanel() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(false);
  const [preparing, setPreparing] = useState("");
  const [error, setError] = useState("");
  const [enabled, setEnabled] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await fetch("/api/agent/watch?limit=20", { credentials: "include" });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "Watcher unavailable");
      setItems(d.findings || []);
      setEnabled(Boolean(d.watcher?.running || d.watcher?.enabled));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Watcher unavailable");
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 60000);
    return () => window.clearInterval(timer);
  }, [load]);

  async function toggleWatch() {
    setError("");
    try {
      const endpoint = enabled ? "/api/agent/watch/unsubscribe" : "/api/agent/watch/subscribe";
      const r = await fetch(endpoint, { method: "POST", credentials: "include" });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "Could not change watcher");
      setEnabled(!enabled);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not change watcher");
    }
  }

  async function scanNow() {
    setLoading(true);
    setError("");
    try {
      const r = await fetch("/api/agent/watch/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({}),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "Watch scan failed");
      setItems(d.watch?.findings || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Watch scan failed");
    } finally {
      setLoading(false);
    }
  }

  async function prepare(id: string) {
    setPreparing(id);
    setError("");
    try {
      const r = await fetch("/api/agent/watch/" + encodeURIComponent(id) + "/prepare", {
        method: "POST",
        credentials: "include",
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || "Could not prepare mission");
      setItems((current) => current.map((x) => x.id === id ? { ...x, status: "actioned" } : x));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not prepare mission");
    } finally {
      setPreparing("");
    }
  }

  return (
    <div className="relative shrink-0">
      <button type="button" onClick={() => setOpen((v) => !v)}
        className="rounded-md border border-cyan-400/30 bg-cyan-400/5 px-2.5 py-1.5 font-mono-tech text-[10px] tracking-widest text-cyan-300 hover:bg-cyan-400/10">
        KZ WATCH
      </button>
      {open && (
        <>
          <button type="button" className="fixed inset-0 z-40 cursor-default" aria-label="Close KZ Watch" onClick={() => setOpen(false)} />
          <div className="fixed right-3 top-[62px] z-50 w-[min(calc(100vw-24px),500px)] max-h-[calc(100dvh-78px)] overflow-y-auto rounded-xl border border-cyan-400/20 bg-[#05080f] p-3 shadow-2xl">
            <div className="mb-3 flex items-center gap-2">
              <div className="flex-1">
                <div className="font-mono-tech text-[10px] tracking-widest text-cyan-300">KZ WATCHER</div>
                <div className="text-[10px] text-zinc-600">Observe → rank → report → prepare approval</div>
              </div>
              <button type="button" onClick={toggleWatch}
                className="rounded border border-emerald-400/30 px-2 py-1 font-mono-tech text-[9px] text-emerald-300">
                {enabled ? "WATCHING ON" : "ENABLE WATCH"}
              </button>
              <button type="button" onClick={scanNow} disabled={loading}
                className="rounded border border-cyan-400/30 px-2 py-1 font-mono-tech text-[9px] text-cyan-300 disabled:opacity-50">
                {loading ? "WATCHING…" : "SCAN NOW"}
              </button>
            </div>
            {error && <div className="mb-2 rounded border border-red-500/20 bg-red-500/5 p-2 text-[10px] text-red-300">{error}</div>}
            {!items.length && !loading && (
              <div className="py-8 text-center font-mono-tech text-[10px] text-zinc-600">No watch findings yet. Run a scan.</div>
            )}
            <div className="space-y-2">
              {items.map((item) => (
                <div key={item.id} className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="text-xs font-medium text-zinc-200">{item.title}</div>
                    <span className="shrink-0 font-mono-tech text-[10px] text-cyan-300">{item.score || 0}/100</span>
                  </div>
                  <div className="mt-1 text-[9px] text-zinc-500">
                    {String(item.category || "signal").replaceAll("_", " ").toUpperCase()} · {String(item.confidence || "low").toUpperCase()}
                    {item.estimated_value ? " · EST. $" + Number(item.estimated_value).toFixed(0) : ""}
                  </div>
                  <p className="mt-2 text-[10px] leading-relaxed text-zinc-500">{item.summary || "No summary available."}</p>
                  <div className="mt-2 text-[9px] leading-relaxed text-zinc-600">{item.suggested_action || "Research and verify before acting."}</div>
                  <div className="mt-2 flex gap-2">
                    {item.url && <a href={item.url} target="_blank" rel="noreferrer" className="rounded border border-cyan-400/20 px-2 py-1 font-mono-tech text-[9px] text-cyan-300">SOURCE</a>}
                    {item.category !== "news" && item.status !== "actioned" && (
                      <button type="button" onClick={() => prepare(item.id)} disabled={preparing === item.id}
                        className="rounded border border-emerald-400/25 px-2 py-1 font-mono-tech text-[9px] text-emerald-300 disabled:opacity-50">
                        {preparing === item.id ? "PREPARING…" : "PREPARE FOR APPROVAL"}
                      </button>
                    )}
                    {item.category === "news" && <span className="rounded border border-cyan-400/20 px-2 py-1 font-mono-tech text-[9px] text-cyan-300">REPORT ONLY</span>}
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 border-t border-white/5 pt-2 text-[9px] text-zinc-600">
              {enabled ? "KZ is watching in the background for new signals." : "Enable Watch to let KZ monitor safely in the background."} It never sends, submits, trades, spends money, or changes your systems by itself.
            </div>
          </div>
        </>
      )}
    </div>
  );
}
