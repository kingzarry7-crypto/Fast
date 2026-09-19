"use client";

import React from "react";

type TrendState =
  | "bullish"
  | "bearish"
  | "neutral"
  | "up"
  | "down"
  | string;

interface MarketCardProps {
  symbol?: string;
  asset?: string;
  pair?: string;
  name?: string;
  assetName?: string;
  market?: string;
  category?: string;
  marketType?: string;
  timeframe?: string;
  interval?: string;
  exchange?: string;
  source?: string;

  price?: string | number | null;
  currentPrice?: string | number | null;
  value?: string | number | null;
  lastPrice?: string | number | null;
  close?: string | number | null;

  change?: string | number | null;
  changeValue?: string | number | null;
  priceChange?: string | number | null;
  changePercent?: string | number | null;
  percentChange?: string | number | null;
  percentage?: string | number | null;
  changePct?: string | number | null;

  direction?: TrendState | null;
  trend?: TrendState | string | null;
  bias?: string | null;
  momentum?: string | null;
  signal?: string | null;
  status?: string | null;

  rsi?: string | number | null;
  ema?:
    | string
    | number
    | { value?: any; state?: string }
    | null;
  atr?: string | number | null;
  marketStructure?: string | null;
  structure?: string | null;
  confidence?: string | number | null;
  volatility?: string | null;

  aiRead?: string;
  aiInterpretation?: string;
  interpretation?: string;
  analysis?: string;
  summary?: string;
  marketRead?: string;

  sparkline?: number[] | null;
  chartData?: number[] | { value: number }[] | null;
  history?: number[] | null;
  prices?: number[] | null;

  lastUpdated?: string | null;
  updatedAt?: string | null;
  timestamp?: string | null;
  time?: string | null;

  loading?: boolean;
  isLoading?: boolean;
  error?: string | null;
  errorMessage?: string | null;

  onClick?: () => void;
  onSelect?: () => void;
  href?: string;
  to?: string;
  link?: string;
  selected?: boolean;
  active?: boolean;
  disabled?: boolean;

  data?: Record<string, any>;

  className?: string;
}

function safeNum(v: any): string {
  if (
    v === null ||
    v === undefined ||
    v === ""
  ) {
    return "N/A";
  }

  if (
    typeof v === "number" &&
    Number.isNaN(v)
  ) {
    return "N/A";
  }

  if (typeof v === "object") {
    const candidate =
      v.value ??
      v.price ??
      v.current ??
      v.close ??
      v.displayValue ??
      v.rawValue;

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

function safePercent(v: any): string | null {
  if (
    v === null ||
    v === undefined ||
    v === ""
  ) {
    return null;
  }

  const value = String(v).trim();

  if (
    value === "" ||
    value.toLowerCase() === "n/a"
  ) {
    return null;
  }

  if (value.includes("%")) {
    return value;
  }

  const numeric = Number(value);

  if (
    !Number.isNaN(numeric) &&
    Math.abs(numeric) < 1000
  ) {
    return value;
  }

  return value;
}

function inferTrend(
  props: MarketCardProps
): {
  trend: string | null;
  isBull: boolean;
  isBear: boolean;
} {
  const raw =
    props.direction ??
    props.trend ??
    props.bias ??
    props.signal ??
    (props.data as any)?.trend ??
    (props.data as any)?.direction ??
    (props.data as any)?.bias;

  if (!raw) {
    return {
      trend: null,
      isBull: false,
      isBear: false,
    };
  }

  const trend = String(raw).toLowerCase();

  const isBull = [
    "bullish",
    "up",
    "long",
    "buy",
    "bull",
    "rising",
  ].some((item) => trend.includes(item));

  const isBear = [
    "bearish",
    "down",
    "short",
    "sell",
    "bear",
    "falling",
  ].some((item) => trend.includes(item));

  return {
    trend: String(raw),
    isBull,
    isBear,
  };
}

function getTrendTone(
  isBull: boolean,
  isBear: boolean
) {
  if (isBull) {
    return {
      text: "text-cyan-200/85",
      border:
        "border-cyan-300/20",
      background:
        "bg-cyan-300/[0.07]",
      dot:
        "bg-cyan-300 shadow-[0_0_9px_rgba(34,211,238,0.8)]",
      glow:
        "drop-shadow-[0_0_14px_rgba(34,211,238,0.18)]",
      line: "rgba(34,211,238,0.92)",
    };
  }

  if (isBear) {
    return {
      text: "text-rose-200/85",
      border:
        "border-rose-300/20",
      background:
        "bg-rose-300/[0.07]",
      dot:
        "bg-rose-300 shadow-[0_0_9px_rgba(251,113,133,0.75)]",
      glow:
        "drop-shadow-[0_0_14px_rgba(251,113,133,0.16)]",
      line: "rgba(251,113,133,0.9)",
    };
  }

  return {
    text: "text-white/55",
    border:
      "border-white/[0.09]",
    background:
      "bg-white/[0.035]",
    dot: "bg-white/35",
    glow: "",
    line: "rgba(255,255,255,0.38)",
  };
}

function MiniSparkline({
  data,
  isBull,
  isBear,
  id,
}: {
  data: number[];
  isBull: boolean;
  isBear: boolean;
  id: string;
}) {
  if (!data || data.length < 2) {
    return null;
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const width = 220;
  const height = 58;

  const points = data
    .map((value, index) => {
      const x =
        (index / (data.length - 1)) *
        width;

      const y =
        height -
        ((value - min) / range) *
          (height - 6) -
        3;

      return `${x},${y}`;
    })
    .join(" ");

  const lastValue = data[data.length - 1];

  const lastY =
    height -
    ((lastValue - min) / range) *
      (height - 6) -
    3;

  const tone = getTrendTone(
    isBull,
    isBear
  );

  const gradientId = `kz-market-gradient-${id}`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="h-[58px] w-full overflow-visible"
      aria-hidden="true"
    >
      <defs>
        <linearGradient
          id={gradientId}
          x1="0"
          x2="0"
          y1="0"
          y2="1"
        >
          <stop
            offset="0%"
            stopColor={tone.line}
            stopOpacity="0.24"
          />
          <stop
            offset="100%"
            stopColor={tone.line}
            stopOpacity="0"
          />
        </linearGradient>
      </defs>

      <path
        d={`M 0 ${height} L ${points} L ${width} ${height} Z`}
        fill={`url(#${gradientId})`}
      />

      <polyline
        fill="none"
        stroke={tone.line}
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />

      <circle
        cx={width}
        cy={lastY}
        r="3"
        fill={tone.line}
      />

      <circle
        cx={width}
        cy={lastY}
        r="7"
        fill={tone.line}
        opacity="0.08"
      />
    </svg>
  );
}

function MetricChip({
  label,
  value,
}: {
  label: string;
  value: any;
}) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const display = safeNum(value);

  return (
    <div className="min-w-0 rounded-[11px] border border-white/[0.06] bg-white/[0.025] px-3 py-2.5">
      <div className="truncate text-[8px] font-medium uppercase tracking-[0.14em] text-white/30">
        {label}
      </div>

      <div
        className={`mt-1 truncate text-[11px] font-medium ${
          display === "N/A"
            ? "text-white/25"
            : "text-white/70"
        }`}
      >
        {display}
      </div>
    </div>
  );
}

export default function MarketCard(
  props: MarketCardProps
) {
  const symbol =
    props.symbol ??
    props.asset ??
    props.pair ??
    (props.data as any)?.symbol ??
    "—";

  const name =
    props.name ??
    props.assetName ??
    (props.data as any)?.name;

  const marketCategory =
    props.market ??
    props.category ??
    props.marketType ??
    (props.data as any)?.market;

  const timeframe =
    props.timeframe ??
    props.interval ??
    (props.data as any)?.timeframe;

  const exchange =
    props.exchange ??
    props.source ??
    (props.data as any)?.exchange ??
    (props.data as any)?.source;

  const priceRaw =
    props.price ??
    props.currentPrice ??
    props.value ??
    props.lastPrice ??
    props.close ??
    (props.data as any)?.price ??
    (props.data as any)?.currentPrice;

  const priceDisplay =
    safeNum(priceRaw);

  const isPriceNA =
    priceDisplay === "N/A";

  const changeRaw =
    props.change ??
    props.changeValue ??
    props.priceChange ??
    (props.data as any)?.change;

  const changePercentRaw =
    props.changePercent ??
    props.percentChange ??
    props.percentage ??
    props.changePct ??
    (props.data as any)?.changePercent ??
    (props.data as any)?.percentChange;

  const {
    trend,
    isBull,
    isBear,
  } = inferTrend(props);

  const trendTone = getTrendTone(
    isBull,
    isBear
  );

  const aiText =
    props.aiRead ??
    props.aiInterpretation ??
    props.interpretation ??
    props.analysis ??
    props.summary ??
    props.marketRead ??
    (props.data as any)?.aiRead ??
    (props.data as any)?.aiInterpretation;

  const loading =
    props.loading ??
    props.isLoading ??
    false;

  const error =
    props.error ??
    props.errorMessage ??
    null;

  const sparkRaw =
    props.sparkline ??
    props.chartData ??
    props.history ??
    props.prices ??
    (props.data as any)?.sparkline ??
    (props.data as any)?.chartData ??
    (props.data as any)?.history;

  let sparkData: number[] | null =
    null;

  if (Array.isArray(sparkRaw)) {
    if (
      sparkRaw.length >= 2 &&
      sparkRaw.every(
        (value) =>
          typeof value === "number" &&
          Number.isFinite(value)
      )
    ) {
      sparkData = sparkRaw;
    } else if (
      sparkRaw.length >= 2 &&
      sparkRaw.every(
        (point) =>
          point &&
          typeof point === "object"
      )
    ) {
      const mapped = sparkRaw
        .map((point: any) => {
          const value =
            point.value ??
            point.price ??
            point.close;

          const numeric =
            typeof value === "number"
              ? value
              : Number(value);

          return numeric;
        })
        .filter((value) =>
          Number.isFinite(value)
        );

      if (mapped.length >= 2) {
        sparkData = mapped;
      }
    }
  }

  const isInteractive =
    !!(
      props.onClick ||
      props.onSelect ||
      props.href ||
      props.to ||
      props.link
    );

  const destination =
    props.href ??
    props.to ??
    props.link;

  const hasTechnicalData =
    props.rsi != null ||
    props.ema != null ||
    props.atr != null ||
    props.momentum != null ||
    props.volatility != null ||
    props.marketStructure != null ||
    props.structure != null ||
    props.confidence != null;

  const hasAnyData =
    symbol !== "—" ||
    !isPriceNA ||
    changeRaw != null ||
    changePercentRaw != null ||
    !!aiText ||
    !!sparkData ||
    hasTechnicalData;

  if (loading) {
    return (
      <div
        className={`relative overflow-hidden rounded-[22px] border border-white/[0.07] bg-[#080D15] ${props.className || ""}`}
        aria-busy="true"
        aria-label="Market intelligence loading"
      >
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-[radial-gradient(400px_180px_at_20%_0%,rgba(34,211,238,0.06),transparent)]"
        />

        <div className="relative p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 animate-pulse rounded-[11px] bg-white/[0.055]" />

              <div>
                <div className="h-3 w-20 animate-pulse rounded-full bg-white/[0.07]" />
                <div className="mt-2 h-2 w-28 animate-pulse rounded-full bg-white/[0.04]" />
              </div>
            </div>

            <div className="h-6 w-14 animate-pulse rounded-full bg-white/[0.04]" />
          </div>

          <div className="mt-7 h-8 w-32 animate-pulse rounded bg-white/[0.07]" />

          <div className="mt-3 h-3 w-20 animate-pulse rounded-full bg-white/[0.045]" />

          <div className="mt-6 grid grid-cols-3 gap-2">
            {[0, 1, 2].map((index) => (
              <div
                key={index}
                className="h-12 animate-pulse rounded-[11px] bg-white/[0.025]"
              />
            ))}
          </div>

          <div className="mt-5 h-[58px] animate-pulse rounded-[12px] bg-white/[0.025]" />
        </div>

        <div
          aria-hidden="true"
          className="absolute inset-y-0 left-0 w-1/3 -translate-x-full animate-[kzMarketShimmer_2.2s_infinite] bg-gradient-to-r from-transparent via-white/[0.035] to-transparent"
        />

        <style jsx>{`
          @keyframes kzMarketShimmer {
            100% {
              transform: translateX(420%);
            }
          }

          @media (prefers-reduced-motion: reduce) {
            .animate-\$begin:math:display$kzMarketShimmer\_2\\\\\.2s\_infinite\\$end:math:display$ {
              animation: none;
            }
          }
        `}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`relative overflow-hidden rounded-[22px] border border-rose-300/15 bg-[#0B090D] p-5 ${props.className || ""}`}
        role="alert"
        aria-label="Market data unavailable"
      >
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-[radial-gradient(400px_180px_at_0%_0%,rgba(244,63,94,0.065),transparent)]"
        />

        <div className="relative">
          <div className="flex items-center gap-2.5">
            <span
              aria-hidden="true"
              className="h-1.5 w-1.5 rounded-full bg-rose-300 shadow-[0_0_10px_rgba(251,113,133,0.7)]"
            />

            <span className="text-[9px] font-medium uppercase tracking-[0.15em] text-rose-200/65">
              Market data unavailable
            </span>
          </div>

          <p className="mt-3 text-[12px] leading-5 text-white/55">
            {error}
          </p>

          <div className="mt-4 flex items-center gap-2 text-[9px] uppercase tracking-[0.12em] text-white/20">
            <span>
              {symbol !== "—"
                ? symbol
                : "MARKET"}
            </span>

            {timeframe && (
              <>
                <span
                  aria-hidden="true"
                  className="h-3 w-px bg-white/10"
                />
                <span>
                  {timeframe}
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (!hasAnyData) {
    return (
      <div
        className={`relative overflow-hidden rounded-[22px] border border-white/[0.06] bg-[#080D15] p-5 ${props.className || ""}`}
        aria-label="Market data pending"
      >
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-[radial-gradient(420px_180px_at_50%_0%,rgba(56,189,248,0.045),transparent)]"
        />

        <div className="relative flex flex-col items-center py-5 text-center">
          <div className="flex h-11 w-11 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.025]">
            <span className="h-1.5 w-1.5 rounded-full bg-white/25" />
          </div>

          <div className="mt-4 text-[9px] font-medium uppercase tracking-[0.16em] text-white/30">
            Market data pending
          </div>

          <p className="mt-2 max-w-xs text-[11px] leading-5 text-white/35">
            Awaiting actual market data.
            No fabricated values will be shown.
          </p>
        </div>
      </div>
    );
  }

  const changeDisplay =
    changeRaw != null
      ? safeNum(changeRaw)
      : null;

  const changePercentDisplay =
    changePercentRaw != null
      ? safePercent(changePercentRaw)
      : null;

  const content = (
    <>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
      >
        <div className="absolute inset-0 bg-[radial-gradient(500px_220px_at_12%_0%,rgba(56,189,248,0.09),transparent),radial-gradient(420px_220px_at_88%_5%,rgba(139,92,246,0.085),transparent)]" />

        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff05_1px,transparent_1px),linear-gradient(to_bottom,#ffffff05_1px,transparent_1px)] bg-[size:32px_32px] opacity-30 [mask-image:radial-gradient(ellipse_at_center,#000_50%,transparent_92%)]" />

        <div className="absolute left-1/2 top-0 h-px w-[82%] -translate-x-1/2 bg-gradient-to-r from-transparent via-cyan-300/25 to-transparent" />
      </div>

      <span
        aria-hidden="true"
        className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 rounded-tl-[14px] border-l border-t border-cyan-300/15"
      />

      <span
        aria-hidden="true"
        className="pointer-events-none absolute right-2.5 top-2.5 h-4 w-4 rounded-tr-[14px] border-r border-t border-white/10"
      />

      <span
        aria-hidden="true"
        className="pointer-events-none absolute bottom-2.5 left-2.5 h-4 w-4 rounded-bl-[14px] border-b border-l border-white/[0.06]"
      />

      <span
        aria-hidden="true"
        className="pointer-events-none absolute bottom-2.5 right-2.5 h-4 w-4 rounded-br-[14px] border-b border-r border-white/[0.06]"
      />

      <div className="relative p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex min-w-0 items-center gap-3">
              <div className="relative flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-[11px] border border-white/[0.09] bg-gradient-to-b from-white/[0.075] to-white/[0.02]">
                <div
                  aria-hidden="true"
                  className="absolute inset-0 bg-cyan-300/[0.035] blur-md"
                />

                <span className="relative text-[11px] font-semibold uppercase tracking-wide text-white/75">
                  {String(symbol)
                    .charAt(0)
                    .toUpperCase()}
                </span>
              </div>

              <div className="min-w-0">
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                  <span className="truncate text-[13px] font-semibold tracking-[-0.01em] text-white/95">
                    {symbol}
                  </span>

                  {trend && (
                    <span
                      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2 py-1 text-[8px] font-medium uppercase tracking-[0.1em] ${trendTone.border} ${trendTone.background} ${trendTone.text}`}
                    >
                      <span
                        aria-hidden="true"
                        className={`h-1 w-1 rounded-full ${trendTone.dot}`}
                      />

                      {trend}
                    </span>
                  )}
                </div>

                {(name || marketCategory) && (
                  <div className="mt-1 flex min-w-0 items-center gap-2 text-[10px] text-white/32">
                    {name && (
                      <span className="truncate">
                        {name}
                      </span>
                    )}

                    {name &&
                      marketCategory && (
                        <span
                          aria-hidden="true"
                          className="h-3 w-px shrink-0 bg-white/10"
                        />
                      )}

                    {marketCategory && (
                      <span className="shrink-0">
                        {marketCategory}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="flex shrink-0 flex-col items-end gap-1.5">
            {timeframe && (
              <span className="rounded-full border border-cyan-300/10 bg-cyan-300/[0.045] px-2.5 py-1 text-[8px] font-medium uppercase tracking-[0.12em] text-cyan-100/55">
                {timeframe}
              </span>
            )}

            {exchange && (
              <span className="max-w-[100px] truncate text-[9px] text-white/22">
                {exchange}
              </span>
            )}
          </div>
        </div>

        <div className="mt-6">
          <div className="flex flex-wrap items-end gap-x-3 gap-y-2">
            <div
              className={`max-w-full truncate text-[28px] font-semibold leading-none tracking-[-0.04em] ${
                isPriceNA
                  ? "text-white/25"
                  : "text-white"
              } ${
                !isPriceNA
                  ? trendTone.glow
                  : ""
              }`}
            >
              {priceDisplay}
            </div>

            {(changeDisplay ||
              changePercentDisplay) && (
              <div className="flex flex-wrap items-center gap-2 pb-0.5">
                {changeDisplay &&
                  changeDisplay !==
                    "N/A" && (
                    <span
                      className={`text-[11px] font-medium ${
                        isBull
                          ? "text-cyan-200/75"
                          : isBear
                            ? "text-rose-200/75"
                            : "text-white/45"
                      }`}
                    >
                      {changeDisplay}
                    </span>
                  )}

                {changePercentDisplay && (
                  <span
                    className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[9px] font-medium ${
                      isBull
                        ? "border-cyan-300/20 bg-cyan-300/[0.07] text-cyan-100/80"
                        : isBear
                          ? "border-rose-300/20 bg-rose-300/[0.07] text-rose-100/80"
                          : "border-white/[0.08] bg-white/[0.035] text-white/55"
                    }`}
                  >
                    <span aria-hidden="true">
                      {isBull
                        ? "↗"
                        : isBear
                          ? "↘"
                          : "•"}
                    </span>

                    {changePercentDisplay}
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="mt-2 text-[8px] font-medium uppercase tracking-[0.14em] text-white/20">
            Market value
          </div>
        </div>

        {hasTechnicalData && (
          <div className="mt-5 grid grid-cols-3 gap-2">
            <MetricChip
              label="RSI"
              value={props.rsi}
            />

            <MetricChip
              label="EMA"
              value={props.ema}
            />

            <MetricChip
              label="ATR"
              value={props.atr}
            />
          </div>
        )}

        {sparkData && (
          <div className="relative mt-5 overflow-hidden rounded-[14px] border border-white/[0.06] bg-[#090F18]/85 px-3 pb-2 pt-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-[8px] font-medium uppercase tracking-[0.14em] text-white/25">
                Price history
              </span>

              <span className="text-[8px] uppercase tracking-[0.12em] text-white/18">
                {sparkData.length} points
              </span>
            </div>

            <div className="mt-2">
              <MiniSparkline
                data={sparkData}
                isBull={isBull}
                isBear={isBear}
                id={String(symbol).replace(
                  /[^a-zA-Z0-9_-]/g,
                  ""
                )}
              />
            </div>
          </div>
        )}

        {aiText && (
          <div className="relative mt-5 overflow-hidden rounded-[15px] border border-cyan-300/12 bg-gradient-to-b from-cyan-300/[0.045] to-white/[0.01] p-px">
            <div className="relative overflow-hidden rounded-[14px] bg-[#08121C]/90 p-3.5 backdrop-blur-xl">
              <div
                aria-hidden="true"
                className="absolute -right-8 -top-8 h-20 w-20 rounded-full bg-cyan-300/[0.055] blur-2xl"
              />

              <div className="relative flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className="h-1.5 w-1.5 rounded-full bg-cyan-300 shadow-[0_0_9px_rgba(34,211,238,0.7)]"
                />

                <span className="text-[8px] font-medium uppercase tracking-[0.14em] text-cyan-200/55">
                  AI market read
                </span>
              </div>

              <p className="relative mt-2 line-clamp-3 text-[11px] leading-[1.6] text-white/58">
                {aiText}
              </p>
            </div>
          </div>
        )}

        {(props.momentum ||
          props.volatility ||
          props.marketStructure ||
          props.structure ||
          props.confidence) && (
          <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-[8px] uppercase tracking-[0.12em] text-white/25">
            {props.momentum && (
              <span>
                Momentum:{" "}
                <strong className="font-medium text-white/50">
                  {safeNum(
                    props.momentum
                  )}
                </strong>
              </span>
            )}

            {props.volatility && (
              <span>
                Volatility:{" "}
                <strong className="font-medium text-white/50">
                  {safeNum(
                    props.volatility
                  )}
                </strong>
              </span>
            )}

            {(props.marketStructure ||
              props.structure) && (
              <span>
                Structure:{" "}
                <strong className="font-medium text-white/50">
                  {props.marketStructure ??
                    props.structure}
                </strong>
              </span>
            )}

            {props.confidence !=
              null && (
              <span>
                Confidence:{" "}
                <strong className="font-medium text-white/50">
                  {safeNum(
                    props.confidence
                  )}
                </strong>
              </span>
            )}
          </div>
        )}

        <div className="mt-5 flex items-center justify-between gap-3 border-t border-white/[0.05] pt-3.5">
          <span className="min-w-0 truncate text-[8px] uppercase tracking-[0.12em] text-white/18">
            {props.lastUpdated ??
              props.updatedAt ??
              props.timestamp ??
              props.time ??
              ""}
          </span>

          <span className="flex shrink-0 items-center gap-1.5 text-[8px] uppercase tracking-[0.12em] text-white/20">
            <span
              aria-hidden="true"
              className="h-1 w-1 rounded-full bg-white/20"
            />
            KZ • Intel
          </span>
        </div>
      </div>
    </>
  );

  if (destination) {
    return (
      <a
        href={destination}
        onClick={
          props.onClick ??
          props.onSelect
        }
        aria-label={
          symbol !== "—"
            ? `Open market ${symbol}`
            : "Open market"
        }
        className={`kz-card kz-glass group relative block overflow-hidden rounded-[22px] border border-white/[0.08] bg-gradient-to-b from-[#0D1522] to-[#070A11] shadow-[0_12px_40px_rgba(0,0,0,0.48),inset_0_1px_0_rgba(255,255,255,0.06)] transition-all duration-300 hover:-translate-y-[2px] hover:border-cyan-300/[0.15] hover:shadow-[0_18px_55px_rgba(0,0,0,0.58),0_0_35px_rgba(34,211,238,0.045)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/30 ${
          props.active ||
          props.selected
            ? "border-cyan-300/25 ring-1 ring-cyan-300/20"
            : ""
        } ${
          props.disabled
            ? "pointer-events-none opacity-50"
            : ""
        } ${props.className || ""}`}
      >
        {content}
      </a>
    );
  }

  return (
    <div
      role={
        isInteractive
          ? "button"
          : undefined
      }
      tabIndex={
        isInteractive &&
        !props.disabled
          ? 0
          : undefined
      }
      aria-disabled={
        props.disabled || undefined
      }
      aria-label={
        isInteractive
          ? symbol !== "—"
            ? `Market ${symbol}`
            : "Market card"
          : undefined
      }
      onClick={
        props.disabled
          ? undefined
          : props.onClick ??
            props.onSelect
      }
      onKeyDown={(event) => {
        if (
          !isInteractive ||
          props.disabled
        ) {
          return;
        }

        if (
          event.key === "Enter" ||
          event.key === " "
        ) {
          event.preventDefault();

          (
            props.onClick ??
            props.onSelect
          )?.();
        }
      }}
      className={`kz-card kz-glass group relative overflow-hidden rounded-[22px] border border-white/[0.08] bg-gradient-to-b from-[#0D1522] to-[#070A11] shadow-[0_12px_40px_rgba(0,0,0,0.48),inset_0_1px_0_rgba(255,255,255,0.06)] transition-all duration-300 ${
        isInteractive
          ? "cursor-pointer hover:-translate-y-[2px] hover:border-cyan-300/[0.15] hover:shadow-[0_18px_55px_rgba(0,0,0,0.58),0_0_35px_rgba(34,211,238,0.045)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/30"
          : ""
      } ${
        props.active ||
        props.selected
          ? "border-cyan-300/25 ring-1 ring-cyan-300/20"
          : ""
      } ${
        props.disabled
          ? "pointer-events-none opacity-50"
          : ""
      } ${props.className || ""}`}
    >
      {content}
    </div>
  );
}
