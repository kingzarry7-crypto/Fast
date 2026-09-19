"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

export default function RegisterPage() {
  const router = useRouter();
  const { signUp } = useAuth();
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
      await signUp(email, password, username, displayName);
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
        <div className="text-center mb-8">
          <h1 className="text-xl font-bold text-white">CREATE ACCOUNT</h1>
          <p className="text-[10px] font-mono text-cyan-400/50 tracking-widest mt-1">
            KING ZARRY AI
          </p>
        </div>

        {error && (
          <div className="mb-4 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-2 text-xs text-red-300 font-mono">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {[
            { label: "EMAIL", value: email, set: setEmail, type: "email", required: true },
            { label: "PASSWORD", value: password, set: setPassword, type: "password", required: true },
            { label: "USERNAME (OPTIONAL)", value: username, set: setUsername, type: "text", required: false },
            { label: "DISPLAY NAME (OPTIONAL)", value: displayName, set: setDisplayName, type: "text", required: false },
          ].map((f) => (
            <div key={f.label}>
              <label className="block text-[10px] font-mono text-cyan-400/50 tracking-widest mb-1.5">
                {f.label}
              </label>
              <input
                type={f.type}
                value={f.value}
                onChange={(e) => f.set(e.target.value)}
                required={f.required}
                className="w-full bg-[#031322]/80 border border-cyan-500/20 focus:border-cyan-500/50 rounded-lg px-4 py-3 text-sm text-white outline-none transition-colors"
              />
            </div>
          ))}
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
