"use client";

import { useState } from "react";
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
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden flex items-center justify-center p-6">
      <HeroRings size={720} />

      <div className="relative z-10 w-full max-w-md">
        <div className="flex flex-col items-center mb-4">
          <AICore state={loading ? "thinking" : "idle"} size={220} />
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
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/60 mb-2">
                EMAIL
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="w-full bg-black/40 border border-cyan-500/25 focus:border-cyan-400 rounded-md px-4 py-3 text-sm text-white outline-none transition-colors font-mono-tech tracking-wider"
              />
            </div>
            <div>
              <label className="block font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/60 mb-2">
                PASSWORD
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                className="w-full bg-black/40 border border-cyan-500/25 focus:border-cyan-400 rounded-md px-4 py-3 text-sm text-white outline-none transition-colors font-mono-tech tracking-wider"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-md bg-cyan-400 text-black font-display font-bold text-xs tracking-[0.3em] shadow-[0_0_25px_rgba(0,240,255,0.5)] hover:bg-cyan-300 hover:shadow-[0_0_40px_rgba(0,240,255,0.7)] transition-all disabled:opacity-50 disabled:shadow-none"
            >
              {loading ? "AUTHENTICATING..." : "SIGN IN"}
            </button>
          </form>
        </div>

        <p className="text-center font-mono-tech text-[10px] tracking-widest text-cyan-400/40 mt-6">
          NO ACCOUNT?{" "}
          <Link
            href="/register"
            className="text-cyan-400 hover:text-cyan-300 kz-glow-soft"
          >
            REGISTER
          </Link>
        </p>
      </div>
    </div>
  );
}
