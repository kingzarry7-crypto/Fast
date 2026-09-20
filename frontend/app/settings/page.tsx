"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuth } from "@/hooks/useAuth";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <ProtectedRoute>
      <div className="p-6 lg:p-10 max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-8">Settings</h1>

        <div className="kz-panel p-6 space-y-6">
          <div>
            <p className="text-[10px] font-mono text-cyan-400/40 tracking-widest mb-2">
              ACCOUNT
            </p>
            <div className="space-y-3">
              <Row label="Email" value={user?.email || "—"} />
              <Row label="Username" value={user?.username || "—"} />
              <Row label="Display Name" value={user?.display_name || "—"} />
              <Row label="Account Status" value={user?.account_status || "—"} />
              <Row
                label="Member Since"
                value={user?.created_at?.slice(0, 10) || "—"}
              />
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-cyan-500/5 pb-2">
      <span className="text-xs font-mono text-cyan-400/50">{label}</span>
      <span className="text-sm text-white/90">{value}</span>
    </div>
  );
}
