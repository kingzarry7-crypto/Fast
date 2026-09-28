"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const r = await api.forgotPassword(email);
      setInfo(
        r.dev_code
          ? `${r.message} Dev code: ${r.dev_code}`
          : r.message || "Check your email for a code."
      );
      setTimeout(() => {
        router.push(`/reset-password?email=${encodeURIComponent(email.trim())}`);
      }, 1200);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[#020914]">
      <form onSubmit={onSubmit} className="kz-panel w-full max-w-md p-8 space-y-4">
        <h1 className="font-display text-xl font-bold text-white tracking-wider">
          Forgot password
        </h1>
        <p className="text-sm text-cyan-400/60">
          We will email a 6-digit reset code if the account exists.
        </p>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Your account email"
          className="w-full rounded-lg bg-black/40 border border-cyan-500/25 px-3 py-2 text-sm text-white"
        />
        {error && <p className="text-sm text-amber-200">{error}</p>}
        {info && <p className="text-sm text-cyan-200/80">{info}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 rounded-lg bg-cyan-400 text-black text-xs font-bold tracking-widest disabled:opacity-40"
        >
          {loading ? "SENDING…" : "SEND RESET CODE"}
        </button>
        <Link href="/login" className="block text-center text-xs text-cyan-400/50">
          Back to login
        </Link>
      </form>
    </div>
  );
}
