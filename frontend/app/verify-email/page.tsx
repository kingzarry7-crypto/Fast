"use client";

import { FormEvent, useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

function VerifyForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { refresh } = useAuth();
  const [email, setEmail] = useState(params.get("email") || "");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !code.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      await api.verifyEmail(email, code);
      await refresh();
      router.replace("/chat");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail || err.message : "Verification failed"
      );
    } finally {
      setLoading(false);
    }
  };

  const onResend = async () => {
    if (!email.trim() || resending) return;
    setResending(true);
    setError(null);
    try {
      const r = await api.resendVerification(email);
      setInfo(
        r.dev_code
          ? `${r.message || "Code sent."} Dev code: ${r.dev_code}`
          : r.message || "If eligible, a new code was sent."
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not resend");
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[#020914]">
      <form onSubmit={onSubmit} className="kz-panel w-full max-w-md p-8 space-y-4">
        <h1 className="font-display text-xl font-bold text-white tracking-wider">
          Verify email
        </h1>
        <p className="text-sm text-cyan-400/60">
          Enter the 6-digit code we sent to your inbox.
        </p>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          className="w-full rounded-lg bg-black/40 border border-cyan-500/25 px-3 py-2 text-sm text-white"
        />
        <input
          type="text"
          required
          inputMode="numeric"
          maxLength={12}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="6-digit code"
          className="w-full rounded-lg bg-black/40 border border-cyan-500/25 px-3 py-2 text-sm text-white tracking-[0.3em]"
        />
        {error && <p className="text-sm text-amber-200">{error}</p>}
        {info && <p className="text-sm text-cyan-200/80">{info}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 rounded-lg bg-cyan-400 text-black text-xs font-bold tracking-widest disabled:opacity-40"
        >
          {loading ? "VERIFYING…" : "VERIFY & LOGIN"}
        </button>
        <button
          type="button"
          onClick={onResend}
          disabled={resending}
          className="w-full py-2 text-[10px] font-mono-tech tracking-widest text-cyan-400/70"
        >
          {resending ? "SENDING…" : "RESEND CODE"}
        </button>
        <Link href="/login" className="block text-center text-xs text-cyan-400/50">
          Back to login
        </Link>
      </form>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <VerifyForm />
    </Suspense>
  );
}
