"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuth } from "@/hooks/useAuth";
import { api, ApiError, type AdminStats } from "@/lib/api";

export default function AdminPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [requiresPassword, setRequiresPassword] = useState(false);
  const [adminConfigured, setAdminConfigured] = useState(true);
  const [password, setPassword] = useState("");
  const [unlocking, setUnlocking] = useState(false);

  const loadMeAndStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const me = await api.getAdminMe();
      setIsAdmin(!!me.is_admin);
      setRequiresPassword(!!me.requires_password);
      setAdminConfigured(me.admin_emails_configured !== false);
      if (!me.is_admin) {
        setError(
          me.admin_emails_configured === false
            ? "No admin emails on server. Set ADMIN_EMAIL or ADMIN_EMAILS on Railway to your login email."
            : "Admin access denied. Your login email must match ADMIN_EMAIL / ADMIN_EMAILS on Railway."
        );
        setLoading(false);
        return;
      }
      if (me.requires_password) {
        setLoading(false);
        return;
      }
      const data = await api.getAdminStats();
      setStats(data);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.detail || e.message : "Could not load admin"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!user) return;
    loadMeAndStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id, user?.email]);

  const handleUnlock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim() || unlocking) return;
    setUnlocking(true);
    setError(null);
    try {
      await api.unlockAdmin(password.trim());
      setRequiresPassword(false);
      setPassword("");
      const data = await api.getAdminStats();
      setStats(data);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail || err.message
          : "Invalid admin password"
      );
    } finally {
      setUnlocking(false);
    }
  };

  return (
    <ProtectedRoute>
      <div className="p-6 lg:p-10 max-w-5xl mx-auto">
        <div className="flex items-center justify-between gap-4 mb-8">
          <h1 className="font-display text-2xl font-bold text-white kz-glow-text tracking-wider">
            Admin · Revenue
          </h1>
          <Link
            href="/dashboard"
            className="font-mono-tech text-[10px] tracking-widest text-cyan-400/70 hover:text-cyan-300"
          >
            ← DASHBOARD
          </Link>
        </div>

        {loading && (
          <p className="font-mono-tech text-xs text-cyan-400/50">Loading…</p>
        )}

        {error && (
          <div className="kz-panel p-6 text-sm text-amber-200/90 mb-6">
            {error}
            {!isAdmin && (
              <div className="mt-4 text-xs text-cyan-400/60 space-y-2 font-mono-tech">
                <p>On Railway set:</p>
                <pre className="bg-black/40 p-3 rounded text-[10px] overflow-x-auto">{`ADMIN_EMAIL=your-login@email.com
ADMIN_EMAILS=your-login@email.com
ADMIN_PASSWORD=optional-extra-secret`}</pre>
                <p>
                  Use the <strong>same email</strong> you use to log in on the
                  website. Password for site login is your account password;
                  ADMIN_PASSWORD is only if you set an extra admin unlock.
                </p>
              </div>
            )}
          </div>
        )}

        {isAdmin && requiresPassword && (
          <form
            onSubmit={handleUnlock}
            className="kz-panel p-6 max-w-md space-y-4 mb-6"
          >
            <p className="font-mono-tech text-[10px] tracking-[0.25em] text-cyan-300">
              ADMIN PASSWORD (FROM RAILWAY ENV)
            </p>
            <p className="text-xs text-cyan-400/60">
              Enter ADMIN_PASSWORD from Railway to unlock this panel.
            </p>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="ADMIN_PASSWORD"
              className="w-full rounded-lg bg-black/40 border border-cyan-500/25 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400"
              autoComplete="current-password"
            />
            <button
              type="submit"
              disabled={unlocking || !password.trim()}
              className="px-4 py-2 rounded-lg bg-cyan-400 text-black text-xs font-bold tracking-widest disabled:opacity-40"
            >
              {unlocking ? "CHECKING…" : "UNLOCK ADMIN"}
            </button>
          </form>
        )}

        {!loading && isAdmin && !requiresPassword && stats && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <StatCard
                label="ACTIVE VIP"
                value={String(stats.active_subscribers)}
              />
              <StatCard
                label="PAYMENTS"
                value={String(stats.payments_count)}
              />
              <StatCard
                label="REVENUE (USD)"
                value={`$${Number(stats.revenue_usd || 0).toFixed(2)}`}
              />
            </div>

            <div className="kz-panel p-6">
              <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40 mb-4">
                RECENT STRIPE PAYMENTS
              </p>
              {(!stats.recent_payments ||
                stats.recent_payments.length === 0) && (
                <p className="text-sm text-cyan-400/50">
                  No web payments yet. Complete a Stripe test checkout from
                  Pricing.
                </p>
              )}
              <div className="space-y-2">
                {(stats.recent_payments || []).map((p, i) => (
                  <div
                    key={`${p.created_at}-${i}`}
                    className="flex flex-wrap items-center justify-between gap-2 border-b border-cyan-500/10 py-2 text-sm"
                  >
                    <span className="text-white/90 font-mono-tech text-xs">
                      {p.email || "—"}
                    </span>
                    <span className="text-cyan-300/80 font-mono-tech text-[10px] tracking-wider">
                      {(p.plan || "—").toUpperCase()} · $
                      {((p.amount_cents || 0) / 100).toFixed(2)} · {p.status}
                    </span>
                    <span className="text-cyan-400/40 font-mono-tech text-[9px]">
                      {p.created_at?.slice(0, 19) || ""}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <p className="text-xs text-cyan-400/40 leading-relaxed">
              Web revenue: Stripe → webhook → Neon. Telegram Stars stay on the
              bot. Logged in as admin via Railway ADMIN_EMAIL / ADMIN_EMAILS.
            </p>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="kz-panel p-5">
      <p className="font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/40 mb-2">
        {label}
      </p>
      <p className="font-display text-2xl font-bold text-white tracking-wider">
        {value}
      </p>
    </div>
  );
}
