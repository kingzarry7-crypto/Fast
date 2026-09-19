import React from "react";

export type CardVariant =
  | "default"
  | "glass"
  | "holographic"
  | "elevated"
  | "outline"
  | "transparent";

export type CardPadding = "none" | "sm" | "md" | "lg";
export type CardRadius = "sm" | "md" | "lg" | "xl";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: CardVariant;
  padding?: CardPadding;
  radius?: CardRadius;
  glow?: boolean;
  hover?: boolean;
  border?: boolean;
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
}

const PADDING_CLASSES: Record<CardPadding, string> = {
  none: "p-0",
  sm: "p-3 sm:p-4",
  md: "p-4 sm:p-6",
  lg: "p-6 sm:p-8",
};

const RADIUS_CLASSES: Record<CardRadius, string> = {
  sm: "rounded-lg",
  md: "rounded-xl",
  lg: "rounded-2xl",
  xl: "rounded-2xl sm:rounded-3xl",
};

const VARIANT_CLASSES: Record<CardVariant, string> = {
  default:
    "bg-black/80 backdrop-blur-xl text-white",

  glass:
    "bg-black/60 backdrop-blur-2xl text-white",

  holographic:
    "bg-black/70 backdrop-blur-2xl text-white",

  elevated:
    "bg-black/90 text-white shadow-[0_12px_45px_rgba(0,0,0,0.65)]",

  outline:
    "bg-black/35 backdrop-blur-md text-white",

  transparent:
    "bg-transparent text-white",
};

const BORDER_CLASSES: Record<CardVariant, string> = {
  default: "border-cyan-500/25",
  glass: "border-cyan-400/25",
  holographic: "border-cyan-400/50",
  elevated: "border-white/10",
  outline: "border-cyan-500/40",
  transparent: "border-cyan-500/20",
};

const GLOW_CLASSES: Record<CardVariant, string> = {
  default: "shadow-[0_4px_30px_rgba(6,182,212,0.10)]",
  glass: "shadow-[0_4px_35px_rgba(6,182,212,0.12)]",
  holographic:
    "shadow-[0_0_35px_rgba(6,182,212,0.24),0_0_70px_rgba(168,85,247,0.08)]",
  elevated: "shadow-[0_12px_45px_rgba(0,0,0,0.7),0_0_22px_rgba(6,182,212,0.10)]",
  outline: "shadow-[0_0_22px_rgba(6,182,212,0.08)]",
  transparent: "shadow-none",
};

export function Card({
  children,
  variant = "default",
  padding = "md",
  radius = "xl",
  glow = false,
  hover = false,
  border = true,
  className = "",
  onClick,
  disabled = false,
  ...props
}: CardProps) {
  const isInteractive = Boolean(onClick) && !disabled;

  const classes = [
    "relative",
    "flex",
    "flex-col",
    "min-w-0",
    "overflow-hidden",
    "isolate",
    PADDING_CLASSES[padding],
    RADIUS_CLASSES[radius],
    VARIANT_CLASSES[variant],

    border ? "border" : "border-0",
    border ? BORDER_CLASSES[variant] : "",

    glow ? GLOW_CLASSES[variant] : "",

    hover || isInteractive
      ? [
          "transition-all",
          "duration-300",
          "hover:-translate-y-0.5",
          "hover:border-cyan-400/55",
          "hover:shadow-[0_8px_38px_rgba(6,182,212,0.16)]",
          "motion-reduce:transition-none",
          "motion-reduce:hover:translate-y-0",
        ].join(" ")
      : "",

    isInteractive
      ? [
          "cursor-pointer",
          "focus:outline-none",
          "focus-visible:ring-2",
          "focus-visible:ring-cyan-400/70",
          "focus-visible:ring-offset-2",
          "focus-visible:ring-offset-black",
        ].join(" ")
      : "",

    disabled ? "opacity-50 cursor-not-allowed" : "",

    className,
  ]
    .filter(Boolean)
    .join(" ");

  const decorativeLayer =
    variant === "holographic" ? (
      <>
        {/* Ambient holographic glow */}
        <div
          className="pointer-events-none absolute -inset-20 -z-10 rounded-full bg-[radial-gradient(circle,rgba(6,182,212,0.10),transparent_62%)] blur-2xl"
          aria-hidden="true"
        />

        {/* Technical corner brackets */}
        <div
          className="pointer-events-none absolute left-0 top-0 h-4 w-4 border-l border-t border-cyan-400/80"
          aria-hidden="true"
        />

        <div
          className="pointer-events-none absolute right-0 top-0 h-4 w-4 border-r border-t border-cyan-400/80"
          aria-hidden="true"
        />

        <div
          className="pointer-events-none absolute bottom-0 left-0 h-4 w-4 border-b border-l border-cyan-400/80"
          aria-hidden="true"
        />

        <div
          className="pointer-events-none absolute bottom-0 right-0 h-4 w-4 border-b border-r border-cyan-400/80"
          aria-hidden="true"
        />

        {/* Very subtle holographic scan texture */}
        <div
          className="pointer-events-none absolute inset-0 opacity-30 [background-image:linear-gradient(to_bottom,transparent_0%,transparent_96%,rgba(6,182,212,0.035)_100%)] [background-size:100%_5px]"
          aria-hidden="true"
        />
      </>
    ) : null;

  const content = (
    <>
      {decorativeLayer}
      <div className="relative z-10 min-w-0">{children}</div>
    </>
  );

  if (onClick) {
    return (
      <div
        {...props}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled || undefined}
        className={classes}
        onClick={disabled ? undefined : onClick}
        onKeyDown={(event) => {
          if (disabled) return;

          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onClick();
          }
        }}
      >
        {content}
      </div>
    );
  }

  return (
    <div {...props} className={classes}>
      {content}
    </div>
  );
}
