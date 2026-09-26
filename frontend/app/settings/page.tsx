"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuth } from "@/hooks/useAuth";
import {
  clearVipLocal,
  getMembershipSnapshot,
  getTelegramVipStartUrl,
  setVipLocal,
  type MembershipSnapshot,
} from "@/lib/membership";

export default function SettingsPage() {
  const { user, logout, refresh: refreshAuth } = useAuth();
  const [membership, setMembership] = useState<MembershipSnapshot | null>(
    null
  );

  const refresh = () => setMembership(getMembershipSnapshot(user?.id));

  useEffect(() => {
    refresh();
    window.addEventListener("kz-membership-change", refresh);
    return () => window.removeEventListener("kz-membership-change", refresh);
  }, [user?.id]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("checkout") === "success") {
      const plan = params.get("plan");
      if (plan) setVipLocal(plan);
      refreshAuth?.();
      refresh();
      window.history.replaceState({}, "", "/settings");
    }
  }, [refreshAuth]);

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

          <div className="pt-4 border-t border-cyan-500/10 space-y-4">
            <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40">
              MEMBERSHIP
            </p>
            <div className="space-y-3">
              <Row
                label="PLAN"
                value={
                  user?.is_subscribed || membership?.isVip
                    ? String(
                        user?.plan || membership?.plan || "VIP"
                      ).toUpperCase()
                    : "FREE"
                }
              />
              <Row
                label="STATUS"
                value={
                  user?.is_subscribed || membership?.isVip
                    ? "ACTIVE"
                    : "FREE TIER"
                }
              />
              <Row
                label="FREE MSGS TODAY"
                value={
                  membership
                    ? `${membership.freeMessagesUsedToday} / ${membership.freeDailyLimit}`
                    : "—"
                }
              />
              {user?.subscription_expires_at && (
                <Row
                  label="EXPIRES"
                  value={String(user.subscription_expires_at).slice(0, 10)}
                />
              )}
            </div>
            <p className="text-xs text-cyan-400/50 leading-relaxed">
              Web VIP unlocks after Stripe payment (webhook). Telegram Stars stay
              on the bot; you can mark local VIP here after paying on Telegram.
            </p>
            <div className="flex flex-wrap gap-3">
              <a
                href={getTelegramVipStartUrl()}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 rounded-md font-mono-tech text-[10px] tracking-widest text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/10 transition-all"
              >
                OPEN TELEGRAM VIP
              </a>
              <Link
                href="/pricing"
                className="px-4 py-2 rounded-md font-mono-tech text-[10px] tracking-widest text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/10 transition-all"
              >
                VIEW PRICING
              </Link>
              {!membership?.isVip ? (
                <button
                  type="button"
                  onClick={() => {
                    setVipLocal("telegram");
                    refresh();
                  }}
                  className="px-4 py-2 rounded-md font-mono-tech text-[10px] tracking-widest text-black bg-cyan-400 hover:bg-cyan-300 transition-all"
                >
                  I PAID ON TELEGRAM — ACTIVATE VIP
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    clearVipLocal();
                    refresh();
                  }}
                  className="px-4 py-2 rounded-md font-mono-tech text-[10px] tracking-widest text-amber-300/90 border border-amber-500/30 hover:bg-amber-500/10 transition-all"
                >
                  CLEAR LOCAL VIP
                </button>
              )}
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
