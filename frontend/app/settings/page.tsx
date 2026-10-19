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
import { api, type ChatBehaviorPreferences, type PlatformStatus, type KittyMultiPaperSettings, type KittyMultiPaperStatus, type KittyTechnicalSignal } from "@/lib/api";
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
const KITTY_MARKET_OPTIONS = ["BTC/USD", "BTC/USDT", "ETH/USD", "ETH/USDT", "SOL/USD", "BNB/USD", "XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"];

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
  const [kittyMultiSettings, setKittyMultiSettings] = useState<KittyMultiPaperSettings | null>(null);
  const [kittyMultiStatus, setKittyMultiStatus] = useState<KittyMultiPaperStatus | null>(null);
  const [kittyMultiLoading, setKittyMultiLoading] = useState(true);
  const [kittyMultiSaving, setKittyMultiSaving] = useState(false);
  const [kittyMultiRunning, setKittyMultiRunning] = useState(false);
  const [kittyMultiError, setKittyMultiError] = useState("");
  const [kittyMultiNotice, setKittyMultiNotice] = useState("");
  const [kittySignalSymbol, setKittySignalSymbol] = useState("BTC/USD");
  const [kittySignalTimeframe, setKittySignalTimeframe] = useState("1h");
  const [kittySignal, setKittySignal] = useState<KittyTechnicalSignal | null>(null);
  const [kittySignalLoading, setKittySignalLoading] = useState(false);
  const [kittySignalError, setKittySignalError] = useState("");

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
    Promise.all([api.getKittyMultiPaperSettings(), api.getKittyMultiPaperStatus()])
      .then(([settings, status]) => {
        if (!cancelled) {
          setKittyMultiSettings(settings);
          setKittyMultiStatus(status);
        }
      })
      .catch((error) => {
        if (!cancelled) setKittyMultiError(error instanceof Error ? error.message : "Could not load multi-market paper controls.");
      })
      .finally(() => {
        if (!cancelled) setKittyMultiLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const loadKittySignal = async () => {
    setKittySignalLoading(true);
    setKittySignalError("");
    setKittySignal(null);
    try {
      const result = await api.getKittyTechnicalSignal(kittySignalSymbol, kittySignalTimeframe);
      setKittySignal(result);
    } catch (error) {
      setKittySignalError(error instanceof Error ? error.message : "Live technical signal unavailable for this symbol/timeframe.");
    } finally {
      setKittySignalLoading(false);
    }
  };

  const saveKittyMultiSettings = async () => {
    if (!kittyMultiSettings) return;
    setKittyMultiSaving(true);
    setKittyMultiError("");
    setKittyMultiNotice("");
    try {
      const result = await api.saveKittyMultiPaperSettings({
        enabled: kittyMultiSettings.enabled,
        symbols: kittyMultiSettings.symbols,
        timeframe: kittyMultiSettings.timeframe,
        max_order_notional_usd: Number(kittyMultiSettings.max_order_notional_usd),
      });
      setKittyMultiSettings({
        enabled: result.enabled,
        symbols: result.symbols,
        timeframe: result.timeframe,
        max_order_notional_usd: result.max_order_notional_usd,
        mode: "paper_only",
        live_trading_enabled: false,
        message: result.message,
      });
      setKittyMultiStatus(result);
      setKittyMultiNotice(result.message || (result.enabled ? "Paper simulator enabled." : "Paper simulator paused."));
    } catch (error) {
      setKittyMultiError(error instanceof Error ? error.message : "Could not save paper settings.");
    } finally {
      setKittyMultiSaving(false);
    }
  };

  const runKittyMultiCycle = async () => {
    if (!kittyMultiSettings?.enabled) {
      setKittyMultiError("Enable and save the paper simulator before running a cycle.");
      return;
    }
    setKittyMultiRunning(true);
    setKittyMultiError("");
    setKittyMultiNotice("");
    try {
      const result = await api.runKittyMultiPaperCycle();
      const status = await api.getKittyMultiPaperStatus();
      setKittyMultiStatus(status);
      const available = result.results?.filter((row) => row.status !== "unavailable").length || 0;
      setKittyMultiNotice(`Paper cycle finished: ${available} market(s) processed; see results below.`);
    } catch (error) {
      setKittyMultiError(error instanceof Error ? error.message : "Could not run a paper cycle.");
    } finally {
      setKittyMultiRunning(false);
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
                <SectionTitle title="KITTY MARKET SIGNALS" subtitle="CRYPTO · GOLD · FOREX · COMPLETED CANDLES" />
                <p className="mt-3 text-xs leading-relaxed text-cyan-100/55">
                  Choose a supported market and timeframe to calculate a transparent EMA/RSI/MACD confluence signal. This is not Kitty&apos;s trained BTC classifier and has not been proven profitable. It never places orders.
                </p>
                <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_140px_auto]">
                  <label className="block text-xs text-cyan-100/65">Market
                    <select value={kittySignalSymbol} onChange={(event) => setKittySignalSymbol(event.target.value)} className="mt-2 w-full rounded-lg border border-cyan-500/20 bg-black/30 px-3 py-2 text-sm text-white">
                      <option value="BTC/USD">BTC/USD</option><option value="BTC/USDT">BTC/USDT</option><option value="ETH/USD">ETH/USD</option><option value="ETH/USDT">ETH/USDT</option><option value="SOL/USD">SOL/USD</option><option value="BNB/USD">BNB/USD</option><option value="XAU/USD">Gold · XAU/USD</option><option value="EUR/USD">EUR/USD</option><option value="GBP/USD">GBP/USD</option><option value="USD/JPY">USD/JPY</option><option value="AUD/USD">AUD/USD</option>
                    </select>
                  </label>
                  <label className="block text-xs text-cyan-100/65">Timeframe
                    <select value={kittySignalTimeframe} onChange={(event) => setKittySignalTimeframe(event.target.value)} className="mt-2 w-full rounded-lg border border-cyan-500/20 bg-black/30 px-3 py-2 text-sm text-white">
                      <option value="15m">15 minutes</option><option value="30m">30 minutes</option><option value="1h">1 hour</option><option value="2h">2 hours</option><option value="4h">4 hours</option><option value="1d">1 day</option>
                    </select>
                  </label>
                  <button type="button" onClick={() => void loadKittySignal()} disabled={kittySignalLoading} className="self-end rounded-lg bg-cyan-400 px-4 py-2 font-mono-tech text-[10px] font-bold tracking-widest text-[#001018] transition hover:bg-cyan-300 disabled:opacity-50">{kittySignalLoading ? "ANALYZING…" : "GET SIGNAL"}</button>
                </div>
                {kittySignalError && <p className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-200/80">{kittySignalError}</p>}
                {kittySignal && <div className="mt-4 rounded-xl border border-cyan-500/15 bg-black/20 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-bold tracking-wider text-white">{kittySignal.symbol} · {kittySignal.timeframe}</span>
                    <span className={kittySignal.signal === "BUY" ? "rounded-full border border-emerald-400/30 px-3 py-1 text-xs font-bold text-emerald-300" : kittySignal.signal === "SELL" ? "rounded-full border border-rose-400/30 px-3 py-1 text-xs font-bold text-rose-300" : "rounded-full border border-amber-400/30 px-3 py-1 text-xs font-bold text-amber-200"}>{kittySignal.signal}</span>
                  </div>
                  <div className="mt-3 grid gap-3 sm:grid-cols-3">
                    <Row label="LATEST PRICE" value={String(kittySignal.price)} />
                    <Row label="CONFIRMATIONS" value={kittySignal.confirmation_count + " / " + kittySignal.confirmations_required} />
                    <Row label="RSI (14)" value={String(kittySignal.indicators.rsi_14)} />
                  </div>
                  <p className="mt-3 text-[10px] text-cyan-100/50">Completed candle: {kittySignal.completed_candle_time} · {Math.round(kittySignal.confidence_score * 100)}% rule confirmations (not a probability of profit).</p>
                  <div className="mt-3 space-y-1">{kittySignal.reasons.map((reason) => <p key={reason} className="text-xs text-cyan-100/65">• {reason}</p>)}</div>
                  {kittySignal.signal !== "NO TRADE" && <div className="mt-3 grid gap-3 sm:grid-cols-3">
                    <Row label="STOP REFERENCE" value={kittySignal.risk_levels.stop_reference == null ? "—" : String(kittySignal.risk_levels.stop_reference)} />
                    <Row label="TARGET 1 REFERENCE" value={kittySignal.risk_levels.target_1_reference == null ? "—" : String(kittySignal.risk_levels.target_1_reference)} />
                    <Row label="TARGET 2 REFERENCE" value={kittySignal.risk_levels.target_2_reference == null ? "—" : String(kittySignal.risk_levels.target_2_reference)} />
                  </div>}
                  <p className="mt-3 text-[10px] leading-relaxed text-amber-100/60">{kittySignal.warning}</p>
                </div>}
              </section>

              <section className="kz-panel p-5 sm:p-6">
                <SectionTitle title="KITTY MULTI-MARKET PAPER TRADING" subtitle="BTC · GOLD · CRYPTO · FOREX · SIMULATED ONLY" />
                <p className="mt-3 text-xs leading-relaxed text-cyan-100/55">
                  Kitty evaluates completed candles and records simulated buys/sells in an isolated paper ledger. No broker, exchange, Binance demo, or live-order connector is called. The signal rules are experimental; this panel is for testing and collecting paper results, not claiming profitability.
                </p>
                {kittyMultiLoading && <p className="mt-4 text-xs text-cyan-200/60">Loading paper trading controls…</p>}
                {kittyMultiError && <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-xs text-amber-200/80">{kittyMultiError}</div>}
                {kittyMultiSettings && (
                  <>
                    <div className="mt-4 rounded-xl border border-cyan-500/15 bg-black/20 p-4">
                      <SettingToggle
                        title="Enable multi-market paper simulator"
                        description={kittyMultiSettings.enabled ? "ON — the background worker checks the selected markets at the chosen timeframe." : "OFF — no automatic paper cycles will run until you enable and save."}
                        checked={kittyMultiSettings.enabled}
                        onChange={(checked) => setKittyMultiSettings({ ...kittyMultiSettings, enabled: checked })}
                      />
                      <div className="border-t border-cyan-500/10 pt-4">
                        <p className="mb-3 text-xs text-cyan-100/65">Markets to paper trade</p>
                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                          {KITTY_MARKET_OPTIONS.map((symbol) => (
                            <label key={symbol} className="flex items-center gap-2 text-xs text-cyan-100/70">
                              <input
                                type="checkbox"
                                checked={kittyMultiSettings.symbols.includes(symbol)}
                                onChange={(event) => {
                                  const symbols = event.target.checked
                                    ? [...kittyMultiSettings.symbols, symbol]
                                    : kittyMultiSettings.symbols.filter((item) => item !== symbol);
                                  setKittyMultiSettings({ ...kittyMultiSettings, symbols });
                                }}
                                className="accent-cyan-400"
                              />
                              {symbol === "XAU/USD" ? "Gold · XAU/USD" : symbol}
                            </label>
                          ))}
                        </div>
                      </div>
                      <div className="mt-4 grid gap-4 border-t border-cyan-500/10 pt-4 sm:grid-cols-2">
                        <label className="block text-xs text-cyan-100/65">
                          Candle timeframe
                          <select value={kittyMultiSettings.timeframe} onChange={(event) => setKittyMultiSettings({ ...kittyMultiSettings, timeframe: event.target.value })}
                            className="mt-2 w-full rounded-lg border border-cyan-500/20 bg-black/30 px-3 py-2 text-sm text-white">
                            <option value="15m">15 minutes</option><option value="30m">30 minutes</option><option value="1h">1 hour</option><option value="2h">2 hours</option><option value="4h">4 hours</option><option value="1d">1 day</option>
                          </select>
                        </label>
                        <label className="block text-xs text-cyan-100/65">
                          Max simulated order notional (USD)
                          <input type="number" min="1" max="250" step="5" value={kittyMultiSettings.max_order_notional_usd}
                            onChange={(event) => setKittyMultiSettings({ ...kittyMultiSettings, max_order_notional_usd: Number(event.target.value) })}
                            className="mt-2 w-full rounded-lg border border-cyan-500/20 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400/50" />
                          <span className="mt-1 block text-[10px] text-cyan-100/35">Hard cap: $250 per simulated entry.</span>
                        </label>
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap items-center gap-3">
                      <button type="button" onClick={() => void saveKittyMultiSettings()}
                        disabled={kittyMultiSaving || kittyMultiLoading || kittyMultiSettings.symbols.length === 0 || kittyMultiSettings.max_order_notional_usd <= 0 || kittyMultiSettings.max_order_notional_usd > 250}
                        className="rounded-lg bg-cyan-400 px-4 py-2 font-mono-tech text-[10px] font-bold tracking-widest text-[#001018] transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50">
                        {kittyMultiSaving ? "SAVING…" : "SAVE PAPER SETTINGS"}
                      </button>
                      <button type="button" onClick={() => void runKittyMultiCycle()}
                        disabled={kittyMultiRunning || kittyMultiLoading || !kittyMultiSettings.enabled}
                        className="rounded-lg border border-cyan-500/30 px-4 py-2 font-mono-tech text-[10px] font-bold tracking-widest text-cyan-200 transition hover:bg-cyan-500/10 disabled:cursor-not-allowed disabled:opacity-50">
                        {kittyMultiRunning ? "RUNNING…" : "RUN PAPER CYCLE NOW"}
                      </button>
                      {kittyMultiNotice && <span className="text-xs text-emerald-300">{kittyMultiNotice}</span>}
                    </div>
                    {kittyMultiStatus && (
                      <div className="mt-4 rounded-xl border border-cyan-500/15 bg-black/20 p-4">
                        <div className="grid gap-3 sm:grid-cols-3">
                          <Row label="PAPER CASH" value={`$${Number(kittyMultiStatus.cash_usd).toFixed(2)}`} />
                          <Row label="EQUITY" value={`$${Number(kittyMultiStatus.equity_usd).toFixed(2)}`} />
                          <Row label="OPEN POSITIONS" value={String(kittyMultiStatus.positions.length)} />
                        </div>
                        <p className="mt-3 text-[10px] leading-relaxed text-amber-100/60">{kittyMultiStatus.warning}</p>
                        {kittyMultiStatus.recent_orders.length > 0 && (
                          <div className="mt-4 space-y-2">
                            <p className="text-[10px] font-bold tracking-widest text-cyan-100/45">RECENT SIMULATED ORDERS</p>
                            {kittyMultiStatus.recent_orders.slice(0, 6).map((order, index) => (
                              <div key={String(order.id || index)} className="rounded-lg border border-cyan-500/10 px-3 py-2 text-[10px] text-cyan-100/60">
                                {String(order.symbol)} · {String(order.side)} · {Number(order.quantity).toPrecision(5)} @ {Number(order.price).toFixed(5)} · fee ${Number(order.fee_usd).toFixed(3)}
                              </div>
                            ))}
                          </div>
                        )}
                        {kittyMultiStatus.recent_cycles.some((cycle) => cycle.status === "unavailable") && (
                          <p className="mt-3 text-[10px] text-amber-200/70">Some markets did not return enough fresh candles. They are skipped, not simulated with fake prices.</p>
                        )}
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
