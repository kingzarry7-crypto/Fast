"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import AICore from "@/components/AICore";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || loading) return;
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      const result = await api.forgotPassword(email.trim());
      setInfo(result.message || "If an account matches that email, a reset code will be sent.");
      window.setTimeout(() => {
        window.location.assign(`/reset-password?email=${encodeURIComponent(email.trim())}`);
      }, 1200);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not request a reset code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="relative isolate flex min-h-[100dvh] items-center justify-center overflow-hidden bg-[#040b1a] px-5 py-10 text-[#dff7ff]">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_25%_25%,rgba(56,214,255,.16),transparent_35%),radial-gradient(ellipse_at_80%_75%,rgba(120,90,255,.12),transparent_38%)]" />
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center text-center">
          <AICore state={loading ? "thinking" : "idle"} size={150} />
          <p className="mt-3 font-mono-tech text-[9px] tracking-[0.35em] text-cyan-200/50">ACCOUNT RECOVERY</p>
          <h1 className="mt-3 font-display text-2xl font-bold tracking-[0.12em] text-white">RESET PASSWORD</h1>
          <p className="mt-3 max-w-sm text-sm leading-6 text-cyan-50/55">Enter the email address associated with your King Zarry AI account. If the account exists, we’ll send instructions to reset your password.</p>
        </div>

        <form onSubmit={onSubmit} className="mt-7 space-y-4 rounded-[22px] border border-cyan-300/20 bg-[linear-gradient(145deg,rgba(8,22,47,.9),rgba(4,11,26,.86))] p-5 shadow-[0_24px_90px_rgba(0,0,0,.4)] backdrop-blur-2xl sm:p-7">
          <label htmlFor="recovery-email" className="block font-mono-tech text-[10px] tracking-[0.22em] text-cyan-100/60">ACCOUNT EMAIL</label>
          <input id="recovery-email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className="w-full rounded-xl border border-cyan-100/15 bg-[#040b1a]/75 px-4 py-3.5 text-base text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/70 focus:ring-2 focus:ring-cyan-300/10" />
          {error && <p role="alert" className="rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</p>}
          {info && <p role="status" className="rounded-xl border border-emerald-300/20 bg-emerald-300/5 px-4 py-3 text-sm text-emerald-100/80">{info}</p>}
          <button type="submit" disabled={loading} className="w-full rounded-xl bg-[linear-gradient(110deg,#38d6ff,#63a7ff)] px-4 py-3.5 font-display text-xs font-bold tracking-[0.2em] text-[#021024] transition hover:brightness-110 disabled:cursor-wait disabled:opacity-60">
            {loading ? "REQUESTING RESET…" : "SEND RESET INSTRUCTIONS"}
          </button>
          <Link href="/login" className="block rounded-xl border border-cyan-100/15 px-4 py-3 text-center text-xs text-cyan-100/65 transition hover:bg-cyan-300/5 hover:text-white">Back to sign in</Link>
        </form>
        <p className="mt-5 text-center font-mono-tech text-[8px] tracking-[0.2em] text-cyan-100/25">KING ZARRY AI · SECURE ACCOUNT RECOVERY</p>
      </div>
    </main>
  );
}
