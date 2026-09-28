"use client";

import { FormEvent, useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";

function ResetForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState(params.get("email") || "");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !code.trim() || password.length < 8 || loading) return;
    setLoading(true);
    setError(null);
    try {
      await api.resetPassword(email, code, password);
      router.replace("/login?reset=1");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail || err.message : "Reset failed"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[#020914]">
      <form onSubmit={onSubmit} className="kz-panel w-full max-w-md p-8 space-y-4">
        <h1 className="font-display text-xl font-bold text-white tracking-wider">
          Reset password
        </h1>
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
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="6-digit code"
          className="w-full rounded-lg bg-black/40 border border-cyan-500/25 px-3 py-2 text-sm text-white tracking-[0.3em]"
        />
        <input
          type="password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="New password (min 8)"
          className="w-full rounded-lg bg-black/40 border border-cyan-500/25 px-3 py-2 text-sm text-white"
        />
        {error && <p className="text-sm text-amber-200">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 rounded-lg bg-cyan-400 text-black text-xs font-bold tracking-widest disabled:opacity-40"
        >
          {loading ? "SAVING…" : "UPDATE PASSWORD"}
        </button>
        <Link href="/login" className="block text-center text-xs text-cyan-400/50">
          Back to login
        </Link>
      </form>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetForm />
    </Suspense>
  );
}
