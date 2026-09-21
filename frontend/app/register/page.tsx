"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import AICore from "@/components/AICore";
import { useAuth } from "@/hooks/useAuth";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await register(email, password, username, displayName);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="kz-panel w-full max-w-md p-8">
        <div className="flex flex-col items-center mb-8">
          <AICore state={loading ? "thinking" : "idle"} size={160} />
          <h1 className="text-2xl font-bold text-white kz-glow-text mt-10">
            CREATE ACCOUNT
          </h1>
          <p className="text-[10px] font-mono text-cyan-400/50 tracking-[0.4em] mt-2">
            KING ZARRY AI
          </p>
        </div>

        {error && (
          <div className="mb-4 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-2 text-xs text-red-300 font-mono">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[10px] font-mono text-cyan-400/50 tracking-widest mb-1.5">
              EMAIL
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              className="w-full bg-[#031322]/80 border border-cyan-500/20 focus:border-cyan-500/50 rounded-lg px-4 py-3 text-sm text-white outline-none transition-colors"
            />
          </div>
          <div>
            <label className="block text-[10px] font-mono text-cyan-400/50 tracking-widest mb-1.5">
              PASSWORD
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              className="w-full bg-[#031322]/80 border border-cyan-500/20 focus:border-cyan-500/50 rounded-lg px-4 py-3 text-sm text-white outline-none transition-colors"
            />
            <p className="text-[9px] font-mono text-cyan-400/30 mt-1">
              Minimum 8 characters
            </p>
          </div>
          <div>
            <label className="block text-[10px] font-mono text-cyan-400/50 tracking-widest mb-1.5">
              USERNAME (OPTIONAL)
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-[#031322]/80 border border-cyan-500/20 focus:border-cyan-500/50 rounded-lg px-4 py-3 text-sm text-white outline-none transition-colors"
            />
          </div>
          <div>
            <label className="block text-[10px] font-mono text-cyan-400/50 tracking-widest mb-1.5">
              DISPLAY NAME (OPTIONAL)
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full bg-[#031322]/80 border border-cyan-500/20 focus:border-cyan-500/50 rounded-lg px-4 py-3 text-sm text-white outline-none transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-lg bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 text-xs font-mono tracking-widest hover:bg-cyan-500/30 transition-all disabled:opacity-50"
          >
            {loading ? "CREATING..." : "REGISTER"}
          </button>
        </form>

        <p className="text-center text-xs text-cyan-400/40 mt-6">
          Already have an account?{" "}
          <Link href="/login" className="text-cyan-400 hover:text-cyan-300">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
