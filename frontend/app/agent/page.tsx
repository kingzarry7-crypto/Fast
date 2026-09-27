"use client";

import { useCallback, useEffect, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import {
  api,
  type AgentBrief,
  type AgentJob,
} from "@/lib/api";

export default function AgentPage() {
  const [goal, setGoal] = useState("");
  const [running, setRunning] = useState(false);
  const [briefLoading, setBriefLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [brief, setBrief] = useState<AgentBrief | null>(null);
  const [jobs, setJobs] = useState<AgentJob[]>([]);
  const [learning, setLearning] = useState<Record<string, unknown>[]>([]);
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);

  const refresh = useCallback(async () => {
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
      /* backend agent may not be deployed yet */
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleRunGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    const g = goal.trim();
    if (!g || running) return;
    setRunning(true);
    setError(null);
    try {
      const res = await api.runAgentGoal(g);
      const msg =
        (typeof res.summary === "string" && res.summary) ||
        (typeof res.message === "string" && res.message) ||
        (res.status === "awaiting_approval"
          ? "Job logged — needs your approval (risky action)."
          : "Agent finished.");
      setSummary(msg);
      if (res.brief && typeof res.brief === "object") {
        setBrief(res.brief as AgentBrief);
      }
      setGoal("");
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Agent run failed");
    } finally {
      setRunning(false);
    }
  };

  const handleMorningBrief = async () => {
    setBriefLoading(true);
    setError(null);
    try {
      const res = await api.generateMorningBrief();
      if (res.brief) {
        setBrief(res.brief);
        setSummary(res.brief.summary_text || "Morning brief ready.");
      }
      await refresh();
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Morning brief failed — is agent_core on Railway?"
      );
    } finally {
      setBriefLoading(false);
    }
  };

  const handleApprove = async (jobId: string) => {
    try {
      await api.approveAgentJob(jobId);
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Approve failed");
    }
  };

  const toolsLive = Array.isArray(status?.tools_live)
    ? (status!.tools_live as string[])
    : [];
  const toolsRoadmap = Array.isArray(status?.tools_roadmap)
    ? (status!.tools_roadmap as string[])
    : [];

  return (
    <ProtectedRoute>
      <div className="min-h-screen px-4 py-6 md:px-8 md:py-8 max-w-5xl mx-auto">
        <header className="mb-8">
          <p className="font-mono-tech text-[10px] tracking-[0.35em] text-cyan-400/50 mb-2">
            PHASE 1 · PLANNER + TOOLS + JOB LOG
          </p>
          <h1 className="font-display text-2xl md:text-3xl font-bold text-white tracking-wide">
            AGENT COMMAND
          </h1>
          <p className="mt-2 text-sm text-cyan-400/60 max-w-2xl">
            Overnight market watch, morning signals, and auto-learn. Safe jobs run
            now. Social / browser actions wait for your approval.
          </p>
        </header>

        {error && (
          <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200 font-mono-tech">
            {error}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-5 space-y-4">
            <h2 className="font-mono-tech text-xs tracking-[0.25em] text-cyan-300">
              RUN GOAL
            </h2>
            <form onSubmit={handleRunGoal} className="space-y-3">
              <textarea
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                rows={3}
                placeholder='e.g. "Morning signal when I wake up" or "Analyze BTC"'
                disabled={running}
                className="w-full rounded-lg bg-black/40 border border-cyan-500/25 focus:border-cyan-400 px-3 py-2 text-sm text-white placeholder-cyan-400/30 outline-none font-mono-tech resize-none"
              />
              <div className="flex flex-wrap gap-2">
                <button
                  type="submit"
                  disabled={running || !goal.trim()}
                  className="px-4 py-2 rounded-lg bg-cyan-400 text-black text-xs font-bold tracking-widest hover:bg-cyan-300 disabled:opacity-40"
                >
                  {running ? "RUNNING…" : "EXECUTE"}
                </button>
                <button
                  type="button"
                  onClick={handleMorningBrief}
                  disabled={briefLoading}
                  className="px-4 py-2 rounded-lg border border-cyan-500/40 text-cyan-200 text-xs font-mono-tech tracking-widest hover:bg-cyan-500/10 disabled:opacity-40"
                >
                  {briefLoading ? "SCANNING…" : "MORNING BRIEF"}
                </button>
              </div>
            </form>
            <div className="flex flex-wrap gap-2">
              {[
                "Morning signal when I wake up",
                "Analyze BTC multi-timeframe",
                "Watch the full market today",
              ].map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => setGoal(q)}
                  className="px-2.5 py-1 rounded-md text-[10px] font-mono-tech border border-cyan-500/20 text-cyan-400/70 hover:text-cyan-200"
                >
                  {q}
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-5 space-y-3">
            <h2 className="font-mono-tech text-xs tracking-[0.25em] text-cyan-300">
              CAPABILITIES
            </h2>
            {status ? (
              <>
                <p className="text-[11px] font-mono-tech text-emerald-300/90">
                  Phase {String(status.phase ?? "1")} · live
                </p>
                <div>
                  <p className="text-[9px] tracking-widest text-cyan-400/40 mb-1">
                    LIVE TOOLS
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {toolsLive.map((t) => (
                      <span
                        key={t}
                        className="px-2 py-0.5 rounded border border-emerald-500/30 text-[10px] text-emerald-200/90 font-mono-tech"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-[9px] tracking-widest text-cyan-400/40 mb-1">
                    ROADMAP
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {toolsRoadmap.map((t) => (
                      <span
                        key={t}
                        className="px-2 py-0.5 rounded border border-zinc-600/40 text-[10px] text-zinc-400 font-mono-tech"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <p className="text-sm text-cyan-400/50">
                Agent API not reachable yet. Deploy agent_core.py + updated api.py on Railway.
              </p>
            )}
          </section>
        </div>

        {(summary || brief) && (
          <section className="mt-6 rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-5">
            <h2 className="font-mono-tech text-xs tracking-[0.25em] text-cyan-300 mb-3">
              LATEST BRIEF
            </h2>
            <pre className="whitespace-pre-wrap text-sm text-cyan-100/90 font-mono-tech leading-relaxed">
              {summary || brief?.summary_text || "—"}
            </pre>
            <p className="mt-3 text-[10px] text-cyan-400/40">
              Not financial advice. Trading involves risk.
            </p>
          </section>
        )}

        <section className="mt-6 rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-mono-tech text-xs tracking-[0.25em] text-cyan-300">
              JOB LOG
            </h2>
            <button
              type="button"
              onClick={() => refresh()}
              className="text-[10px] font-mono-tech text-cyan-400/60 hover:text-cyan-200"
            >
              REFRESH
            </button>
          </div>
          {jobs.length === 0 ? (
            <p className="text-sm text-cyan-400/40">No jobs yet.</p>
          ) : (
            <ul className="space-y-2">
              {jobs.slice(0, 15).map((job) => (
                <li
                  key={job.id}
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 rounded-lg border border-cyan-500/15 px-3 py-2"
                >
                  <div className="min-w-0">
                    <p className="font-mono-tech text-[11px] text-white truncate">
                      {job.title || job.job_type}
                    </p>
                    <p className="text-[10px] text-cyan-400/40 font-mono-tech">
                      {job.job_type} · {job.status}
                    </p>
                  </div>
                  {job.status === "awaiting_approval" && (
                    <button
                      type="button"
                      onClick={() => handleApprove(job.id)}
                      className="shrink-0 px-3 py-1.5 rounded-md border border-amber-500/40 text-amber-200 text-[10px] font-mono-tech tracking-wider hover:bg-amber-500/10"
                    >
                      APPROVE
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="mt-6 rounded-xl border border-cyan-500/20 bg-[#020914]/80 p-5 mb-10">
          <h2 className="font-mono-tech text-xs tracking-[0.25em] text-cyan-300 mb-3">
            AUTO-LEARN LOG
          </h2>
          {learning.length === 0 ? (
            <p className="text-sm text-cyan-400/40">
              Learning events appear after morning briefs and scans.
            </p>
          ) : (
            <ul className="space-y-1.5 max-h-48 overflow-y-auto kz-scroll">
              {learning.slice(0, 20).map((row, i) => (
                <li
                  key={String(row.id || i)}
                  className="text-[10px] font-mono-tech text-cyan-300/70 border-b border-cyan-500/10 py-1.5"
                >
                  {String(row.symbol || "—")} · {String(row.signal || "—")} ·{" "}
                  {String(row.outcome || "")} ·{" "}
                  {String(row.created_at || "").slice(0, 19)}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </ProtectedRoute>
  );
}
