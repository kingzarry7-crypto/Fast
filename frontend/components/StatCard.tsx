"use client";

export function LineChart({
  color = "#00f0ff",
  height = 32,
}: {
  color?: string;
  height?: number;
}) {
  return (
    <svg
      width="100%"
      height={height}
      viewBox="0 0 100 30"
      preserveAspectRatio="none"
      className="block"
    >
      <defs>
        <linearGradient id="kzLine" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path
        d="M0,22 L12,18 L24,20 L36,12 L48,15 L60,8 L72,11 L84,5 L100,9"
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        style={{ filter: `drop-shadow(0 0 4px ${color})` }}
      />
      <path
        d="M0,22 L12,18 L24,20 L36,12 L48,15 L60,8 L72,11 L84,5 L100,9 L100,30 L0,30 Z"
        fill="url(#kzLine)"
      />
    </svg>
  );
}

export default function StatCard({
  title,
  value,
  sub,
  color = "#00f0ff",
  showChart = false,
  className = "",
}: {
  title: string;
  value?: string;
  sub?: string;
  color?: string;
  showChart?: boolean;
  className?: string;
}) {
  return (
    <div className={`kz-glass p-4 ${className}`}>
      <p
        className="font-mono-tech text-[10px] tracking-[0.3em] mb-2"
        style={{ color: `${color}aa` }}
      >
        {title}
      </p>
      {value && (
        <p
          className="font-display text-sm font-bold"
          style={{ color, textShadow: `0 0 8px ${color}88` }}
        >
          {value}
        </p>
      )}
      {sub && (
        <p className="font-mono-tech text-[10px] tracking-widest text-cyan-200/40 mt-1">
          {sub}
        </p>
      )}
      {showChart && (
        <div className="mt-2">
          <LineChart color={color} />
        </div>
      )}
    </div>
  );
}
