"use client";
import { useEffect, useState } from "react";
type Worker = { running:boolean; last_run:string|null; last_error:string|null; runs:number; policy:string };
export default function WorkerPanel() {
  const [worker,setWorker]=useState<Worker|null>(null);
  useEffect(()=>{
    let active=true;
    const load=async()=>{ try { const r=await fetch("/api/workflows/worker/status",{credentials:"include"}); if(r.ok && active) setWorker((await r.json()).worker); } catch {} };
    load(); const id=window.setInterval(load,10000); return()=>{active=false;window.clearInterval(id)};
  },[]);
  return <div className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
    <div className="flex items-center justify-between"><span className="font-mono-tech text-[9px] tracking-widest text-zinc-500">AUTONOMOUS WORKER</span><span className={worker?.running ? "text-[9px] text-emerald-300" : "text-[9px] text-zinc-600"}>{worker?.running ? "● RUNNING" : "○ STARTING"}</span></div>
    <div className="mt-1 text-[9px] text-zinc-600">{worker ? (worker.runs + " scheduler cycles • " + worker.policy) : "Checking worker health…"}</div>
    {worker?.last_error && <div className="mt-1 text-[9px] text-amber-400">{worker.last_error}</div>}
  </div>;
}