import React from "react";

export type SpinnerSize = "xs" | "sm" | "md" | "lg" | "xl";

export type SpinnerVariant =
  | "default"
  | "primary"
  | "ai"
  | "muted"
  | "white";

export interface SpinnerProps {
  size?: SpinnerSize;
  variant?: SpinnerVariant;
  label?: string;
  className?: string;
}

const SIZE_CLASSES: Record<
  SpinnerSize,
  {
    spinner: string;
    text: string;
    gap: string;
  }
> = {
  xs: {
    spinner: "h-3 w-3",
    text: "text-[10px]",
    gap: "gap-1.5",
  },
  sm: {
    spinner: "h-4 w-4",
    text: "text-xs",
    gap: "gap-2",
  },
  md: {
    spinner: "h-6 w-6",
    text: "text-xs",
    gap: "gap-2.5",
  },
  lg: {
    spinner: "h-8 w-8",
    text: "text-sm",
    gap: "gap-3",
  },
  xl: {
    spinner: "h-12 w-12",
    text: "text-base",
    gap: "gap-3.5",
  },
};

const VARIANT_CLASSES: Record<SpinnerVariant, string> = {
  default:
    "text-cyan-400/90 drop-shadow-[0_0_8px_rgba(6,182,212,0.40)]",

  primary:
    "text-cyan-400 drop-shadow-[0_0_9px_rgba(6,182,212,0.55)]",

  ai:
    "text-cyan-300 drop-shadow-[0_0_12px_rgba(6,182,212,0.70)]",

  muted:
    "text-neutral-500",

  white:
    "text-white drop-shadow-[0_0_6px_rgba(255,255,255,0.45)]",
};

const LABEL_CLASSES: Record<SpinnerVariant, string> = {
  default: "text-cyan-200/80",
  primary: "text-cyan-200/90",
  ai: "text-cyan-100",
  muted: "text-neutral-400",
  white: "text-white/90",
};

export function Spinner({
  size = "md",
  variant = "default",
  label,
  className = "",
}: SpinnerProps) {
  const sizeConfig = SIZE_CLASSES[size];
  const variantClass = VARIANT_CLASSES[variant];
  const labelClass = LABEL_CLASSES[variant];

  return (
    <div
      role="status"
      aria-label={label || "Loading"}
      className={[
        "inline-flex items-center",
        sizeConfig.gap,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <svg
        className={[
          "shrink-0",
          "animate-spin",
          "motion-reduce:animate-none",
          sizeConfig.spinner,
          variantClass,
        ].join(" ")}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <circle
          cx="12"
          cy="12"
          r="9.5"
          stroke="currentColor"
          strokeWidth="2.5"
          className="opacity-20"
        />

        <path
          d="M21.5 12a9.5 9.5 0 0 1-9.5 9.5"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          className="opacity-90"
        />
      </svg>

      {label && (
        <span
          className={[
            "font-mono font-medium tracking-wider",
            sizeConfig.text,
            labelClass,
          ].join(" ")}
        >
          {label}
        </span>
      )}
    </div>
  );
}

export default Spinner;
