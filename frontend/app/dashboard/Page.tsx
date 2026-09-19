"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import AICore from "@/components/AICore";
import { useAuth } from "@/hooks/useAuth";

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <ProtectedRoute>
      <div className="p-6 lg:p-10 max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-10">
          <p className="text-[10px] font-mono text-cyan-400/50 tracking-[0.4em] mb-2">
            SYSTEM ONLINE
          </p>
          <h1 className="text-3xl font-bold text-white kz-glow-text">
            Command Centre
          </h1>
          <p className="text-sm text-cyan-200/50 mt-1">
            Welcome back{user?.display_name ? `, ${user.display_name}` : ""}.
          </p>
        </div>

        {/* Core */}
        <div className="kz-panel p-10 mb-8 flex flex-col items-center">
          <AICore state="idle" size={180} />
        </div>

        {/* Status grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { label: "AI CORE", value: "ACTIVE", color: "text-emerald-400" },
            { label: "DATABASE", value: "NEON", color: "text-cyan-400" },
            { label: "SESSION", value: user ? "AUTHENTICATED" : "—", color: "text-cyan-400" },
          ].map((s) => (
            <div key={s.label} className="kz-panel p-5">
              <p className="text-[10px] font-mono text-cyan-400/40 tracking-widest mb-1">
                {s.label}
              </p>
              <p className={`text-lg font-bold font-mono ${s.color}`}>
                {s.value}
              </p>
            </div>
          ))}
        </div>
      </div>
    </ProtectedRoute>
  );
}
