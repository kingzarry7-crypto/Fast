"use client";

import { useCallback, useEffect, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";

type CTraderStatus = {
  configured?: boolean;
  connected?: boolean;
  account_id?: string | null;
  environment?: string | null;
  demo_verified?: boolean;
  automated_orders_enabled?: boolean;
  message?: string;
  detail?: string;
};
type SignalRow = {
  symbol?: string;
  status?: string;
  timeframe?: string;
  completed_candle_time?: string;
  signal?: { signal?: string; candidate_signal?: string; signal_gate_reason?: string; strategy_edge_validated?: boolean; price?: number; reasons?: string[]; signal_type?: string };
  signal_type?: string;
  model_validated_for_market?: boolean;
  error?: string;
};
type PaperStatus = {
  mode?: string;
  enabled?: boolean;
  timeframe?: string;
  starting_cash_usd?: number;
  cash_usd?: number;
  open_positions_value_usd?: number;
  equity_usd?: number;
  positions?: Array<{ symbol?: string; quantity?: number; mark_price?: number }>;
  recent_orders?: Array<{ symbol?: string; side?: string; price?: number; created_at?: string; notional_usd?: number }>;
  live_trading_enabled?: boolean;
  warning?: string;
};

function money(value?: number) {
  return typeof value === "number" && Number.isFinite(value)
    ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(value)
    : "—";
}
function signalLabel(row?: SignalRow) {
  if (!row || row.status !== "available" || !row.completed_candle_time) return "WAIT / NO TRADE";
  const stamp = Date.parse(row.completed_candle_time);
  if (!Number.isFinite(stamp) || Date.now() - stamp > 3 * 60 * 60 * 1000 || stamp > Date.now() + 5 * 60 * 1000) return "WAIT / NO TRADE";
  const value = String(row.signal?.signal || "").toUpperCase().replaceAll("_", " ");
  return ["BUY", "SELL", "NO TRADE"].includes(value) ? value : "WAIT / NO TRADE";
}
function candidateLabel(row?: SignalRow) {
  if (!row || row.status !== "available" || !row.completed_candle_time) return "UNAVAILABLE";
  const stamp = Date.parse(row.completed_candle_time);
  if (!Number.isFinite(stamp) || Date.now() - stamp > 3 * 60 * 60 * 1000 || stamp > Date.now() + 5 * 60 * 1000) return "STALE";
  const value = String(row.signal?.candidate_signal || "NO SETUP").toUpperCase().replaceAll("_", " ");
  return ["BUY", "SELL", "NO TRADE"].includes(value) ? value : "NO SETUP";
}
function signalClass(value: string) {
  if (value === "BUY") return "border-emerald-400/30 bg-emerald-400/10 text-emerald-200";
  if (value === "SELL") return "border-rose-400/30 bg-rose-400/10 text-rose-200";
  return "border-amber-300/25 bg-amber-300/5 text-amber-100";
}
function panel() {
  return "rounded-2xl border border-cyan-400/15 bg-[#07111f]/85 shadow-[0_18px_60px_rgba(0,0,0,0.18)]";
}

export default function TraderPage() {
  const [broker, setBroker] = useState<CTraderStatus | null>(null);
  const [paper, setPaper] = useState<PaperStatus | null>(null);
  const [signals, setSignals] = useState<SignalRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    const [brokerResult, paperResult, signalsResult] = await Promise.allSettled([
      fetch("/api/ctrader/status", { credentials: "include", cache: "no-store" }).then(async (r) => {
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || "Could not verify cTrader status");
        return data as CTraderStatus;
      }),
      fetch("/api/trader/paper/status", { credentials: "include", cache: "no-store" }).then(async (r) => {
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || "Paper ledger unavailable");
        return data as PaperStatus;
      }),
      fetch("/api/trader/paper/signals?symbols=BTC%2FUSD%2CXAU%2FUSD&timeframe=1h", { credentials: "include", cache: "no-store" }).then(async (r) => {
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || "Kitty signals unavailable");
        return data as { results?: SignalRow[] };
      }),
    ]);
    if (brokerResult.status === "fulfilled") setBroker(brokerResult.value);
    else { setBroker(null); setError((old) => old || (brokerResult.reason instanceof Error ? brokerResult.reason.message : "cTrader status unavailable")); }
    if (paperResult.status === "fulfilled") setPaper(paperResult.value);
    else setPaper(null);
    if (signalsResult.status === "fulfilled") setSignals(signalsResult.value.results || []);
    else setSignals([]);
    if (paperResult.status === "rejected" && signalsResult.status === "rejected") {
      setError((old) => old || "Kitty and paper-trading endpoints are unavailable. Check the Railway API deployment and sign-in session.");
    }
    setLoading(false);
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const disconnect = async () => {
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/ctrader/disconnect", { method: "POST", credentials: "include" });
      const raw = await response.text();
      let data: { detail?: string; message?: string } = {};
      try { data = JSON.parse(raw) as typeof data; } catch { /* empty response */ }
      if (!response.ok) throw new Error(data.detail || data.message || "cTrader disconnect failed");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "cTrader disconnect failed");
    } finally { setBusy(false); }
  };

  const markets = ["BTC/USD", "XAU/USD"];
  return (
    <ProtectedRoute>
      <div className="min-h-full bg-[#030812] p-4 text-white sm:p-6 lg:p-10">
        <div className="mx-auto max-w-7xl space-y-6">
          <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="font-mono-tech text-[10px] tracking-[0.35em] text-cyan-300/60">KING ZARRY AI · TRADING LAB</p>
              <h1 className="mt-2 font-display text-3xl font-bold tracking-wider sm:text-4xl">King Zarry Trader</h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300/70">Demo connection, completed-candle Kitty research signals, and an isolated paper ledger. Live broker orders are disabled.</p>
            </div>
            <button type="button" onClick={() => void refresh()} disabled={loading} className="rounded-xl border border-cyan-300/30 bg-cyan-300/10 px-4 py-2.5 font-mono-tech text-[10px] tracking-widest text-cyan-100 hover:bg-cyan-300/15 disabled:opacity-50">
              {loading ? "CHECKING…" : "REFRESH STATUS"}
            </button>
          </header>

          {error && <div role="alert" className="rounded-xl border border-amber-300/25 bg-amber-300/5 p-4 text-sm text-amber-100">{error}</div>}

          <section className={panel() + " p-5 sm:p-6"}>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-mono-tech text-[10px] tracking-[0.25em] text-cyan-300/60">BROKER CONNECTION</p>
                <h2 className="mt-2 text-xl font-semibold">cTrader Open API</h2>
                <p className="mt-1 text-sm text-slate-300/65">{broker?.message || "Checking server-side OAuth and demo-account verification…"}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {broker?.connected && broker.demo_verified ? (
                  <span className="rounded-lg border border-emerald-400/30 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-100">DEMO VERIFIED</span>
                ) : (
                  <span className="rounded-lg border border-amber-300/25 bg-amber-300/5 px-3 py-2 text-xs text-amber-100">{broker?.connected ? "VERIFY DEMO ACCOUNT" : broker?.configured ? "NOT CONNECTED" : "SERVER SETUP REQUIRED"}</span>
                )}
                {!broker?.connected && <a href="/api/ctrader/connect" className="rounded-lg bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-200">Connect cTrader</a>}
                {broker?.connected && <button type="button" disabled={busy} onClick={() => void disconnect()} className="rounded-lg border border-rose-300/30 px-4 py-2 text-sm text-rose-100 hover:bg-rose-300/10 disabled:opacity-50">{busy ? "PLEASE WAIT…" : "Disconnect"}</button>}
              </div>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-white/5 bg-black/20 p-3"><p className="text-[10px] tracking-widest text-slate-400">ACCOUNT ID</p><p className="mt-2 break-all text-sm">{broker?.account_id || "Not available"}</p></div>
              <div className="rounded-xl border border-white/5 bg-black/20 p-3"><p className="text-[10px] tracking-widest text-slate-400">ENVIRONMENT</p><p className="mt-2 text-sm">{broker?.environment || "Unknown"}</p></div>
              <div className="rounded-xl border border-white/5 bg-black/20 p-3"><p className="text-[10px] tracking-widest text-slate-400">ORDER PERMISSION</p><p className="mt-2 text-sm text-amber-100">Disabled by design</p></div>
            </div>
          </section>

          <section>
            <div className="mb-3 flex items-end justify-between gap-3"><div><p className="font-mono-tech text-[10px] tracking-[0.25em] text-cyan-300/60">KITTY · COMPLETED CANDLES</p><h2 className="mt-1 text-xl font-semibold">Market signals</h2></div><span className="text-xs text-slate-400">1-hour timeframe</span></div>
            <div className="grid gap-4 md:grid-cols-2">
              {markets.map((symbol) => {
                const row = signals.find((item) => item.symbol === symbol);
                const label = signalLabel(row);\n                const candidate = candidateLabel(row);
                return <article key={symbol} className={panel() + " p-5"}>
                  <div className="flex items-start justify-between gap-3"><div><p className="text-xs tracking-widest text-slate-400">MARKET</p><h3 className="mt-1 text-2xl font-semibold">{symbol}</h3></div><span className={"rounded-lg border px-3 py-1.5 text-xs font-semibold " + signalClass(label)}>{label}</span></div>
                  <div className="mt-5 grid grid-cols-2 gap-3">
                    <div className="rounded-xl bg-black/20 p-3"><p className="text-[10px] tracking-widest text-slate-500">REFERENCE PRICE</p><p className="mt-2 text-lg">{typeof row?.signal?.price === "number" ? row.signal.price.toLocaleString(undefined, { maximumFractionDigits: 5 }) : "—"}</p></div>
                    <div className="rounded-xl bg-black/20 p-3"><p className="text-[10px] tracking-widest text-slate-500">COMPLETED CANDLE</p><p className="mt-2 text-xs text-slate-200">{row?.completed_candle_time ? new Date(row.completed_candle_time).toLocaleString() : "No fresh data"}</p></div>
                  </div>
                  <div className="mt-4 rounded-xl border border-cyan-300/10 bg-cyan-300/[0.04] p-3">
                    <p className="text-[10px] tracking-widest text-cyan-200/70">RESEARCH SETUP · NOT AN APPROVED TRADE</p>
                    <p className="mt-2 text-sm font-semibold text-slate-100">{candidate}</p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-400">{row?.signal?.strategy_edge_validated === true ? "This strategy has passed its recorded validation gate." : row?.signal?.signal_gate_reason || "Candidate setups are informational only; the actionable signal remains gated."}</p>
                  </div>
                  <p className="mt-3 text-xs leading-relaxed text-slate-400">{row?.status === "available" ? "Technical confluence is experimental and does not establish profitability. The actionable signal remains WAIT / NO TRADE unless separately validated." : "Signal unavailable or stale. Defaulting to WAIT / NO TRADE."}</p>
                </article>;
              })}
            </div>
          </section>

          <section className={panel() + " p-5 sm:p-6"}>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-mono-tech text-[10px] tracking-[0.25em] text-cyan-300/60">SIMULATION ONLY</p><h2 className="mt-1 text-xl font-semibold">Kitty paper ledger</h2></div><span className="rounded-lg border border-amber-300/25 bg-amber-300/5 px-3 py-1.5 text-xs text-amber-100">{paper?.enabled ? "PAPER WORKER ENABLED" : "PAPER WORKER PAUSED"}</span></div>
            <div className="mt-5 grid gap-3 grid-cols-2 lg:grid-cols-4">
              {[["Starting cash", money(paper?.starting_cash_usd)], ["Available cash", money(paper?.cash_usd)], ["Open positions", money(paper?.open_positions_value_usd)], ["Paper equity", money(paper?.equity_usd)]].map(([label, value]) => <div key={label} className="rounded-xl border border-white/5 bg-black/20 p-4"><p className="text-[10px] tracking-widest text-slate-500">{label.toUpperCase()}</p><p className="mt-2 text-lg font-semibold">{value}</p></div>)}
            </div>
            <p className="mt-4 text-xs leading-relaxed text-slate-400">{paper?.warning || "Paper ledger data is not available. No balance or P&L has been inferred."}</p>
            {Array.isArray(paper?.recent_orders) && paper.recent_orders.length > 0 && <div className="mt-5 overflow-x-auto"><h3 className="mb-2 text-sm font-semibold">Recent simulated orders</h3><table className="w-full min-w-[480px] text-left text-xs"><thead className="text-slate-500"><tr><th className="py-2">Market</th><th>Side</th><th>Notional</th><th>Time</th></tr></thead><tbody>{paper.recent_orders.slice(0, 8).map((order, i) => <tr key={String(order.created_at || i)} className="border-t border-white/5"><td className="py-2">{order.symbol || "—"}</td><td>{order.side || "—"}</td><td>{money(order.notional_usd)}</td><td>{order.created_at ? new Date(order.created_at).toLocaleString() : "—"}</td></tr>)}</tbody></table></div>}
          </section>
          <p className="pb-4 text-[10px] leading-relaxed text-slate-500">Safety notice: cTrader connection is informational only. This page never submits broker orders or enables live trading. Kitty’s experimental signals do not establish profitability; use WAIT / NO TRADE whenever data is missing, stale, or unverified.</p>
        </div>
      </div>
    </ProtectedRoute>
  );
}
