"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

type PluginData = { tools?: Array<{ provider: string; available?: boolean; connection_status?: string }>; providers?: Record<string, { connected?: boolean }> };
type CoreMode = "idle" | "thinking" | "listening" | "executing" | "error";
const modules = [
  { id: "chat", title: "Chat", subtitle: "Talk to your AI", href: "/chat", icon: "◉", color: "#35d9ff", angle: -90 },
  { id: "plugins", title: "Plugins", subtitle: "Tools & extensions", href: "/plugins", icon: "✣", color: "#bd79ff", angle: -45 },
  { id: "workflow", title: "Workflow", subtitle: "Automate & execute", href: "/agent", icon: "⌘", color: "#20bfff", angle: 0 },
  { id: "revenue", title: "Revenue", subtitle: "Opportunities & results", href: "/agent", icon: "↗", color: "#20e49a", angle: 35 },
  { id: "accounts", title: "Accounts", subtitle: "Connected services", href: "/settings", icon: "↗", color: "#32d9ff", angle: 75 },
  { id: "settings", title: "Settings", subtitle: "Preferences & security", href: "/settings", icon: "⚙", color: "#72bfff", angle: 115 },
  { id: "delivery", title: "Delivery", subtitle: "Telegram & Discord", href: "/settings", icon: "➤", color: "#309dff", angle: 155 },
  { id: "memory", title: "Memory", subtitle: "Knowledge & context", href: "/history", icon: "❋", color: "#ef85ff", angle: 195 },
  { id: "business", title: "Business", subtitle: "Shopify & store", href: "/agent", icon: "▣", color: "#ffb54a", angle: 235 },
  { id: "development", title: "Development", subtitle: "GitHub & code", href: "/plugins", icon: "⌘", color: "#9d8aff", angle: 270 },
] as const;

function HumanHead({ mode, tilt }: { mode: CoreMode; tilt: { x: number; y: number } }) {
  return <div className={"kz-human-head kz-head-" + mode} style={{ ["--head-x" as string]: tilt.y + "deg", ["--head-y" as string]: tilt.x + "deg" }} aria-label={"King Zarry AI " + mode}>
    <div className="kz-head-halo" /><div className="kz-head-neck" />
    <svg viewBox="0 0 240 280" className="kz-head-svg" role="img" aria-label="Holographic human AI head">
      <defs>
        <linearGradient id="kzSkin" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#a7f6ff"/><stop offset=".28" stopColor="#167ecb"/><stop offset=".62" stopColor="#061c46"/><stop offset="1" stopColor="#42dfff"/></linearGradient>
        <linearGradient id="kzFace" x1="0" y1="0" x2="0.9" y2="1"><stop offset="0" stopColor="#092b60"/><stop offset=".52" stopColor="#03112c"/><stop offset="1" stopColor="#0a5592"/></linearGradient>
        <filter id="kzGlow"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <g className="kz-head-model" filter="url(#kzGlow)">
        <path d="M72 63 Q72 24 120 21 Q168 24 168 63 L178 112 Q183 165 151 196 L145 229 L95 229 L89 196 Q57 165 62 112 Z" fill="url(#kzSkin)" stroke="#43eaff" strokeWidth="2.5"/>
        <path d="M78 69 Q83 35 120 35 Q157 35 162 69 L165 119 Q164 164 140 188 L136 217 L104 217 L100 188 Q76 164 75 119 Z" fill="url(#kzFace)" stroke="#138fdc" strokeWidth="1.5"/>
        <path d="M75 101 Q92 88 108 101 L104 115 Q90 108 78 117Z" fill="#00dfff" opacity=".85"/><path d="M132 101 Q148 88 165 101 L162 117 Q149 108 135 115Z" fill="#00dfff" opacity=".85"/>
        <path d="M81 104 Q94 96 105 104 M135 104 Q147 96 160 104" fill="none" stroke="#e6ffff" strokeWidth="3" strokeLinecap="round"/>
        <ellipse cx="94" cy="108" rx="7" ry="4" fill="#5effff"/><ellipse cx="147" cy="108" rx="7" ry="4" fill="#5effff"/>
        <path d="M120 111 L111 146 L122 151" fill="none" stroke="#2aa8eb" strokeWidth="3" strokeLinecap="round"/>
        <path d="M101 168 Q120 177 139 168 Q132 188 120 188 Q108 186 101 168Z" fill="#020b20" stroke="#25bff2" strokeWidth="2"/>
        <path d="M110 177 Q120 180 130 177" fill="none" stroke="#a6ffff" strokeWidth="2"/>
        <path d="M65 104 L51 115 L58 147 L72 152 M175 104 L189 115 L182 147 L168 152" fill="none" stroke="#4deaff" strokeWidth="3"/>
        <path d="M94 45 L103 59 L120 53 L137 59 L146 45" fill="none" stroke="#00efff" strokeWidth="2" opacity=".85"/>
        <path d="M95 202 L105 232 L135 232 L145 202 M102 215 L120 223 L138 215" fill="none" stroke="#00dfff" strokeWidth="2"/>
        <path d="M87 126 L96 131 M144 131 L153 126 M82 151 L92 157 M148 157 L158 151" stroke="#00cfff" strokeWidth="2" opacity=".8"/>
        <path d="M120 26 L120 48" stroke="#aaffff" strokeWidth="2"/><path d="M112 35 L120 26 L128 35" fill="none" stroke="#aaffff" strokeWidth="2"/>
      </g>
    </svg>
  </div>;
}

export default function VentureCoreDashboard() {
  const router = useRouter();
  const [mode, setMode] = useState<CoreMode>("idle");
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [active, setActive] = useState<string | null>(null);
  const [plugins, setPlugins] = useState<PluginData | null>(null);
  const [workflowStatus, setWorkflowStatus] = useState("Checking workflow status…");
  const [message, setMessage] = useState("");
  const [recent, setRecent] = useState<Array<{ title: string; detail: string; time: string }>>([]);
  const dragStart = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const providerCount = useMemo(() => Object.values(plugins?.providers || {}).filter(p => p.connected).length, [plugins]);
  useEffect(() => {
    let mounted = true;
    const refresh = async () => {
      try {
        const p = await fetch("/api/plugins", { credentials: "include", cache: "no-store" });
        if (p.ok) { const data = await p.json() as PluginData; if (mounted) setPlugins(data); }
      } catch { /* visible status remains unknown, not falsely connected */ }
      try {
        const status = await api.getAgentStatus() as Record<string, unknown>;
        if (mounted) setWorkflowStatus(String(status.status || status.state || (status.running ? "Worker running" : "No active worker reported")));
      } catch { if (mounted) setWorkflowStatus("Workflow status unavailable"); }
    };
    void refresh();
    const id = window.setInterval(refresh, 30000);
    const onActivity = (event: Event) => {
      const detail = (event as CustomEvent<{ state?: CoreMode; title?: string; detail?: string }>).detail;
      if (detail?.state) setMode(detail.state);
      if (detail?.title) setRecent(old => [{ title: detail.title!, detail: detail.detail || "Live app activity", time: "Just now" }, ...old].slice(0, 4));
    };
    window.addEventListener("kz-core-state", onActivity);
    return () => { mounted = false; window.clearInterval(id); window.removeEventListener("kz-core-state", onActivity); };
  }, []);
  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const value = message.trim();
    if (!value) { router.push("/chat"); return; }
    setMode("thinking");
    setRecent(old => [{ title: "Request submitted", detail: value.slice(0, 90), time: "Just now" }, ...old].slice(0, 4));
    window.dispatchEvent(new CustomEvent("kz-core-request", { detail: { message: value } }));
    sessionStorage.setItem("kz-dashboard-prompt", value);
    router.push("/chat");
  };
  const startDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    dragStart.current = { x: event.clientX, y: event.clientY, tx: tilt.x, ty: tilt.y };
    setDragging(true); event.currentTarget.setPointerCapture(event.pointerId);
  };
  const moveDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging || !dragStart.current) return;
    setTilt({ x: Math.max(-18, Math.min(18, dragStart.current.tx + (event.clientY - dragStart.current.y) * .35)), y: Math.max(-25, Math.min(25, dragStart.current.ty + (event.clientX - dragStart.current.x) * .35)) });
  };
  const endDrag = () => { setDragging(false); dragStart.current = null; };
  const connectionLabel = (provider: string) => plugins?.providers?.[provider]?.connected ? "LINK RECORD · VERIFY" : "NOT LINKED";
  return <div className="kz-venture min-h-0 h-full w-full overflow-auto">
    <header className="kz-venture-top"><Link href="/dashboard" className="kz-brand"><span className="kz-brand-mark">♛</span><span><b>KING ZARRY AI</b><small>YOUR AI · YOUR POWER</small></span></Link>
      <form className="kz-quick-search" onSubmit={submit}><span>⌕</span><input value={message} onChange={e => setMessage(e.target.value)} placeholder="Ask KZ anything…" aria-label="Ask King Zarry AI" /><button type="submit" aria-label="Send request">➤</button></form>
      <div className="kz-top-actions"><Link href="/alerts" aria-label="Alerts">♧</Link><Link href="/settings" aria-label="Settings">⚙</Link></div>
    </header>
    <div className="kz-venture-layout">
      <aside className="kz-venture-sidebar"><div className="kz-side-links">{[{label:"Home",href:"/dashboard",icon:"⌂"},{label:"Chat",href:"/chat",icon:"◉"},{label:"Workflow",href:"/agent",icon:"⌘"},{label:"Plugins",href:"/plugins",icon:"✣"},{label:"Accounts",href:"/settings",icon:"↗"},{label:"Revenue",href:"/agent",icon:"↗"},{label:"Memory",href:"/history",icon:"❋"},{label:"Settings",href:"/settings",icon:"⚙"}].map(item=><Link key={item.label} href={item.href} className={active===item.label.toLowerCase()?"active":""}><span>{item.icon}</span>{item.label}</Link>)}</div><div className="kz-side-status"><i/> AI CORE <small>ONLINE · API STATUS NOT ASSUMED</small></div></aside>
      <main className="kz-venture-main">
        <section className="kz-orbit-stage">
          <div className="kz-orbit orbit-a"/><div className="kz-orbit orbit-b"/><div className="kz-orbit orbit-c"/><div className="kz-orbit orbit-d"/>
          <svg className="kz-orbit-links" viewBox="0 0 1000 720" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="kzFlow"><stop stopColor="#00dfff" stopOpacity="0"/><stop offset=".5" stopColor="#00eaff"/><stop offset="1" stopColor="#9d68ff" stopOpacity="0"/></linearGradient></defs><ellipse cx="500" cy="355" rx="330" ry="245" fill="none" stroke="url(#kzFlow)" strokeWidth="1.5" strokeDasharray="7 11" className="kz-flow-line"/><ellipse cx="500" cy="355" rx="260" ry="195" fill="none" stroke="#1269d8" strokeOpacity=".5" strokeWidth="1"/></svg>
          <div className="kz-core-anchor" onPointerDown={startDrag} onPointerMove={moveDrag} onPointerUp={endDrag} onPointerCancel={endDrag} style={{ cursor: dragging ? "grabbing" : "grab" }}>
            <div className="kz-core-aura"/><HumanHead mode={mode} tilt={tilt}/><div className="kz-core-title"><b>VETURE CORE</b><span>KING ZARRY AI</span><small>{mode==="idle"?"THINKING · PLANNING · READY":mode==="error"?"ATTENTION REQUIRED":mode.toUpperCase()+" · KZ ACTIVE"}</small></div>
          </div>
          {modules.map((item,index) => {
            const rad=item.angle*Math.PI/180; const x=50+Math.cos(rad)*37; const y=50+Math.sin(rad)*35;
            const status=item.id==="plugins" ? (plugins ? providerCount+" providers linked" : "Checking providers…") : item.id==="workflow" ? workflowStatus : item.id==="accounts" ? (plugins ? providerCount+" link records" : "Status unknown") : "Open module";
            return <Link key={item.id} href={item.href} onClick={()=>{setActive(item.id);setMode("executing");}} className={"kz-orbit-card "+(active===item.id?"is-active":"")} style={{left:x+"%",top:y+"%",["--module-color" as string]:item.color,animationDelay:(index*-.72)+"s"}}><span className="kz-module-icon">{item.icon}</span><span className="kz-module-copy"><b>{item.title}</b><small>{item.subtitle}</small><em>{status.length>30?status.slice(0,28)+"…":status}</em></span><span className="kz-module-arrow">›</span></Link>;
          })}
        </section>
        <aside className="kz-venture-right"><section className="kz-info-card"><div className="kz-card-heading">KZ STATUS <span><i/> Live UI</span></div><div className="kz-info-row"><span>◉</span><label>Linked providers</label><b>{plugins?providerCount:"—"}</b></div><div className="kz-info-row"><span>✣</span><label>Registered tools</label><b>{plugins?.tools?.length ?? "—"}</b></div><div className="kz-info-row"><span>⌘</span><label>Workflow status</label><b className="kz-status-value">{workflowStatus.length>18?workflowStatus.slice(0,16)+"…":workflowStatus}</b></div><div className="kz-info-row"><span>↗</span><label>Provider auth</label><b>Not verified</b></div></section><section className="kz-info-card"><div className="kz-card-heading">RECENT ACTIVITY <Link href="/history">View all</Link></div>{recent.length?recent.map((item,i)=><div className="kz-activity" key={i}><i/><span><b>{item.title}</b><small>{item.detail}</small><em>{item.time}</em></span></div>):<p className="kz-empty-activity">Activity appears here as this dashboard receives live events.</p>}</section><section className="kz-info-card kz-provider-card"><div className="kz-card-heading">CONNECTORS</div>{["google","github","shopify"].map(p=><div className="kz-provider-row" key={p}><span>{p==="google"?"G":p==="github"?"⌘":"S"}</span><label>{p==="google"?"Google Workspace":p==="github"?"GitHub":"Shopify"}</label><small>{plugins?connectionLabel(p):"Checking…"}</small></div>)}<Link href="/settings" className="kz-manage-link">Manage accounts ↗</Link></section></aside>
        <form className="kz-bottom-prompt" onSubmit={submit}><span>✧</span><input value={message} onChange={e=>setMessage(e.target.value)} onFocus={()=>setMode("listening")} placeholder="Ask KZ to do something…" aria-label="Ask KZ to do something"/><button type="submit">➤</button><Link href="/chat">Open full chat ↗</Link></form>
      </main>
    </div>
  </div>;
}
