"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuth } from "@/hooks/useAuth";
import { api, type AgentBrief, type AgentJob } from "@/lib/api";

export default function AgentPage() {
  const { user, refresh: refreshAuth } = useAuth();
  const isVip = Boolean(user?.is_subscribed);
  const [goal, setGoal] = useState("");
  const [running, setRunning] = useState(false);
  const [briefLoading, setBriefLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [brief, setBrief] = useState<AgentBrief | null>(null);
  const [jobs, setJobs] = useState<AgentJob[]>([]);
  const [learning, setLearning] = useState<Record<string, unknown>[]>([]);
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);

  const refreshAgent = useCallback(async () => {
    if (!isVip) return;
    try {
      const [st, j, learn, latest] = await Promise.all([
        api.getAgentStatus().catch(() => null),
        api.listAgentJobs().catch(() => ({ jobs: [] as AgentJob[] })),
        api.getAgentLearning().catch(() => ({ learning: [] as Record<string, unknown>[] })),
        api.getLatestMorningBrief().catch(() => ({ brief: null })),
      ]);
      if (st) setStatus(st);
      setJobs(j.jobs || []);
      setLearning(learn.learning || []);
      if (latest?.brief) {
        setBrief(latest.brief);
        if (latest.brief.summary_text) setSummary(latest.brief.summary_text);
      }
    } catch {
      /* agent may not be deployed */
    }
  }, [isVip]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (new URLSearchParams(window.location.search).get("checkout") === "success") {
      refreshAuth?.();
    }
  }, [refreshAuth]);

  useEffect(() => {
    if (isVip) refreshAgent();
  }, [refreshAgent, isVip]);

  const handleRunGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    const g = goal.trim();
    if (!isVip || !g || running) return;
    setRunning(true);
    setError(null);
    try {
      const res = await api.runAgentGoal(g);
      const msg =
        (typeof res.summary === "string" && res.summary) ||
        (typeof res.message === "string" && res.message) ||
        "Agent finished.";
      setSummary(msg);
      setGoal("");
      await refreshAgent();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Agent run failed");
    } finally {
      setRunning(false);
    }
  };

  const handleMorningBrief = async () => {
    if (!isVip) return;
    setBriefLoading(true);
    setError(null);
    try {
      const res = await api.generateMorningBrief();
      if (res.brief) {
        setBrief(res.brief);
        setSummary(res.brief.summary_text || "Morning brief ready.");
      }
      await refreshAgent();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Morning brief failed");
    } finally {
      setBriefLoading(false);
    }
  };

  const startCheckout = async (plan: string) => {
    setCheckoutError(null);
    setCheckoutLoading(plan);
    try {
      const res = await api.createCheckoutSession(plan);
      if (res?.url) {
        window.location.href = res.url;
        return;
      }
      setCheckoutError("No payment link. Check billing keys on Railway.");
    } catch (err: unknown) {
      setCheckoutError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setCheckoutLoading(null);
    }
  };

  const toolsLive = Array.isArray(status?.tools_live) ? (status!.tools_live as string[]) : [];

  return (
    <ProtectedRoute>
      <div className="min-h-screen px-4 py-6 md:px-8 md:py-8 max-w-5xl mx-auto">
        {!isVip ? (
          <section className="mx-auto max-w-3xl space-y-6">
            <div className="rounded-2xl border border-cyan-500/25 bg-[#020914]/90 p-6 sm:p-8">
              <p className="font-mono-tech text-[10px] tracking-[0.35em] text-cyan-400/50 mb-3">
                AGENT ACCESS · VIP REQUIRED
              </p>
              <h1 className="font-display text-2xl sm:text-3xl font-bold text-white tracking-wide">
                Unlock Agent Command
              </h1>
              <p className="mt-3 text-sm text-cyan-200/70">
                Background scans, morning briefs, and auto-learn are VIP-only. Chat still works for free accounts.
              </p>
              {(checkoutError || error) && (
                <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                  {checkoutError || error}
                </div>
              )}
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              {[
                { plan: "monthly", label: "Monthly", hint: "30 days VIP" },
                { plan: "quarterly", label: "90-Day", hint: "Best value" },
                { plan: "yearly", label: "Yearly", hint: "Full year" },
              ].map((p) => (
                <div key={p.plan} className="rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-4">
                  <p className="font-display text-lg font-bold text-white">{p.label}</p>
                  <p className="mt-1 text-[10px] font-mono-tech text-cyan-400/50">{p.hint}</p>
                  <button
                    type="button"
                    disabled={!!checkoutLoading}
                    onClick={() => startCheckout(p.plan)}
                    className="mt-4 w-full rounded-lg bg-cyan-400 px-3 py-2.5 text-[10px] font-bold tracking-widest text-black disabled:opacity-40"
                  >
                    {checkoutLoading === p.plan ? "OPENING…" : "UPGRADE"}
                  </button>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-3">
              <Link href="/pricing" className="rounded-lg border border-cyan-500/30 px-5 py-3 text-xs font-mono-tech text-cyan-200">
                VIEW ALL PLANS
              </Link>
              <Link href="/chat" className="rounded-lg border border-cyan-500/30 px-5 py-3 text-xs font-mono-tech text-cyan-200">
                USE AI CHAT
              </Link>
              <button type="button" onClick={() => refreshAuth?.()} className="rounded-lg border border-cyan-500/20 px-5 py-3 text-[10px] font-mono-tech text-cyan-400/60">
                REFRESH STATUS
              </button>
            </div>
          </section>
        ) : (
          <>
            <header className="mb-8">
              <p className="font-mono-tech text-[10px] tracking-[0.35em] text-cyan-400/50 mb-2">PHASE 1 · AGENT</p>
              <h1 className="font-display text-2xl md:text-3xl font-bold text-white tracking-wide">AGENT COMMAND</h1>
              <p className="mt-2 text-sm text-cyan-400/60">Overnight watch, morning signals, and auto-learn.</p>
            </header>

            {error && (
              <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {error}
              </div>
            )}

            <div className="grid gap-6 lg:grid-cols-2">
              <section className="rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-5 space-y-4">
                <h2 className="font-mono-tech text-xs tracking-[0.25em] text-cyan-300">RUN GOAL</h2>
                <form onSubmit={handleRunGoal} className="space-y-3">
                  <textarea
                    value={goal}
                    onChange={(e) => setGoal(e.target.value)}
                    rows={3}
                    placeholder='e.g. "Morning signal when I wake up"'
                    disabled={running}
                    className="w-full rounded-lg bg-black/40 border border-cyan-500/25 px-3 py-2 text-sm text-white outline-none font-mono-tech resize-none"
                  />
                  <div className="flex flex-wrap gap-2">
                    <button type="submit" disabled={running || !goal.trim()} className="px-4 py-2 rounded-lg bg-cyan-400 text-black text-xs font-bold tracking-widest disabled:opacity-40">
                      {running ? "RUNNING…" : "EXECUTE"}
                    </button>
                    <button type="button" onClick={handleMorningBrief} disabled={briefLoading} className="px-4 py-2 rounded-lg border border-cyan-500/40 text-cyan-200 text-xs font-mono-tech disabled:opacity-40">
                      {briefLoading ? "SCANNING…" : "MORNING BRIEF"}
                    </button>
                  </div>
                </form>
                {summary && <p className="text-sm text-cyan-200/80 font-mono-tech whitespace-pre-wrap">{summary}</p>}
              </section>

              <section className="rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-5 space-y-3">
                <h2 className="font-mono-tech text-xs tracking-[0.25em] text-cyan-300">STATUS</h2>
                {status ? (
                  <p className="text-[11px] font-mono-tech text-emerald-300/90">
                    Phase {String(status.phase ?? "1")} · live · tools {toolsLive.length}
                  </p>
                ) : (
                  <p className="text-sm text-cyan-400/50">Agent API not reachable yet.</p>
                )}
                {brief?.summary_text && (
                  <p className="text-xs text-cyan-200/70 font-mono-tech whitespace-pre-wrap">{brief.summary_text}</p>
                )}
              </section>
            </div>

            <section className="mt-6 rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-5">
              <h2 className="font-mono-tech text-xs tracking-[0.25em] text-cyan-300 mb-3">JOBS</h2>
              {jobs.length === 0 ? (
                <p className="text-sm text-cyan-400/40">No jobs yet.</p>
              ) : (
                <ul className="space-y-2 max-h-48 overflow-y-auto">
                  {jobs.slice(0, 15).map((job, i) => (
                    <li key={String(job.id || i)} className="text-[10px] font-mono-tech text-cyan-300/70 border-b border-cyan-500/10 py-1.5">
                      {String(job.id || "—")} · {String(job.status || "—")}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="mt-6 rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-5 mb-10">
              <h2 className="font-mono-tech text-xs tracking-[0.25em] text-cyan-300 mb-3">AUTO-LEARN LOG</h2>
              {learning.length === 0 ? (
                <p className="text-sm text-cyan-400/40">Learning events appear after briefs and scans.</p>
              ) : (
                <ul className="space-y-1.5 max-h-48 overflow-y-auto">
                  {learning.slice(0, 20).map((row, i) => (
                    <li key={String(row.id || i)} className="text-[10px] font-mono-tech text-cyan-300/70 border-b border-cyan-500/10 py-1.5">
                      {String(row.symbol || "—")} · {String(row.signal || "—")} · {String(row.created_at || "").slice(0, 19)}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </div>
    </ProtectedRoute>
  );
}
