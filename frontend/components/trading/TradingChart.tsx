"use client";

import React, { useMemo, useState } from "react";

export type ChartDirection = "BUY" | "SELL" | "LONG" | "SHORT" | "BULLISH" | "BEARISH" | string;

export interface ChartCandle {
  time?: string | number | null;
  timestamp?: string | number | null;
  date?: string | null;
  open?: number | null;
  high?: number | null;
  low?: number | null;
  close?: number | null;
  price?: number | null;
  value?: number | null;
  closePrice?: number | null;
  ema9?: number | null;
  ema21?: number | null;
  ema50?: number | null;
  ema?: number | null;
  rsi?: number | null;
  volume?: number | null;
  [key: string]: any;
}

export interface TradingChartProps {
  data?: ChartCandle[] | null;
  candles?: ChartCandle[] | null;
  points?: ChartCandle[] | null;
  history?: ChartCandle[] | null;
  chartData?: ChartCandle[] | null;
  prices?: ChartCandle[] | null;
  series?: ChartCandle[] | null;
  symbol?: string;
  asset?: string;
  pair?: string;
  market?: string;
  marketType?: string;
  name?: string;
  timeframe?: string;
  interval?: string;
  tf?: string;
  selectedTimeframe?: string;
  timeframes?: string[];
  availableTimeframes?: string[];
  onTimeframeChange?: (tf: string) => void;
  currentPrice?: string | number | null;
  price?: string | number | null;
  lastPrice?: string | number | null;
  change?: string | number | null;
  changePercent?: string | number | null;
  percentChange?: string | number | null;
  source?: string | null;
  exchange?: string | null;
  status?: string | null;
  direction?: ChartDirection | null;
  side?: ChartDirection | null;
  bias?: ChartDirection | null;
  entry?: string | number | null;
  entryPrice?: string | number | null;
  stopLoss?: string | number | null;
  sl?: string | number | null;
  takeProfit1?: string | number | null;
  tp1?: string | number | null;
  takeProfit2?: string | number | null;
  tp2?: string | number | null;
  takeProfit3?: string | number | null;
  tp3?: string | number | null;
  aiAnalysis?: string | null;
  aiInterpretation?: string | null;
  marketRead?: string | null;
  analysis?: string | null;
  summary?: string | null;
  reasoning?: string | null;
  onPointClick?: (candle: ChartCandle, index: number) => void;
  onCandleClick?: (candle: ChartCandle, index: number) => void;
  onClick?: (candle: ChartCandle, index: number) => void;
  loading?: boolean;
  isLoading?: boolean;
  error?: string | null;
  errorMessage?: string | null;
  dataKey?: string;
  className?: string;
  height?: number;
  compact?: boolean;
  hideHeader?: boolean;
  hideGrid?: boolean;
  hideAxis?: boolean;
  showVolume?: boolean;
  dataProps?: Record<string, any>;
  [key: string]: any;
}

function safeNum(v: any): number | null {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return isNaN(n)? null : n;
}
function safeStr(v: any): string | null {
  if (v === null || v === undefined || v === "") return null;
  return String(v);
}
function normalizeDir(d?: string | null) {
  if (!d) return null;
  const s = String(d).toUpperCase().trim();
  const longKeys = ["BUY", "LONG", "BULLISH", "BULL"];
  const shortKeys = ["SELL", "SHORT", "BEARISH", "BEAR"];
  const isLong = longKeys.some((k) => s.includes(k));
  const isShort = shortKeys.some((k) => s.includes(k));
  return { label: s, isLong, isShort, isNeutral:!isLong &&!isShort };
}
function getCandlePrice(c: ChartCandle): number | null {
  return safeNum(c.close?? c.price?? c.value?? c.closePrice);
}
function getOHLC(c: ChartCandle): { o: number; h: number; l: number; cl: number } | null {
  const o = safeNum(c.open);
  const h = safeNum(c.high);
  const l = safeNum(c.low);
  const cl = safeNum(c.close?? c.price);
  if (o!== null && h!== null && l!== null && cl!== null) return { o, h, l, cl };
  return null;
}

export default function TradingChart(props: TradingChartProps) {
  const rawData = props.data?? props.candles?? props.points?? props.history?? props.chartData?? props.prices?? props.series?? null;
  const symbol = props.symbol?? props.asset?? props.pair?? props.name?? null;
  const market = props.market?? props.marketType?? null;
  const timeframe = props.timeframe?? props.interval?? props.tf?? props.selectedTimeframe?? null;
  const timeframes = props.timeframes?? props.availableTimeframes?? null;
  const currentPrice = safeStr(props.currentPrice?? props.price?? props.lastPrice?? null);
  const change = safeStr(props.change?? null);
  const changePct = safeStr(props.changePercent?? props.percentChange?? null);
  const source = safeStr(props.source?? props.exchange?? null);
  const status = safeStr(props.status?? null);
  const directionRaw = props.direction?? props.side?? props.bias?? null;
  const dirInfo = normalizeDir(directionRaw? String(directionRaw) : null);
  const entry = safeNum(props.entry?? props.entryPrice?? null);
  const sl = safeNum(props.stopLoss?? props.sl?? null);
  const tp1 = safeNum(props.takeProfit1?? props.tp1?? null);
  const tp2 = safeNum(props.takeProfit2?? props.tp2?? null);
  const tp3 = safeNum(props.takeProfit3?? props.tp3?? null);
  const aiText = props.aiAnalysis?? props.aiInterpretation?? props.marketRead?? props.analysis?? props.summary?? props.reasoning?? null;
  const loading = props.loading?? props.isLoading?? false;
  const error = props.error?? props.errorMessage?? null;
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const normalized = useMemo(() => {
    if (!rawData ||!Array.isArray(rawData) || rawData.length === 0) return [];
    return rawData as ChartCandle[];
  }, [rawData]);

  const hasOHLC = useMemo(() => {
    if (normalized.length === 0) return false;
    return normalized.some((c) => getOHLC(c)!== null);
  }, [normalized]);

  const stats = useMemo(() => {
    if (normalized.length === 0) return null;
    const prices: number[] = [];
    normalized.forEach((c) => {
      const p = getCandlePrice(c);
      if (p!== null) prices.push(p);
      const ohlc = getOHLC(c);
      if (ohlc) prices.push(ohlc.h, ohlc.l);
      const ema9 = safeNum(c.ema9);
      const ema21 = safeNum(c.ema21);
      const ema50 = safeNum(c.ema50);
      if (ema9!== null) prices.push(ema9);
      if (ema21!== null) prices.push(ema21);
      if (ema50!== null) prices.push(ema50);
    });
    [entry, sl, tp1, tp2, tp3].forEach((v) => { if (v!== null && v!== undefined) prices.push(v as number); });
    if (prices.length === 0) return null;
    let min = Math.min(...prices);
    let max = Math.max(...prices);
    const pad = (max - min) * 0.12 || max * 0.02 || 1;
    min -= pad; max += pad;
    if (min === max) { min -= 1; max += 1; }
    return { min, max };
  }, [normalized, entry, sl, tp1, tp2, tp3]);

  if (loading) {
    return (
      <section className={`kz-panel relative rounded-[24px] border border-white/[0.07] bg-[#0A0E16] overflow-hidden ${props.className || ""}`} aria-busy="true">
        <div aria-hidden="true" className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff06_1px,transparent_1px),linear-gradient(to_bottom,#ffffff06_1px,transparent_1px)] bg-[size:32px_32px] opacity-30" />
        <div className="relative">
          <div className="h-[56px] border-b border-white/[0.06] px-6 flex items-center justify-between">
            <div className="h-4 w-28 rounded-full bg-white/[0.06] animate-pulse" />
            <div className="h-6 w-20 rounded-full bg-white/[0.05] animate-pulse" />
          </div>
          <div className="p-6">
            <div className="h-[320px] rounded-[16px] bg-gradient-to-b from-white/[0.04] to-white/[0.01] border border-white/[0.06] relative overflow-hidden">
              <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.8s_infinite] bg-gradient-to-r from-transparent via-white/[0.05] to-transparent" />
            </div>
          </div>
        </div>
        <style>{`@keyframes shimmer { 100% { transform: translateX(100%); } }`}</style>
      </section>
    );
  }

  if (error) {
    return (
      <section className={`relative rounded-[24px] border border-rose-400/20 bg-[#0E0A0D] p-6 ${props.className || ""}`} role="alert">
        <div className="text-[11px] tracking-[0.14em] text-rose-300/60">CHART DATA UNAVAILABLE</div>
        <div className="mt-2 text-[13px] text-white/70">{error}</div>
      </section>
    );
  }

  if (!normalized || normalized.length === 0 ||!stats) {
    return (
      <section className={`relative rounded-[24px] border border-white/[0.06] bg-[#0A0E16] p-6 ${props.className || ""}`}>
        <div className="text-[10px] tracking-[0.14em] text-white/30">MARKET DATA UNAVAILABLE</div>
        <div className="mt-2 text-[13px] text-white/40">No chart data — awaiting real data from props. No fabricated candles.</div>
      </section>
    );
  }

  const W = 800; const H = props.height?? 360;
  const padL = 12; const padR = 56; const padT = 16; const padB = 28;
  const chartW = W - padL - padR; const chartH = H - padT - padB;
  const xStep = chartW / Math.max(1, normalized.length - 1);
  const yScale = (price: number) => { const { min, max } = stats; const ratio = (price - min) / (max - min || 1); return padT + chartH - ratio * chartH; };

  const priceLinePoints = normalized.map((c,i)=>{ const p=getCandlePrice(c); if(p===null) return null; return `${padL+i*xStep},${yScale(p)}`; }).filter(Boolean).join(" ");
  const ema9Points = normalized.map((c,i)=>{ const v=safeNum(c.ema9); if(v===null) return null; return `${padL+i*xStep},${yScale(v)}`; }).filter(Boolean).join(" ");
  const ema21Points = normalized.map((c,i)=>{ const v=safeNum(c.ema21); if(v===null) return null; return `${padL+i*xStep},${yScale(v)}`; }).filter(Boolean).join(" ");
  const ema50Points = normalized.map((c,i)=>{ const v=safeNum(c.ema50); if(v===null) return null; return `${padL+i*xStep},${yScale(v)}`; }).filter(Boolean).join(" ");

  const hoverCandle = hoverIdx!== null? normalized[hoverIdx] : null;
  const hoverPrice = hoverCandle? getCandlePrice(hoverCandle) : null;

  return (
    <section className={`kz-panel kz-glass relative rounded-[24px] md:rounded-[28px] border border-white/[0.08] bg-gradient-to-b from-[#0F1728] to-[#080B14] overflow-hidden shadow-[0_20px_64px_rgba(0,0,0,0.6),inset_0_1px_0_rgba(255,255,255,0.07)] ${props.className || ""}`} aria-label={`Trading chart ${symbol?? ""} ${timeframe?? ""}`.trim()}>
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(700px_320px_at_15%_0%,rgba(56,189,248,0.11),transparent),radial-gradient(600px_280px_at_85%_8%,rgba(139,92,246,0.10),transparent)]" />
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-300/25 to-transparent" />
      </div>
      <span aria-hidden="true" className="pointer-events-none absolute left-3 top-3 w-5 h-5 border-l border-t border-cyan-300/20 rounded-tl-[20px]" />
      <span aria-hidden="true" className="pointer-events-none absolute right-3 top-3 w-5 h-5 border-r border-t border-cyan-300/20 rounded-tr-[20px]" />

      <div className="relative">
        {!props.hideHeader && (
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 px-6 h-auto md:h-[64px] py-4 md:py-0 border-b border-white/[0.06]">
            <div className="flex items-center gap-4 min-w-0">
              <div className="w-8 h-8 rounded-[10px] bg-white/[0.06] border border-white/10 flex items-center justify-center shrink-0">
                <span className="w-2 h-2 rounded-full bg-cyan-300 shadow-[0_0_10px_rgba(34,211,238,0.7)] animate-pulse" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="text-[13px] font-semibold tracking-[-0.01em] truncate">{symbol?? "—"}</span>
                  {timeframe && <span className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] tracking-[0.08em] text-white/45">{timeframe}</span>}
                  {dirInfo && <span className={`rounded-full border px-2.5 py-1 text-[10px] tracking-[0.08em] font-medium ${dirInfo.isLong? "border-cyan-300/20 bg-cyan-400/[0.08] text-cyan-200/80" : dirInfo.isShort? "border-rose-300/20 bg-rose-400/[0.08] text-rose-200/75" : "border-white/10 bg-white/[0.04] text-white/50"}`}>{dirInfo.label}</span>}
                </div>
                <div className="mt-1 flex items-center gap-3 text-[11px]">
                  {currentPrice && <span className="text-[13px] font-medium text-white">{currentPrice}</span>}
                  {change && <span className="text-white/50">{change}</span>}
                  {changePct && <span className="text-white/50">{changePct}</span>}
                  {source && <span className="text-white/25">{source}</span>}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {timeframes && timeframes.length > 0 && (
                <div className="flex items-center gap-1 rounded-full border border-white/[0.06] bg-white/[0.03] p-1">
                  {timeframes.slice(0,7).map((tf)=>{ const active=tf===timeframe; return <button key={tf} onClick={()=>props.onTimeframeChange?.(tf)} className={`h-7 px-3 rounded-full text-[11px] font-medium transition-colors ${active? "bg-white text-black" : "text-white/50 hover:text-white/80 hover:bg-white/[0.06]"}`} aria-pressed={active}>{tf}</button>; })}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="p-3 md:p-5">
          <div className="rounded-[18px] border border-white/[0.06] bg-[#0A0F1B]/80 backdrop-blur overflow-hidden">
            <div className="relative"[STRIPPED 30 bytes]`0 0 ${W} ${H}`} className="w-full h-[360px] md:h-[400px] block select-none" role="img" aria-label={`Price chart for ${symbol?? "market"}`}>
                {!props.hideGrid && (
                  <g aria-hidden="true">
                    {[0,1,2,3,4].map((i)=>{ const y=padT+(i/4)*chartH; return <line key={`hg-${i}`} x1={padL} x2={W-padR} y1={y} y2={y} stroke="rgba(255,255,255,0.06)" strokeWidth="1" strokeDasharray="4 8" />; })}
                  </g>
                )}
                {entry!==null && <g><line x1={padL} x2={W-padR} y1={yScale(entry)} y2={yScale(entry)} stroke="rgba(34,211,238,0.35)" strokeWidth="1" strokeDasharray="6 6" /><rect x={W-padR+2} y={yScale(entry)-10} width="48" height="16" rx="8" fill="rgba(34,211,238,0.12)" stroke="rgba(34,211,238,0.25)" /><text x={W-padR+26} y={yScale(entry)+1} textAnchor="middle" fontSize="8" fill="rgba(165,243,252,0.9)" fontWeight="600">ENTRY</text></g>}
                {sl!==null && <g><line x1={padL} x2={W-padR} y1={yScale(sl)} y2={yScale(sl)} stroke="rgba(251,113,133,0.35)" strokeWidth="1" strokeDasharray="6 6" /><rect x={W-padR+2} y={yScale(sl)-10} width="32" height="16" rx="8" fill="rgba(251,113,133,0.12)" stroke="rgba(251,113,133,0.25)" /><text x={W-padR+18} y={yScale(sl)+1} textAnchor="middle" fontSize="8" fill="rgba(255,228,230,0.9)" fontWeight="600">SL</text></g>}
                {tp1!==null && <g><line x1={padL} x2={W-padR} y1={yScale(tp1)} y2={yScale(tp1)} stroke="rgba(16,185,129,0.30)" strokeWidth="1" strokeDasharray="4 8" /><rect x={W-padR+2} y={yScale(tp1)-10} width="38" height="16" rx="8" fill="rgba(16,185,129,0.12)" stroke="rgba(16,185,129,0.25)" /><text x={W-padR+21} y={yScale(tp1)+1} textAnchor="middle" fontSize="8" fill="rgba(167,243,208,0.9)" fontWeight="600">TP1</text></g>}
                {tp2!==null && <g><line x1={padL} x2={W-padR} y1={yScale(tp2)} y2={yScale(tp2)} stroke="rgba(16,185,129,0.25)" strokeWidth="1" strokeDasharray="4 8" /><rect x={W-padR+2} y={yScale(tp2)-10} width="38" height="16" rx="8" fill="rgba(16,185,129,0.10)" stroke="rgba(16,185,129,0.20)" /><text x={W-padR+21} y={yScale(tp2)+1} textAnchor="middle" fontSize="8" fill="rgba(167,243,208,0.85)" fontWeight="600">TP2</text></g>}
                {tp3!==null && <g><line x1={padL} x2={W-padR} y1={yScale(tp3)} y2={yScale(tp3)} stroke="rgba(16,185,129,0.20)" strokeWidth="1" strokeDasharray="4 8" /><rect x={W-padR+2} y={yScale(tp3)-10} width="38" height="16" rx="8" fill="rgba(16,185,129,0.08)" stroke="rgba(16,185,129,0.15)" /><text x={W-padR+21} y={yScale(tp3)+1} textAnchor="middle" fontSize="8" fill="rgba(167,243,208,0.80)" fontWeight="600">TP3</text></g>}

                {hasOHLC? (
                  <g>
                    {normalized.map((c,i)=>{ const ohlc=getOHLC(c); if(!ohlc) return null; const x=padL+i*xStep; const yO=yScale(ohlc.o); const yC=yScale(ohlc.cl); const yH=yScale(ohlc.h); const yL=yScale(ohlc.l); const isBull=ohlc.cl>=ohlc.o; const bodyW=Math.max(2,xStep*0.6); const bodyH=Math.abs(yC-yO)||1; const bodyY=Math.min(yO,yC); return <g key={i} onMouseEnter={()=>setHoverIdx(i)} onMouseLeave={()=>setHoverIdx(null)}><line x1={x} x2={x} y1={yH} y2={yL} stroke={isBull?"rgba(34,211,238,0.55)":"rgba(251,113,133,0.55)"} strokeWidth="1" /><rect x={x-bodyW/2} y={bodyY} width={bodyW} height={bodyH} fill={isBull?"rgba(34,211,238,0.85)":"rgba(251,113,133,0.85)"} rx="1" /></g>; })}
                  </g>
                ) : (
                  <g>
                    <defs><linearGradient id="kz-price-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor={dirInfo?.isLong?"rgba(34,211,238,0.25)":dirInfo?.isShort?"rgba(251,113,133,0.20)":"rgba(255,255,255,0.18)"} /><stop offset="100%" stopColor="rgba(0,0,0,0)" /></linearGradient></defs>
                    {priceLinePoints && <><path d={`M ${padL} ${padT+chartH} L ${priceLinePoints} L ${padL+(normalized.length-1)*xStep} ${padT+chartH} Z`} fill="url(#kz-price-fill)" opacity="0.8" /><polyline fill="none" stroke={dirInfo?.isLong?"rgba(34,211,238,0.9)":dirInfo?.isShort?"rgba(251,113,133,0.85)":"rgba(255,255,255,0.75)"} strokeWidth="1.6" points={priceLinePoints} /></>}
                  </g>
                )}

                {ema9Points && <polyline fill="none" stroke="rgba(34,211,238,0.55)" strokeWidth="1" strokeDasharray="2 3" points={ema9Points} />}
                {ema21Points && <polyline fill="none" stroke="rgba(125,211,252,0.55)" strokeWidth="1" strokeDasharray="2 3" points={ema21Points} />}
                {ema50Points && <polyline fill="none" stroke="rgba(196,181,253,0.55)" strokeWidth="1" strokeDasharray="2 3" points={ema50Points} />}

                {hoverIdx!==null && <g aria-hidden="true"><line x1={padL+hoverIdx*xStep} x2={padL+hoverIdx*xStep} y1={padT} y2={padT+chartH} stroke="rgba(255,255,255,0.15)" strokeWidth="1" strokeDasharray="3 6" /></g>}

                {!props.hideAxis && stats && (
                  <g fontSize="10" fill="rgba(255,255,255,0.35)" fontFamily="monospace">
                    <text x={W-padR+4} y={padT+4} dominantBaseline="hanging">{stats.max.toFixed(2)}</text>
                    <text x={W-padR+4} y={padT+chartH/2} dominantBaseline="middle">{((stats.max+stats.min)/2).toFixed(2)}</text>
                    <text x={W-padR+4} y={padT+chartH} dominantBaseline="auto">{stats.min.toFixed(2)}</text>
                  </g>
                )}
              </svg>

              {hoverCandle && hoverIdx!==null && (
                <div className="pointer-events-none absolute left-4 top-4 rounded-[12px] border border-white/[0.08] bg-[#0E1524]/90 backdrop-blur px-3 py-2.5">
                  <div className="text-[10px] text-white/30">{hoverCandle.time?? hoverCandle.timestamp?? `IDX ${hoverIdx}`}</div>
                  <div className="mt-1 text-[11px] text-white/70">P {hoverPrice?? "—"}</div>
                </div>
              )}

              <div className="absolute inset-0" onMouseMove={(e)=>{ const rect=(e.currentTarget as HTMLElement).getBoundingClientRect(); const x=e.clientX-rect.left; const rel=(x/rect.width)*W; const idx=Math.round((rel-padL)/xStep); if(idx>=0&&idx<normalized.length) setHoverIdx(idx); }} onMouseLeave={()=>setHoverIdx(null)} />
            </div>
          </div>

          {aiText && (
            <div className="mt-4 rounded-[14px] border border-cyan-300/12 bg-gradient-to-b from-cyan-400/[0.06] to-white/[0.01] p-[1px]">
              <div className="rounded-[13px] bg-[#0A131D]/90 backdrop-blur p-4">
                <div className="text-[10px] tracking-[0.12em] text-cyan-200/60">AI MARKET INTELLIGENCE</div>
                <p className="mt-2.5 text-[12.5px] leading-[1.6] text-white/70 whitespace-pre-wrap">{aiText}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
