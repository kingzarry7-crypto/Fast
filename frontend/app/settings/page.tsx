"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import AICore from "@/components/AICore";
import {
  clearVipLocal,
  getMembershipSnapshot,
  getTelegramVipStartUrl,
  setVipLocal,
  type MembershipSnapshot,
} from "@/lib/membership";
import { api, type PlatformStatus } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

type Preferences = {
  signalsOnly: boolean;
  humanReplies: boolean;
  rememberPreferences: boolean;
  riskReminder: boolean;
};

const DEFAULT_PREFERENCES: Preferences = {
  signalsOnly: true,
  humanReplies: true,
  rememberPreferences: true,
  riskReminder: true,
};

const TELEGRAM_FALLBACK = "https://t.me/KingZarryAI_bot";
const DISCORD_FALLBACK = "https://discord.com/channels/1537104053207568394";

export default function SettingsPage() {
  const { user, logout, refresh: refreshAuth } = useAuth();
  const [membership, setMembership] = useState<MembershipSnapshot | null>(null);
  const [platforms, setPlatforms] = useState<PlatformStatus | null>(null);
  const [platformLoading, setPlatformLoading] = useState(true);
  const [platformError, setPlatformError] = useState("");
  const [saved, setSaved] = useState(false);
  const [preferences, setPreferences] = useState<Preferences>(DEFAULT_PREFERENCES);

  const refreshMembership = () =>
    setMembership(getMembershipSnapshot(user?.id, user?.is_subscribed));

  useEffect(() => {
    refreshMembership();
    window.addEventListener("kz-membership-change", refreshMembership);
    return () => window.removeEventListener("kz-membership-change", refreshMembership);
  }, [user?.id, user?.is_subscribed]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem("kz-settings-preferences");
      if (raw) setPreferences({ ...DEFAULT_PREFERENCES, ...JSON.parse(raw) });
    } catch {
      setPreferences(DEFAULT_PREFERENCES);
    }
  }, []);

  const loadPlatforms = async () => {
    setPlatformLoading(true);
    setPlatformError("");
    try {
      const result = await api.getPlatformStatus();
      setPlatforms(result);
    } catch (error) {
      setPlatformError(
        error instanceof Error ? error.message : "Could not check platform status."
      );
    } finally {
      setPlatformLoading(false);
    }
  };

  useEffect(() => {
    void loadPlatforms();
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("checkout") === "success") {
      const plan = params.get("plan");
      if (plan) setVipLocal(plan);
      refreshAuth?.();
      refreshMembership();
      window.history.replaceState({}, "", "/settings");
    }
  }, [refreshAuth]);

  const telegramUrl =
    platforms?.telegram?.url || TELEGRAM_FALLBACK;
  const discordUrl =
    platforms?.discord?.invite_url ||
    process.env.NEXT_PUBLIC_DISCORD_INVITE_URL ||
    DISCORD_FALLBACK;

  const telegramState = useMemo(() => {
    if (platformLoading) return "CHECKING";
    if (platforms?.telegram?.reachable) return "LIVE";
    if (platforms?.telegram?.configured) return "CONFIGURED";
    return "NOT CONNECTED";
  }, [platformLoading, platforms]);

  const discordState = useMemo(() => {
    if (platformLoading) return "CHECKING";
    if (platforms?.discord?.reachable) return "LIVE";
    if (platforms?.discord?.configured) return "CONFIGURED";
    return "OPEN DISCORD";
  }, [platformLoading, platforms]);

  const savePreferences = () => {
    try {
      window.localStorage.setItem(
        "kz-settings-preferences",
        JSON.stringify(preferences)
      );
    } catch {
      // Settings still remain active for the current session.
    }
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1800);
  };

  return (
    <ProtectedRoute>
      <div className="min-h-full p-4 sm:p-6 lg:p-10">
        <div className="mx-auto max-w-6xl space-y-6">
          <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="font-mono-tech text-[10px] tracking-[0.35em] text-cyan-400/45">
                KING ZARRY AI · COMMAND CENTRE
              </p>
              <h1 className="mt-2 font-display text-2xl sm:text-3xl font-bold tracking-wider text-white kz-glow-text">
                Settings
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-cyan-100/55">
                Control how your AI behaves and open the platforms that are actually connected.
              </p>
            </div>
            <button
              type="button"
              onClick={loadPlatforms}
              disabled={platformLoading}
              className="self-start rounded-lg border border-cyan-500/25 px-4 py-2 font-mono-tech text-[10px] tracking-widest text-cyan-300 transition hover:bg-cyan-500/10 disabled:opacity-50"
            >
              {platformLoading ? "CHECKING..." : "REFRESH CONNECTIONS"}
            </button>
          </header>

          <section className="grid gap-6 lg:grid-cols-[280px_1fr]">
            <div className="kz-panel min-h-[300px] flex flex-col items-center justify-center overflow-visible p-6">
              <p className="font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/45">
                YOUR AI
              </p>
              <div className="mt-8">
                <AICore state="idle" size={205} />
              </div>
              <div className="mt-12 text-center">
                <p className="font-display text-lg font-bold tracking-wider text-white">
                  King Zarry AI
                </p>
                <p className="mt-1 text-xs text-cyan-300/50">
                  Ready for chat, signals, voice and platform commands.
                </p>
              </div>
            </div>

            <div className="space-y-6">
              <section className="kz-panel p-5 sm:p-6">
                <SectionTitle title="PLATFORMS" subtitle="REAL CONNECTIONS" />
                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  <PlatformCard
                    name="Telegram"
                    description="Open the King Zarry AI bot directly in Telegram."
                    state={telegramState}
                    href={telegramUrl}
                    action="OPEN TELEGRAM"
                    icon="TG"
                  />
                  <PlatformCard
                    name="Discord"
                    description="Open the King Zarry AI Discord destination."
                    state={discordState}
                    href={discordUrl}
                    action="OPEN DISCORD"
                    icon="DS"
                  />
                </div>
                {platformError && (
                  <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-xs text-amber-200/75">
                    Live status check failed: {platformError}. The platform buttons remain real external destinations; refresh after the backend is available.
                  </div>
                )}
              </section>

              <section className="kz-panel p-5 sm:p-6">
                <SectionTitle
                  title="CHAT BEHAVIOR"
                  subtitle="PERSONAL PREFERENCES"
                />
                <div className="mt-4 divide-y divide-cyan-500/10">
                  <SettingToggle
                    title="Signals only when I ask"
                    description="Normal chat stays normal. No surprise trade ideas."
                    checked={preferences.signalsOnly}
                    onChange={(checked) =>
                      setPreferences((p) => ({ ...p, signalsOnly: checked }))
                    }
                  />
                  <SettingToggle
                    title="Human-style replies"
                    description="Natural, relaxed tone instead of robotic answers."
                    checked={preferences.humanReplies}
                    onChange={(checked) =>
                      setPreferences((p) => ({ ...p, humanReplies: checked }))
                    }
                  />
                  <SettingToggle
                    title="Remember my preferences"
                    description="Keep this device's chat preferences available between visits."
                    checked={preferences.rememberPreferences}
                    onChange={(checked) =>
                      setPreferences((p) => ({ ...p, rememberPreferences: checked }))
                    }
                  />
                  <SettingToggle
                    title="Add risk reminder to signals"
                    description="Show a short not-financial-advice reminder under signals."
                    checked={preferences.riskReminder}
                    onChange={(checked) =>
                      setPreferences((p) => ({ ...p, riskReminder: checked }))
                    }
                  />
                </div>
                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={savePreferences}
                    className="rounded-lg bg-cyan-400 px-4 py-2 font-mono-tech text-[10px] font-bold tracking-widest text-[#001018] transition hover:bg-cyan-300"
                  >
                    {saved ? "SAVED" : "SAVE CHANGES"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setPreferences(DEFAULT_PREFERENCES);
                      try {
                        window.localStorage.removeItem("kz-settings-preferences");
                      } catch {}
                    }}
                    className="rounded-lg border border-cyan-500/20 px-4 py-2 font-mono-tech text-[10px] tracking-widest text-cyan-300/70 transition hover:bg-cyan-500/10"
                  >
                    RESET TO DEFAULT
                  </button>
                </div>
              </section>

              <section className="kz-panel p-5 sm:p-6">
                <SectionTitle title="AI BRAIN" subtitle="WORKING ROUTES" />
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <ActionCard
                    label="CHAT CORE"
                    value="Open the live AI conversation"
                    href="/chat"
                  />
                  <ActionCard
                    label="AGENT"
                    value="Run and monitor agent tasks"
                    href="/agent"
                  />
                  <ActionCard
                    label="VOICE"
                    value="Open the live voice conversation"
                    href="/chat?voice=1"
                  />
                  <ActionCard
                    label="MEMORY"
                    value="Manage cross-platform memory linking"
                    href="/history"
                  />
                </div>
              </section>

              <section className="kz-panel p-5 sm:p-6">
                <SectionTitle title="MEMBERSHIP" subtitle="ACCOUNT ACCESS" />
                <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <Row label="PLAN" value={user?.is_subscribed || membership?.isVip ? String(user?.plan || membership?.plan || "VIP").toUpperCase() : "FREE"} />
                  <Row label="STATUS" value={user?.is_subscribed || membership?.isVip ? "ACTIVE" : "FREE TIER"} />
                  <Row label="FREE MSGS" value={membership ? `${membership.freeMessagesUsedToday} / ${membership.freeDailyLimit}` : "—"} />
                  <Row label="EXPIRES" value={user?.subscription_expires_at ? String(user.subscription_expires_at).slice(0, 10) : "—"} />
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  <a
                    href={getTelegramVipStartUrl()}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-lg border border-cyan-500/30 px-4 py-2 font-mono-tech text-[10px] tracking-widest text-cyan-300 transition hover:bg-cyan-500/10"
                  >
                    OPEN TELEGRAM VIP
                  </a>
                  <Link
                    href="/pricing"
                    className="rounded-lg border border-cyan-500/30 px-4 py-2 font-mono-tech text-[10px] tracking-widest text-cyan-300 transition hover:bg-cyan-500/10"
                  >
                    VIEW PRICING
                  </Link>
                  {!membership?.isVip ? (
                    <button
                      type="button"
                      onClick={() => {
                        setVipLocal("telegram");
                        refreshMembership();
                      }}
                      className="rounded-lg bg-cyan-400 px-4 py-2 font-mono-tech text-[10px] font-bold tracking-widest text-[#001018]"
                    >
                      I PAID ON TELEGRAM — ACTIVATE VIP
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => {
                        clearVipLocal();
                        refreshMembership();
                      }}
                      className="rounded-lg border border-amber-500/30 px-4 py-2 font-mono-tech text-[10px] tracking-widest text-amber-300"
                    >
                      CLEAR LOCAL VIP
                    </button>
                  )}
                </div>
              </section>

              <section className="flex flex-wrap items-center justify-between gap-4 border-t border-cyan-500/10 pt-5">
                <div>
                  <p className="font-mono-tech text-[10px] tracking-widest text-cyan-400/45">
                    ACCOUNT
                  </p>
                  <p className="mt-1 text-xs text-cyan-100/45">
                    {user?.email || "Signed-in King Zarry AI account"}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={logout}
                  className="rounded-lg border border-red-500/25 px-4 py-2 font-mono-tech text-[10px] tracking-widest text-red-300/80 transition hover:bg-red-500/10"
                >
                  SIGN OUT
                </button>
              </section>
            </div>
          </section>
        </div>
      </div>
    </ProtectedRoute>
  );
}

function SectionTitle({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <div>
      <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/50">
        {title}
      </p>
      <p className="mt-1 text-[11px] text-cyan-100/35">{subtitle}</p>
    </div>
  );
}

function PlatformCard({
  name,
  description,
  state,
  href,
  action,
  icon,
}: {
  name: string;
  description: string;
  state: string;
  href: string;
  action: string;
  icon: string;
}) {
  const live = state === "LIVE";
  return (
    <div className="rounded-2xl border border-cyan-500/10 bg-black/20 p-4 transition hover:border-cyan-400/25">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-400/25 bg-cyan-400/5 font-display text-xs font-bold text-cyan-300">
            {icon}
          </div>
          <div>
            <p className="font-display text-sm font-bold tracking-wider text-white">
              {name}
            </p>
            <div className="mt-1 flex items-center gap-2">
              <span
                className={`h-1.5 w-1.5 rounded-full ${live ? "bg-emerald-400 animate-pulse" : "bg-cyan-400/40"}`}
              />
              <span className="font-mono-tech text-[9px] tracking-widest text-cyan-300/55">
                {state}
              </span>
            </div>
          </div>
        </div>
      </div>
      <p className="mt-4 min-h-10 text-xs leading-relaxed text-cyan-100/45">
        {description}
      </p>
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-4 inline-flex w-full items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-500/5 px-4 py-2.5 font-mono-tech text-[10px] font-bold tracking-widest text-cyan-200 transition hover:bg-cyan-500/15"
      >
        {action} ↗
      </a>
    </div>
  );
}

function SettingToggle({
  title,
  description,
  checked,
  onChange,
}: {
  title: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-5 py-4">
      <span>
        <span className="block text-sm font-medium text-white/90">{title}</span>
        <span className="mt-1 block text-xs leading-relaxed text-cyan-100/40">
          {description}
        </span>
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-5 w-5 shrink-0 accent-cyan-400"
      />
    </label>
  );
}

function ActionCard({
  label,
  value,
  href,
}: {
  label: string;
  value: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="rounded-xl border border-cyan-500/10 bg-black/20 p-4 transition hover:border-cyan-400/30 hover:bg-cyan-500/5"
    >
      <p className="font-mono-tech text-[9px] tracking-[0.25em] text-cyan-400/50">
        {label}
      </p>
      <p className="mt-2 text-sm text-white/80">{value}</p>
      <p className="mt-3 font-mono-tech text-[9px] tracking-widest text-cyan-300/55">
        OPEN →
      </p>
    </Link>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-cyan-500/10 bg-black/15 p-3">
      <p className="font-mono-tech text-[9px] tracking-widest text-cyan-400/45">
        {label}
      </p>
      <p className="mt-2 text-sm text-white/90 font-mono-tech">{value}</p>
    </div>
  );
}
