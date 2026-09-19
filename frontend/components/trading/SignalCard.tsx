"use client";

import React from "react";

export type SignalDirection = "BUY" | "SELL" | "LONG" | "SHORT" | "BULLISH" | "BEARISH" | string;
export type SignalStatus = "active" | "pending" | "closed" | "invalid" | "waiting" | string;

export interface SignalCardProps {
  id?: string;
  signalId?: string;
  symbol?: string;
  asset?: string;
  pair?: string;
  market?: string;
  marketType?: string;
  category?: string;
  name?: string;
  direction?: SignalDirection;
  side?: SignalDirection;
  type?: SignalDirection;
  bias?: SignalDirection;
  action?: SignalDirection;
  timeframe?: string;
  interval?: string;
  tf?: string;
  entry?: string | number | null;
  entryPrice?: string | number | null;
  entryZone?: string | null;
  stopLoss?: string | number | null;
  sl?: string | number | null;
  takeProfit?: string | number | null;
  takeProfit1?: string | number | null;
  tp1?: string | number | null;
  takeProfit2?: string | number | null;
  tp2?: string | number | null;
  takeProfit3?: string | number | null;
  tp3?: string | number | null;
  tps?: Array<string | number | null> | null;
  confidence?: string | number | null;
  confidenceScore?: string | number | null;
  riskReward?: string | number | null;
  rr?: string | number | null;
  risk?: string | null;
  reward?: string | null;
  status?: SignalStatus | null;
  marketStructure?: string | null;
  structure?: string | null;
  rsi?: string | number | null;
  ema?: string | number | null;
  atr?: string | number | null;
  multiTimeframe?: Record<string, string> | null;
  mtf?: Record<string, string> | null;
  timeframes?: Record<string, string> | null;
  reasoning?: string | null;
  analysis?: string | null;
  aiRead?: string | null;
  aiReasoning?: string | null;
  aiInterpretation?: string | null;
  summary?: string | null;
  timestamp?: string | null;
  createdAt?: string | null;
  time?: string | null;
  source?: string | null;
  exchange?: string | null;
  loading?: boolean;
  isLoading?: boolean;
  error?: string | null;
  errorMessage?: string | null;
  onClick?: () => void;
  onSelect?: () => void;
  href?: string;
  to?: string;
  link?: string;
  selected?: boolean;
  active?: boolean;
  disabled?: boolean;
  data?: Record<string, any>;
  className?: string;
}

function safeVal(v: any): string | null {
  if (v === null || v === undefined || v === "") return null;
  if (typeof v === "object") {
    const cand = (v as any).value?? (v as any).price?? (v as any).level;
    if (cand!== undefined && cand!== null && cand!== "") return String(cand);
    return null;
  }
  return String(v);
}

function formatLevel(v: any): string | null {
  return safeVal(v);
}

function normalizeDir(dir?: string | null): { label: string; isLong: boolean; isShort: boolean; isNeutral: boolean } | null {
  if (!dir) return null;
  const d = String(dir).toUpperCase().trim();
  const longKeys = ["BUY", "LONG", "BULLISH", "BULL"];
  const shortKeys = ["SELL", "SHORT", "BEARISH", "BEAR"];
  const isLong = longKeys.some((k) => d.includes(k));
  const isShort = shortKeys.some((k) => d.includes(k));
  return { label: d, isLong, isShort, isNeutral:!isLong &&!isShort };
}

export default function SignalCard(props: SignalCardProps) {
  const symbol = props.symbol?? props.asset?? props.pair?? (props.data as any)?.symbol?? null;
  const market = props.market?? props.marketType?? props.category?? (props.data as any)?.market?? null;
  const directionRaw = props.direction?? props.side?? props.type?? props.bias?? props.action?? (props.data as any)?.direction?? null;
  const dirInfo = normalizeDir(directionRaw? String(directionRaw) : null);
  const timeframe = props.timeframe?? props.interval?? props.tf?? (props.data as any)?.timeframe?? null;

  const entry = formatLevel(props.entry?? props.entryPrice?? props.entryZone?? (props.data as any)?.entry);
  const sl = formatLevel(props.stopLoss?? props.sl?? (props.data as any)?.stopLoss);
  const tp1 = formatLevel(props.takeProfit1?? props.tp1?? props.takeProfit?? (props.data as any)?.tp1);
  const tp2 = formatLevel(props.takeProfit2?? props.tp2?? (props.data as any)?.tp2);
  const tp3 = formatLevel(props.takeProfit3?? props.tp3?? (props.data as any)?.tp3);
  const tpsExtra = props.tps?.map(formatLevel).filter(Boolean) as string[] | null;

  const hasTPs =!!(tp1 || tp2 || tp3 || (tpsExtra && tpsExtra.length));
  const confidence = safeVal(props.confidence?? props.confidenceScore?? (props.data as any)?.confidence);
  const rr = safeVal(props.riskReward?? props.rr?? props.risk?? (props.data as any)?.rr);
  const status = safeVal(props.status?? (props.data as any)?.status);
  const marketStructure = safeVal(props.marketStructure?? props.structure?? (props.data as any)?.marketStructure);
  const rsi = safeVal(props.rsi?? (props.data as any)?.rsi);
  const ema = safeVal(props.ema?? (props.data as any)?.ema);
  const atr = safeVal(props.atr?? (props.data as any)?.atr);
  const reasoning = props.reasoning?? props.aiReasoning?? props.aiRead?? props.aiInterpretation?? props.analysis?? props.summary?? (props.data as any)?.reasoning?? null;
  const timestamp = props.timestamp?? props.createdAt?? props.time?? (props.data as any)?.timestamp?? null;
  const source = props.source?? props.exchange?? (props.data as any)?.source?? null;
  const id = props.id?? props.signalId?? (props.data as any)?.id?? null;
  const loading = props.loading?? props.isLoading?? false;
  const error = props.error?? props.errorMessage?? null;
  const isInteractive =!!(props.onClick || props.onSelect || props.href || props.to || props.link);
  const Tag: any = props.href || props.to || props.link? "a" : "div";
  const tagProps: any = props.href || props.to || props.link? { href: props.href?? props.to?? props.link } : {};
  const mtf = props.multiTimeframe?? props.mtf?? props.timeframes?? (props.data as any)?.mtf?? null;

  if (loading) {
    return (
      <div className={`kz-panel relative rounded-[24px] border border-white/[0.07] bg-[#0A0E16] overflow-hidden ${props.className || ""}`} aria-busy="true">
        <div aria-hidden="true" className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff06_1px,transparent_1px),linear-gradient(to_bottom,#ffffff06_1px,transparent_1px)] bg-[size:32px_32px] opacity-30" />
        <div className="relative p-6">
          <div className="h-3 w-24 rounded-full bg-white/[0.06] animate-pulse" />
          <div className="mt-5 h-8 w-32 rounded bg-white/[0.08] animate-pulse" />
          <div className="mt-6 grid grid-cols-3 gap-2">{[0,1,2].map((i)=><div key={i} className="h-[64px] rounded-[12px] bg-white/[0.04] animate-pulse" />)}</div>
          <div className="mt-6 h-20 rounded-[12px] bg-white/[0.03] animate-pulse" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`relative rounded-[24px] border border-rose-400/20 bg-[#0E0A0D] p-6 ${props.className || ""}`} role="alert">
        <div className="text-[10px] tracking-[0.14em] text-rose-300/60">SIGNAL CORE ERROR</div>
        <div className="mt-2 text-[13px] text-white/70">{error}</div>
      </div>
    );
  }

  const hasAnySignal =!!(symbol || directionRaw || entry || sl || hasTPs || reasoning);
  if (!hasAnySignal) {
    return (
      <div className={`relative rounded-[24px] border border-white/[0.06] bg-[#0A0E16] p-6 ${props.className || ""}`}>
        <div className="flex items-center gap-2"><span aria-hidden="true" className="w-2 h-2 rounded-full bg-white/20" /><span className="text-[10px] tracking-[0.14em] text-white/30">SIGNAL CORE • IDLE</span></div>
        <div className="mt-3 text-[14px] font-medium text-white/60">No signal</div>
        <div className="mt-1 text-[12px] leading-[1.5] text-white/35">Awaiting intelligence from parent. No fabricated signal will be shown.</div>
      </div>
    );
  }

  const content = (
    <>
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(600px_280px_at_15%_0%,rgba(56,189,248,0.12),transparent),radial-gradient(500px_240px_at_85%_5%,rgba(139,92,246,0.11),transparent)]" />
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-300/25 to-transparent" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff05_1px,transparent_1px),linear-gradient(to_bottom,#ffffff05_1px,transparent_1px)] bg-[size:36px_36px] [mask-image:radial-gradient(ellipse_at_center,#000_60%,transparent_92%)] opacity-35" />
      </div>
      <span aria-hidden="true" className="pointer-events-none absolute left-3 top-3 w-5 h-5 border-l border-t border-cyan-300/20 rounded-tl-[18px]" />
      <span aria-hidden="true" className="pointer-events-none absolute right-3 top-3 w-5 h-5 border-r border-t border-cyan-300/20 rounded-tr-[18px]" />
      <span aria-hidden="true" className="pointer-events-none absolute left-3 bottom-3 w-5 h-5 border-l border-b border-white/10 rounded-bl-[18px]" />
      <span aria-hidden="true" className="pointer-events-none absolute right-3 bottom-3 w-5 h-5 border-r border-b border-white/10 rounded-br-[18px]" />

      <div className="relative">
        <div className="flex items-center justify-between px-6 h-[52px] border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-[9px] bg-white/[0.06] border border-white/10 flex items-center justify-center"><span className="w-1.5 h-1.5 rounded-full bg-cyan-300 shadow-[0_0_8px_rgba(34,211,238,0.6)] animate-pulse" aria-hidden="true" /></div>
            <div className="text-[10px] tracking-[0.14em] font-medium text-white/40">SIGNAL CORE {id? <span className="text-white/20">• {String(id).slice(0,12)}</span> : null}</div>
          </div>
          <div className="flex items-center gap-2">
            {timeframe && <span className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] tracking-[0.08em] text-white/45">{timeframe}</span>}
            {status && <span className="rounded-full border border-cyan-300/15 bg-cyan-400/[0.06] px-2.5 py-1 text-[10px] tracking-[0.08em] text-cyan-200/60">{String(status).toUpperCase()}</span>}
          </div>
        </div>

        <div className="p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-[11px] bg-gradient-to-b from-white/[0.08] to-white/[0.02] border border-white/10 flex items-center justify-center"><span className="text-[12px] font-semibold text-white/80">{symbol? String(symbol).charAt(0).toUpperCase() : "—"}</span></div>
                <div><div className="text-[14px] font-semibold truncate">{symbol?? "—"}</div><div className="text-[11px] text-white/35 truncate">{market?? "Market intelligence"} {source? `• ${source}` : ""}</div></div>
              </div>
            </div>
            {confidence && <div className="shrink-0 rounded-[12px] border border-white/[0.06] bg-[#0E131D] px-3 py-2 text-right"><div className="text-[9px] tracking-[0.12em] text-white/30">CONFIDENCE</div><div className="mt-0.5 text-[12px] font-medium text-white/80">{confidence}</div></div>}
          </div>

          {dirInfo && (
            <div className="mt-6">
              <div className={`relative inline-flex items-center gap-3 rounded-[14px] border px-5 py-3 ${dirInfo.isLong? "border-cyan-300/20 bg-gradient-to-b from-cyan-400/[0.10] to-cyan-400/[0.03] shadow-[0_0_24px_rgba(34,211,238,0.15)]" : dirInfo.isShort? "border-rose-300/20 bg-gradient-to-b from-rose-400/[0.10] to-rose-400/[0.03] shadow-[0_0_24px_rgba(251,113,133,0.12)]" : "border-white/10 bg-white/[0.03]"}`}>
                <span aria-hidden="true" className={`w-2 h-2 rounded-full ${dirInfo.isLong? "bg-cyan-300 shadow-[0_0_8px_rgba(34,211,238,0.7)]" : dirInfo.isShort? "bg-rose-300 shadow-[0_0_8px_rgba(251,113,133,0.6)]" : "bg-white/40"}`} />
                <span className={`text-[22px] font-[700] tracking-[-0.03em] leading-none ${dirInfo.isLong? "text-cyan-100" : dirInfo.isShort? "text-rose-100" : "text-white"}`}>{dirInfo.label}</span>
                <span aria-hidden="true" className="ml-1 text-[14px] text-white/20">{dirInfo.isLong? "↗" : dirInfo.isShort? "↘" : "—"}</span>
              </div>
              {rr && <div className="mt-2 text-[11px] text-white/35">R/R {rr}</div>}
            </div>
          )}

          {(entry || sl || hasTPs) && (
            <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {entry && <div className="rounded-[12px] border border-white/[0.06] bg-[#0C111A] p-3"><div className="text-[9px] tracking-[0.12em] text-white/30">ENTRY</div><div className="mt-1.5 text-[13px] font-medium text-white">{entry}</div></div>}
              {sl && <div className="rounded-[12px] border border-rose-300/15 bg-[#121016] p-3"><div className="text-[9px] tracking-[0.12em] text-rose-200/40">STOP LOSS</div><div className="mt-1.5 text-[13px] font-medium text-rose-100/80">{sl}</div></div>}
              {hasTPs && <div className="rounded-[12px] border border-cyan-300/15 bg-[#0A141D] p-3"><div className="text-[9px] tracking-[0.12em] text-cyan-200/40">TAKE PROFIT</div><div className="mt-1.5 space-y-1 text-[12px] font-medium text-cyan-100/80">{tp1 && <div>TP1 {tp1}</div>}{tp2 && <div>TP2 {tp2}</div>}{tp3 && <div>TP3 {tp3}</div>}{tpsExtra?.map((t,i)=><div key={i}>TP{i+4} {t}</div>)}</div></div>}
            </div>
          )}

          {(marketStructure || rsi || ema || atr) && (
            <div className="mt-5 rounded-[12px] border border-white/[0.06] bg-white/[0.01] p-3.5">
              <div className="text-[9px] tracking-[0.12em] text-white/30">TECHNICAL INTELLIGENCE</div>
              <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
                {marketStructure && <div><div className="text-white/30">Structure</div><div className="mt-1 text-white/70">{marketStructure}</div></div>}
                {rsi && <div><div className="text-white/30">RSI</div><div className="mt-1 text-white/70">{rsi}</div></div>}
                {ema && <div><div className="text-white/30">EMA</div><div className="mt-1 text-white/70">{ema}</div></div>}
                {atr && <div><div className="text-white/30">ATR</div><div className="mt-1 text-white/70">{atr}</div></div>}
              </div>
            </div>
          )}

          {mtf && Object.keys(mtf).length>0 && (
            <div className="mt-4 flex flex-wrap gap-2">{Object.entries(mtf).slice(0,6).map(([tf,dir])=><span key={tf} className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[10px] tracking-[0.06em] text-white/50"><span className="text-white/25">{tf.toUpperCase()}</span><span className="text-white/70">{String(dir).toUpperCase()}</span></span>)}</div>
          )}

          {reasoning && (
            <div className="mt-5 rounded-[14px] border border-cyan-300/12 bg-gradient-to-b from-cyan-400/[0.06] to-white/[0.01] p-[1px]">
              <div className="rounded-[13px] bg-[#0A131D]/90 backdrop-blur p-4">
                <div className="flex items-center justify-between"><div className="text-[10px] tracking-[0.12em] font-medium text-cyan-200/60">AI SIGNAL REASONING</div><div className="text-[10px] text-white/20">KING ZARRY AI • CORE</div></div>
                <p className="mt-2.5 text-[12.5px] leading-[1.6] text-white/70 whitespace-pre-wrap">{reasoning}</p>
              </div>
            </div>
          )}

          <div className="mt-5 flex items-center justify-between text-[10px] text-white/25">
            <span className="truncate">{timestamp?? ""}</span>
            <span className="flex items-center gap-1.5 shrink-0 ml-3"><span aria-hidden="true" className="w-1 h-1 rounded-full bg-white/20" />KZ • SIGNAL • {symbol?? "—"} {timeframe? `• ${timeframe}` : ""}</span>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <Tag {...tagProps} onClick={props.onClick?? props.onSelect} className={`kz-card kz-glass group relative rounded-[24px] border border-white/[0.08] bg-gradient-to-b from-[#0F1728] to-[#080B14] overflow-hidden shadow-[0_16px_48px_rgba(0,0,0,0.55),inset_0_1px_0_rgba(255,255,255,0.07)] transition-all hover:border-white/[0.13] hover:shadow-[0_20px_64px_rgba(0,0,0,0.65),0_0_0_1px_rgba(255,255,255,0.06)] ${isInteractive? "cursor-pointer hover:-translate-y-[0.5px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/30" : ""} ${props.active || props.selected? "ring-1 ring-cyan-300/30 border-cyan-300/25" : ""} ${props.disabled? "opacity-60 pointer-events-none" : ""} ${props.className || ""}`} role={isInteractive? "button" : undefined} tabIndex={isInteractive? 0 : undefined} aria-label={symbol? `Signal ${symbol} ${directionRaw?? ""}` : "Trading signal"} onKeyDown={(e:any)=>{if(isInteractive && (e.key==="Enter"||e.key===" ")){e.preventDefault();(props.onClick??props.onSelect)?.();}}}>
      {content}
    </Tag>
  );
}
