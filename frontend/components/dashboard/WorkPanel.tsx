"use client";

import { useCallback, useEffect, useState } from "react";

type WorkflowStepOutput = {
  message?: string;
  browser_plan?: { summary?: string };
  action?: { payload?: Record<string, unknown>; type?: string; text?: string; selector?: string };
};

type Workflow = {
  id: string; goal: string; status: string; risk: string; potential_revenue?: number;
  plan?: Array<{ id: string; title: string; status: string; risk: string; requires_approval?: boolean;
    approval_id?: string; output?: WorkflowStepOutput; }>;
};

export default function WorkPanel() {
  const [open, setOpen] = useState(false);
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [error, setError] = useState("");
  const [browserReady, setBrowserReady] = useState<boolean | null>(null);
  const waitingCount = workflows.filter((item) => item.status === "waiting_for_approval").length;

  const load = useCallback(async () => {
    try {
      const response = await fetch("/api/workflows", { credentials: "include" });
      if (!response.ok) return;
      const data = await response.json();
      setWorkflows(data.workflows || []);
    } catch {}
  }, []);

  useEffect(() => {
    if (!open) return;
    load();
    fetch("/api/browser/status", { credentials: "include" }).then((r) => r.ok ? r.json() : null).then((d) => setBrowserReady(d?.browser?.available === true)).catch(() => setBrowserReady(false));
    const timer = window.setInterval(load, 5000);
    return () => window.clearInterval(timer);
  }, [open, load]);

  async function startWork() {
    const text = goal.trim();
    if (!text || loading) return;
    setLoading(true); setError("");
    try {
      const response = await fetch("/api/workflows", {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: text }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || data.error || "Could not start work");
      setGoal(""); await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start work");
    } finally { setLoading(false); }
  }

  async function approve(id: string, approved: boolean) {
    try {
      await fetch("/api/workflows/" + id + "/approve", {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved }),
      });
      await load();
    } catch {}
  }

  return (
    <>
      <button type="button" onClick={() => setOpen(true)}
        className="rounded-md border border-violet-400/40 bg-violet-400/10 px-2.5 py-1.5 font-mono-tech text-[10px] tracking-widest text-violet-200 hover:bg-violet-400/20 shrink-0">
        WORK
      </button>

      {open && (
        <>
          <button type="button" aria-label="Close Work" onClick={() => setOpen(false)}
            className="fixed inset-0 z-[70] bg-black/60 backdrop-blur-[2px]" />
          <aside className="fixed right-0 top-0 z-[80] flex h-[100dvh] w-full max-w-md flex-col border-l border-violet-400/20 bg-[#060811] shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
              <div>
                <div className="font-mono-tech text-xs tracking-[0.22em] text-violet-200">AUTONOMOUS WORK</div>
                <div className="mt-1 font-mono-tech text-[8px] tracking-widest text-zinc-600">BROWSER {browserReady === null ? "CHECKING" : browserReady ? "READY" : "OFFLINE"}</div>
                <div className="mt-1 text-[10px] text-zinc-500">Give the goal. KZ researches, prepares and waits for approval when needed.</div>
                {waitingCount > 0 && <div className="mt-2 inline-flex rounded border border-amber-400/25 bg-amber-400/5 px-2 py-1 font-mono-tech text-[9px] tracking-widest text-amber-300">{waitingCount} APPROVAL{waitingCount === 1 ? "" : "S"} WAITING</div>}
              </div>
              <button type="button" onClick={() => setOpen(false)} className="rounded-md px-2 py-1 text-zinc-500 hover:bg-white/5">×</button>
            </div>

            <div className="border-b border-white/5 p-4">
              <textarea value={goal} onChange={(e) => setGoal(e.target.value)}
                onKeyDown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") startWork(); }}
                placeholder="Example: Find me 5 legitimate website clients this week and prepare the best offers."
                className="min-h-24 w-full resize-none rounded-xl border border-violet-400/15 bg-white/[0.03] p-3 text-sm text-white outline-none placeholder:text-zinc-600 focus:border-violet-400/40" />
              <button type="button" disabled={!goal.trim() || loading} onClick={startWork}
                className="mt-2 w-full rounded-xl border border-violet-400/30 bg-violet-400/10 px-4 py-2.5 font-mono-tech text-[10px] tracking-widest text-violet-100 disabled:opacity-40">
                {loading ? "STARTING..." : "START WORK"}
              </button>
              {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto p-3">
              {!workflows.length && <p className="px-2 py-8 text-center text-xs text-zinc-600">No work started yet.</p>}
              {workflows.map((workflow) => {
                const waiting = workflow.status === "waiting_for_approval";
                const step = workflow.plan?.find((item) => item.status === "waiting_for_approval");
                return (
                  <div key={workflow.id} className="mb-3 rounded-xl border border-white/5 bg-white/[0.025] p-3">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm text-zinc-200">{workflow.goal}</p>
                      <span className="shrink-0 rounded border border-white/10 px-1.5 py-0.5 font-mono-tech text-[8px] uppercase text-zinc-500">
                        {workflow.status.replaceAll("_", " ")}
                      </span>
                    </div>
                    <div className="mt-2 flex gap-3 font-mono-tech text-[9px] uppercase tracking-wider text-zinc-600">
                      <span>risk:{workflow.risk}</span>
                      <span>potential:{Number(workflow.potential_revenue || 0).toFixed(0)}</span>
                    </div>
                    {waiting && (
                      <div className="mt-3 rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                        <div className="font-mono-tech text-[9px] tracking-widest text-amber-300">APPROVAL REQUIRED · CONSEQUENT ACTION</div>
                        <div className="mt-2 rounded border border-white/10 bg-black/20 p-2">
                          <div className="text-[9px] uppercase tracking-widest text-zinc-600">WHAT KZ WANTS TO DO</div>
                          <p className="mt-1 text-xs leading-relaxed text-zinc-300">${step?.output?.message || step?.output?.browser_plan?.summary || step?.title || "A consequential action is ready."}</p>
                        </div>
                        <div className="mt-2 grid grid-cols-2 gap-2 text-[9px] font-mono-tech uppercase tracking-wider">
                          <div className="rounded border border-white/5 bg-white/[0.02] p-2"><span className="text-zinc-600">RISK</span><div className="mt-1 text-amber-300">${step?.risk || workflow.risk}</div></div>
                          <div className="rounded border border-white/5 bg-white/[0.02] p-2"><span className="text-zinc-600">POTENTIAL</span><div className="mt-1 text-zinc-300">$${Number(workflow.potential_revenue || 0).toFixed(0)}</div></div>
                        </div>
                        <div className="mt-2 rounded border border-cyan-400/10 bg-cyan-400/5 p-2">
                          <div className="text-[9px] uppercase tracking-widest text-cyan-300">APPROVAL SCOPE</div>
                          <div className="mt-1 text-[10px] leading-relaxed text-zinc-400">Approve only the exact prepared action plan. If the plan changes, it must be prepared and approved again.</div>
                        </div>
                        <div className="mt-2 text-[9px] leading-relaxed text-zinc-600">Approval is bound to this workflow/action plan. Rejecting stops this workflow; KZ will not silently approve or change the action behind your approval.</div>
                        <div className="mt-3 flex gap-2">
                          <button type="button" onClick={() => approve(workflow.id, true)} className="flex-1 rounded-lg border border-emerald-400/25 bg-emerald-400/10 py-2 font-mono-tech text-[9px] tracking-widest text-emerald-200">APPROVE EXACT PLAN</button>
                          <button type="button" onClick={() => approve(workflow.id, false)} className="flex-1 rounded-lg border border-red-400/20 bg-red-400/5 py-2 font-mono-tech text-[9px] tracking-widest text-red-300">REJECT</button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </aside>
        </>
      )}
    </>
  );
}
