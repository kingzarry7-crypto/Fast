"use client";

import { useState } from "react";

type Opportunity = {
  id: string; title: string; url: string; summary: string; score: number;
  confidence: string; estimated_value: number; next_action: string; reasons: string[];
};

export default function OpportunityPanel() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [category, setCategory] = useState("clients");
  const [items, setItems] = useState<Opportunity[]>([]);
  const [error, setError] = useState("");
  const [prospect, setProspect] = useState<any>(null);
  const [preparing, setPreparing] = useState(false);

  async function hunt() {
    setLoading(true); setError("");
    try {
      const r = await fetch(`/api/opportunities/hunt?category=${encodeURIComponent(category)}&max_results=8`, { credentials: "include" });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || "Opportunity hunt failed");
      setItems(data.opportunities || []);
    } catch (e) { setError(e instanceof Error ? e.message : "Opportunity hunt failed"); }
    finally { setLoading(false); }
  }

  async function prepare(o: Opportunity) {
    setPreparing(true); setError("");
    try {
      const r = await fetch("/api/acquisition/prepare", { method:"POST", headers:{"Content-Type":"application/json"}, credentials:"include", body:JSON.stringify({opportunity:o}) });
      const data = await r.json(); if (!r.ok) throw new Error(data?.detail || "Preparation failed");
      setProspect(data.acquisition);
    } catch (e) { setError(e instanceof Error ? e.message : "Preparation failed"); } finally { setPreparing(false); }
  }

  return <div className="relative shrink-0">
    <button type="button" onClick={() => setOpen(v => !v)} className="rounded-md border border-emerald-400/30 bg-emerald-400/5 px-2.5 py-1.5 font-mono-tech text-[10px] tracking-widest text-emerald-300 hover:bg-emerald-400/10">HUNT</button>
    {open && <>
      <button className="fixed inset-0 z-40 cursor-default" aria-label="Close opportunities" onClick={() => setOpen(false)} />
      <div className="fixed right-3 top-[62px] z-50 w-[min(calc(100vw-24px),430px)] max-h-[calc(100dvh-78px)] overflow-y-auto rounded-xl border border-emerald-400/20 bg-[#05080f] p-3 shadow-2xl">
        <div className="mb-3 flex items-center gap-2">
          <div className="flex-1"><div className="font-mono-tech text-[10px] tracking-widest text-emerald-300">OPPORTUNITY HUNTER</div><div className="text-[10px] text-zinc-600">Public signals → score → review → approve</div></div>
          <select value={category} onChange={e => setCategory(e.target.value)} className="rounded border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-zinc-300"><option value="clients">Clients</option><option value="jobs">Jobs</option><option value="saas">SaaS</option></select>
          <button onClick={hunt} disabled={loading} className="rounded border border-emerald-400/30 px-2 py-1 font-mono-tech text-[9px] text-emerald-300 disabled:opacity-50">{loading ? "SEARCHING" : "HUNT"}</button>
        </div>
        {error && <div className="mb-2 rounded border border-red-500/20 bg-red-500/5 p-2 text-[10px] text-red-300">{error}</div>}
        {!items.length && !loading && <div className="py-8 text-center font-mono-tech text-[10px] text-zinc-600">Run HUNT to find public opportunities.</div>}
        <div className="space-y-2">{items.map(o => <div key={o.id} className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
          <div className="flex items-start justify-between gap-2"><div className="text-xs font-medium text-zinc-200">{o.title}</div><span className="shrink-0 font-mono-tech text-[10px] text-emerald-300">{o.score}/100</span></div>
          <div className="mt-1 text-[10px] text-zinc-500">{o.confidence.toUpperCase()} · potential ${o.estimated_value.toFixed(0)}</div>
          <p className="mt-2 line-clamp-3 text-[10px] leading-relaxed text-zinc-500">{o.summary || "No summary available."}</p>
          <div className="mt-2 flex gap-2"><button onClick={()=>prepare(o)} disabled={preparing} className="rounded border border-emerald-400/20 px-2 py-1 font-mono-tech text-[9px] text-emerald-300 disabled:opacity-50">{preparing ? "PREPARING" : "PREPARE"}</button><a href={o.url} target="_blank" rel="noreferrer" className="rounded border border-cyan-400/20 px-2 py-1 font-mono-tech text-[9px] text-cyan-300">SOURCE</a></div>
        </div>)}</div>
        {prospect && <div className="mt-3 rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3"><div className="font-mono-tech text-[9px] tracking-widest text-emerald-300">ACQUISITION DRAFT · {prospect.qualification?.fit_score}/100</div><div className="mt-2 text-[10px] text-zinc-300">{prospect.outreach?.subject}</div><p className="mt-1 text-[10px] leading-relaxed text-zinc-500">{prospect.outreach?.message}</p><div className="mt-2 text-[9px] text-amber-300">DRAFT ONLY — explicit approval is required before external outreach.</div></div>}<div className="mt-3 border-t border-white/5 pt-2 text-[9px] text-zinc-600">Research signals are not guaranteed jobs, clients, or income. Verify before acting.</div>
      </div>
    </>}
  </div>;
}
