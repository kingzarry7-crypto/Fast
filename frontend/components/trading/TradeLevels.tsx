"use client";

import React from "react";

export type TradeDirection = "BUY" | "SELL" | "LONG" | "SHORT" | "BULLISH" | "BEARISH" | string;

export interface TradeLevelsProps {
  symbol?: string;
  asset?: string;
  pair?: string;
  market?: string;
  name?: string;
  timeframe?: string;
  interval?: string;
  tf?: string;
  entry?: string | number | null;
  entryPrice?: string | number | null;
  entryZone?: string | null;
  stopLoss?: string | number | null;
  sl?: string | number | null;
  takeProfit1?: string | number | null;
  tp1?: string | number | null;
  takeProfit2?: string | number | null;
  tp2?: string | number | null;
  takeProfit3?: string | number | null;
  tp3?: string | number | null;
  tps?: Array<string | number | null> | null;
  takeProfit?: string | number | null;
  direction?: TradeDirection | null;
  side?: TradeDirection | null;
  signal?: TradeDirection | null;
  bias?: TradeDirection | null;
  type?: TradeDirection | null;
  riskReward?: string | number | null;
  rr?: string | number | null;
  risk?: string | number | null;
  reward?: string | number | null;
  isLoading?: boolean;
  loading?: boolean;
  error?: string | null;
  errorMessage?: string | null;
  onClick?: () => void;
  onSelect?: () => void;
  selected?: boolean;
  active?: boolean;
  disabled?: boolean;
  data?: Record<string, any>;
  className?: string;
}

function safe(v: any): string | null {
  if (v === null || v === undefined || v === "") return null;
  if (typeof v === "object") {
    const cand = (v as any).value?? (v as any).price?? (v as any).level?? (v as any).close;
    if (cand!== undefined && cand!== null && cand!== "") return String(cand);
    return null;
  }
  return String(v);
}

function normalizeDir(d?: string | null) {
  if (!d) return null;
  const s = String(d).toUpperCase().trim();
  const longKeys = ["BUY", "LONG", "BULLISH", "BULL"];
  const shortKeys = ["SELL", "SHORT", "BEARISH", "BEAR"];
  const isLong = longKeys.some((k) => s.includes(k));
  const isShort = shortKeys.some((k) => s.includes(k));
  return { raw: s, label: s, isLong, isShort, isNeutral:!isLong &&!isShort };
}

function LevelRow({ label, sub, value, tone, glow }: { label: string; sub: string; value: string; tone: "entry" | "sl" | "tp"; glow?: boolean }) {
  const toneStyles = tone === "entry"? "border-cyan-300/20 bg-gradient-to-b from-cyan-400/[0.10] to-cyan-400/[0.03] shadow-[0_0_20px_rgba(34,211,238,0.12)]" : tone === "sl"? "border-rose-300/20 bg-gradient-to-b from-rose-400/[0.09] to-rose-400/[0.02] shadow-[0_0_18px_rgba(251,113,133,0.10)]" : "border-emerald-300/15 bg-gradient-to-b from-white/[0.05] to-white/[0.01]";
  return (
    <div className={`relative rounded-[14px] border p-4 flex items-center justify-between overflow-hidden ${toneStyles}`}>
      <div className="flex items-center gap-3">
        <div className={`w-8 h-8 rounded-[10px] border flex items-center justify-center ${tone === "entry"? "bg-cyan-400/[0.08] border-cyan-300/20" : tone === "sl"? "bg-rose-400/[0.07] border-rose-300/20" : "bg-white/[0.04] border-white/10"}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${tone === "entry"? "bg-cyan-300 shadow-[0_0_8px_rgba(34,211,238,0.6)]" : tone === "sl"? "bg-rose-300 shadow-[0_0_8px_rgba(251,113,133,0.5)]" : "bg-emerald-300/70"}`} aria-hidden="true" />
        </div>
        <div>
          <div className="text-[10px] tracking-[0.12em] font-medium text-white/35">{sub}</div>
          <div className="mt-0.5 text-[11px] font-semibold text-white/80">{label}</div>
        </div>
      </div>
      <div className={`text-[14px] font-[600] tracking-[-0.01em] ${tone === "entry"? "text-cyan-100" : tone === "sl"? "text-rose-100/90" : "text-white"}`}>{value}</div>
      <span aria-hidden="true" className="pointer-events-none absolute left-0 top-1/2 -translate-y-1/2 w-px h-8 bg-gradient-to-b from-transparent via-white/10 to-transparent" />
    </div>
  );
}

function ExecutionMap({ entry, sl, tps, dir }: { entry: string | null; sl: string | null; tps: string[]; dir: ReturnType<typeof normalizeDir> }) {
  if (!entry &&!sl && tps.length === 0) return null;
  const isShort = dir?.isShort?? false;
  const ordered = isShort? [...tps.map((v,i)=>({type:"tp" as const,label:`TP${i+1}`,val:v})), entry?{type:"entry" as const,label:"ENTRY",val:entry}:null, sl?{type:"sl" as const,label:"STOP LOSS",val:sl}:null].filter(Boolean) : [sl?{type:"sl" as const,label:"STOP LOSS",val:sl}:null, entry?{type:"entry" as const,label:"ENTRY",val:entry}:null,...tps.map((v,i)=>({type:"tp" as const,label:`TP${i+1}`,val:v}))].filter(Boolean);
  const visual = isShort? ordered : [...ordered].reverse();
  return (
    <div className="relative rounded-[14px] border border-white/[0.06] bg-[#0C111A] p-4 overflow-hidden">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,#ffffff05_1px,transparent_1px)] bg-[size:100%_24px] opacity-30" />
      <div className="text-[9px] tracking-[0.14em] text-white/25">EXECUTION MAP {isShort? "• SHORT" : "• LONG"} • ILLUSTRATIVE ORDER</div>
      <div className="mt-4 relative pl-6">
        <span aria-hidden="true" className="absolute left-[7px] top-1 bottom-1 w-px bg-gradient-to-b from-cyan-300/20 via-white/10 to-rose-300/20" />
        <div className="space-y-3">
          {visual.map((item:any,idx:number)=>(
            <div key={idx} className="relative flex items-center gap-3">
              <span aria-hidden="true" className={`absolute -left-6 w-3 h-3 rounded-full border flex items-center justify-center ${item.type==="entry"?"bg-cyan-400/10 border-cyan-300/30":item.type==="sl"?"bg-rose-400/10 border-rose-300/30":"bg-white/[0.06] border-white/10"}`}>
                <span className={`w-1 h-1 rounded-full ${item.type==="entry"?"bg-cyan-300":item.type==="sl"?"bg-rose-300":"bg-white/50"}`} />
              </span>
              <div className={`flex-1 rounded-[10px] border px-3 py-2 flex items-center justify-between ${item.type==="entry"?"border-cyan-300/20 bg-cyan-400/[0.06]":item.type==="sl"?"border-rose-300/15 bg-rose-400/[0.05]":"border-white/[0.06] bg-white/[0.02]"}`}>
                <span className="text-[10px] tracking-[0.08em] text-white/40">{item.label}</span>
                <span className="text-[12px] font-medium text-white/80">{item.val}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function TradeLevels(props: TradeLevelsProps) {
  const symbol = props.symbol?? props.asset?? props.pair?? (props.data as any)?.symbol?? null;
  const timeframe = props.timeframe?? props.interval?? props.tf?? (props.data as any)?.timeframe?? null;
  const dirRaw = props.direction?? props.side?? props.signal?? props.bias?? props.type?? (props.data as any)?.direction?? null;
  const dir = normalizeDir(dirRaw? String(dirRaw) : null);
  const entry = safe(props.entry?? props.entryPrice?? props.entryZone?? (props.data as any)?.entry);
  const sl = safe(props.stopLoss?? props.sl?? (props.data as any)?.stopLoss);
  const tp1 = safe(props.takeProfit1?? props.tp1?? (props.data as any)?.tp1);
  const tp2 = safe(props.takeProfit2?? props.tp2?? (props.data as any)?.tp2);
  const tp3 = safe(props.takeProfit3?? props.tp3?? (props.data as any)?.tp3);
  const singleTP = safe(props.takeProfit?? (props.data as any)?.takeProfit);
  const extraTps = (props.tps?? (props.data as any)?.tps?? []) as Array<any>;
  const extraFormatted = extraTps.map(safe).filter(Boolean) as string[];
  const tpList: string[] = [];
  if (tp1) tpList.push(tp1); if (tp2) tpList.push(tp2); if (tp3) tpList.push(tp3);
  if (tpList.length===0 && singleTP) tpList.push(singleTP);
  if (tpList.length===0 && extraFormatted.length) tpList.push(...extraFormatted.slice(0,3));
  const rr = safe(props.riskReward?? props.rr?? props.risk?? (props.data as any)?.rr);
  const loading = props.isLoading?? props.loading?? false;
  const error = props.error?? props.errorMessage?? null;
  const isInteractive =!!(props.onClick || props.onSelect);
  const hasAny =!!(entry || sl || tpList.length>0);

  if (loading) {
    return (<section className={`kz-panel relative rounded-[24px] border border-white/[0.07] bg-[#0A0E16] overflow-hidden ${props.className||""}`} aria-busy="true"><div className="relative p-6"><div className="h-3 w-28 rounded-full bg-white/[0.06] animate-pulse" /><div className="mt-6 space-y-3">{[0,1,2,3,4].map((i)=><div key={i} className="h-[58px] rounded-[14px] bg-white/[0.04] border border-white/[0.04] animate-pulse" />)}</div></div></section>);
  }
  if (error) {
    return (<section className={`relative rounded-[24px] border border-rose-400/20 bg-[#0E0A0D] p-6 ${props.className||""}`} role="alert"><div className="text-[10px] tracking-[0.14em] text-rose-300/60">EXECUTION LEVELS UNAVAILABLE</div><div className="mt-2 text-[13px] text-white/70">{error}</div></section>);
  }
  if (!hasAny) {
    return (<section className={`relative rounded-[24px] border border-white/[0.06] bg-[#0A0E16] p-6 ${props.className||""}`}><div className="flex items-center gap-2"><span aria-hidden="true" className="w-2 h-2 rounded-full bg-white/20" /><span className="text-[10px] tracking-[0.14em] text-white/30">TRADE LEVELS • PENDING</span></div><div className="mt-3 text-[14px] font-medium text-white/60">Trade levels unavailable</div><div className="mt-1 text-[12px] leading-[1.5] text-white/35">Parent must supply entry, stop loss and take profit levels. No fabricated values are shown.</div></section>);
  }

  return (
    <section onClick={props.onClick?? props.onSelect} className={`kz-panel kz-glass group relative rounded-[24px] md:rounded-[28px] border border-white/[0.08] bg-gradient-to-b from-[#0F1728] to-[#080B14] overflow-hidden shadow-[0_20px_64px_rgba(0,0,0,0.6),inset_0_1px_0_rgba(255,255,255,0.07)] ${isInteractive? "cursor-pointer hover:border-white/[0.12] hover:-translate-y-[0.5px] transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/30" : ""} ${props.active||props.selected? "ring-1 ring-cyan-300/30 border-cyan-300/20" : ""} ${props.disabled? "opacity-60 pointer-events-none" : ""} ${props.className||""}`} role={isInteractive? "button" : undefined} tabIndex={isInteractive? 0 : undefined} aria-label={symbol? `Trade levels ${symbol}` : "Trade execution levels"}>
      <div aria-hidden="true" className="pointer-events-none absolute inset-0"><div className="absolute inset-0 bg-[radial-gradient(700px_300px_at_15%_0%,rgba(56,189,248,0.11),transparent),radial-gradient(500px_260px_at_85%_10%,rgba(139,92,246,0.10),transparent)]" /><div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-300/25 to-transparent" /></div>
      <span aria-hidden="true" className="pointer-events-none absolute left-3 top-3 w-5 h-5 border-l border-t border-cyan-300/20 rounded-tl-[18px]" /><span aria-hidden="true" className="pointer-events-none absolute right-3 top-3 w-5 h-5 border-r border-t border-cyan-300/20 rounded-tr-[18px]" /><span aria-hidden="true" className="pointer-events-none absolute left-3 bottom-3 w-5 h-5 border-l border-b border-white/10 rounded-bl-[18px]" /><span aria-hidden="true" className="pointer-events-none absolute right-3 bottom-3 w-5 h-5 border-r border-b border-white/10 rounded-br-[18px]" />
      <div className="relative">
        <div className="flex items-center justify-between px-6 h-[56px] border-b border-white/[0.06]">
          <div className="flex items-center gap-3"><div className="w-7 h-7 rounded-[9px] bg-white/[0.06] border border-white/10 flex items-center justify-center"><span className="w-1.5 h-1.5 rounded-full bg-cyan-300 shadow-[0_0_8px_rgba(34,211,238,0.6)] animate-pulse" aria-hidden="true" /></div><div><div className="text-[11px] tracking-[0.14em] font-medium text-white/50">TRADE EXECUTION LEVELS</div><div className="text-[10px] text-white/25">KING ZARRY AI • EXECUTION CONSOLE</div></div></div>
          <div className="flex items-center gap-2">{symbol && <span className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] font-medium tracking-wide text-white/70">{symbol}</span>}{timeframe && <span className="rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[10px] tracking-[0.08em] text-white/40">{timeframe}</span>}{dir && <span className={`rounded-full border px-2.5 py-1 text-[10px] tracking-[0.08em] font-medium ${dir.isLong? "border-cyan-300/20 bg-cyan-400/[0.08] text-cyan-200/80" : dir.isShort? "border-rose-300/20 bg-rose-400/[0.08] text-rose-200/75" : "border-white/10 bg-white/[0.04] text-white/50"}`}>{dir.label}</span>}</div>
        </div>
        <div className="p-5 md:p-6">
          <div className="grid lg:grid-cols-[1.15fr_0.85fr] gap-5">
            <div className="space-y-3">
              {entry && <LevelRow label="ENTRY" sub="EXECUTION PRICE" value={entry} tone="entry" glow />}
              {sl && <LevelRow label="STOP LOSS" sub="RISK BOUNDARY" value={sl} tone="sl" />}
              {tpList[0] && <LevelRow label="TAKE PROFIT 1" sub="TARGET • TP1" value={tpList[0]} tone="tp" />}
              {tpList[1] && <LevelRow label="TAKE PROFIT 2" sub="TARGET • TP2" value={tpList[1]} tone="tp" />}
              {tpList[2] && <LevelRow label="TAKE PROFIT 3" sub="TARGET • TP3" value={tpList[2]} tone="tp" />}
              {rr && <div className="mt-4 rounded-[12px] border border-white/[0.06] bg-[#0E131D] px-4 py-3 flex items-center justify-between"><span className="text-[10px] tracking-[0.12em] text-white/30">RISK / REWARD</span><span className="text-[12px] font-medium text-white/70">{rr}</span></div>}
              <div className="pt-2 text-[10px] text-white/25 leading-[1.4]">Levels supplied by parent • No calculation unless explicitly provided • Not financial advice</div>
            </div>
            <div className="space-y-4">
              <ExecutionMap entry={entry} sl={sl} tps={tpList} dir={dir} />
              <div className="rounded-[12px] border border-white/[0.06] bg-white/[0.02] p-4"><div className="text-[9px] tracking-[0.12em] text-white/30">DIRECTION LOGIC</div><div className="mt-2 text-[11.5px] leading-[1.5] text-white/50">{dir?.isLong? "Long orientation: Stop below entry, targets above. Map shows SL → Entry → TP1 → TP2 → TP3." : dir?.isShort? "Short orientation: Stop above entry, targets below. Map shows TPs → Entry → SL." : "Neutral orientation: Levels displayed as supplied. Provide direction to adapt visual ordering."}</div></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
