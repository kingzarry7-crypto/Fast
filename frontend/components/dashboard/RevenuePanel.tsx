"use client";

import { useCallback, useEffect, useState } from "react";

type Revenue = {
  potential_revenue: number; confirmed_revenue: number; estimated_cost: number;
  confirmed_profit: number; active_work: number; waiting_for_approval: number;
  completed_work: number; warning: string;
  pipeline: Array<{ workflow_id: string; goal: string; status: string; potential_revenue: number; risk: string }>;
};

export default function RevenuePanel() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<Revenue | null>(null);
  const load = useCallback(async () => {
    try { const r = await fetch("/api/revenue", { credentials: "include" }); if (r.ok) setData((await r.json()).revenue || null); } catch {}
  }, []);
  useEffect(() => {
    if (!open) return; load(); const timer = window.setInterval(load, 10000);
    return () => window.clearInterval(timer);
  }, [open, load]);

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className="rounded-md border border-emerald-400/25 bg-emerald-400/5 px-2.5 py-1.5 font-mono-tech text-[10px] tracking-widest text-emerald-200 hover:bg-emerald-400/10 shrink-0">REVENUE</button>
      {open && (
        <>
          <button type="button" aria-label="Close Revenue" onClick={() => setOpen(false)} className="fixed inset-0 z-[70] bg-black/60 backdrop-blur-[2px]" />
          <aside className="fixed right-0 top-0 z-[80] flex h-[100dvh] w-full max-w-md flex-col border-l border-emerald-400/15 bg-[#060811] shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
              <div><div className="font-mono-tech text-xs tracking-[0.22em] text-emerald-200">REVENUE ENGINE</div><div className="mt-1 text-[10px] text-zinc-500">Pipeline, work progress and approval queue.</div></div>
              <button type="button" onClick={() => setOpen(false)} className="rounded-md px-2 py-1 text-zinc-500 hover:bg-white/5">×</button>
            </div>
            <div className="grid grid-cols-2 gap-2 p-4">
              {[["Potential", data?.potential_revenue], ["Confirmed", data?.confirmed_revenue], ["Costs", data?.estimated_cost], ["Profit", data?.confirmed_profit]].map(([label, value]) => (
                <div key={label} className="rounded-xl border border-white/5 bg-white/[0.025] p-3"><div className="font-mono-tech text-[8px] tracking-widest text-zinc-600">{label}</div><div className="mt-1 text-lg text-zinc-200">{"$"}{Number(value || 0).toFixed(2)}</div></div>
              ))}
            </div>
            <div className="mx-4 rounded-xl border border-amber-400/15 bg-amber-400/5 p-3 text-[10px] leading-5 text-zinc-400">{data?.warning || "Revenue forecasts are not payment receipts."}</div>
            <div className="grid grid-cols-3 gap-2 p-4">
              <div className="rounded-lg border border-white/5 p-2 text-center"><b className="block text-zinc-200">{data?.active_work ?? 0}</b><span className="text-[8px] text-zinc-600">ACTIVE</span></div>
              <div className="rounded-lg border border-white/5 p-2 text-center"><b className="block text-amber-200">{data?.waiting_for_approval ?? 0}</b><span className="text-[8px] text-zinc-600">APPROVAL</span></div>
              <div className="rounded-lg border border-white/5 p-2 text-center"><b className="block text-zinc-200">{data?.completed_work ?? 0}</b><span className="text-[8px] text-zinc-600">DONE</span></div>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4">
              <div className="mb-2 font-mono-tech text-[9px] tracking-widest text-emerald-300/70">PIPELINE</div>
              {!data?.pipeline?.length && <p className="text-xs text-zinc-600">No revenue opportunities yet.</p>}
              {data?.pipeline?.map((item) => (
                <div key={item.workflow_id} className="mb-2 rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <div className="text-xs text-zinc-300">{item.goal}</div>
                  <div className="mt-2 flex justify-between font-mono-tech text-[8px] uppercase text-zinc-600"><span>{item.status.replaceAll("_", " ")}</span><span>{"$"}{Number(item.potential_revenue || 0).toFixed(0)} potential</span></div>
                </div>
              ))}
            </div>
          </aside>
        </>
      )}
    </>
  );
}
