"use client";

import { useCallback, useEffect, useState } from "react";

type Workflow = {
  id: string;
  goal: string;
  status: string;
};

type Delivery = {
  delivery_id: string;
  package_name: string;
  status: string;
  approval_required: boolean;
  verification?: { qa_passed?: boolean; explicit_verification?: boolean; missing_checks?: string[] };
  deliverables?: Array<{ name: string; status: string; description: string }>;
  handoff?: { summary?: string; next_steps?: string[]; send_status?: string };
};

export default function DeliveryPanel() {
  const [open, setOpen] = useState(false);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [selected, setSelected] = useState<Delivery | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const r = await fetch("/api/workflows", { credentials: "include" });
      if (!r.ok) return;
      const data = await r.json();
      setWorkflows((data.workflows || []).filter((w: Workflow) => w.status === "completed"));
    } catch {}
  }, []);

  useEffect(() => {
    if (!open) return;
    load();
  }, [open, load]);

  async function prepare(workflowId: string) {
    setLoading(true);
    setError("");
    try {
      const r = await fetch("/api/delivery/package", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow_id: workflowId }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Could not prepare delivery");
      setSelected(data.delivery);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not prepare delivery");
    } finally {
      setLoading(false);
    }
  }

  async function verify() {
    if (!selected || loading) return;
    setLoading(true);
    setError("");
    try {
      const r = await fetch("/api/delivery/verify", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          delivery: selected,
          checks: { deliverables_reviewed: true, result_checked: true },
        }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Verification failed");
      setSelected(data.delivery);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button type="button" onClick={() => setOpen(true)}
        className="rounded-md border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-1.5 font-mono-tech text-[10px] tracking-widest text-emerald-200 hover:bg-emerald-400/20 shrink-0">
        DELIVERY
      </button>

      {open && (
        <>
          <button type="button" aria-label="Close Delivery" onClick={() => setOpen(false)}
            className="fixed inset-0 z-[70] bg-black/60 backdrop-blur-[2px]" />
          <aside className="fixed right-0 top-0 z-[80] flex h-[100dvh] w-full max-w-md flex-col border-l border-emerald-400/20 bg-[#060811] shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
              <div>
                <div className="font-mono-tech text-xs tracking-[0.22em] text-emerald-200">DELIVERY AGENT</div>
                <div className="mt-1 text-[10px] text-zinc-500">Prepare, QA and package completed work. Nothing is sent automatically.</div>
              </div>
              <button type="button" onClick={() => setOpen(false)} className="rounded-md px-2 py-1 text-zinc-500 hover:bg-white/5">×</button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto p-3">
              {selected ? (
                <div className="space-y-3">
                  <button type="button" onClick={() => setSelected(null)} className="text-[10px] font-mono-tech tracking-widest text-zinc-500 hover:text-zinc-300">← BACK TO COMPLETED WORK</button>
                  <div className="rounded-xl border border-white/5 bg-white/[0.025] p-3">
                    <div className="text-sm text-zinc-200">{selected.package_name}</div>
                    <div className="mt-2 font-mono-tech text-[9px] uppercase tracking-wider text-zinc-500">status: {selected.status.replaceAll("_", " ")}</div>
                  </div>

                  <div className="rounded-xl border border-white/5 bg-white/[0.025] p-3">
                    <div className="font-mono-tech text-[9px] tracking-widest text-emerald-300">DELIVERABLES</div>
                    <div className="mt-2 space-y-2">
                      {(selected.deliverables || []).map((item) => (
                        <div key={item.name} className="rounded-lg border border-white/5 p-2">
                          <div className="text-xs text-zinc-200">{item.name}</div>
                          <div className="mt-1 text-[10px] text-zinc-600">{item.status.replaceAll("_", " ")}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {selected.verification?.qa_passed ? (
                    <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/5 p-3 text-xs text-emerald-200">
                      QA PASSED — ready for explicit handoff approval.
                    </div>
                  ) : (
                    <button type="button" disabled={loading} onClick={verify}
                      className="w-full rounded-xl border border-amber-400/25 bg-amber-400/10 py-2.5 font-mono-tech text-[9px] tracking-widest text-amber-200 disabled:opacity-40">
                      {loading ? "VERIFYING..." : "RUN DELIVERY QA"}
                    </button>
                  )}

                  <div className="rounded-xl border border-white/5 bg-white/[0.025] p-3 text-[10px] text-zinc-500">
                    External client delivery remains <span className="text-amber-300">DRAFT ONLY</span> until you explicitly approve the handoff.
                  </div>
                </div>
              ) : (
                <>
                  {!workflows.length && <p className="px-2 py-8 text-center text-xs text-zinc-600">No completed work is ready for delivery.</p>}
                  {workflows.map((w) => (
                    <div key={w.id} className="mb-3 rounded-xl border border-white/5 bg-white/[0.025] p-3">
                      <p className="text-sm text-zinc-200">{w.goal}</p>
                      <button type="button" disabled={loading} onClick={() => prepare(w.id)}
                        className="mt-3 w-full rounded-lg border border-emerald-400/25 bg-emerald-400/10 py-2 font-mono-tech text-[9px] tracking-widest text-emerald-200 disabled:opacity-40">
                        {loading ? "PREPARING..." : "PREPARE DELIVERY"}
                      </button>
                    </div>
                  ))}
                </>
              )}
              {error && <p className="mt-3 text-xs text-red-400">{error}</p>}
            </div>
          </aside>
        </>
      )}
    </>
  );
}
