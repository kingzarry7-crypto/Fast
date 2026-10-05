"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import AICore from "@/components/AICore";
import HeroRings from "@/components/HeroRings";
import { useAuth } from "@/hooks/useAuth";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await register(email, password, username, displayName);
      if (result.requires_verification) {
        router.replace(`/verify-email?email=${encodeURIComponent(email.trim().toLowerCase())}`);
        return;
      }
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden flex items-center justify-center p-6">
      <HeroRings size={720} color="#8b5cf6" />

      <div className="relative z-10 w-full max-w-md">
        <div className="flex flex-col items-center mb-4">
          <AICore state={loading ? "thinking" : "idle"} size={180} />
          <h1 className="font-display text-2xl font-bold text-white kz-glow-text mt-12 tracking-wider">
            CREATE ACCOUNT
          </h1>
          <p className="font-mono-tech text-[10px] tracking-[0.5em] text-cyan-400/50 mt-3">
            KING ZARRY AI
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
              <div className="relative">
                <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
                className="w-full bg-black/40 border border-cyan-500/25 focus:border-cyan-400 rounded-md pl-4 pr-12 py-3 text-sm text-white outline-none transition-colors font-mono-tech tracking-wider"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-cyan-400/80 hover:text-cyan-300 transition-colors"
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
              <p className="font-mono-tech text-[9px] tracking-widest text-cyan-400/30 mt-1.5">
                MIN 8 CHARACTERS
              </p>
            </div>
            <div>
              <label className="block font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/60 mb-2">
                USERNAME (OPTIONAL)
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-black/40 border border-cyan-500/25 focus:border-cyan-400 rounded-md px-4 py-3 text-sm text-white outline-none transition-colors font-mono-tech tracking-wider"
              />
            </div>
            <div>
              <label className="block font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/60 mb-2">
                DISPLAY NAME (OPTIONAL)
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full bg-black/40 border border-cyan-500/25 focus:border-cyan-400 rounded-md px-4 py-3 text-sm text-white outline-none transition-colors font-mono-tech tracking-wider"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-md bg-cyan-400 text-black font-display font-bold text-xs tracking-[0.3em] shadow-[0_0_25px_rgba(0,240,255,0.5)] hover:bg-cyan-300 hover:shadow-[0_0_40px_rgba(0,240,255,0.7)] transition-all disabled:opacity-50 disabled:shadow-none"
            >
              {loading ? "CREATING..." : "REGISTER"}
            </button>
          </form>
        </div>

        <p className="text-center font-mono-tech text-[10px] tracking-widest text-cyan-400/40 mt-6">
          ALREADY HAVE ACCESS?{" "}
          <Link
            href="/login"
            className="text-cyan-400 hover:text-cyan-300 kz-glow-soft"
          >
            SIGN IN
          </Link>
        </p>
      </div>
    </div>
  );
}
