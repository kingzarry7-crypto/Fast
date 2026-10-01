"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuth } from "@/hooks/useAuth";
import { api, ApiError, type AdminStats } from "@/lib/api";

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="kz-panel p-5">
      <p className="font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/40 mb-2">
        {label}
      </p>
      <p className="font-display text-2xl font-bold text-white tracking-wider">
        {value}
      </p>
      {sub && (
        <p className="mt-1 font-mono-tech text-[10px] text-cyan-400/40">{sub}</p>
      )}
    </div>
  );
}

export default function AdminPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [requiresPassword, setRequiresPassword] = useState(false);
  const [password, setPassword] = useState("");
  const [unlocking, setUnlocking] = useState(false);
  const [actingId, setActingId] = useState<string | null>(null);

  const loadMeAndStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const me = await api.getAdminMe();
      setIsAdmin(!!me.is_admin);
      setRequiresPassword(!!me.requires_password);
      if (!me.is_admin) {
        const hint = typeof me.hint === "string" ? me.hint : "";
        setError(
          hint ||
            (me.admin_emails_configured === false
              ? "Set ADMIN_EMAIL on Railway to your login email."
              : "Your login email must match ADMIN_EMAIL on Railway.")
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
        e instanceof ApiError
          ? `${e.status}: ${e.detail || e.message}`
          : "Could not load admin"
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
      await api.adminUnlock(password.trim());
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

  const n = (v: unknown) => String(typeof v === "number" ? v : Number(v) || 0);

  const setStatus = async (
    userId: string,
    status: "active" | "suspended" | "banned"
  ) => {
    if (!userId || actingId) return;
    const labels = { active: "reactivate", suspended: "suspend", banned: "ban" };
    if (!window.confirm(`Are you sure you want to ${labels[status]} this user?`)) {
      return;
    }
    setActingId(userId);
    setError(null);
    try {
      if (status === "active") {
        await api.adminUnbanUser(userId);
      } else {
        await api.adminBanUser(userId, status);
      }
      await loadMeAndStats();
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.detail || e.message
          : "Could not update user status"
      );
    } finally {
      setActingId(null);
    }
  };

  return (
    <ProtectedRoute>
      <div className="p-6 lg:p-10 max-w-6xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="font-display text-2xl font-bold text-white kz-glow-text tracking-wider">
              Admin · Command Centre
            </h1>
            <p className="mt-1 font-mono-tech text-[10px] tracking-widest text-cyan-400/50">
              Users · usage · revenue · recent activity
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => loadMeAndStats()}
              className="font-mono-tech text-[10px] tracking-widest text-cyan-300 border border-cyan-500/30 px-3 py-1.5 rounded-md hover:bg-cyan-500/10"
            >
              REFRESH
            </button>
            <Link
              href="/dashboard"
              className="font-mono-tech text-[10px] tracking-widest text-cyan-400/70 hover:text-cyan-300"
            >
              ← DASHBOARD
            </Link>
          </div>
        </div>

        {loading && (
          <p className="font-mono-tech text-xs text-cyan-400/50">Loading…</p>
        )}

        {error && (
          <div className="kz-panel p-6 text-sm text-amber-200/90 mb-6">{error}</div>
        )}

        {isAdmin && requiresPassword && (
          <form
            onSubmit={handleUnlock}
            className="kz-panel p-6 max-w-md space-y-4 mb-6"
          >
            <p className="font-mono-tech text-[10px] tracking-[0.25em] text-cyan-300">
              ADMIN PASSWORD
            </p>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg bg-black/40 border border-cyan-500/25 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400"
            />
            <button
              type="submit"
              disabled={unlocking || !password.trim()}
              className="px-4 py-2 rounded-lg bg-cyan-400 text-black text-xs font-bold tracking-widest disabled:opacity-40"
            >
              {unlocking ? "CHECKING…" : "UNLOCK"}
            </button>
          </form>
        )}

        {!loading && isAdmin && !requiresPassword && stats && (
          <div className="space-y-8">
            <section>
              <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40 mb-3">
                USERS
              </p>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Stat label="TOTAL USERS" value={n(stats.users_total)} />
                <Stat
                  label="ACTIVE 7D"
                  value={n(stats.users_active_7d)}
                  sub="logged in last 7 days"
                />
                <Stat
                  label="ACTIVE 30D"
                  value={n(stats.users_active_30d)}
                />
                <Stat label="NEW 7D" value={n(stats.users_new_7d)} />
              </div>
            </section>

            <section>
              <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40 mb-3">
                USAGE
              </p>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Stat label="SESSIONS LIVE" value={n(stats.sessions_active)} />
                <Stat
                  label="CONVERSATIONS"
                  value={n(stats.conversations_total)}
                />
                <Stat label="MESSAGES" value={n(stats.messages_total)} />
                <Stat label="MESSAGES 24H" value={n(stats.messages_24h)} />
              </div>
            </section>

            <section>
              <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40 mb-3">
                REVENUE (WEB)
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Stat
                  label="ACTIVE VIP"
                  value={n(stats.active_subscribers)}
                />
                <Stat label="PAYMENTS" value={n(stats.payments_count)} />
                <Stat
                  label="REVENUE USD"
                  value={`$${Number(stats.revenue_usd || 0).toFixed(2)}`}
                />
              </div>
            </section>

            <section className="kz-panel p-6">
              <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40 mb-4">
                RECENT USERS
              </p>
              {(!stats.recent_users || !(stats.recent_users as unknown[]).length) && (
                <p className="text-sm text-cyan-400/50">No users yet.</p>
              )}
              <div className="space-y-2 max-h-80 overflow-y-auto kz-scroll">
                {((stats.recent_users as Array<Record<string, unknown>> | undefined) || []).map((u, i) => {
                  const st = String(u.account_status || "active").toLowerCase();
                  const busy = actingId === String(u.id || "");
                  const isSelf =
                    user?.email &&
                    u.email &&
                    user.email.toLowerCase() === String(u.email).toLowerCase();
                  return (
                    <div
                      key={String(u.id || i)}
                      className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-cyan-500/10 py-3 text-sm"
                    >
                      <div className="min-w-0">
                        <p className="font-mono-tech text-xs text-white truncate">
                          {String(u.email || "—")}
                          {isSelf ? " (you)" : ""}
                        </p>
                        <p className="font-mono-tech text-[10px] text-cyan-300/70">
                          <span
                            className={
                              st === "banned"
                                ? "text-red-300"
                                : st === "suspended"
                                  ? "text-amber-300"
                                  : "text-emerald-300/80"
                            }
                          >
                            {st.toUpperCase()}
                          </span>
                          {u.last_login_at
                            ? ` · last ${String(u.last_login_at).slice(0, 16)}`
                            : ""}
                          {" · joined "}
                          {String(u.created_at || "").slice(0, 19)}
                        </p>
                      </div>
                      {!isSelf && u.id && (
                        <div className="flex flex-wrap gap-1.5 shrink-0">
                          {st !== "active" && (
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => setStatus(String(u.id), "active")}
                              className="px-2.5 py-1 rounded-md text-[9px] font-mono-tech tracking-wider border border-emerald-500/40 text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-40"
                            >
                              ACTIVATE
                            </button>
                          )}
                          {st !== "suspended" && (
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => setStatus(String(u.id), "suspended")}
                              className="px-2.5 py-1 rounded-md text-[9px] font-mono-tech tracking-wider border border-amber-500/40 text-amber-200 hover:bg-amber-500/10 disabled:opacity-40"
                            >
                              SUSPEND
                            </button>
                          )}
                          {st !== "banned" && (
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => setStatus(String(u.id), "banned")}
                              className="px-2.5 py-1 rounded-md text-[9px] font-mono-tech tracking-wider border border-red-500/40 text-red-200 hover:bg-red-500/10 disabled:opacity-40"
                            >
                              BAN
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="kz-panel p-6">
              <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40 mb-4">
                RECENT WEB PAYMENTS
              </p>
              {(!stats.recent_payments || !(stats.recent_payments as unknown[]).length) && (
                <p className="text-sm text-cyan-400/50">
                  No web payments yet. Telegram Stars stay on the bot.
                </p>
              )}
              <div className="space-y-2">
                {((stats.recent_payments as Array<Record<string, unknown>> | undefined) || []).map((p, i) => (
                  <div
                    key={`${String(p.created_at)}-${i}`}
                    className="flex flex-wrap justify-between gap-2 border-b border-cyan-500/10 py-2 text-sm"
                  >
                    <span className="font-mono-tech text-xs">
                      {String(p.email || "—")}
                    </span>
                    <span className="font-mono-tech text-[10px] text-cyan-300/80">
                      {String(p.plan || "—").toUpperCase()} · $
                      {((Number(p.amount_cents) || 0) / 100).toFixed(2)} · {String(p.status || "")}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            <p className="text-xs text-cyan-400/40">
              Logged in as admin
              {stats.admin_email ? ` (${String(stats.admin_email)})` : ""}. Web
              VIP is Paystack/Stripe. Telegram Stars are separate on the bot.
            </p>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
