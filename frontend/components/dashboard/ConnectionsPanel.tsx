"use client";

import { useState } from "react";

type Page = { url?: string; title?: string; text?: string; inputs?: {selector:string;type:string;name?:string|null;placeholder?:string|null}[] };

export default function ConnectionsPanel() {
  const [open,setOpen]=useState(false);
  const [url,setUrl]=useState("");
  const [page,setPage]=useState<Page|null>(null);
  const [busy,setBusy]=useState(false);
  const [selector,setSelector]=useState("");
  const [value,setValue]=useState("");
  const [message,setMessage]=useState("");

  async function start() {
    if(!url.trim()) return;
    setBusy(true); setMessage("");
    try {
      const r=await fetch("/api/browser/connect/start",{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:url.trim()})});
      const d=await r.json(); if(!r.ok) throw new Error(d.detail||"Could not open account");
      setPage(d.page); setMessage("Login yourself in the KZ browser session. KZ does not save your password.");
    } catch(e){setMessage(e instanceof Error?e.message:"Could not connect");} finally{setBusy(false);}
  }

  async function action(type:string) {
    setBusy(true);
    try {
      const r=await fetch("/api/browser/connect/action",{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({type,selector,value})});
      const d=await r.json(); if(!r.ok) throw new Error(d.detail||"Action failed");
      setPage(d.page);
    } catch(e){setMessage(e instanceof Error?e.message:"Action failed");} finally{setBusy(false);}
  }

  return <>
    <button type="button" onClick={()=>setOpen(true)} className="rounded-md border border-cyan-400/30 bg-cyan-400/5 px-2.5 py-1.5 font-mono-tech text-[10px] tracking-widest text-cyan-200 hover:bg-cyan-400/10">ACCOUNTS</button>
    {open && <>
      <button className="fixed inset-0 z-[70] bg-black/60" aria-label="Close accounts" onClick={()=>setOpen(false)}/>
      <aside className="fixed right-0 top-0 z-[80] flex h-[100dvh] w-full max-w-md flex-col border-l border-cyan-400/20 bg-[#060811] shadow-2xl">
        <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
          <div><div className="font-mono-tech text-xs tracking-[0.2em] text-cyan-200">CONNECTED ACCOUNTS</div><div className="mt-1 text-[10px] text-zinc-500">Connect by logging in yourself. Passwords and OTPs are never saved in KZ memory.</div></div>
          <button onClick={()=>setOpen(false)} className="px-2 py-1 text-zinc-500">×</button>
        </div>
        <div className="border-b border-white/5 p-4">
          <input value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://your-site.com/login" className="w-full rounded-lg border border-cyan-400/15 bg-white/[0.03] p-3 text-sm text-white outline-none"/>
          <button disabled={busy||!url.trim()} onClick={start} className="mt-2 w-full rounded-lg border border-cyan-400/25 bg-cyan-400/10 py-2 font-mono-tech text-[9px] tracking-widest text-cyan-100 disabled:opacity-40">{busy?"OPENING...":"OPEN LOGIN"}</button>
          {message && <p className="mt-2 text-xs text-zinc-400">{message}</p>}
        </div>
        {page && <div className="min-h-0 flex-1 overflow-y-auto p-4">
          <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
            <div className="truncate text-xs text-cyan-200">{page.title||"Connected page"}</div>
            <div className="mt-1 break-all text-[9px] text-zinc-600">{page.url}</div>
          </div>
          <div className="mt-3 space-y-2">
            {(page.inputs||[]).map((x,i)=><button key={i} onClick={()=>setSelector(x.selector)} className={"block w-full rounded-lg border p-2 text-left text-xs "+(selector===x.selector?"border-cyan-400/40 bg-cyan-400/10 text-cyan-100":"border-white/5 text-zinc-500")}>{x.type} · {x.name||x.placeholder||x.selector}</button>)}
          </div>
          {selector && <div className="mt-3 rounded-lg border border-cyan-400/15 p-3">
            <div className="text-[9px] font-mono-tech tracking-widest text-cyan-300">SELECTED FIELD</div>
            <input value={value} onChange={e=>setValue(e.target.value)} type={page.inputs?.find(x=>x.selector===selector)?.type==="password"?"password":"text"} placeholder="Enter value (not stored by KZ)" className="mt-2 w-full rounded-lg border border-white/10 bg-black/20 p-2 text-sm text-white"/>
            <button onClick={()=>action("fill")} disabled={busy} className="mt-2 w-full rounded-lg border border-cyan-400/20 py-2 font-mono-tech text-[9px] tracking-widest text-cyan-200">FILL FIELD</button>
          </div>}
          <div className="mt-3 flex gap-2"><button onClick={()=>action("refresh")} className="flex-1 rounded-lg border border-white/10 py-2 font-mono-tech text-[9px] tracking-widest text-zinc-400">REFRESH</button><button onClick={()=>action("click")} disabled={!selector} className="flex-1 rounded-lg border border-amber-400/20 py-2 font-mono-tech text-[9px] tracking-widest text-amber-200">CLICK SELECTED</button></div>
          <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg border border-white/5 bg-black/20 p-3 text-[10px] text-zinc-500">{page.text||""}</pre>
        </div>}
      </aside>
    </>}
  </>;
}
