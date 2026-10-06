"use client";

import { useCallback, useEffect, useState } from "react";

type Snapshot = {
  workflows: any[];
  revenue: any;
  learning: any;
  browser: any;
  worker: any;
};

export default function CommandStatusPanel() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [w, r, l, b, k] = await Promise.allSettled([
        fetch("/api/workflows", { credentials: "include" }).then(x => x.ok ? x.json() : null),
        fetch("/api/revenue", { credentials: "include" }).then(x => x.ok ? x.json() : null),
        fetch("/api/learning", { credentials: "include" }).then(x => x.ok ? x.json() : null),
        fetch("/api/browser/status", { credentials: "include" }).then(x => x.ok ? x.json() : null),
        fetch("/api/workflows/worker/status", { credentials: "include" }).then(x => x.ok ? x.json() : null),
      ]);
      setData({
        workflows: w.status === "fulfilled" ? (w.value?.workflows || []) : [],
        revenue: r.status === "fulfilled" ? (r.value?.revenue || {}) : {},
        learning: l.status === "fulfilled" ? (l.value?.learning || {}) : {},
        browser: b.status === "fulfilled" ? (b.value?.browser || {}) : {},
        worker: k.status === "fulfilled" ? (k.value?.worker || {}) : {},
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    load();
    const timer = window.setInterval(load, 8000);
    return () => window.clearInterval(timer);
  }, [open, load]);

  const workflows = data?.workflows || [];
  const waiting = workflows.filter(x => x.status === "waiting_for_approval").length;
  const active = workflows.filter(x => !["completed", "failed", "rejected"].includes(x.status)).length;
  const completed = workflows.filter(x => x.status === "completed").length;
  const browserReady = data?.browser?.available === true;
  const workerRunning = data?.worker?.running === true || data?.worker?.started === true;

  const card = (label: string, value: string, detail: string) => (
    <div className="rounded-xl border border-white/5 bg-white/[0.025] p-3">
      <div className="font-mono-tech text-[8px] tracking-widest text-zinc-600">{label}</div>
      <div className="mt-1 text-lg text-zinc-200">{value}</div>
      <div className="mt-1 text-[9px] text-zinc-600">{detail}</div>
    </div>
  );

  return (
    <>
      <button type="button" onClick={() => setOpen(true)}
        className="shrink-0 rounded-md border border-cyan-400/30 bg-cyan-400/5 px-2.5 py-1.5 font-mono-tech text-[10px] tracking-widest text-cyan-200 hover:bg-cyan-400/10">
        KZ STATUS
      </button>

      {open && (
        <>
          <button type="button" aria-label="Close KZ Status" onClick={() => setOpen(false)}
            className="fixed inset-0 z-[70] bg-black/60 backdrop-blur-[2px]" />
          <aside className="fixed right-0 top-0 z-[80] flex h-[100dvh] w-full max-w-md flex-col border-l border-cyan-400/15 bg-[#060811] shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
              <div>
                <div className="font-mono-tech text-xs tracking-[0.22em] text-cyan-200">KZ COMMAND STATUS</div>
                <div className="mt-1 text-[10px] text-zinc-500">One view of work, approvals, browser, verification and learning.</div>
              </div>
              <button type="button" onClick={() => setOpen(false)} className="rounded-md px-2 py-1 text-zinc-500 hover:bg-white/5">×</button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto p-4">
              <div className="mb-3 grid grid-cols-2 gap-2">
                {card("ACTIVE WORK", String(active), "plans currently moving")}
                {card("APPROVAL QUEUE", String(waiting), waiting ? "action needs your decision" : "nothing waiting")}
                {card("COMPLETED", String(completed), "verified workflow completions")}
                {card("LEARNED", String(data?.learning?.count ?? 0), "stored workflow lessons")}
              </div>

              <div className="mb-3 grid grid-cols-2 gap-2">
                <div className={"rounded-xl border p-3 " + (browserReady ? "border-emerald-400/20 bg-emerald-400/5" : "border-red-400/20 bg-red-400/5")}>
                  <div className="font-mono-tech text-[8px] tracking-widest text-zinc-600">BROWSER</div>
                  <div className={"mt-1 text-sm " + (browserReady ? "text-emerald-200" : "text-red-300")}>{browserReady ? "READY" : "OFFLINE"}</div>
                  <div className="mt-1 text-[9px] text-zinc-600">Chromium execution runtime</div>
                </div>
                <div className={"rounded-xl border p-3 " + (workerRunning ? "border-emerald-400/20 bg-emerald-400/5" : "border-amber-400/20 bg-amber-400/5")}>
                  <div className="font-mono-tech text-[8px] tracking-widest text-zinc-600">WORKER</div>
                  <div className={"mt-1 text-sm " + (workerRunning ? "text-emerald-200" : "text-amber-200")}>{workerRunning ? "RUNNING" : "CHECK"}</div>
                  <div className="mt-1 text-[9px] text-zinc-600">safe workflow continuation</div>
                </div>
              </div>

              <div className="rounded-xl border border-amber-400/15 bg-amber-400/5 p-3">
                <div className="font-mono-tech text-[9px] tracking-widest text-amber-300">REVENUE TRUTH</div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-[10px]">
                  <div><span className="text-zinc-600">Potential</span><div className="text-zinc-200">$ {Number(data?.revenue?.potential_revenue || 0).toFixed(2)}</div></div>
                  <div><span className="text-zinc-600">Confirmed</span><div className="text-emerald-200">$ {Number(data?.revenue?.confirmed_revenue || 0).toFixed(2)}</div></div>
                </div>
                <div className="mt-2 text-[9px] leading-relaxed text-zinc-500">{data?.revenue?.warning || "Potential revenue is not payment confirmation."}</div>
              </div>

              <div className="mt-3">
                <div className="mb-2 font-mono-tech text-[9px] tracking-widest text-cyan-300">RECENT WORK</div>
                {!workflows.length && <div className="rounded-xl border border-white/5 p-3 text-[10px] text-zinc-600">No workflows yet.</div>}
                {workflows.slice(0, 8).map((w) => (
                  <div key={w.id} className="mb-2 rounded-lg border border-white/5 bg-white/[0.02] p-3">
                    <div className="text-[11px] leading-relaxed text-zinc-300">{w.goal}</div>
                    <div className="mt-1 font-mono-tech text-[8px] uppercase tracking-wider text-zinc-600">{String(w.status).replaceAll("_", " ")} · risk:{w.risk || "green"}</div>
                  </div>
                ))}
              </div>

              <button type="button" onClick={load} disabled={loading}
                className="mt-2 w-full rounded-lg border border-cyan-400/20 bg-cyan-400/5 py-2 font-mono-tech text-[9px] tracking-widest text-cyan-200 disabled:opacity-40">
                {loading ? "REFRESHING..." : "REFRESH STATUS"}
              </button>

              <div className="mt-3 text-[9px] leading-relaxed text-zinc-600">
                KZ never treats potential revenue as received money. Consequential external actions remain approval-gated and are only reported as successful when verification evidence exists.
              </div>
            </div>
          </aside>
        </>
      )}
    </>
  );
}
