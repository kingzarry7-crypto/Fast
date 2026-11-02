"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type AdminImageGenerationSmokeTest } from "@/lib/api";

type SmokeStatus = {
  status: "not_run" | "failed" | "ok" | string;
  request_id?: string | null;
  provider?: string | null;
  error_type?: string | null;
  failure_stage?: string | null;
  http_status_code?: number | null;
  completed_at?: string | null;
};

export default function ZarryImageSmokeTest() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AdminImageGenerationSmokeTest | null>(null);
  const [diagnostic, setDiagnostic] = useState<SmokeStatus | null>(null);
  const [statusBusy, setStatusBusy] = useState(true);
  const [error, setError] = useState("");
  const [statusError, setStatusError] = useState("");

  const refreshStatus = useCallback(async () => {
    setStatusBusy(true);
    setStatusError("");
    try {
      const response = await fetch("/api/assistant/admin/image-generation-smoke-status", {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "include",
        cache: "no-store",
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        const message = data && typeof data.detail === "string" ? data.detail : `Could not read image test status (HTTP ${response.status}).`;
        throw new Error(message);
      }
      setDiagnostic(data as SmokeStatus);
    } catch (e) {
      setStatusError(e instanceof Error ? e.message : "Could not read image test status.");
      setDiagnostic(null);
    } finally {
      setStatusBusy(false);
    }
  }, []);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  async function run() {
    if (busy || statusBusy || statusError || !diagnostic || diagnostic.status !== "not_run") return;
    if (!window.confirm("This consumes the one-time image smoke test and may reserve up to $0.01. Continue?")) return;
    setBusy(true);
    setError("");
    try {
      setResult(await api.adminImageGenerationSmokeTest());
      await refreshStatus();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail || e.message : "Test failed; the one-time lock may be consumed.");
      await refreshStatus();
    } finally {
      setBusy(false);
    }
  }

  const alreadyUsed = diagnostic !== null && diagnostic.status !== "not_run";

  return <section className="kz-panel p-6">
    <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/50 mb-2">ZARRY · ONE-TIME IMAGE TEST</p>
    <p className="text-xs text-cyan-100/60 mb-4">Admin-only, one-time provider smoke test. Maximum $0.01 reservation. Public image generation remains disabled.</p>

    <div className="mb-4 rounded-lg border border-cyan-400/15 bg-black/20 p-3 text-xs">
      <div className="flex items-center justify-between gap-3 mb-2">
        <span className="text-cyan-100/70">Saved test record</span>
        <button type="button" onClick={() => void refreshStatus()} disabled={statusBusy} className="underline text-cyan-300 disabled:opacity-40">
          {statusBusy ? "Checking…" : "Refresh"}
        </button>
      </div>
      {statusBusy && <p className="text-cyan-100/50">Reading the saved result…</p>}
      {statusError && <p role="alert" className="text-amber-200">{statusError} The test is locked until its status can be verified.</p>}
      {!statusBusy && !statusError && diagnostic?.status === "not_run" && <p className="text-cyan-200">Not used — one-time test is available.</p>}
      {!statusBusy && !statusError && diagnostic && diagnostic.status !== "not_run" && (
        <div className="space-y-1 text-cyan-100/80">
          <p>Result: <strong className={diagnostic.status === "ok" ? "text-emerald-300" : "text-amber-200"}>{diagnostic.status}</strong></p>
          {diagnostic.provider && <p>Provider: {diagnostic.provider}</p>}
          {diagnostic.request_id && <p>Request ID: {diagnostic.request_id}</p>}
          {diagnostic.error_type && <p>Error type: <strong>{diagnostic.error_type}</strong></p>}
          {diagnostic.failure_stage && <p>Failure stage: <strong>{diagnostic.failure_stage}</strong></p>}
          {diagnostic.http_status_code && <p>Provider HTTP status: {diagnostic.http_status_code}</p>}
          {diagnostic.completed_at && <p>Completed: {diagnostic.completed_at}</p>}
          <p className="pt-1 text-amber-200/80">The one-time lock is consumed. This panel will not retry it.</p>
        </div>
      )}
    </div>

    <button type="button" onClick={run} disabled={busy || statusBusy || !!statusError || !diagnostic || diagnostic.status !== "not_run" || !!result} className="px-4 py-2 rounded-lg bg-cyan-400 text-black text-xs font-bold tracking-widest disabled:opacity-40">
      {busy ? "GENERATING…" : alreadyUsed || result ? "TEST USED" : statusBusy ? "CHECKING STATUS…" : statusError ? "STATUS UNAVAILABLE" : "RUN ONE-TIME IMAGE TEST"}
    </button>
    {result && <div className="mt-4 text-xs font-mono-tech text-emerald-200"><p>Generation passed · public retrieval {result.public_retrieval}</p><a className="underline break-all" href={result.image_url} target="_blank" rel="noreferrer">Open generated image</a></div>}
    {error && <p role="alert" className="mt-4 text-xs text-amber-200">{error}</p>}
  </section>;
}
