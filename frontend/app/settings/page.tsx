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
import { api, type ChatBehaviorPreferences, type PlatformStatus, type KittyPaperSettings, type KittyDemoSettings } from "@/lib/api";
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
  const [savingPreferences, setSavingPreferences] = useState(false);
  const [settingsError, setSettingsError] = useState("");
  const [preferences, setPreferences] = useState<Preferences>(DEFAULT_PREFERENCES);
  const [kittySettings, setKittySettings] = useState<KittyPaperSettings | null>(null);
  const [kittyLoading, setKittyLoading] = useState(true);
  const [kittySaving, setKittySaving] = useState(false);
  const [kittyError, setKittyError] = useState("");
  const [kittyNotice, setKittyNotice] = useState("");
  const [kittyDemoSettings, setKittyDemoSettings] = useState<KittyDemoSettings | null>(null);
  const [kittyDemoLoading, setKittyDemoLoading] = useState(true);
  const [kittyDemoSaving, setKittyDemoSaving] = useState(false);
  const [kittyDemoError, setKittyDemoError] = useState("");
  const [kittyDemoNotice, setKittyDemoNotice] = useState("");
  const [kittyDemoAcknowledged, setKittyDemoAcknowledged] = useState(false);

  const refreshMembership = () =>
    setMembership(getMembershipSnapshot(user?.id, user?.is_subscribed));

  useEffect(() => {
    refreshMembership();
    window.addEventListener("kz-membership-change", refreshMembership);
    return () => window.removeEventListener("kz-membership-change", refreshMembership);
  }, [user?.id, user?.is_subscribed]);

  useEffect(() => {
    let cancelled = false;
    void api
      .getChatBehaviorPreferences()
      .then((result) => {
        if (!cancelled && result?.preferences) {
          setPreferences({ ...DEFAULT_PREFERENCES, ...result.preferences });
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setSettingsError(
            error instanceof Error
              ? error.message
              : "Could not load saved settings."
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    void api.getKittyPaperSettings()
      .then((result) => {
        if (!cancelled) setKittySettings(result);
      })
      .catch((error) => {
        if (!cancelled) setKittyError(error instanceof Error ? error.message : "Could not load Kitty controls. VIP sign-in may be required.");
      })
      .finally(() => {
        if (!cancelled) setKittyLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    void api.getKittyDemoSettings()
      .then((result) => { if (!cancelled) setKittyDemoSettings(result); })
      .catch((error) => { if (!cancelled) setKittyDemoError(error instanceof Error ? error.message : "Could not load Kitty demo controls."); })
      .finally(() => { if (!cancelled) setKittyDemoLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const saveKittyDemoSettings = async () => {
    if (!kittyDemoSettings) return;
    setKittyDemoSaving(true);
    setKittyDemoError("");
    setKittyDemoNotice("");
    try {
      const result = await api.saveKittyDemoSettings({
        enabled: kittyDemoSettings.enabled,
        order_btc: Number(kittyDemoSettings.order_btc),
        max_notional_usd: Number(kittyDemoSettings.max_notional_usd),
        acknowledge_experimental_model: kittyDemoAcknowledged,
      });
      setKittyDemoSettings(result);
      setKittyDemoNotice(result.message || (result.enabled ? "Kitty demo trading enabled." : "Kitty demo trading paused."));
    } catch (error) {
      setKittyDemoError(error instanceof Error ? error.message : "Could not apply Kitty demo settings.");
    } finally {
      setKittyDemoSaving(false);
    }
  };

  const saveKittySettings = async () => {
    if (!kittySettings) return;
    setKittySaving(true);
    setKittyError("");
    setKittyNotice("");
    try {
      const result = await api.saveKittyPaperSettings({
        enabled: kittySettings.enabled,
        order_btc: Number(kittySettings.order_btc),
        max_notional_usd: Number(kittySettings.max_notional_usd),
      });
      setKittySettings(result);
      setKittyNotice(result.message || "Kitty paper settings applied.");
    } catch (error) {
      setKittyError(error instanceof Error ? error.message : "Could not apply Kitty settings.");
    } finally {
      setKittySaving(false);
    }
  };

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

  const savePreferences = async (next: Preferences = preferences) => {
    setSavingPreferences(true);
    setSettingsError("");
    try {
      const result = await api.saveChatBehaviorPreferences(
        next as ChatBehaviorPreferences
      );
      setPreferences({ ...DEFAULT_PREFERENCES, ...result.preferences });
      setSaved(true);
      window.setTimeout(() => setSaved(false), 1800);
    } catch (error) {
      setSettingsError(
        error instanceof Error
          ? error.message
          : "Could not save settings."
      );
    } finally {
      setSavingPreferences(false);
    }
  };

  const changePreference = (key: keyof Preferences, checked: boolean) => {
    const next = { ...preferences, [key]: checked };
    setPreferences(next);
    void savePreferences(next);
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
                <SectionTitle title="KITTY V3" subtitle="PAPER TRADING · RESEARCH CONTROLS" />
                <p className="mt-3 text-xs leading-relaxed text-cyan-100/55">
                  These controls start or pause Kitty&apos;s simulated BTC/USD paper trader and tune its simulated order size. They do not place Binance Demo or live orders.
                </p>
                {kittyLoading && <p className="mt-4 text-xs text-cyan-200/60">Loading Kitty settings…</p>}
                {kittyError && <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-xs text-amber-200/80">{kittyError}</div>}
                {kittySettings && (
                  <>
                    <div className="mt-4 rounded-xl border border-cyan-500/15 bg-black/20 p-4">
                      <SettingToggle
                        title="Enable Kitty paper trader"
                        description={kittySettings.enabled ? "ON — Kitty may evaluate new completed daily candles in the simulator." : "OFF — no new paper-trading cycles will be processed."}
                        checked={kittySettings.enabled}
                        onChange={(checked) => setKittySettings({ ...kittySettings, enabled: checked })}
                      />
                      <div className="grid gap-4 border-t border-cyan-500/10 pt-4 sm:grid-cols-2">
                        <label className="block text-xs text-cyan-100/65">
                          Simulated BTC order quantity
                          <input type="number" min="0.000001" max="0.01" step="0.0001" value={kittySettings.order_btc}
                            onChange={(event) => setKittySettings({ ...kittySettings, order_btc: Number(event.target.value) })}
                            className="mt-2 w-full rounded-lg border border-cyan-500/20 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400/50" />
                          <span className="mt-1 block text-[10px] text-cyan-100/35">Hard cap: 0.01 BTC per simulated entry.</span>
                        </label>
                        <label className="block text-xs text-cyan-100/65">
                          Maximum simulated order value (USD)
                          <input type="number" min="1" max="500" step="5" value={kittySettings.max_notional_usd}
                            onChange={(event) => setKittySettings({ ...kittySettings, max_notional_usd: Number(event.target.value) })}
                            className="mt-2 w-full rounded-lg border border-cyan-500/20 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400/50" />
                          <span className="mt-1 block text-[10px] text-cyan-100/35">Hard cap: $500 in the simulator.</span>
                        </label>
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap items-center gap-3">
                      <button type="button" onClick={() => void saveKittySettings()}
                        disabled={kittySaving || kittyLoading || kittySettings.order_btc <= 0 || kittySettings.order_btc > 0.01 || kittySettings.max_notional_usd <= 0 || kittySettings.max_notional_usd > 500}
                        className="rounded-lg bg-cyan-400 px-4 py-2 font-mono-tech text-[10px] font-bold tracking-widest text-[#001018] transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50">
                        {kittySaving ? "APPLYING…" : "SAVE & APPLY KITTY SETTINGS"}
                      </button>
                      {kittyNotice && <span className="text-xs text-emerald-300">{kittyNotice}</span>}
                    </div>
                    <p className="mt-3 text-[10px] leading-relaxed text-amber-200/60">
                      Tuning currently applies to this running backend process and resets on a backend restart unless environment defaults are also updated. Kitty V3&apos;s training symbol is not yet confirmed, so keep this in paper mode while validating the model.
                    </p>
                  </>
                )}
              </section>

              <section className="kz-panel p-5 sm:p-6">
                <SectionTitle title="KITTY V3" subtitle="BINANCE SPOT DEMO · REAL DEMO ORDERS" />
                <p className="mt-3 text-xs leading-relaxed text-amber-100/70">
                  This is a separate, opt-in Binance Spot Demo worker, not paper simulation. It can submit demo-market orders only; it cannot route orders to Binance live. Kitty&apos;s training symbol is unconfirmed and this model is experimental, so use demo funds only.
                </p>
                {kittyDemoLoading && <p className="mt-4 text-xs text-cyan-200/60">Checking demo trading readiness…</p>}
                {kittyDemoError && <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-xs text-amber-200/80">{kittyDemoError}</div>}
                {kittyDemoSettings && (
                  <>
                    <div className="mt-4 rounded-xl border border-cyan-500/15 bg-black/20 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-xs font-bold tracking-wider text-white">BINANCE SPOT DEMO STATUS</span>
                        <span className={kittyDemoSettings.ready ? "rounded-full border border-emerald-400/30 px-3 py-1 text-[10px] text-emerald-300" : "rounded-full border border-amber-400/30 px-3 py-1 text-[10px] text-amber-200"}>{kittyDemoSettings.ready ? "READY" : "NOT READY"}</span>
                      </div>
                      <p className="mt-2 text-xs text-cyan-100/55">
                        {kittyDemoSettings.enabled ? "AUTO DEMO TRADING ARMED" : "AUTO DEMO TRADING OFF"} · tracked Kitty position: {Number(kittyDemoSettings.position_btc || 0).toFixed(6)} BTC · poll interval: {kittyDemoSettings.poll_seconds || 900}s
                      </p>
                      {!kittyDemoSettings.ready && <p className="mt-2 text-xs text-amber-200/80">Check Railway: TRADING_MODE=demo, Binance Spot Demo API key/secret, and AGENT_TRADING_KILL_SWITCH=false. Keep TRADING_ENABLED=false; Kitty has a separate safety gate.</p>}
                      <SettingToggle
                        title="Enable Kitty Binance Demo auto-trading"
                        description={kittyDemoSettings.enabled ? "ON — Kitty may place capped BTCUSDT market orders after each new completed daily candle." : "OFF — no Binance orders will be submitted."}
                        checked={kittyDemoSettings.enabled}
                        onChange={(checked) => setKittyDemoSettings({ ...kittyDemoSettings, enabled: checked })}
                      />
                      <div className="grid gap-4 border-t border-cyan-500/10 pt-4 sm:grid-cols-2">
                        <label className="block text-xs text-cyan-100/65">
                          BTC per entry
                          <input type="number" min="0.000001" max="0.001" step="0.0001" value={kittyDemoSettings.order_btc}
                            onChange={(event) => setKittyDemoSettings({ ...kittyDemoSettings, order_btc: Number(event.target.value) })}
                            className="mt-2 w-full rounded-lg border border-cyan-500/20 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400/50" />
                          <span className="mt-1 block text-[10px] text-cyan-100/35">Hard cap: 0.001 BTC per entry.</span>
                        </label>
                        <label className="block text-xs text-cyan-100/65">
                          Maximum order value (USD)
                          <input type="number" min="1" max="25" step="1" value={kittyDemoSettings.max_notional_usd}
                            onChange={(event) => setKittyDemoSettings({ ...kittyDemoSettings, max_notional_usd: Number(event.target.value) })}
                            className="mt-2 w-full rounded-lg border border-cyan-500/20 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400/50" />
                          <span className="mt-1 block text-[10px] text-cyan-100/35">Hard cap: $25 per entry.</span>
                        </label>
                      </div>
                      <label className="mt-4 flex items-start gap-2 text-xs leading-relaxed text-amber-100/70">
                        <input type="checkbox" checked={kittyDemoAcknowledged} onChange={(event) => setKittyDemoAcknowledged(event.target.checked)} className="mt-0.5 accent-cyan-400" />
                        I understand Kitty is experimental, its training symbol is unconfirmed, and these are Binance demo orders only.
                      </label>
                    </div>
                    <div className="mt-4 flex flex-wrap items-center gap-3">
                      <button type="button" onClick={() => void saveKittyDemoSettings()}
                        disabled={kittyDemoSaving || kittyDemoLoading || kittyDemoSettings.order_btc <= 0 || kittyDemoSettings.order_btc > 0.001 || kittyDemoSettings.max_notional_usd <= 0 || kittyDemoSettings.max_notional_usd > 25 || (kittyDemoSettings.enabled && !kittyDemoAcknowledged)}
                        className="rounded-lg bg-cyan-400 px-4 py-2 font-mono-tech text-[10px] font-bold tracking-widest text-[#001018] transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50">
                        {kittyDemoSaving ? "APPLYING…" : kittyDemoSettings.enabled ? "ENABLE DEMO AUTO-TRADING" : "SAVE / PAUSE DEMO TRADING"}
                      </button>
                      {kittyDemoNotice && <span className="text-xs text-emerald-300">{kittyDemoNotice}</span>}
                    </div>
                    {kittyDemoSettings.recent_cycles && kittyDemoSettings.recent_cycles.length > 0 && (
                      <div className="mt-4 space-y-2">
                        <p className="text-[10px] font-bold tracking-widest text-cyan-100/45">RECENT DEMO CYCLES</p>
                        {kittyDemoSettings.recent_cycles.slice(0, 4).map((cycle, index) => (
                          <div key={String(cycle.candle_time || index)} className="rounded-lg border border-cyan-500/10 px-3 py-2 text-[10px] text-cyan-100/60">
                            {String(cycle.candle_time || "—")} · {String(cycle.status || "unknown")} · {String(cycle.signal || "no signal")} {cycle.side ? "· " + String(cycle.side) : ""}
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </section>

              <section className="kz-panel p-5 sm:p-6">
                <SectionTitle
                  title="CHAT BEHAVIOR"
                  subtitle="PERSONAL PREFERENCES"
                />
                {settingsError && (
                  <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-xs text-amber-200/80">
                    {settingsError}
                  </div>
                )}
                <div className="mt-4 divide-y divide-cyan-500/10">
                  <SettingToggle
                    title="Signals only when I ask"
                    description="Normal chat stays normal. No surprise trade ideas."
                    checked={preferences.signalsOnly}
                    onChange={(checked) => changePreference("signalsOnly", checked)}
                  />
                  <SettingToggle
                    title="Human-style replies"
                    description="Natural, relaxed tone instead of robotic answers."
                    checked={preferences.humanReplies}
                    onChange={(checked) => changePreference("humanReplies", checked)}
                  />
                  <SettingToggle
                    title="Remember my preferences"
                    description="Keep this device's chat preferences available between visits."
                    checked={preferences.rememberPreferences}
                    onChange={(checked) => changePreference("rememberPreferences", checked)}
                  />
                  <SettingToggle
                    title="Add risk reminder to signals"
                    description="Show a short not-financial-advice reminder under signals."
                    checked={preferences.riskReminder}
                    onChange={(checked) => changePreference("riskReminder", checked)}
                  />
                </div>
                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={() => void savePreferences()}
                    className="rounded-lg bg-cyan-400 px-4 py-2 font-mono-tech text-[10px] font-bold tracking-widest text-[#001018] transition hover:bg-cyan-300"
                  >
                    {savingPreferences ? "SAVING..." : saved ? "SAVED" : "SAVE CHANGES"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setPreferences(DEFAULT_PREFERENCES);
                      void savePreferences(DEFAULT_PREFERENCES);
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
