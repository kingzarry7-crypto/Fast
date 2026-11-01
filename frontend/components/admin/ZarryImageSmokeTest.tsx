"use client";
import { useState } from "react";
import { api, ApiError, type AdminImageGenerationSmokeTest } from "@/lib/api";

export default function ZarryImageSmokeTest() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AdminImageGenerationSmokeTest | null>(null);
  const [error, setError] = useState("");
  async function run() {
    if (busy || result) return;
    if (!window.confirm("This consumes the one-time image test and may reserve up to $0.01. Continue?")) return;
    setBusy(true);
    setError("");
    try { setResult(await api.adminImageGenerationSmokeTest()); }
    catch (e) { setError(e instanceof ApiError ? e.detail || e.message : "Test failed; the one-time lock may be consumed."); }
    finally { setBusy(false); }
  }
  return <section className="kz-panel p-6">
    <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/50 mb-2">ZARRY · ONE-TIME IMAGE TEST</p>
    <p className="text-xs text-cyan-100/60 mb-4">Admin-only, one-time provider smoke test. Maximum $0.01 reservation. Public image generation remains disabled.</p>
    <button type="button" onClick={run} disabled={busy || !!result} className="px-4 py-2 rounded-lg bg-cyan-400 text-black text-xs font-bold tracking-widest disabled:opacity-40">{busy ? "GENERATING…" : result ? "TEST USED" : "RUN ONE-TIME IMAGE TEST"}</button>
    {result && <div className="mt-4 text-xs font-mono-tech text-emerald-200"><p>Generation passed · public retrieval {result.public_retrieval}</p><a className="underline break-all" href={result.image_url} target="_blank" rel="noreferrer">Open generated image</a></div>}
    {error && <p role="alert" className="mt-4 text-xs text-amber-200">{error}</p>}
  </section>;
}
