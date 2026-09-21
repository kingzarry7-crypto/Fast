"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuth } from "@/hooks/useAuth";

export default function SettingsPage() {
  const { user, logout } = useAuth();

  return (
    <ProtectedRoute>
      <div className="p-6 lg:p-10 max-w-3xl mx-auto">
        <h1 className="font-display text-2xl font-bold text-white kz-glow-text mb-8 tracking-wider">
          Settings
        </h1>

        <div className="kz-panel p-6 space-y-6">
          <div>
            <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40 mb-3">
              ACCOUNT
            </p>
            <div className="space-y-3">
              <Row label="EMAIL" value={user?.email || "—"} />
              <Row label="USERNAME" value={user?.username || "—"} />
              <Row label="DISPLAY NAME" value={user?.display_name || "—"} />
              <Row
                label="ACCOUNT STATUS"
                value={user?.account_status || "—"}
              />
              <Row
                label="MEMBER SINCE"
                value={user?.created_at?.slice(0, 10) || "—"}
              />
            </div>
          </div>

          <div className="pt-4 border-t border-cyan-500/10">
            <button
              onClick={logout}
              className="px-4 py-2 rounded-md font-mono-tech text-[10px] tracking-widest text-red-400/80 border border-red-500/30 hover:bg-red-500/10 hover:text-red-300 transition-all"
            >
              SIGN OUT
            </button>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-cyan-500/5 pb-2">
      <span className="font-mono-tech text-[10px] tracking-widest text-cyan-400/50">
        {label}
      </span>
      <span className="text-sm text-white/90 font-mono-tech tracking-wider">
        {value}
      </span>
    </div>
  );
}
