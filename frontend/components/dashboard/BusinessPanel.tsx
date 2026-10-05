"use client";

import { useCallback, useEffect, useState } from "react";

type Dashboard = {
  potential_revenue: number;
  confirmed_revenue: number;
  estimated_cost: number;
  confirmed_profit: number;
  kpis: { active_work:number; waiting_for_approval:number; completed_work:number; failed_work:number; opportunities_seen:number; delivery_ready:number };
  funnel: { opportunities:number; prepared_work:number; active:number; completed:number; failed:number };
  priority_work: Array<{workflow_id:string; goal:string; status:string; potential_revenue:number; risk:string}>;
  next_actions: string[];
  warning: string;
};

const money = (n:number) => "$" + Number(n || 0).toFixed(2);

export default function BusinessPanel() {
  const [open,setOpen]=useState(false);
  const [data,setData]=useState<Dashboard|null>(null);
  const [loading,setLoading]=useState(false);

  const load=useCallback(async()=>{
    setLoading(true);
    try {
      const r=await fetch("/api/business/dashboard",{credentials:"include"});
      if(r.ok) setData((await r.json()).dashboard||null);
    } finally { setLoading(false); }
  },[]);

  useEffect(()=>{ if(!open)return; load(); const t=window.setInterval(load,15000); return()=>window.clearInterval(t); },[open,load]);

  return <>
    <button type="button" onClick={()=>setOpen(true)}
      className="rounded-md border border-cyan-400/30 bg-cyan-400/5 px-2.5 py-1.5 font-mono-tech text-[10px] tracking-widest text-cyan-200 hover:bg-cyan-400/10 shrink-0">
      BUSINESS
    </button>

    {open && <>
      <button type="button" aria-label="Close Business" onClick={()=>setOpen(false)} className="fixed inset-0 z-[70] bg-black/60 backdrop-blur-[2px]" />
      <aside className="fixed right-0 top-0 z-[80] flex h-[100dvh] w-full max-w-lg flex-col border-l border-cyan-400/15 bg-[#060811] shadow-2xl">
        <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
          <div>
            <div className="font-mono-tech text-xs tracking-[0.22em] text-cyan-200">BUSINESS COMMAND CENTER</div>
            <div className="mt-1 text-[10px] text-zinc-500">One view of revenue pipeline, work, approvals and delivery.</div>
          </div>
          <button type="button" onClick={()=>setOpen(false)} className="rounded-md px-2 py-1 text-zinc-500 hover:bg-white/5">×</button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              ["Potential",money(data?.potential_revenue||0)],
              ["Confirmed",money(data?.confirmed_revenue||0)],
              ["Costs",money(data?.estimated_cost||0)],
              ["Profit",money(data?.confirmed_profit||0)]
            ].map(([a,b])=><div key={a} className="rounded-xl border border-white/5 bg-white/[0.025] p-3"><div className="font-mono-tech text-[8px] tracking-widest text-zinc-600">{a}</div><div className="mt-1 text-base text-zinc-200">{b}</div></div>)}
          </div>

          <div className="mt-3 grid grid-cols-3 gap-2">
            {[
              ["ACTIVE",data?.kpis.active_work],["APPROVAL",data?.kpis.waiting_for_approval],["DONE",data?.kpis.completed_work],
              ["FAILED",data?.kpis.failed_work],["OPPORTUNITIES",data?.kpis.opportunities_seen],["DELIVERY",data?.kpis.delivery_ready]
            ].map(([a,b])=><div key={String(a)} className="rounded-lg border border-white/5 p-2 text-center"><b className="block text-zinc-200">{b??0}</b><span className="text-[7px] tracking-wider text-zinc-600">{a}</span></div>)}
          </div>

          <section className="mt-4 rounded-xl border border-white/5 bg-white/[0.02] p-3">
            <div className="font-mono-tech text-[9px] tracking-widest text-cyan-300/70">BUSINESS FUNNEL</div>
            <div className="mt-3 grid grid-cols-5 gap-1">
              {[
                ["OPPORTUNITIES",data?.funnel.opportunities],["WORK",data?.funnel.prepared_work],["ACTIVE",data?.funnel.active],["DONE",data?.funnel.completed],["FAILED",data?.funnel.failed]
              ].map(([a,b])=><div key={String(a)} className="min-w-0 text-center"><div className="mx-auto flex h-9 w-9 items-center justify-center rounded-full border border-cyan-400/15 bg-cyan-400/5 text-xs text-cyan-200">{b??0}</div><div className="mt-1 truncate text-[7px] text-zinc-600">{a}</div></div>)}
            </div>
          </section>

          <section className="mt-3">
            <div className="mb-2 font-mono-tech text-[9px] tracking-widest text-cyan-300/70">PRIORITY WORK</div>
            {!data?.priority_work?.length && <div className="rounded-xl border border-white/5 p-4 text-center text-xs text-zinc-600">No revenue-bearing work yet.</div>}
            {data?.priority_work?.map(w=><div key={w.workflow_id} className="mb-2 rounded-xl border border-white/5 bg-white/[0.02] p-3">
              <div className="text-xs text-zinc-300">{w.goal}</div>
              <div className="mt-2 flex justify-between font-mono-tech text-[8px] uppercase text-zinc-600"><span>{w.status.replaceAll("_"," ")}</span><span>{money(w.potential_revenue)} potential</span></div>
            </div>)}
          </section>

          <section className="mt-3 rounded-xl border border-amber-400/15 bg-amber-400/5 p-3">
            <div className="font-mono-tech text-[9px] tracking-widest text-amber-200">NEXT ACTIONS</div>
            <ul className="mt-2 space-y-1 text-[10px] text-zinc-400">
              {(data?.next_actions?.length ? data.next_actions : ["No urgent business action detected."]).map(x=><li key={x}>• {x}</li>)}
            </ul>
          </section>

          <div className="mt-3 text-[9px] leading-4 text-zinc-600">{loading ? "Refreshing…" : data?.warning || "Revenue figures are forecasts until payment is verified."}</div>
        </div>
      </aside>
    </>}
  </>;
}
