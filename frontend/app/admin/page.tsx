"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuth } from "@/hooks/useAuth";
import { api, ApiError, type AdminStats } from "@/lib/api";

function isAdminEmail(email?: string | null): boolean {
  if (!email) return false;
  const raw =
    (typeof process !== "undefined" &&
      process.env.NEXT_PUBLIC_ADMIN_EMAILS) ||
    "";
  const set = new Set(
    raw
      .split(",")
      .map((e) => e.trim().toLowerCase())
      .filter(Boolean)
  );
  return set.has(email.trim().toLowerCase());
}

export default function AdminPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const allowed = isAdminEmail(user?.email);

  useEffect(() => {
    if (!user) return;
    if (!allowed) {
      setLoading(false);
      setError(
        "Admin access required. Set your email in NEXT_PUBLIC_ADMIN_EMAILS and ADMIN_EMAILS."
      );
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await api.getAdminStats();
        if (!cancelled) setStats(data);
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof ApiError
              ? e.detail || e.message
              : "Could not load admin stats"
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user, allowed]);

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

        {!allowed && (
          <div className="kz-panel p-6 text-sm text-amber-200/90">
            {error || "Not authorized."}
            <p className="mt-3 text-xs text-cyan-400/50">
              Add your login email to Railway ADMIN_EMAILS and Vercel
              NEXT_PUBLIC_ADMIN_EMAILS (comma-separated).
            </p>
          </div>
        )}

        {allowed && loading && (
          <p className="font-mono-tech text-xs text-cyan-400/60">Loading stats…</p>
        )}

        {allowed && error && !stats && (
          <div className="kz-panel p-6 text-sm text-red-300/90">{error}</div>
        )}

        {allowed && stats && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <StatCard label="ACTIVE VIP" value={String(stats.active_subscribers)} />
              <StatCard label="PAYMENTS" value={String(stats.payments_count)} />
              <StatCard
                label="REVENUE (USD)"
                value={`$${Number(stats.revenue_usd || 0).toFixed(2)}`}
              />
            </div>

            <div className="kz-panel p-6">
              <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40 mb-4">
                RECENT STRIPE PAYMENTS
              </p>
              {(!stats.recent_payments || stats.recent_payments.length === 0) && (
                <p className="text-sm text-cyan-400/50">
                  No web payments yet. Complete a Stripe test checkout from Pricing.
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
              Web revenue comes from Stripe Checkout → webhook → Neon. Telegram
              Stars still show in the bot owner balance and /stats, not on this page.
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
