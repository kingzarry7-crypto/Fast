"use client";
import { useState } from "react";
import { api, ApiError, type AdminImageGenerationSmokeTest, type AdminImageStorageTest } from "@/lib/api";

export default function ZarryImageSmokeTest() {
  const [storageBusy, setStorageBusy] = useState(false);
  const [storageResult, setStorageResult] = useState<AdminImageStorageTest | null>(null);
  const [storageError, setStorageError] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AdminImageGenerationSmokeTest | null>(null);
  const [error, setError] = useState("");

  async function verifyStorage() {
    if (storageBusy || storageResult?.status === "ok") return;
    if (!window.confirm("Run the R2 storage round-trip test? It writes and removes a temporary test object.")) return;
    setStorageBusy(true);
    setStorageError("");
    try { setStorageResult(await api.adminImageStorageTest()); }
    catch (e) { setStorageError(e instanceof ApiError ? e.detail || e.message : "Storage test failed."); }
    finally { setStorageBusy(false); }
  }
  async function run() {
    if (busy || result || storageResult?.status !== "ok") return;
    if (!window.confirm("This consumes the one-time image smoke test and may reserve up to $0.01. Continue?")) return;
    setBusy(true);
    setError("");
    try { setResult(await api.adminImageGenerationSmokeTest()); }
    catch (e) { setError(e instanceof ApiError ? e.detail || e.message : "Test failed; the one-time lock may be consumed."); }
    finally { setBusy(false); }
  }
  return <section className="kz-panel p-6">
    <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/50 mb-2">ZARRY · ONE-TIME IMAGE TEST</p>
    <p className="text-xs text-cyan-100/60 mb-4">Run storage verification first. The one-time provider test reserves at most $0.01. Public image generation remains disabled until an operator records approval after both tests pass.</p>
    <div className="flex flex-wrap gap-2">
      <button type="button" onClick={() => void verifyStorage()} disabled={storageBusy || storageResult?.status === "ok"} className="px-4 py-2 rounded-lg border border-cyan-400/40 text-cyan-100 text-xs font-bold tracking-widest disabled:opacity-40">{storageBusy ? "VERIFYING STORAGE…" : storageResult ? "R2 STORAGE VERIFIED" : "VERIFY R2 STORAGE"}</button>
      <button type="button" onClick={run} disabled={busy || !!result || storageResult?.status !== "ok"} className="px-4 py-2 rounded-lg bg-cyan-400 text-black text-xs font-bold tracking-widest disabled:opacity-40">{busy ? "GENERATING…" : result ? "ONE-TIME TEST USED" : "RUN ONE-TIME IMAGE TEST"}</button>
    </div>
    {storageResult && <p className="mt-3 text-xs font-mono-tech text-emerald-200">R2 upload, public retrieval and cleanup verified{storageResult.public_host ? " · " + storageResult.public_host : ""}.</p>}
    {storageError && <p role="alert" className="mt-3 text-xs text-amber-200">{storageError}</p>}
    {result && <div className="mt-4 text-xs font-mono-tech text-emerald-200"><p>Generation passed · public retrieval {result.public_retrieval}</p><a className="underline break-all" href={result.image_url} target="_blank" rel="noreferrer">Open generated image</a></div>}
    {error && <p role="alert" className="mt-4 text-xs text-amber-200">{error}</p>}
  </section>;
}
