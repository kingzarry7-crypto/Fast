"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";

type CategoryId =
  | "PROFILE"
  | "AI BEHAVIOUR"
  | "MEMORY"
  | "VOICE"
  | "VISION"
  | "NOTIFICATIONS"
  | "TRADING"
  | "AGENTS"
  | "APPEARANCE"
  | "SECURITY"
  | "PRIVACY"
  | "SUBSCRIPTION"
  | "SYSTEM";

type SaveStatus = "IDLE" | "SAVING" | "SAVED";

type SettingsState = {
  displayName: string;
  username: string;

  responseStyle: string;
  proactiveSuggestions: boolean;
  contextAwareness: boolean;

  saveConversations: boolean;
  useRelevantMemory: boolean;
  personalContext: boolean;

  voiceOutput: boolean;
  autoPlay: boolean;
  voiceSpeed: string;

  imageAnalysis: boolean;
  docAnalysis: boolean;

  notifAi: boolean;
  notifMarket: boolean;
  notifNews: boolean;
  notifAgent: boolean;
  notifSecurity: boolean;

  defaultMarket: string;
  defaultTimeframe: string;
  riskPreference: string;

  agentPermRead: boolean;
  agentPermAnalyze: boolean;
  agentApproval: boolean;

  theme: string;
  hudIntensity: string;
};

const STORAGE_KEY = "king_zarry_web_settings";

const defaultSettings: SettingsState = {
  displayName: "KING ZARRY",
  username: "kingzarry",

  responseStyle: "BALANCED",
  proactiveSuggestions: true,
  contextAwareness: true,

  saveConversations: true,
  useRelevantMemory: true,
  personalContext: true,

  voiceOutput: true,
  autoPlay: false,
  voiceSpeed: "1.0x",

  imageAnalysis: true,
  docAnalysis: true,

  notifAi: true,
  notifMarket: true,
  notifNews: true,
  notifAgent: true,
  notifSecurity: true,

  defaultMarket: "BTC/USDT",
  defaultTimeframe: "15M",
  riskPreference: "MODERATE",

  agentPermRead: true,
  agentPermAnalyze: true,
  agentApproval: true,

  theme: "DARK",
  hudIntensity: "HIGH",
};

const navItems = [
  { label: "HOME", href: "/" },
  { label: "CHAT", href: "/chat" },
  { label: "MARKETS", href: "/markets" },
  { label: "SIGNALS", href: "/signals" },
  { label: "NEWS", href: "/news" },
  { label: "ALERTS", href: "/alerts" },
  { label: "HISTORY", href: "/history" },
  { label: "PRICING", href: "/pricing" },
  { label: "SETTINGS", href: "/settings" },
];

const categories: CategoryId[] = [
  "PROFILE",
  "AI BEHAVIOUR",
  "MEMORY",
  "VOICE",
  "VISION",
  "NOTIFICATIONS",
  "TRADING",
  "AGENTS",
  "APPEARANCE",
  "SECURITY",
  "PRIVACY",
  "SUBSCRIPTION",
  "SYSTEM",
];

const coreNodes = [
  { label: "IDENTITY", status: "LOCAL" },
  { label: "AI", status: "READY" },
  { label: "MEMORY", status: "READY" },
  { label: "VOICE", status: "READY" },
  { label: "VISION", status: "READY" },
  { label: "AGENTS", status: "READY" },
  { label: "TOOLS", status: "READY" },
  { label: "SECURITY", status: "READY" },
];

function Toggle({
  enabled,
  onChange,
}: {
  enabled: boolean;
  onChange: () => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={onChange}
      className={`h-6 w-12 rounded-full p-1 transition ${
        enabled
          ? "bg-cyan-500 shadow-[0_0_10px_rgba(0,240,255,0.3)]"
          : "border border-cyan-500/40 bg-cyan-950"
      }`}
    >
      <span
        className={`block h-4 w-4 rounded-full bg-black transition-transform ${
          enabled ? "translate-x-6" : "translate-x-0"
        }`}
      />
    </button>
  );
}

function SettingToggle({
  label,
  description,
  enabled,
  onChange,
}: {
  label: string;
  description: string;
  enabled: boolean;
  onChange: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-4">
      <div>
        <span className="block font-mono text-xs font-bold text-white">
          {label}
        </span>

        <span className="mt-1 block font-mono text-[10px] leading-relaxed text-cyan-400/60">
          {description}
        </span>
      </div>

      <Toggle enabled={enabled} onChange={onChange} />
    </div>
  );
}

export default function KingZarrySettingsPage() {
  const [activeTab, setActiveTab] =
    useState<CategoryId>("PROFILE");

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [saveStatus, setSaveStatus] =
    useState<SaveStatus>("IDLE");

  const [settings, setSettings] =
    useState<SettingsState>(defaultSettings);

  const [loaded, setLoaded] = useState(false);

  /*
   * Load saved browser settings.
   *
   * This is intentionally local for now.
   * It does not pretend to be a server/database save.
   */
  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);

      if (stored) {
        const parsed = JSON.parse(stored);

        setSettings({
          ...defaultSettings,
          ...parsed,
        });
      }
    } catch {
      // Keep defaults if local storage is unavailable/corrupt.
    } finally {
      setLoaded(true);
    }
  }, []);

  const updateSetting = <K extends keyof SettingsState>(
    key: K,
    value: SettingsState[K]
  ) => {
    setSettings((current) => ({
      ...current,
      [key]: value,
    }));

    setSaveStatus("IDLE");
  };

  const handleSave = () => {
    setSaveStatus("SAVING");

    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(settings)
      );

      window.setTimeout(() => {
        setSaveStatus("SAVED");

        window.setTimeout(() => {
          setSaveStatus("IDLE");
        }, 2200);
      }, 500);
    } catch {
      setSaveStatus("IDLE");
    }
  };

  const handleReset = () => {
    setSettings(defaultSettings);

    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore storage errors.
    }

    setSaveStatus("IDLE");
  };

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#03060a] font-sans text-cyan-100 selection:bg-cyan-500 selection:text-black">
      {/* BACKGROUND */}
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#072438] via-[#020b14] to-[#010408]" />

      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(to_right,#091a2815_1px,transparent_1px),linear-gradient(to_bottom,#091a2815_1px,transparent_1px)] bg-[size:32px_32px]" />

      <div className="pointer-events-none fixed inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,240,255,0.012)_3px,transparent_4px)]" />

      <div className="pointer-events-none fixed left-[15%] top-[-10%] h-[600px] w-[600px] rounded-full bg-cyan-600/10 blur-[140px]" />

      <div className="pointer-events-none fixed bottom-[-10%] right-[15%] h-[600px] w-[600px] rounded-full bg-indigo-600/10 blur-[140px]" />

      {/* HEADER */}
      <header className="relative z-30 border-b border-cyan-500/15 bg-[#030810]/85 px-4 py-4 backdrop-blur-xl sm:px-6">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-cyan-500/40 bg-cyan-950/30 text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
              <span className="text-lg font-extrabold tracking-wider">
                KZ
              </span>

              <span className="absolute -right-1 -top-1 flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-500" />
              </span>
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold tracking-widest text-white sm:text-base">
                  KING ZARRY AI
                </h1>

                <span className="hidden rounded border border-cyan-500/30 bg-cyan-950/40 px-1.5 py-0.5 font-mono text-[8px] tracking-wider text-cyan-400 sm:inline-block">
                  SYSTEM CONTROL
                </span>
              </div>

              <div className="flex items-center gap-2 font-mono text-[9px] text-cyan-400/70">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />
                <span>CONFIGURATION</span>
              </div>
            </div>
          </Link>

          {/* DESKTOP NAV */}
          <nav className="hidden items-center gap-1 rounded-lg border border-cyan-500/10 bg-cyan-950/20 p-1 lg:flex">
            {navItems.map((item) => {
              const active = item.label === "SETTINGS";

              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className={`rounded px-3 py-1.5 font-mono text-xs tracking-wider transition ${
                    active
                      ? "border border-cyan-500/40 bg-cyan-500/20 text-cyan-200 shadow-[0_0_10px_rgba(0,240,255,0.2)]"
                      : "text-cyan-400/60 hover:bg-cyan-500/10 hover:text-cyan-200"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* MOBILE MENU */}
          <button
            type="button"
            aria-label="Toggle navigation"
            onClick={() =>
              setMobileMenuOpen((current) => !current)
            }
            className="rounded border border-cyan-500/30 bg-cyan-950/40 p-2 text-cyan-400 transition hover:bg-cyan-500/20 lg:hidden"
          >
            {mobileMenuOpen ? (
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            ) : (
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            )}
          </button>
        </div>
      </header>

      {/* MOBILE NAV */}
      {mobileMenuOpen && (
        <div className="relative z-30 border-b border-cyan-500/30 bg-[#040c16]/95 p-4 backdrop-blur-xl lg:hidden">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {navItems.map((item) => {
              const active = item.label === "SETTINGS";

              return (
                <Link
                  key={item.label}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`rounded border p-2 text-center font-mono text-[10px] tracking-wider transition ${
                    active
                      ? "border-cyan-500/50 bg-cyan-500/20 text-cyan-300"
                      : "border-cyan-500/10 text-cyan-400/70 hover:bg-cyan-500/10"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* MAIN */}
      <main className="relative z-20 mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 md:py-8">
        {/* TITLE */}
        <section className="flex flex-col gap-4 border-b border-cyan-500/10 pb-5 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400 shadow-[0_0_10px_#00f0ff]" />

              <span className="font-mono text-[9px] tracking-[0.25em] text-cyan-400/50">
                CONTROL MODULE
              </span>
            </div>

            <h2 className="text-2xl font-bold tracking-widest text-white">
              SYSTEM SETTINGS
            </h2>

            <p className="mt-2 max-w-2xl font-mono text-xs leading-relaxed text-cyan-400/60">
              Configure your KING ZARRY AI environment, preferences,
              memory and interface behavior.
            </p>
          </div>

          <div className="w-full max-w-sm rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-4 backdrop-blur-md">
            <div className="mb-2 flex items-center justify-between font-mono text-[9px] tracking-wider text-cyan-400/60">
              <span>SETTINGS STORAGE</span>
              <span className="text-cyan-400">
                {loaded ? "READY" : "LOADING"}
              </span>
            </div>

            <div className="flex items-center gap-2 font-mono text-xs text-cyan-100">
              <span className="h-2 w-2 rounded-full bg-cyan-400" />
              BROWSER PREFERENCE STORAGE
            </div>

            <p className="mt-2 font-mono text-[8px] leading-relaxed text-cyan-400/40">
              These preferences currently persist on this browser.
              Account-level synchronization can be connected later.
            </p>
          </div>
        </section>

        {/* CORE HUD */}
        <section className="relative overflow-hidden rounded-2xl border border-cyan-500/20 bg-[#020914]/80 p-5 backdrop-blur-md sm:p-6">
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff08_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff08_1px,transparent_1px)] bg-[size:16px_16px]" />

          <div className="relative z-10 flex flex-col items-center gap-8 lg:flex-row">
            {/* CORE */}
            <div className="flex w-full flex-col items-center lg:w-1/3">
              <div className="relative flex h-36 w-36 items-center justify-center">
                <div className="absolute inset-0 animate-[spin_25s_linear_infinite] rounded-full border border-cyan-500/30" />

                <div className="absolute inset-2 animate-[spin_18s_linear_infinite_reverse] rounded-full border border-dashed border-cyan-400/20" />

                <div className="absolute inset-5 animate-pulse rounded-full bg-cyan-500/10 blur-md shadow-[0_0_25px_rgba(0,240,255,0.3)]" />

                <div className="relative z-10 flex h-16 w-16 flex-col items-center justify-center rounded-full border border-cyan-400/60 bg-[#031322] shadow-[inset_0_0_15px_rgba(0,240,255,0.4)]">
                  <span className="text-lg font-extrabold tracking-tighter text-white">
                    KZ
                  </span>

                  <span className="-mt-1 font-mono text-[8px] tracking-widest text-cyan-400/80">
                    CORE
                  </span>
                </div>

                <div className="absolute h-full w-full animate-[spin_10s_linear_infinite]">
                  <div className="absolute left-1/2 top-0 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-cyan-300 shadow-[0_0_8px_#00f0ff]" />
                </div>
              </div>

              <div className="mt-3 text-center">
                <div className="font-mono text-xs font-bold tracking-widest text-cyan-200">
                  SYSTEM CONTROL CORE
                </div>

                <div className="mt-1 font-mono text-[9px] text-cyan-500/60">
                  PERSONAL CONFIGURATION
                </div>
              </div>
            </div>

            {/* NODES */}
            <div className="grid w-full grid-cols-2 gap-2.5 sm:grid-cols-4 lg:w-2/3">
              {coreNodes.map((node) => (
                <div
                  key={node.label}
                  className="rounded-xl border border-cyan-500/15 bg-cyan-950/20 p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <span className="block font-mono text-xs font-bold text-white">
                        {node.label}
                      </span>

                      <span className="mt-1 block font-mono text-[8px] text-cyan-400/50">
                        CONFIGURATION
                      </span>
                    </div>

                    <span className="rounded border border-cyan-500/30 bg-cyan-500/20 px-1.5 py-0.5 font-mono text-[8px] text-cyan-300">
                      {node.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* SETTINGS GRID */}
        <section className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* SIDEBAR */}
          <aside className="lg:col-span-4">
            <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-4 backdrop-blur-md">
              <div className="mb-3 border-b border-cyan-500/15 px-3 pb-3 font-mono text-[10px] font-bold tracking-widest text-cyan-400/70">
                CONTROL CONSOLE
              </div>

              <div className="space-y-1">
                {categories.map((category) => {
                  const active = activeTab === category;

                  return (
                    <button
                      key={category}
                      type="button"
                      onClick={() => setActiveTab(category)}
                      className={`flex w-full items-center justify-between rounded-xl border px-3.5 py-2.5 text-left font-mono text-xs tracking-wider transition ${
                        active
                          ? "border-cyan-400 bg-cyan-500/20 text-cyan-300 shadow-[0_0_12px_rgba(0,240,255,0.15)]"
                          : "border-cyan-500/10 bg-cyan-950/20 text-cyan-400/70 hover:bg-cyan-500/10 hover:text-cyan-200"
                      }`}
                    >
                      <span>{category}</span>

                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          active
                            ? "animate-pulse bg-cyan-400"
                            : "bg-cyan-900"
                        }`}
                      />
                    </button>
                  );
                })}
              </div>
            </div>
          </aside>

          {/* CONTENT */}
          <div className="lg:col-span-8">
            <div className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md sm:p-6">
              {/* PROFILE */}
              {activeTab === "PROFILE" && (
                <div className="space-y-6">
                  <SectionHeader
                    title="AI USER IDENTITY"
                    status="ACCOUNT PROFILE"
                  />

                  <div className="flex items-center gap-4 rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-4">
                    <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl border border-cyan-400 bg-cyan-950/40 font-mono text-xl font-bold text-cyan-300 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                      KZ
                    </div>

                    <div>
                      <h4 className="font-mono text-sm font-bold text-white">
                        {settings.displayName}
                      </h4>

                      <span className="mt-1 block font-mono text-[10px] text-cyan-400/60">
                        @{settings.username}
                      </span>

                      <span className="mt-1 block font-mono text-[9px] text-cyan-400/40">
                        AUTHENTICATED WEB ACCOUNT
                      </span>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <InputField
                      label="DISPLAY NAME"
                      value={settings.displayName}
                      onChange={(value) =>
                        updateSetting("displayName", value)
                      }
                    />

                    <InputField
                      label="USERNAME"
                      value={settings.username}
                      onChange={(value) =>
                        updateSetting("username", value)
                      }
                    />
                  </div>

                  <div className="rounded-xl border border-cyan-500/15 bg-cyan-950/10 p-4 font-mono text-[9px] leading-relaxed text-cyan-400/50">
                    Your authenticated email address is managed by the
                    account system. It is not hardcoded into this
                    settings interface.
                  </div>
                </div>
              )}

              {/* AI BEHAVIOUR */}
              {activeTab === "AI BEHAVIOUR" && (
                <div className="space-y-6">
                  <SectionHeader
                    title="AI COMMUNICATION & BEHAVIOUR"
                    status="PREFERENCE CONTROL"
                  />

                  <ChoiceGroup
                    label="RESPONSE STYLE"
                    options={[
                      "CONCISE",
                      "BALANCED",
                      "DETAILED",
                      "CREATIVE",
                      "FORMAL",
                    ]}
                    value={settings.responseStyle}
                    onChange={(value) =>
                      updateSetting("responseStyle", value)
                    }
                  />

                  <div className="space-y-3">
                    <SettingToggle
                      label="PROACTIVE SUGGESTIONS"
                      description="Allow the interface to offer contextual follow-up ideas."
                      enabled={settings.proactiveSuggestions}
                      onChange={() =>
                        updateSetting(
                          "proactiveSuggestions",
                          !settings.proactiveSuggestions
                        )
                      }
                    />

                    <SettingToggle
                      label="CONTEXT AWARENESS"
                      description="Use the active conversation context when available."
                      enabled={settings.contextAwareness}
                      onChange={() =>
                        updateSetting(
                          "contextAwareness",
                          !settings.contextAwareness
                        )
                      }
                    />
                  </div>
                </div>
              )}

              {/* MEMORY */}
              {activeTab === "MEMORY" && (
                <div className="space-y-6">
                  <SectionHeader
                    title="MEMORY SYSTEM"
                    status="PREFERENCE CONTROL"
                  />

                  <div className="space-y-3">
                    <SettingToggle
                      label="SAVE CONVERSATIONS"
                      description="Allow conversation history to be retained by the web application."
                      enabled={settings.saveConversations}
                      onChange={() =>
                        updateSetting(
                          "saveConversations",
                          !settings.saveConversations
                        )
                      }
                    />

                    <SettingToggle
                      label="USE RELEVANT MEMORY"
                      description="Allow relevant stored context to influence future conversations."
                      enabled={settings.useRelevantMemory}
                      onChange={() =>
                        updateSetting(
                          "useRelevantMemory",
                          !settings.useRelevantMemory
                        )
                      }
                    />

                    <SettingToggle
                      label="PERSONAL CONTEXT"
                      description="Use your saved preferences when supported by the AI system."
                      enabled={settings.personalContext}
                      onChange={() =>
                        updateSetting(
                          "personalContext",
                          !settings.personalContext
                        )
                      }
                    />
                  </div>

                  <div className="rounded-xl border border-red-500/20 bg-red-950/10 p-4">
                    <h4 className="font-mono text-xs font-bold text-red-400">
                      MEMORY MANAGEMENT
                    </h4>

                    <p className="mt-1 font-mono text-[10px] leading-relaxed text-red-200/60">
                      Memory deletion requires a backend action. This
                      button is intentionally not pretending to delete
                      your server-side memory.
                    </p>

                    <Link
                      href="/history"
                      className="mt-3 inline-flex rounded-lg border border-red-500/40 bg-red-500/10 px-3.5 py-2 font-mono text-[10px] text-red-300 transition hover:bg-red-500/20"
                    >
                      VIEW HISTORY
                    </Link>
                  </div>
                </div>
              )}

              {/* VOICE */}
              {activeTab === "VOICE" && (
                <div className="space-y-6">
                  <SectionHeader
                    title="VOICE SYSTEM"
                    status="PREFERENCE CONTROL"
                  />

                  <div className="flex items-center justify-between rounded-xl border border-cyan-500/30 bg-cyan-950/30 p-4">
                    <span className="font-mono text-[10px] text-cyan-300">
                      VOICE OUTPUT CONFIGURATION
                    </span>

                    <div className="flex items-end gap-1">
                      {[40, 70, 30, 90, 50, 80, 20, 60, 100, 45].map(
                        (height, index) => (
                          <div
                            key={index}
                            style={{ height: `${height * 0.3}px` }}
                            className="w-1.5 rounded-full bg-cyan-400/80"
                          />
                        )
                      )}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <SettingToggle
                      label="VOICE OUTPUT"
                      description="Enable audio response generation where supported."
                      enabled={settings.voiceOutput}
                      onChange={() =>
                        updateSetting(
                          "voiceOutput",
                          !settings.voiceOutput
                        )
                      }
                    />

                    <SettingToggle
                      label="AUTO PLAY AUDIO"
                      description="Automatically play generated audio responses."
                      enabled={settings.autoPlay}
                      onChange={() =>
                        updateSetting(
                          "autoPlay",
                          !settings.autoPlay
                        )
                      }
                    />
                  </div>

                  <ChoiceGroup
                    label="VOICE SPEED"
                    options={["0.8x", "1.0x", "1.2x", "1.5x"]}
                    value={settings.voiceSpeed}
                    onChange={(value) =>
                      updateSetting("voiceSpeed", value)
                    }
                  />
                </div>
              )}

              {/* VISION */}
              {activeTab === "VISION" && (
                <div className="space-y-6">
                  <SectionHeader
                    title="VISION SYSTEM"
                    status="PREFERENCE CONTROL"
                  />

                  <div className="space-y-3">
                    <SettingToggle
                      label="IMAGE ANALYSIS"
                      description="Enable image analysis preferences for supported uploads."
                      enabled={settings.imageAnalysis}
                      onChange={() =>
                        updateSetting(
                          "imageAnalysis",
                          !settings.imageAnalysis
                        )
                      }
                    />

                    <SettingToggle
                      label="DOCUMENT ANALYSIS"
                      description="Enable document and visual-content analysis preferences."
                      enabled={settings.docAnalysis}
                      onChange={() =>
                        updateSetting(
                          "docAnalysis",
                          !settings.docAnalysis
                        )
                      }
                    />
                  </div>

                  <div className="rounded-xl border border-cyan-500/15 bg-cyan-950/10 p-4 font-mono text-[9px] leading-relaxed text-cyan-400/50">
                    These settings control your preference state. Actual
                    model availability depends on the connected AI
                    provider and backend configuration.
                  </div>
                </div>
              )}

              {/* NOTIFICATIONS */}
              {activeTab === "NOTIFICATIONS" && (
                <div className="space-y-6">
                  <SectionHeader
                    title="INTELLIGENCE NOTIFICATIONS"
                    status="PREFERENCE CONTROL"
                  />

                  <div className="space-y-3">
                    <SettingToggle
                      label="AI RESPONSES"
                      description="Notification preference for supported AI activity."
                      enabled={settings.notifAi}
                      onChange={() =>
                        updateSetting("notifAi", !settings.notifAi)
                      }
                    />

                    <SettingToggle
                      label="MARKET ALERTS"
                      description="Notification preference for supported market alerts."
                      enabled={settings.notifMarket}
                      onChange={() =>
                        updateSetting(
                          "notifMarket",
                          !settings.notifMarket
                        )
                      }
                    />

                    <SettingToggle
                      label="NEWS ALERTS"
                      description="Notification preference for supported news alerts."
                      enabled={settings.notifNews}
                      onChange={() =>
                        updateSetting(
                          "notifNews",
                          !settings.notifNews
                        )
                      }
                    />

                    <SettingToggle
                      label="AGENT ACTIVITY"
                      description="Notification preference for supported agent events."
                      enabled={settings.notifAgent}
                      onChange={() =>
                        updateSetting(
                          "notifAgent",
                          !settings.notifAgent
                        )
                      }
                    />

                    <SettingToggle
                      label="SECURITY ALERTS"
                      description="Notification preference for security-related events."
                      enabled={settings.notifSecurity}
                      onChange={() =>
                        updateSetting(
                          "notifSecurity",
                          !settings.notifSecurity
                        )
                      }
                    />
                  </div>
                </div>
              )}

              {/* TRADING */}
              {activeTab === "TRADING" && (
                <div className="space-y-6">
                  <SectionHeader
                    title="MARKET INTELLIGENCE"
                    status="PREFERENCE CONTROL"
                  />

                  <div className="grid gap-4 md:grid-cols-2">
                    <SelectField
                      label="DEFAULT MARKET"
                      value={settings.defaultMarket}
                      onChange={(value) =>
                        updateSetting("defaultMarket", value)
                      }
                      options={[
                        "BTC/USDT",
                        "ETH/USDT",
                        "SOL/USDT",
                        "XAU/USD",
                        "EUR/USD",
                        "GBP/USD",
                      ]}
                    />

                    <SelectField
                      label="DEFAULT TIMEFRAME"
                      value={settings.defaultTimeframe}
                      onChange={(value) =>
                        updateSetting("defaultTimeframe", value)
                      }
                      options={["15M", "1H", "4H", "1D"]}
                    />
                  </div>

                  <ChoiceGroup
                    label="RISK PREFERENCE"
                    options={[
                      "CONSERVATIVE",
                      "MODERATE",
                      "AGGRESSIVE",
                    ]}
                    value={settings.riskPreference}
                    onChange={(value) =>
                      updateSetting("riskPreference", value)
                    }
                  />

                  <div className="rounded-xl border border-amber-500/20 bg-amber-950/10 p-4 font-mono text-[9px] leading-relaxed text-amber-200/60">
                    Trading preferences do not execute trades and do
                    not guarantee market outcomes. They are preference
                    settings for supported AI analysis.
                  </div>
                </div>
              )}

              {/* AGENTS */}
              {activeTab === "AGENTS" && (
                <div className="space-y-6">
                  <SectionHeader
                    title="AI AGENT CONTROL"
                    status="PERMISSION PREFERENCES"
                  />

                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {["READ", "ANALYZE", "DRAFT", "ACTION"].map(
                      (step, index) => (
                        <div
                          key={step}
                          className="rounded-lg border border-cyan-500/20 bg-cyan-950/20 p-3 text-center"
                        >
                          <span className="block font-mono text-[8px] text-cyan-400/50">
                            STEP 0{index + 1}
                          </span>

                          <span className="mt-1 block font-mono text-[10px] font-bold text-cyan-100">
                            {step}
                          </span>
                        </div>
                      )
                    )}
                  </div>

                  <div className="space-y-3">
                    <SettingToggle
                      label="READ ACCESS"
                      description="Allow supported agents to read permitted context."
                      enabled={settings.agentPermRead}
                      onChange={() =>
                        updateSetting(
                          "agentPermRead",
                          !settings.agentPermRead
                        )
                      }
                    />

                    <SettingToggle
                      label="ANALYSIS ACCESS"
                      description="Allow supported agents to perform analysis tasks."
                      enabled={settings.agentPermAnalyze}
                      onChange={() =>
                        updateSetting(
                          "agentPermAnalyze",
                          !settings.agentPermAnalyze
                        )
                      }
                    />

                    <SettingToggle
                      label="APPROVAL REQUIRED FOR CRITICAL TASKS"
                      description="Require confirmation before supported high-impact actions."
                      enabled={settings.agentApproval}
                      onChange={() =>
                        updateSetting(
                          "agentApproval",
                          !settings.agentApproval
                        )
                      }
                    />
                  </div>
                </div>
              )}

              {/* APPEARANCE */}
              {activeTab === "APPEARANCE" && (
                <div className="space-y-6">
                  <SectionHeader
                    title="INTERFACE APPEARANCE"
                    status="HUD CONFIGURATION"
                  />

                  <ChoiceGroup
                    label="THEME ENVIRONMENT"
                    options={["DARK", "LIGHT", "SYSTEM"]}
                    value={settings.theme}
                    onChange={(value) =>
                      updateSetting("theme", value)
                    }
                  />

                  <ChoiceGroup
                    label="HUD GLOW INTENSITY"
                    options={["LOW", "BALANCED", "HIGH"]}
                    value={settings.hudIntensity}
                    onChange={(value) =>
                      updateSetting("hudIntensity", value)
                    }
                  />

                  <div className="rounded-xl border border-cyan-500/15 bg-cyan-950/10 p-4 font-mono text-[9px] leading-relaxed text-cyan-400/50">
                    The current interface uses the KING ZARRY AI dark
                    HUD environment. Full global theme switching can be
                    connected when the application theme system is
                    enabled.
                  </div>
                </div>
              )}

              {/* SECURITY */}
              {activeTab === "SECURITY" && (
                <div className="space-y-6">
                  <SectionHeader
                    title="SECURITY CONTROL"
                    status="ACCOUNT SECURITY"
                  />

                  <div className="space-y-3">
                    <div className="flex flex-col gap-4 rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-4 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <span className="block font-mono text-xs font-bold text-white">
                          CHANGE PASSWORD
                        </span>

                        <span className="mt-1 block font-mono text-[10px] text-cyan-400/60">
                          Password management is handled by account authentication.
                        </span>
                      </div>

                      <Link
                        href="/login"
                        className="inline-flex justify-center rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-3 py-2 font-mono text-[10px] text-cyan-300"
                      >
                        ACCOUNT LOGIN
                      </Link>
                    </div>

                    <div className="flex flex-col gap-4 rounded-xl border border-red-500/20 bg-red-950/10 p-4 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <span className="block font-mono text-xs font-bold text-white">
                          SESSION CONTROL
                        </span>

                        <span className="mt-1 block font-mono text-[10px] text-red-200/60">
                          Server-side session management can be connected to the authentication API.
                        </span>
                      </div>

                      <button
                        type="button"
                        onClick={() => {
                          window.location.href = "/login";
                        }}
                        className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 font-mono text-[10px] text-red-300 transition hover:bg-red-500/20"
                      >
                        RETURN TO LOGIN
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* PRIVACY */}
              {activeTab === "PRIVACY" && (
                <div className="space-y-6">
                  <SectionHeader
                    title="PRIVACY CONTROL"
                    status="DATA PREFERENCES"
                  />

                  <p className="font-mono text-xs leading-relaxed text-cyan-200/75">
                    Privacy preferences determine how the web application
                    should handle supported conversation and personalization
                    features. Server-side enforcement depends on the connected
                    backend configuration.
                  </p>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-4">
                      <span className="font-mono text-xs font-bold text-white">
                        MEMORY STORAGE
                      </span>

                      <span className="font-mono text-[9px] text-cyan-400">
                        CONTROLLED
                      </span>
                    </div>

                    <div className="flex items-center justify-between rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-4">
                      <span className="font-mono text-xs font-bold text-white">
                        PERSONALIZATION
                      </span>

                      <span className="font-mono text-[9px] text-cyan-400">
                        CONTROLLED
                      </span>
                    </div>

                    <div className="flex items-center justify-between rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-4">
                      <span className="font-mono text-xs font-bold text-white">
                        CONVERSATION RETENTION
                      </span>

                      <span className="font-mono text-[9px] text-cyan-400">
                        CONTROLLED
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* SUBSCRIPTION */}
              {activeTab === "SUBSCRIPTION" && (
                <div className="space-y-6">
                  <SectionHeader
                    title="AI ACCESS"
                    status="MEMBERSHIP"
                  />

                  <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/30 p-5">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <span className="block font-mono text-[9px] text-cyan-400/60">
                          CURRENT ACCESS
                        </span>

                        <span className="mt-1 block font-mono text-sm font-bold text-white">
                          SIGN IN TO VIEW MEMBERSHIP
                        </span>

                        <span className="mt-1 block font-mono text-[9px] text-cyan-400/50">
                          ACCOUNT STATUS REQUIRED
                        </span>
                      </div>

                      <span className="rounded border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 font-mono text-[9px] text-amber-300">
                        STANDBY
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2 sm:flex-row">
                    <Link
                      href="/pricing"
                      className="rounded-lg bg-cyan-400 px-4 py-2 text-center font-mono text-xs font-bold text-black transition hover:bg-cyan-300"
                    >
                      VIEW PLANS
                    </Link>

                    <Link
                      href="/login"
                      className="rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-4 py-2 text-center font-mono text-xs font-bold text-cyan-300 transition hover:bg-cyan-500/20"
                    >
                      SIGN IN
                    </Link>
                  </div>
                </div>
              )}

              {/* SYSTEM */}
              {activeTab === "SYSTEM" && (
                <div className="space-y-6">
                  <SectionHeader
                    title="SYSTEM INFORMATION"
                    status="WEB CLIENT"
                  />

                  <div className="space-y-2 font-mono text-xs">
                    <InfoRow
                      label="CLIENT"
                      value="KING ZARRY AI WEB"
                    />

                    <InfoRow
                      label="SETTINGS STORAGE"
                      value="BROWSER"
                    />

                    <InfoRow
                      label="AUTHENTICATION"
                      value="SESSION COOKIE"
                    />

                    <InfoRow
                      label="BACKEND"
                      value="FASTAPI"
                    />

                    <InfoRow
                      label="DATABASE"
                      value="WEB POSTGRESQL"
                    />
                  </div>

                  <div className="rounded-xl border border-red-500/20 bg-red-950/10 p-4">
                    <h4 className="font-mono text-xs font-bold text-red-400">
                      RESET LOCAL PREFERENCES
                    </h4>

                    <p className="mt-1 font-mono text-[10px] leading-relaxed text-red-200/60">
                      This removes settings stored in this browser.
                      It does not delete your account or server-side
                      data.
                    </p>

                    <button
                      type="button"
                      onClick={handleReset}
                      className="mt-3 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 font-mono text-[10px] text-red-300 transition hover:bg-red-500/20"
                    >
                      RESET LOCAL SETTINGS
                    </button>
                  </div>
                </div>
              )}

              {/* SAVE BAR */}
              <div className="mt-8 flex flex-col gap-4 border-t border-cyan-500/15 pt-5 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2 font-mono text-[10px] text-cyan-400/70">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      saveStatus === "SAVED"
                        ? "bg-emerald-400"
                        : saveStatus === "SAVING"
                          ? "animate-pulse bg-amber-400"
                          : "bg-cyan-400"
                    }`}
                  />

                  {saveStatus === "IDLE" &&
                    "UNSAVED CHANGES AVAILABLE"}

                  {saveStatus === "SAVING" &&
                    "SAVING LOCAL CONFIGURATION..."}

                  {saveStatus === "SAVED" &&
                    "CONFIGURATION SAVED"}
                </div>

                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleReset}
                    className="rounded-lg border border-cyan-500/30 bg-cyan-950/40 px-4 py-2 font-mono text-[10px] text-cyan-400 transition hover:bg-cyan-500/10"
                  >
                    RESET
                  </button>

                  <button
                    type="button"
                    onClick={handleSave}
                    disabled={saveStatus === "SAVING"}
                    className="rounded-lg bg-cyan-400 px-5 py-2 font-mono text-[10px] font-bold tracking-widest text-black shadow-[0_0_15px_rgba(0,240,255,0.2)] transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {saveStatus === "SAVING"
                      ? "SAVING..."
                      : "SAVE CHANGES"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="border-t border-cyan-500/10 py-6 text-center">
          <div className="font-mono text-[9px] tracking-[0.25em] text-cyan-400/40">
            KING ZARRY AI
          </div>

          <div className="mt-1 font-mono text-[8px] text-cyan-500/30">
            PERSONAL AI INTELLIGENCE ENVIRONMENT
          </div>
        </footer>
      </main>
    </div>
  );
}

/* -------------------------------- */
/* SMALL REUSABLE UI COMPONENTS     */
/* -------------------------------- */

function SectionHeader({
  title,
  status,
}: {
  title: string;
  status: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-cyan-500/15 pb-3">
      <h3 className="font-mono text-xs font-bold tracking-widest text-white">
        {title}
      </h3>

      <span className="font-mono text-[8px] tracking-wider text-cyan-400/50">
        {status}
      </span>
    </div>
  );
}

function InputField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-1.5">
      <label className="block font-mono text-[10px] text-cyan-400/70">
        {label}
      </label>

      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-cyan-500/30 bg-cyan-950/30 px-3.5 py-2.5 font-mono text-xs text-cyan-100 outline-none transition focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/20"
      />
    </div>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
}) {
  return (
    <div className="space-y-1.5">
      <label className="block font-mono text-[10px] text-cyan-400/70">
        {label}
      </label>

      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-cyan-500/30 bg-[#061421] px-3.5 py-2.5 font-mono text-xs text-cyan-100 outline-none focus:border-cyan-400"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </div>
  );
}

function ChoiceGroup({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-2">
      <label className="block font-mono text-[10px] text-cyan-400/70">
        {label}
      </label>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {options.map((option) => {
          const selected = value === option;

          return (
            <button
              key={option}
              type="button"
              onClick={() => onChange(option)}
              className={`rounded-lg border p-2.5 font-mono text-[10px] transition ${
                selected
                  ? "border-cyan-400 bg-cyan-500/25 text-cyan-300 shadow-[0_0_10px_rgba(0,240,255,0.15)]"
                  : "border-cyan-500/15 bg-cyan-950/20 text-cyan-400/70 hover:bg-cyan-500/10"
              }`}
            >
              {option}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-3">
      <span className="text-cyan-400/60">{label}</span>

      <span className="text-cyan-200">{value}</span>
    </div>
  );
}
