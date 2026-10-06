"use client";

import { useEffect, useState } from "react";

type Opportunity = {
  id: string; title: string; url: string; summary: string; score: number;
  confidence: string; estimated_value: number; next_action: string; reasons: string[];
  source_kind?: string; direct_client?: boolean; source_instruction?: string;
  contact_email?: string; contact_phone?: string;
};
type Profile = {
  display_name: string; professional_title: string; business_name: string; contact_email: string;
  website: string; portfolio_url: string; services: string; starting_price: string; currency: string; tone: string;
};
const EMPTY_PROFILE: Profile = {display_name:"",professional_title:"",business_name:"",contact_email:"",website:"",portfolio_url:"",services:"",starting_price:"",currency:"USD",tone:"professional"};

export default function OpportunityPanel() {
  const [open,setOpen]=useState(false),[loading,setLoading]=useState(false),[category,setCategory]=useState("clients");
  const [items,setItems]=useState<Opportunity[]>([]),[error,setError]=useState(""),[prospect,setProspect]=useState<any>(null);
  const [preparing,setPreparing]=useState(false),[profile,setProfile]=useState<Profile>(EMPTY_PROFILE),[profileOpen,setProfileOpen]=useState(false);
  const [profileSaving,setProfileSaving]=useState(false),[profileReady,setProfileReady]=useState(false),[sending,setSending]=useState(false);
  const [channel,setChannel]=useState("email"),[destination,setDestination]=useState("");

  useEffect(()=>{if(open)loadProfile()},[open]);

  async function loadProfile(){try{const r=await fetch("/api/acquisition/profile",{credentials:"include"});const d=await r.json();if(r.ok){setProfile({...EMPTY_PROFILE,...(d.profile||{})});setProfileReady(Boolean(d.readiness?.ready));}}catch{}}
  async function saveProfile(){setProfileSaving(true);setError("");try{const r=await fetch("/api/acquisition/profile",{method:"POST",headers:{"Content-Type":"application/json"},credentials:"include",body:JSON.stringify(profile)});const d=await r.json();if(!r.ok)throw new Error(d?.detail||"Profile save failed");setProfile({...EMPTY_PROFILE,...d.profile});setProfileReady(Boolean(d.readiness?.ready));setProfileOpen(false)}catch(e){setError(e instanceof Error?e.message:"Profile save failed")}finally{setProfileSaving(false)}}
  async function hunt(){setLoading(true);setError("");try{const r=await fetch("/api/opportunities/hunt?category="+encodeURIComponent(category)+"&max_results=8",{credentials:"include"});const d=await r.json();if(!r.ok)throw new Error(d?.detail||"Opportunity hunt failed");setItems(d.opportunities||[])}catch(e){setError(e instanceof Error?e.message:"Opportunity hunt failed")}finally{setLoading(false)}}
  async function prepare(o:Opportunity){setPreparing(true);setError("");try{const r=await fetch("/api/acquisition/prepare",{method:"POST",headers:{"Content-Type":"application/json"},credentials:"include",body:JSON.stringify({opportunity:o})});const d=await r.json();if(!r.ok)throw new Error(d?.detail||"Preparation failed");setProspect(d.acquisition);const c=d.acquisition?.outreach?.contact||{};setChannel(c.email?"email":c.phone?"whatsapp":"email");setDestination(c.email||c.phone||"")}catch(e){setError(e instanceof Error?e.message:"Preparation failed")}finally{setPreparing(false)}}
  async function approveAndSend(){if(!prospect)return;setSending(true);setError("");try{const r=await fetch("/api/acquisition/approve",{method:"POST",headers:{"Content-Type":"application/json"},credentials:"include",body:JSON.stringify({acquisition:prospect,channel,destination})});const d=await r.json();if(!r.ok)throw new Error(d?.detail||d?.error||"Approval failed");if(d.status!=="sent")throw new Error(d.error||d.action?.error||"Message was not sent");setProspect({...prospect,status:"sent"})}catch(e){setError(e instanceof Error?e.message:"Message was not sent")}finally{setSending(false)}}

  const field=(key:keyof Profile,label:string,placeholder:string)=><label className="block"><span className="mb-1 block text-[9px] uppercase tracking-widest text-zinc-500">{label}</span><input value={profile[key]} onChange={e=>setProfile({...profile,[key]:e.target.value})} placeholder={placeholder} className="w-full rounded border border-white/10 bg-black/20 px-2 py-1.5 text-[10px] text-zinc-200 outline-none focus:border-emerald-400/40"/></label>;

  return <div className="relative shrink-0">
    <button type="button" onClick={()=>setOpen(v=>!v)} className="rounded-md border border-emerald-400/30 bg-emerald-400/5 px-2.5 py-1.5 font-mono-tech text-[10px] tracking-widest text-emerald-300 hover:bg-emerald-400/10">HUNT</button>
    {open&&<>
      <button className="fixed inset-0 z-40 cursor-default" aria-label="Close opportunities" onClick={()=>setOpen(false)}/>
      <div className="fixed right-3 top-[62px] z-50 w-[min(calc(100vw-24px),470px)] max-h-[calc(100dvh-78px)] overflow-y-auto rounded-xl border border-emerald-400/20 bg-[#05080f] p-3 shadow-2xl">
        <div className="mb-3 flex items-center gap-2">
          <div className="flex-1"><div className="font-mono-tech text-[10px] tracking-widest text-emerald-300">OPPORTUNITY HUNTER</div><div className="text-[10px] text-zinc-600">Find → qualify → personalize → approve</div></div>
          <button onClick={()=>setProfileOpen(v=>!v)} className="rounded border border-cyan-400/20 px-2 py-1 font-mono-tech text-[9px] text-cyan-300">{profileReady?"PROFILE":"SET PROFILE"}</button>
          <select value={category} onChange={e=>setCategory(e.target.value)} className="rounded border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-zinc-300"><option value="clients">Clients</option><option value="jobs">Jobs</option><option value="saas">SaaS</option></select>
          <button onClick={hunt} disabled={loading} className="rounded border border-emerald-400/30 px-2 py-1 font-mono-tech text-[9px] text-emerald-300 disabled:opacity-50">{loading?"SEARCHING":"HUNT"}</button>
        </div>
        {profileOpen&&<div className="mb-3 rounded-lg border border-cyan-400/20 bg-cyan-400/5 p-3">
          <div className="mb-2 font-mono-tech text-[9px] tracking-widest text-cyan-300">YOUR PROFESSIONAL IDENTITY</div>
          <div className="grid grid-cols-2 gap-2">{field("display_name","Your name","e.g. King Zarry")}{field("professional_title","Professional title","e.g. Web Developer")}{field("business_name","Business / brand","Optional")}{field("contact_email","Your email","you@example.com")}{field("website","Website","https://...")}{field("portfolio_url","Portfolio","https://...")}{field("starting_price","Starting price","80")}{field("currency","Currency","USD")}</div>
          <label className="mt-2 block"><span className="mb-1 block text-[9px] uppercase tracking-widest text-zinc-500">Services you actually offer</span><textarea value={profile.services} onChange={e=>setProfile({...profile,services:e.target.value})} placeholder="Responsive websites, landing pages, AI integrations..." className="h-16 w-full rounded border border-white/10 bg-black/20 px-2 py-1.5 text-[10px] text-zinc-200 outline-none"/></label>
          <div className="mt-2 flex justify-end"><button onClick={saveProfile} disabled={profileSaving} className="rounded border border-emerald-400/30 bg-emerald-400/10 px-3 py-1.5 font-mono-tech text-[9px] text-emerald-300">{profileSaving?"SAVING":"SAVE PROFILE"}</button></div>
          <div className="mt-2 text-[9px] text-zinc-600">KZ uses this profile to write truthful proposals. Credentials and API keys are never stored here.</div>
        </div>}
        {error&&<div className="mb-2 rounded border border-red-500/20 bg-red-500/5 p-2 text-[10px] text-red-300">{error}</div>}
        {!items.length&&!loading&&<div className="py-8 text-center font-mono-tech text-[10px] text-zinc-600">Run HUNT to find public opportunities.</div>}
        <div className="space-y-2">{items.map(o=><div key={o.id} className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
          <div className="flex items-start justify-between gap-2"><div className="text-xs font-medium text-zinc-200">{o.title}</div><span className="shrink-0 font-mono-tech text-[10px] text-emerald-300">{o.score}/100</span></div>
          <div className="mt-1 text-[10px] text-zinc-500">{o.confidence.toUpperCase()} · {String(o.source_kind || "unknown").replaceAll("_"," ").toUpperCase()} · potential ${o.estimated_value.toFixed(0)}</div>
          <p className="mt-2 line-clamp-3 text-[10px] leading-relaxed text-zinc-500">{o.summary||"No summary available."}</p>
          <div className="mt-2 text-[9px] leading-relaxed text-zinc-600">{o.source_instruction}</div><div className="mt-2 flex gap-2"><button onClick={()=>prepare(o)} disabled={preparing} className="rounded border border-emerald-400/20 px-2 py-1 font-mono-tech text-[9px] text-emerald-300 disabled:opacity-50">{preparing?"PREPARING":o.direct_client?"PREPARE PROPOSAL":"PREPARE APPLICATION"}</button><a href={o.url} target="_blank" rel="noreferrer" className="rounded border border-cyan-400/20 px-2 py-1 font-mono-tech text-[9px] text-cyan-300">SOURCE</a></div>
        </div>)}</div>
        {prospect&&<div className="mt-3 rounded-lg border border-emerald-400/20 bg-emerald-400/5 p-3">
          <div className="flex items-center justify-between"><div className="font-mono-tech text-[9px] tracking-widest text-emerald-300">CLIENT ACQUISITION · {prospect.qualification?.fit_score}/100</div><span className="text-[9px] text-zinc-500">{prospect.status}</span></div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-[9px] text-zinc-500"><div>FROM <b className="text-zinc-200">{prospect.profile?.display_name||"Profile incomplete"}</b></div><div>ROLE <b className="text-zinc-200">{prospect.profile?.professional_title||"—"}</b></div></div><div className="mt-2 rounded border border-cyan-400/10 bg-cyan-400/5 p-2 text-[9px] text-cyan-300">{String(prospect.qualification?.source_kind||"direct_client").replaceAll("_"," ").toUpperCase()} · {prospect.qualification?.direct_client?"POSSIBLE DIRECT CLIENT":"NOT A DIRECT CLIENT — USE THE SOURCE/PLATFORM APPLICATION FLOW"}</div>
          <div className="mt-2 rounded border border-white/10 bg-black/20 p-2"><div className="text-[10px] font-medium text-zinc-200">{prospect.outreach?.subject}</div><p className="mt-2 whitespace-pre-wrap text-[10px] leading-relaxed text-zinc-400">{prospect.outreach?.message}</p></div>
          {!prospect.profile_ready&&<div className="mt-2 text-[9px] text-amber-300">PROFILE INCOMPLETE — {prospect.missing_profile?.join(", ")}. <button onClick={()=>setProfileOpen(true)} className="underline">OPEN PROFILE</button></div>}
          {prospect.profile_ready&&prospect.status!=="sent"&&<div className="mt-3 rounded border border-amber-400/20 bg-amber-400/5 p-2">
            <div className="text-[9px] uppercase tracking-widest text-amber-300">EXACT DESTINATION — REVIEW BEFORE APPROVAL</div>
            <div className="mt-2 flex gap-2"><select value={channel} onChange={e=>setChannel(e.target.value)} className="rounded border border-white/10 bg-black/30 px-2 py-1.5 text-[10px] text-zinc-300"><option value="email">Email</option><option value="whatsapp">WhatsApp</option></select><input value={destination} onChange={e=>setDestination(e.target.value)} placeholder={channel==="email"?"client@example.com":"+234..."} className="min-w-0 flex-1 rounded border border-white/10 bg-black/30 px-2 py-1.5 text-[10px] text-zinc-200"/></div>
            <button onClick={approveAndSend} disabled={sending||!destination} className="mt-2 w-full rounded border border-emerald-400/40 bg-emerald-400/10 px-3 py-2 font-mono-tech text-[10px] tracking-widest text-emerald-300 disabled:opacity-40">{sending?"SENDING…":"APPROVE & SEND"}</button>
            <div className="mt-1 text-center text-[8px] text-zinc-600">APPROVAL REQUIRED — nothing is sent before you press APPROVE &amp; SEND.</div>
          </div>}
          {prospect.status==="sent"&&<div className="mt-2 rounded border border-emerald-400/20 bg-emerald-400/5 p-2 text-center font-mono-tech text-[9px] text-emerald-300">SENT — provider confirmed the action.</div>}
        </div>}
        <div className="mt-3 border-t border-white/5 pt-2 text-[9px] text-zinc-600">Research signals are not guaranteed jobs, clients, or income. Verify the opportunity and destination before sending.</div>
      </div>
    </>}
  </div>;
}
