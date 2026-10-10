"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import AICore from "@/components/AICore";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [booted, setBooted] = useState(false);

  useEffect(() => {
    const unlock = () => {
      setBooted(true);
      window.removeEventListener("click", unlock);
      window.removeEventListener("touchstart", unlock);
      window.removeEventListener("keydown", unlock);
    };
    window.addEventListener("click", unlock);
    window.addEventListener("touchstart", unlock);
    window.addEventListener("keydown", unlock);
    return () => {
      window.removeEventListener("click", unlock);
      window.removeEventListener("touchstart", unlock);
      window.removeEventListener("keydown", unlock);
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email.trim(), password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const verificationRequired = error?.toLowerCase().includes("not verified") ?? false;

  return (
    <main className="relative isolate flex min-h-[100dvh] items-center justify-center overflow-hidden bg-transparent px-5 py-10 text-[#dff7ff]">
      <div aria-hidden="true" className="kz-auth-cosmic-surface" />

      <div className="relative z-10 w-full max-w-[420px]">

        <div className="flex flex-col items-center text-center">
          <div className="relative">
            <div className="absolute inset-0 scale-125 rounded-full bg-cyan-400/10 blur-3xl" />
            <AICore state={loading ? "thinking" : "idle"} size={190} bootSound={booted} />
          </div>
          <h1 className="mt-5 font-display text-3xl font-bold tracking-[0.12em] text-[#dff7ff] drop-shadow-[0_0_24px_rgba(56,214,255,.35)] sm:text-4xl">
            KING ZARRY <span className="text-[#f2c76b]">AI</span>
          </h1>
          <p className="mt-3 font-mono-tech text-[9px] tracking-[0.42em] text-cyan-200/55">
            YOUR TRADING & INTELLIGENCE ASSISTANT
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            {["SMART MEMORY", "LIVE INTELLIGENCE", "AI WORKFLOWS"].map((item) => (
              <span key={item} className="rounded-full border border-cyan-200/15 bg-[#08162f]/60 px-3 py-1.5 font-mono-tech text-[8px] tracking-[0.16em] text-cyan-100/65">
                {item}
              </span>
            ))}
          </div>
        </div>

        <section className="mt-8 rounded-[22px] border border-cyan-300/20 bg-[linear-gradient(145deg,rgba(8,22,47,.88),rgba(4,11,26,.82))] p-5 shadow-[0_24px_90px_rgba(0,0,0,.45),0_0_35px_rgba(56,214,255,.08)] backdrop-blur-2xl sm:p-7">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="font-display text-sm font-bold tracking-[0.18em] text-white">SECURE ACCESS</h2>
              <p className="mt-1 font-mono-tech text-[9px] tracking-widest text-cyan-200/40">SIGN IN TO YOUR COMMAND CENTRE</p>
            </div>
            <span className="flex items-center gap-2 rounded-full border border-emerald-300/15 bg-emerald-300/5 px-2.5 py-1.5 font-mono-tech text-[8px] tracking-widest text-emerald-200/80">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_10px_rgba(110,231,183,.8)]" /> SECURE
            </span>
          </div>

          {error && (
            <div role="alert" className="mb-4 rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">
              <span>{error}</span>
              {verificationRequired && (
                <Link href={`/verify-email?email=${encodeURIComponent(email.trim().toLowerCase())}`} className="ml-2 underline text-cyan-200 hover:text-white">
                  Verify email
                </Link>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="login-email" className="mb-2 block font-mono-tech text-[10px] tracking-[0.25em] text-cyan-100/60">EMAIL ADDRESS</label>
              <input id="login-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" placeholder="you@example.com" className="w-full rounded-xl border border-cyan-100/15 bg-[#040b1a]/75 px-4 py-3.5 text-base text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/70 focus:ring-2 focus:ring-cyan-300/10" />
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between gap-3">
                <label htmlFor="login-password" className="block font-mono-tech text-[10px] tracking-[0.25em] text-cyan-100/60">PASSWORD</label>
                <Link href="/forgot-password" className="text-[10px] text-cyan-200/70 hover:text-cyan-100">Forgot password?</Link>
              </div>
              <div className="relative">
                <input id="login-password" type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" placeholder="Enter your password" className="w-full rounded-xl border border-cyan-100/15 bg-[#040b1a]/75 px-4 py-3.5 pr-20 text-base text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/70 focus:ring-2 focus:ring-cyan-300/10" />
                <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword} className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg px-2 py-2 text-[10px] text-cyan-200/70 hover:bg-cyan-300/10 hover:text-white">
                  {showPassword ? "HIDE" : "SHOW"}
                </button>
              </div>
            </div>
            <button type="submit" disabled={loading} className="w-full rounded-xl bg-[linear-gradient(110deg,#38d6ff,#63a7ff)] px-4 py-3.5 font-display text-xs font-bold tracking-[0.24em] text-[#021024] shadow-[0_0_28px_rgba(56,214,255,.22)] transition hover:brightness-110 active:scale-[.99] disabled:cursor-wait disabled:opacity-60">
              {loading ? "AUTHENTICATING…" : "ENTER COMMAND CENTRE"}
            </button>
          </form>
          <p className="mt-4 text-center text-xs leading-relaxed text-slate-400">Your account and connected services stay protected by your real sign-in session.</p>
        </section>

        <div className="mt-5 flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-[10px] tracking-widest text-cyan-100/50">
          <Link href="/register" className="hover:text-cyan-100">CREATE ACCOUNT</Link>
          <span className="text-cyan-100/20">•</span>
          <Link href="/verify-email" className="hover:text-cyan-100">VERIFY EMAIL</Link>
          <span className="text-cyan-100/20">•</span>
          <Link href="/" className="hover:text-cyan-100">HOME</Link>
        </div>
        <p className="mt-6 text-center font-mono-tech text-[8px] tracking-[0.24em] text-cyan-100/25">KING ZARRY AI · AUTHENTICATED ACCESS ONLY</p>
      </div>

    </main>
  );
}
