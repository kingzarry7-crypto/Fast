import React from "react";

export type BadgeVariant =
  | "default"
  | "primary"
  | "secondary"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "neutral"
  | "bullish"
  | "bearish"
  | "ai"
  | "active"
  | "offline";

export type BadgeSize = "sm" | "md" | "lg";

export interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  status?: string;
  className?: string;
  icon?: React.ReactNode;
  dot?: boolean;
  glow?: boolean;
  onClick?: () => void;
  disabled?: boolean;
}

const SIZE_CLASSES: Record<BadgeSize, string> = {
  sm: "min-h-5 px-2 py-0.5 text-[10px] gap-1",
  md: "min-h-6 px-2.5 py-1 text-[11px] gap-1.5",
  lg: "min-h-8 px-3 py-1.5 text-xs gap-2",
};

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  default:
    "bg-black/55 border-cyan-500/30 text-cyan-300",

  primary:
    "bg-cyan-500/15 border-cyan-400/45 text-cyan-200",

  secondary:
    "bg-purple-500/15 border-purple-400/45 text-purple-200",

  success:
    "bg-emerald-500/15 border-emerald-400/45 text-emerald-200",

  warning:
    "bg-amber-500/15 border-amber-400/45 text-amber-200",

  danger:
    "bg-red-500/15 border-red-400/45 text-red-200",

  info:
    "bg-blue-500/15 border-blue-400/45 text-blue-200",

  neutral:
    "bg-neutral-900/75 border-neutral-700/50 text-neutral-300",

  bullish:
    "bg-cyan-500/20 border-cyan-400/55 text-cyan-200",

  bearish:
    "bg-red-500/20 border-red-400/55 text-red-200",

  ai:
    "bg-cyan-950/80 border-cyan-400/55 text-cyan-200",

  active:
    "bg-emerald-500/15 border-emerald-400/50 text-emerald-200",

  offline:
    "bg-neutral-800/70 border-neutral-700/50 text-neutral-400",
};

const DOT_CLASSES: Record<BadgeVariant, string> = {
  default: "bg-cyan-400",

  primary: "bg-cyan-400",

  secondary: "bg-purple-400",

  success: "bg-emerald-400",

  warning: "bg-amber-400",

  danger: "bg-red-400",

  info: "bg-blue-400",

  neutral: "bg-neutral-400",

  bullish: "bg-cyan-400",

  bearish: "bg-red-400",

  ai: "bg-cyan-400",

  active: "bg-emerald-400",

  offline: "bg-neutral-500",
};

const GLOW_CLASSES: Record<BadgeVariant, string> = {
  default: "shadow-[0_0_14px_rgba(6,182,212,0.18)]",

  primary: "shadow-[0_0_16px_rgba(6,182,212,0.25)]",

  secondary: "shadow-[0_0_16px_rgba(168,85,247,0.24)]",

  success: "shadow-[0_0_16px_rgba(16,185,129,0.24)]",

  warning: "shadow-[0_0_16px_rgba(245,158,11,0.22)]",

  danger: "shadow-[0_0_16px_rgba(239,68,68,0.24)]",

  info: "shadow-[0_0_16px_rgba(59,130,246,0.22)]",

  neutral: "shadow-[0_0_12px_rgba(163,163,163,0.08)]",

  bullish: "shadow-[0_0_18px_rgba(6,182,212,0.30)]",

  bearish: "shadow-[0_0_18px_rgba(239,68,68,0.30)]",

  ai: "shadow-[0_0_22px_rgba(6,182,212,0.35)]",

  active: "shadow-[0_0_18px_rgba(16,185,129,0.28)]",

  offline: "shadow-[0_0_10px_rgba(115,115,115,0.08)]",
};

function getDotGlow(variant: BadgeVariant) {
  switch (variant) {
    case "secondary":
      return "shadow-[0_0_8px_rgba(168,85,247,0.9)]";

    case "success":
    case "active":
      return "shadow-[0_0_8px_rgba(16,185,129,0.9)]";

    case "warning":
      return "shadow-[0_0_8px_rgba(245,158,11,0.9)]";

    case "danger":
    case "bearish":
      return "shadow-[0_0_8px_rgba(239,68,68,0.9)]";

    case "info":
      return "shadow-[0_0_8px_rgba(59,130,246,0.9)]";

    case "offline":
    case "neutral":
      return "";

    case "default":
    case "primary":
    case "bullish":
    case "ai":
    default:
      return "shadow-[0_0_8px_rgba(6,182,212,0.9)]";
  }
}

export function Badge({
  children,
  variant = "default",
  size = "md",
  status,
  className = "",
  icon,
  dot = false,
  glow = false,
  onClick,
  disabled = false,
}: BadgeProps) {
  const showDot = dot || Boolean(status);
  const isInteractive = Boolean(onClick);

  const baseClasses = [
    "relative",
    "inline-flex",
    "items-center",
    "justify-center",
    "max-w-full",
    "overflow-hidden",
    "rounded-lg",
    "border",
    "backdrop-blur-md",
    "font-mono",
    "font-medium",
    "uppercase",
    "tracking-wider",
    "leading-none",
    "select-none",
    "transition-all",
    "duration-200",
    "shrink-0",
    "whitespace-nowrap",
    SIZE_CLASSES[size],
    VARIANT_CLASSES[variant],
    glow ? GLOW_CLASSES[variant] : "",
    isInteractive
      ? "cursor-pointer hover:-translate-y-px hover:brightness-110 active:translate-y-0"
      : "",
    disabled ? "opacity-50 cursor-not-allowed" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const content = (
    <>
      {showDot && (
        <span
          className={[
            "relative h-1.5 w-1.5 shrink-0 rounded-full",
            DOT_CLASSES[variant],
            getDotGlow(variant),
            variant === "active" || variant === "ai"
              ? "animate-pulse"
              : "",
          ]
            .filter(Boolean)
            .join(" ")}
          aria-hidden="true"
        />
      )}

      {icon && (
        <span
          className="flex shrink-0 items-center justify-center"
          aria-hidden="true"
        >
          {icon}
        </span>
      )}

      <span className="min-w-0 truncate">{children}</span>

      {status && (
        <span className="sr-only">
          {" "}
          Status: {status}
        </span>
      )}
    </>
  );

  if (isInteractive) {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        aria-disabled={disabled}
        className="inline-flex max-w-full rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/70 focus-visible:ring-offset-2 focus-visible:ring-offset-black"
      >
        <span className={baseClasses}>{content}</span>
      </button>
    );
  }

  return (
    <span
      className={baseClasses}
      aria-disabled={disabled || undefined}
    >
      {content}
    </span>
  );
}
