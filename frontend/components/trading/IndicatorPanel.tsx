"use client";

import React from "react";

type IndicatorState =
  | "bullish"
  | "bearish"
  | "neutral"
  | "rising"
  | "falling"
  | "overbought"
  | "oversold"
  | "strong"
  | "weak"
  | string;

interface RawIndicator {
  label?: string;
  name?: string;
  value?: string | number | null;
  rawValue?: string | number | null;
  displayValue?: string | number | null;
  state?: IndicatorState;
  status?: IndicatorState;
  trend?: IndicatorState;
  bias?: IndicatorState;
  context?: string;
  interpretation?: string;
  period?: string | number;
  [key: string]: any;
}

interface IndicatorPanelProps {
  symbol?: string;
  asset?: string;
  pair?: string;
  timeframe?: string;
  interval?: string;
  tf?: string;
  indicators?: Record<string, RawIndicator | string | number | null> & {
    ema?: RawIndicator | Record<string, RawIndicator> | string | number | null;
    rsi?: RawIndicator | string | number | null;
    atr?: RawIndicator | string | number | null;
    macd?: RawIndicator | string | number | null;
    bollinger?: RawIndicator | Record<string, any> | null;
    bollingerBands?: RawIndicator | Record<string, any> | null;
    ma?: RawIndicator | Record<string, any> | null;
    movingAverages?: Record<string, any> | null;
    trend?: RawIndicator | string | null;
    momentum?: RawIndicator | string | null;
    volatility?: RawIndicator | string | null;
    marketStructure?: RawIndicator | string | null;
    structure?: RawIndicator | string | null;
    supportResistance?: RawIndicator | Record<string, any> | null;
    swings?: Record<string, any> | null;
    swingHigh?: RawIndicator | string | number | null;
    swingLow?: RawIndicator | string | number | null;
    hh?: any;
    hl?: any;
    lh?: any;
    ll?: any;
  };
  data?: Record<string, any>;
  values?: Record<string, any>;
  aiRead?: string;
  aiInterpretation?: string;
  interpretation?: string;
  technicalRead?: string;
  loading?: boolean;
  isLoading?: boolean;
  error?: string | null;
  errorMessage?: string | null;
  className?: string;
}

function safeValue(v: any): string {
  if (
    v === null ||
    v === undefined ||
    v === "" ||
    (typeof v === "number" && Number.isNaN(v))
  ) {
    return "N/A";
  }

  if (typeof v === "object") {
    const candidate =
      v.value ??
      v.displayValue ??
      v.rawValue ??
      v.price ??
      v.level ??
      v.val;

    if (
      candidate !== undefined &&
      candidate !== null &&
      candidate !== ""
    ) {
      return String(candidate);
    }

    return "N/A";
  }

  return String(v);
}

function safeState(v: any): string | null {
  if (!v) return null;

  if (typeof v === "string") {
    return v.toLowerCase();
  }

  if (typeof v === "object") {
    const state =
      v.state ??
      v.status ??
      v.trend ??
      v.bias ??
      v.direction ??
      v.momentum;

    if (typeof state === "string") {
      return state.toLowerCase();
    }
  }

  return null;
}

function getIndicatorMeta(key: string) {
  const normalized = key.toLowerCase();

  const map: Record<string, { label: string; sub: string }> = {
    ema: {
      label: "EMA",
      sub: "EXPONENTIAL MOVING AVERAGE",
    },
    ema21: {
      label: "EMA 21",
      sub: "TREND FILTER",
    },
    ema50: {
      label: "EMA 50",
      sub: "TREND FILTER",
    },
    ema200: {
      label: "EMA 200",
      sub: "HTF TREND",
    },
    rsi: {
      label: "RSI",
      sub: "MOMENTUM OSCILLATOR",
    },
    atr: {
      label: "ATR",
      sub: "VOLATILITY",
    },
    macd: {
      label: "MACD",
      sub: "MOMENTUM",
    },
    bollinger: {
      label: "BOLLINGER",
      sub: "VOLATILITY BANDS",
    },
    bollingerbands: {
      label: "BOLLINGER",
      sub: "VOLATILITY BANDS",
    },
    ma: {
      label: "MA",
      sub: "MOVING AVERAGE",
    },
    trend: {
      label: "TREND",
      sub: "DIRECTIONAL STATE",
    },
    momentum: {
      label: "MOMENTUM",
      sub: "STRENGTH",
    },
    volatility: {
      label: "VOLATILITY",
      sub: "ATR • RANGE",
    },
    structure: {
      label: "STRUCTURE",
      sub: "MARKET STRUCTURE",
    },
    marketstructure: {
      label: "STRUCTURE",
      sub: "MARKET STRUCTURE",
    },
    support: {
      label: "SUPPORT",
      sub: "DEMAND ZONE",
    },
    resistance: {
      label: "RESISTANCE",
      sub: "SUPPLY ZONE",
    },
    swinghigh: {
      label: "SWING HIGH",
      sub: "LAST HH",
    },
    swinglow: {
      label: "SWING LOW",
      sub: "LAST LL",
    },
  };

  return (
    map[normalized] || {
      label: key.replace(/([A-Z])/g, " $1").trim().toUpperCase(),
      sub: "TECHNICAL",
    }
  );
}

function getStateTone(state: string | null) {
  if (!state) {
    return {
      label: null,
      badge:
        "border-white/[0.08] bg-white/[0.035] text-white/45",
      dot: "bg-white/30",
      glow: "",
      icon: "•",
    };
  }

  const s = state.toLowerCase();

  const bullish = [
    "bullish",
    "rising",
    "up",
    "long",
    "bull",
  ].some((item) => s.includes(item));

  const bearish = [
    "bearish",
    "falling",
    "down",
    "short",
    "bear",
  ].some((item) => s.includes(item));

  const neutral = [
    "neutral",
    "sideways",
    "balanced",
    "consolidation",
  ].some((item) => s.includes(item));

  const extreme =
    s.includes("overbought") ||
    s.includes("oversold");

  if (bullish) {
    return {
      label: state,
      badge:
        "border-cyan-300/20 bg-cyan-300/[0.07] text-cyan-100/85",
      dot:
        "bg-cyan-300 shadow-[0_0_10px_rgba(34,211,238,0.8)]",
      glow: "shadow-[0_0_24px_rgba(34,211,238,0.06)]",
      icon: "↗",
    };
  }

  if (bearish) {
    return {
      label: state,
      badge:
        "border-rose-300/20 bg-rose-300/[0.07] text-rose-100/85",
      dot:
        "bg-rose-300 shadow-[0_0_10px_rgba(251,113,133,0.75)]",
      glow: "shadow-[0_0_24px_rgba(251,113,133,0.05)]",
      icon: "↘",
    };
  }

  if (extreme) {
    return {
      label: state,
      badge:
        "border-amber-300/20 bg-amber-300/[0.07] text-amber-100/80",
      dot:
        "bg-amber-300 shadow-[0_0_10px_rgba(251,191,36,0.65)]",
      glow: "shadow-[0_0_24px_rgba(251,191,36,0.04)]",
      icon: "!",
    };
  }

  if (neutral) {
    return {
      label: state,
      badge:
        "border-sky-300/15 bg-sky-300/[0.05] text-sky-100/65",
      dot: "bg-sky-300/60",
      glow: "",
      icon: "•",
    };
  }

  return {
    label: state,
    badge:
      "border-white/[0.08] bg-white/[0.035] text-white/45",
    dot: "bg-white/30",
    glow: "",
    icon: "•",
  };
}

function StateBadge({ state }: { state: string | null }) {
  if (!state) return null;

  const tone = getStateTone(state);

  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-[9px] font-medium uppercase tracking-[0.12em] ${tone.badge}`}
    >
      <span
        aria-hidden="true"
        className={`h-1 w-1 rounded-full ${tone.dot}`}
      />
      {state}
    </span>
  );
}

function IndicatorCard({
  k,
  raw,
  index,
}: {
  k: string;
  raw: any;
  index: number;
}) {
  if (raw === undefined || raw === null) return null;

  let value: any = raw;
  let state: string | null = null;
  let context: string | undefined;
  let labelOverride: string | undefined;

  if (
    typeof raw === "object" &&
    !Array.isArray(raw)
  ) {
    value =
      raw.value ??
      raw.displayValue ??
      raw.rawValue ??
      raw.price ??
      raw.level ??
      raw.val ??
      raw;

    state = safeState(raw);

    context =
      raw.context ??
      raw.interpretation ??
      raw.desc ??
      raw.note;

    labelOverride = raw.label ?? raw.name;

    if (
      typeof value === "object" &&
      value !== null &&
      !Array.isArray(value) &&
      value.value === undefined
    ) {
      const keys = Object.keys(value);

      const looksNested = keys.some(
        (key) =>
          typeof value[key] === "object" ||
          typeof value[key] === "number"
      );

      if (looksNested && keys.length <= 6) {
        return null;
      }
    }
  } else {
    state = safeState(raw);
  }

  const meta = getIndicatorMeta(k);
  const tone = getStateTone(state);

  const displayLabel =
    labelOverride || meta.label;

  const displayValue = safeValue(value);
  const isNA = displayValue === "N/A";

  return (
    <article
      key={`${k}-${index}`}
      className={`group relative min-h-[148px] overflow-hidden rounded-[18px] border border-white/[0.07] bg-white/[0.025] p-px transition-all duration-300 hover:-translate-y-[1px] hover:border-cyan-300/[0.14] hover:bg-white/[0.035] ${tone.glow}`}
    >
      <div className="relative flex h-full flex-col overflow-hidden rounded-[17px] bg-[#080D15]/90 p-4 backdrop-blur-xl">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        >
          <div className="absolute -right-12 -top-12 h-28 w-28 rounded-full bg-cyan-400/[0.07] blur-2xl" />
        </div>

        <div className="relative flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="truncate text-[9px] font-medium uppercase tracking-[0.15em] text-white/30">
              {meta.sub}
            </div>

            <div className="mt-1.5 truncate text-[12px] font-semibold tracking-wide text-white/90">
              {displayLabel}
            </div>
          </div>

          <StateBadge state={state} />
        </div>

        <div className="relative mt-auto pt-6">
          <div className="flex items-end gap-2">
            <div
              className={`truncate text-[22px] font-semibold leading-none tracking-[-0.035em] ${
                isNA
                  ? "text-white/25"
                  : "text-white"
              }`}
            >
              {displayValue}
            </div>

            {!isNA && state && (
              <span
                aria-hidden="true"
                className={`pb-0.5 text-[13px] ${
                  tone.icon === "↗"
                    ? "text-cyan-300/75"
                    : tone.icon === "↘"
                      ? "text-rose-300/75"
                      : tone.icon === "!"
                        ? "text-amber-300/75"
                        : "text-white/25"
                }`}
              >
                {tone.icon}
              </span>
            )}
          </div>

          {context && (
            <div className="mt-3 line-clamp-2 text-[10px] leading-[1.5] text-white/38">
              {context}
            </div>
          )}
        </div>

        <div
          aria-hidden="true"
          className="mt-4 h-px bg-gradient-to-r from-cyan-300/10 via-white/[0.06] to-transparent"
        />

        <div
          aria-hidden="true"
          className="mt-3 flex items-center gap-1"
        >
          <span className="h-[2px] w-7 rounded-full bg-cyan-300/20" />
          <span className="h-[2px] w-3 rounded-full bg-white/[0.06]" />
          <span className="h-[2px] w-2 rounded-full bg-white/[0.035]" />
        </div>
      </div>

      <span
        aria-hidden="true"
        className="pointer-events-none absolute left-0 top-0 h-4 w-4 rounded-tl-[18px] border-l border-t border-cyan-300/15"
      />

      <span
        aria-hidden="true"
        className="pointer-events-none absolute right-0 top-0 h-4 w-4 rounded-tr-[18px] border-r border-t border-white/10"
      />

      <span
        aria-hidden="true"
        className="pointer-events-none absolute bottom-0 left-0 h-3 w-3 rounded-bl-[18px] border-b border-l border-white/[0.06]"
      />

      <span
        aria-hidden="true"
        className="pointer-events-none absolute bottom-0 right-0 h-3 w-3 rounded-br-[18px] border-b border-r border-white/[0.06]"
      />
    </article>
  );
}

function LoadingCard({ index }: { index: number }) {
  return (
    <div
      key={index}
      className="overflow-hidden rounded-[18px] border border-white/[0.06] bg-white/[0.02] p-4"
    >
      <div className="h-2.5 w-20 animate-pulse rounded-full bg-white/[0.07]" />
      <div className="mt-3 h-3 w-14 animate-pulse rounded-full bg-white/[0.05]" />
      <div className="mt-7 h-7 w-24 animate-pulse rounded bg-white/[0.07]" />
      <div className="mt-6 h-px bg-white/[0.05]" />
      <div className="mt-3 flex gap-1">
        <div className="h-1.5 w-7 animate-pulse rounded-full bg-white/[0.06]" />
        <div className="h-1.5 w-3 animate-pulse rounded-full bg-white/[0.04]" />
      </div>
    </div>
  );
}

export default function IndicatorPanel(
  props: IndicatorPanelProps
) {
  const symbol =
    props.symbol ??
    props.asset ??
    props.pair ??
    (props.data?.symbol as string) ??
    (props.indicators?.symbol as string);

  const timeframe =
    props.timeframe ??
    props.interval ??
    props.tf ??
    (props.data?.timeframe as string) ??
    (props.indicators?.timeframe as string);

  const loading =
    props.loading ??
    props.isLoading ??
    false;

  const error =
    props.error ??
    props.errorMessage ??
    null;

  const aiText =
    props.aiRead ??
    props.aiInterpretation ??
    props.interpretation ??
    props.technicalRead ??
    props.data?.aiInterpretation;

  const rawSources: Record<string, any> = {
    ...(props.indicators || {}),
    ...(props.data || {}),
    ...(props.values || {}),
  };

  const ignoreKeys = new Set([
    "symbol",
    "asset",
    "pair",
    "timeframe",
    "interval",
    "tf",
    "aiInterpretation",
    "aiRead",
    "interpretation",
    "technicalRead",
  ]);

  const entries: Array<[string, any]> =
    Object.entries(rawSources).filter(
      ([key]) => !ignoreKeys.has(key)
    );

  const flatEntries: Array<[string, any]> = [];

  for (const [key, value] of entries) {
    if (
      value &&
      typeof value === "object" &&
      !Array.isArray(value)
    ) {
      const subKeys = Object.keys(value);

      const hasValueField =
        "value" in value ||
        "displayValue" in value ||
        "rawValue" in value ||
        "state" in value ||
        "price" in value;

      const isNestedMap =
        !hasValueField &&
        subKeys.length > 0 &&
        subKeys.length <= 8 &&
        subKeys.every(
          (subKey) =>
            typeof value[subKey] !== "undefined"
        );

      if (
        isNestedMap &&
        [
          "ema",
          "ma",
          "movingAverages",
          "bollinger",
          "bollingerBands",
        ].includes(key)
      ) {
        for (const subKey of subKeys) {
          flatEntries.push([
            subKey,
            value[subKey],
          ]);
        }

        continue;
      }
    }

    flatEntries.push([key, value]);
  }

  const priority = [
    "ema",
    "ema21",
    "ema50",
    "ema200",
    "rsi",
    "atr",
    "macd",
    "trend",
    "momentum",
    "volatility",
    "structure",
    "marketStructure",
    "support",
    "resistance",
    "swingHigh",
    "swingLow",
  ];

  flatEntries.sort((a, b) => {
    const aKey = a[0].toLowerCase();
    const bKey = b[0].toLowerCase();

    const ia = priority.findIndex((item) =>
      aKey.includes(item.toLowerCase())
    );

    const ib = priority.findIndex((item) =>
      bKey.includes(item.toLowerCase())
    );

    if (ia === -1 && ib === -1) {
      return aKey.localeCompare(bKey);
    }

    if (ia === -1) return 1;
    if (ib === -1) return -1;

    return ia - ib;
  });

  if (loading) {
    return (
      <section
        className={`kz-panel kz-glass relative overflow-hidden rounded-[24px] border border-white/[0.08] bg-[#070A10] ${props.className || ""}`}
        aria-busy="true"
        aria-label="Technical Intelligence loading"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0"
        >
          <div className="absolute inset-0 bg-[radial-gradient(600px_260px_at_50%_0%,rgba(34,211,238,0.08),transparent)]" />

          <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff06_1px,transparent_1px),linear-gradient(to_bottom,#ffffff06_1px,transparent_1px)] bg-[size:32px_32px] opacity-40" />

          <div className="absolute left-1/2 top-0 h-px w-[70%] -translate-x-1/2 bg-gradient-to-r from-transparent via-cyan-300/20 to-transparent" />
        </div>

        <div className="relative p-6 md:p-7">
          <div className="flex items-center justify-between">
            <div>
              <div className="h-2.5 w-32 animate-pulse rounded-full bg-white/[0.07]" />
              <div className="mt-2 h-2 w-24 animate-pulse rounded-full bg-white/[0.04]" />
            </div>

            <div className="h-8 w-20 animate-pulse rounded-full bg-white/[0.05]" />
          </div>

          <div className="mt-7 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2, 3, 4, 5].map(
              (index) => (
                <LoadingCard
                  key={index}
                  index={index}
                />
              )
            )}
          </div>
        </div>

        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 left-0 w-1/3 -translate-x-full animate-[kzIndicatorShimmer_2.2s_infinite] bg-gradient-to-r from-transparent via-white/[0.035] to-transparent"
        />

        <style jsx>{`
          @keyframes kzIndicatorShimmer {
            100% {
              transform: translateX(420%);
            }
          }
        `}</style>
      </section>
    );
  }

  if (error) {
    return (
      <section
        className={`relative overflow-hidden rounded-[24px] border border-rose-300/15 bg-[#090B11] p-6 md:p-7 ${props.className || ""}`}
        role="alert"
        aria-label="Technical data unavailable"
      >
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-[radial-gradient(500px_220px_at_0%_0%,rgba(244,63,94,0.07),transparent)]"
        />

        <div className="relative">
          <div className="flex items-center gap-3">
            <span
              aria-hidden="true"
              className="h-2 w-2 rounded-full bg-rose-300 shadow-[0_0_12px_rgba(251,113,133,0.7)]"
            />

            <span className="text-[10px] font-medium uppercase tracking-[0.16em] text-rose-200/65">
              Technical data unavailable
            </span>
          </div>

          <div className="mt-3 max-w-2xl text-[13px] leading-6 text-white/55">
            {error}
          </div>

          <div className="mt-5 h-px w-full bg-gradient-to-r from-rose-300/10 via-white/[0.05] to-transparent" />
        </div>
      </section>
    );
  }

  const hasIndicators =
    flatEntries.length > 0;

  const summaryItems = [
    {
      label: "TREND",
      key: "trend",
    },
    {
      label: "MOMENTUM",
      key: "momentum",
    },
    {
      label: "VOLATILITY",
      key: "volatility",
    },
  ];

  return (
    <section
      className={`kz-panel kz-glass kz-console relative overflow-hidden rounded-[24px] border border-white/[0.08] bg-gradient-to-b from-[#0A111C] to-[#06080F] shadow-[0_20px_80px_rgba(0,0,0,0.6),inset_0_1px_0_rgba(255,255,255,0.07)] md:rounded-[28px] ${props.className || ""}`}
      aria-label="Technical Intelligence Indicator Matrix"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
      >
        <div className="absolute inset-0 bg-[radial-gradient(700px_400px_at_18%_0%,rgba(56,189,248,0.10),transparent),radial-gradient(600px_320px_at_82%_8%,rgba(139,92,246,0.10),transparent)]" />

        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff06_1px,transparent_1px),linear-gradient(to_bottom,#ffffff06_1px,transparent_1px)] bg-[size:36px_36px] opacity-35 [mask-image:radial-gradient(ellipse_at_center,#000_58%,transparent_96%)]" />

        <div className="absolute left-1/2 top-0 h-px w-[82%] -translate-x-1/2 bg-gradient-to-r from-transparent via-cyan-300/25 to-transparent" />

        <div className="absolute -top-28 left-1/2 h-[250px] w-[620px] -translate-x-1/2 rounded-full bg-cyan-400/[0.055] blur-[55px]" />
      </div>

      <header className="relative flex min-h-[72px] items-center justify-between gap-4 border-b border-white/[0.06] px-5 py-4 md:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <div className="relative flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-[11px] border border-cyan-300/15 bg-cyan-300/[0.045]">
            <span
              aria-hidden="true"
              className="absolute inset-0 rounded-[11px] bg-cyan-300/[0.04] blur-md"
            />

            <span
              aria-hidden="true"
              className="relative h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_12px_rgba(34,211,238,0.85)]"
            />
          </div>

          <div className="min-w-0">
            <h2 className="truncate text-[11px] font-semibold uppercase tracking-[0.16em] text-white/90">
              Technical Intelligence
            </h2>

            <div className="mt-1 flex items-center gap-2 text-[9px] uppercase tracking-[0.12em] text-white/30">
              <span>Indicator Matrix</span>

              <span
                aria-hidden="true"
                className="h-3 w-px bg-white/10"
              />

              <span className="truncate text-cyan-200/25">
                KING ZARRY AI
              </span>
            </div>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {symbol && (
            <div className="hidden items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.035] px-3 py-1.5 sm:flex">
              <span className="text-[9px] uppercase tracking-[0.12em] text-white/30">
                Asset
              </span>

              <span className="max-w-[120px] truncate text-[11px] font-medium tracking-wide text-white/75">
                {symbol}
              </span>
            </div>
          )}

          {timeframe && (
            <div className="flex items-center gap-2 rounded-full border border-cyan-300/15 bg-cyan-300/[0.055] px-3 py-1.5">
              <span className="text-[9px] uppercase tracking-[0.12em] text-cyan-200/45">
                TF
              </span>

              <span className="text-[11px] font-medium tracking-wide text-cyan-100/80">
                {timeframe}
              </span>
            </div>
          )}
        </div>
      </header>

      <div className="relative p-5 md:p-6">
        {!hasIndicators ? (
          <div className="relative overflow-hidden rounded-[18px] border border-white/[0.06] bg-white/[0.018] p-8 text-center">
            <div
              aria-hidden="true"
              className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.025]"
            >
              <span className="h-2 w-2 rounded-full bg-white/25" />
            </div>

            <div className="mt-4 text-[10px] font-medium uppercase tracking-[0.16em] text-white/35">
              No indicator data
            </div>

            <div className="mx-auto mt-2 max-w-md text-[12px] leading-5 text-white/40">
              Technical indicators will appear here when
              actual indicator data becomes available.
            </div>

            <div className="mt-5 text-[9px] uppercase tracking-[0.12em] text-white/20">
              No fabricated values
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:gap-4 lg:grid-cols-3">
            {flatEntries.map(
              ([key, value], index) => (
                <IndicatorCard
                  key={`${key}-${index}`}
                  k={key}
                  raw={value}
                  index={index}
                />
              )
            )}
          </div>
        )}

        <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
          {summaryItems.map((item) => {
            const raw =
              rawSources[item.key] ??
              rawSources[
                item.key.toLowerCase()
              ] ??
              null;

            const state = safeState(raw);
            const value = safeValue(raw);
            const has =
              raw !== null &&
              raw !== undefined;

            const tone = getStateTone(state);

            return (
              <div
                key={item.label}
                className="group relative overflow-hidden rounded-[15px] border border-white/[0.06] bg-[#0A1018]/85 px-4 py-3.5 transition-colors hover:border-white/[0.09]"
              >
                <div
                  aria-hidden="true"
                  className="absolute inset-y-0 left-0 w-px bg-gradient-to-b from-transparent via-cyan-300/20 to-transparent"
                />

                <div className="flex items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-2.5">
                    <span
                      aria-hidden="true"
                      className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                        state
                          ? tone.dot
                          : "bg-white/20"
                      }`}
                    />

                    <span className="truncate text-[9px] font-medium uppercase tracking-[0.14em] text-white/35">
                      {item.label}
                    </span>
                  </div>

                  <div className="flex min-w-0 items-center gap-2">
                    <span className="max-w-[110px] truncate text-[11px] font-medium text-white/65">
                      {has
                        ? value !== "N/A"
                          ? value
                          : state || "—"
                        : "N/A"}
                    </span>

                    {state && (
                      <StateBadge
                        state={state}
                      />
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {aiText && (
          <div className="relative mt-5 overflow-hidden rounded-[18px] border border-cyan-300/15 bg-gradient-to-b from-cyan-400/[0.055] to-white/[0.01] p-px">
            <div className="relative overflow-hidden rounded-[17px] bg-[#08131D]/90 p-5 backdrop-blur-xl">
              <div
                aria-hidden="true"
                className="absolute right-0 top-0 h-28 w-28 rounded-full bg-cyan-300/[0.055] blur-3xl"
              />

              <div className="relative flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <span
                    aria-hidden="true"
                    className="h-1.5 w-1.5 rounded-full bg-cyan-300 shadow-[0_0_10px_rgba(34,211,238,0.65)]"
                  />

                  <span className="text-[10px] font-medium uppercase tracking-[0.15em] text-cyan-200/65">
                    AI Technical Read
                  </span>
                </div>

                <span className="text-[8px] uppercase tracking-[0.12em] text-white/20">
                  Supplied interpretation
                </span>
              </div>

              <p className="relative mt-3 whitespace-pre-wrap text-[12px] leading-[1.7] text-white/65">
                {aiText}
              </p>
            </div>
          </div>
        )}

        <footer className="mt-5 flex flex-col gap-2 border-t border-white/[0.05] pt-4 text-[8px] uppercase tracking-[0.13em] text-white/20 sm:flex-row sm:items-center sm:justify-between">
          <span>
            Technical intelligence • Actual data only
          </span>

          <span className="hidden md:inline">
            KZ • INTEL • {symbol || "—"} •{" "}
            {timeframe || "—"}
          </span>
        </footer>
      </div>

      <span
        aria-hidden="true"
        className="pointer-events-none absolute left-3 top-3 h-5 w-5 rounded-tl-[20px] border-l border-t border-cyan-300/20"
      />

      <span
        aria-hidden="true"
        className="pointer-events-none absolute right-3 top-3 h-5 w-5 rounded-tr-[20px] border-r border-t border-cyan-300/15"
      />

      <span
        aria-hidden="true"
        className="pointer-events-none absolute bottom-3 left-3 h-5 w-5 rounded-bl-[20px] border-b border-l border-white/[0.07]"
      />

      <span
        aria-hidden="true"
        className="pointer-events-none absolute bottom-3 right-3 h-5 w-5 rounded-br-[20px] border-b border-r border-white/[0.07]"
      />
    </section>
  );
}
