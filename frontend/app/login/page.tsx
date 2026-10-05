"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import AICore from "@/components/AICore";
import HeroRings from "@/components/HeroRings";
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
      await login(email, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const verificationRequired = error?.toLowerCase().includes("not verified") ?? false;

  return (
    <div className="relative min-h-screen overflow-hidden flex items-center justify-center p-6">
      <HeroRings size={720} />

      <div className="relative z-10 w-full max-w-md">
        <div className="flex flex-col items-center mb-4">
          <AICore state={loading ? "thinking" : "idle"} size={220} bootSound={booted} />
          <h1 className="font-display text-2xl font-bold text-white kz-glow-text mt-12 tracking-wider">
            KING ZARRY AI
          </h1>
          <p className="font-mono-tech text-[10px] tracking-[0.5em] text-cyan-400/50 mt-3">
            SECURE ACCESS
          </p>
        </div>

        <div className="kz-glass p-6 mt-8">
          {error && (
            <div className="mb-4 bg-red-500/10 border border-red-500/30 rounded-md px-4 py-2 text-xs text-red-300 font-mono-tech">
              <span>{error}</span>
              {verificationRequired && (
                <Link
                  href={`/verify-email?email=${encodeURIComponent(email.trim().toLowerCase())}`}
                  className="ml-2 underline text-cyan-300 hover:text-cyan-200"
                >
                  VERIFY EMAIL
                </Link>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="login-email"
                className="block font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/60 mb-2"
              >
                EMAIL
              </label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="w-full bg-black/40 border border-cyan-500/25 focus:border-cyan-400 rounded-md px-4 py-3 text-sm text-white outline-none font-mono-tech tracking-wider"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label
                  htmlFor="login-password"
                  className="block font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/60"
                >
                  PASSWORD
                </label>
                <Link
                  href="/forgot-password"
                  className="font-mono-tech text-[10px] tracking-widest text-cyan-400 hover:text-cyan-300"
                >
                  FORGOT PASSWORD?
                </Link>
              </div>

              <div className="relative">
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="w-full bg-black/40 border border-cyan-500/25 focus:border-cyan-400 rounded-md pl-4 pr-14 py-3 text-sm text-white outline-none font-mono-tech tracking-wider"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                  className="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1.5 rounded text-[10px] font-mono-tech text-cyan-400/80 hover:text-cyan-300 hover:bg-cyan-500/10 transition-colors"
                >
                  {showPassword ? (
                    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 3l18 18M10.58 10.58a3 3 0 004.24 4.24M9.88 4.24A10.94 10.94 0 0112 4c5 0 9.27 3.11 11 8a11.02 11.02 0 01-3.18 4.75M6.1 6.1A11.02 11.02 0 003 12c1.73 4.89 6 8 11 8 1.1 0 2.17-.16 3.17-.46" />
                    </svg>
                  ) : (
                    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M2.46 12S5.5 5 12 5s9.54 7 9.54 7-3.04 7-9.54 7-9.54-7-9.54-7z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-md bg-cyan-400 text-black font-display font-bold text-xs tracking-[0.3em] shadow-[0_0_25px_rgba(0,240,255,0.5)] hover:bg-cyan-300 transition-all disabled:opacity-50"
            >
              {loading ? "AUTHENTICATING..." : "SIGN IN"}
            </button>
          </form>
        </div>

        <p className="text-center font-mono-tech text-[10px] tracking-widest text-cyan-400/40 mt-6 space-x-3">
          <Link href="/register" className="text-cyan-400 hover:text-cyan-300">
            REGISTER
          </Link>
          <span className="text-cyan-500/30">·</span>
          <Link href="/forgot-password" className="text-cyan-400 hover:text-cyan-300">
            FORGOT PASSWORD
          </Link>
          <span className="text-cyan-500/30">·</span>
          <Link href="/verify-email" className="text-cyan-400 hover:text-cyan-300">
            VERIFY EMAIL
          </Link>
        </p>
      </div>
    </div>
  );
}
