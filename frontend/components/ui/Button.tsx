import React from "react";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "ghost"
  | "outline"
  | "danger"
  | "success"
  | "ai"
  | "neutral";

export type ButtonSize = "sm" | "md" | "lg" | "icon";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
  fullWidth?: boolean;
  href?: string;
  target?: string;
  rel?: string;
}

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "min-h-8 px-3 py-1.5 text-xs gap-1.5",
  md: "min-h-9 px-4 py-2 text-xs sm:text-sm gap-2",
  lg: "min-h-11 px-6 py-3 text-sm gap-2.5",
  icon: "h-10 w-10 p-2.5 text-sm",
};

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    "bg-cyan-500/20 text-cyan-100 border-cyan-400/50 shadow-[0_0_20px_rgba(6,182,212,0.22)] hover:bg-cyan-500/30 hover:border-cyan-300/70 hover:shadow-[0_0_26px_rgba(6,182,212,0.36)]",

  secondary:
    "bg-black/70 text-cyan-300 border-cyan-500/30 hover:bg-cyan-950/50 hover:border-cyan-400/55",

  ghost:
    "bg-transparent text-cyan-300/80 border-transparent hover:bg-cyan-500/10 hover:text-cyan-100",

  outline:
    "bg-black/40 text-cyan-300 border-cyan-500/40 hover:bg-cyan-500/10 hover:border-cyan-300/70",

  danger:
    "bg-red-950/40 text-red-200 border-red-500/50 hover:bg-red-900/50 hover:border-red-400/70 shadow-[0_0_15px_rgba(239,68,68,0.16)]",

  success:
    "bg-emerald-950/50 text-emerald-200 border-emerald-400/50 hover:bg-emerald-900/50 hover:border-emerald-300/70 shadow-[0_0_15px_rgba(16,185,129,0.16)]",

  ai:
    "bg-cyan-950/90 text-cyan-100 border-cyan-400/65 shadow-[0_0_24px_rgba(6,182,212,0.32)] hover:bg-cyan-900/90 hover:border-cyan-300 hover:shadow-[0_0_32px_rgba(6,182,212,0.48)]",

  neutral:
    "bg-neutral-900/90 text-neutral-200 border-neutral-700/60 hover:bg-neutral-800 hover:border-neutral-600",
};

const SPINNER_CLASSES: Record<ButtonVariant, string> = {
  primary: "border-cyan-300/30 border-t-cyan-300",
  secondary: "border-cyan-400/25 border-t-cyan-400",
  ghost: "border-cyan-400/25 border-t-cyan-400",
  outline: "border-cyan-400/25 border-t-cyan-400",
  danger: "border-red-300/30 border-t-red-300",
  success: "border-emerald-300/30 border-t-emerald-300",
  ai: "border-cyan-300/30 border-t-cyan-200",
  neutral: "border-neutral-400/30 border-t-neutral-300",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = "primary",
      size = "md",
      type = "button",
      disabled = false,
      loading = false,
      icon,
      iconPosition = "left",
      fullWidth = false,
      className = "",
      onClick,
      href,
      target,
      rel,
      "aria-label": ariaLabel,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;
    const isIconOnly = size === "icon" || Boolean(icon && !children);

    const sizeClass = isIconOnly
      ? size === "icon"
        ? SIZE_CLASSES.icon
        : "h-9 w-9 p-2"
      : SIZE_CLASSES[size];

    const baseClasses = [
      fullWidth ? "flex w-full" : "inline-flex",
      "items-center",
      "justify-center",
      "shrink-0",
      "rounded-xl",
      "border",
      "font-mono",
      "font-semibold",
      "uppercase",
      "tracking-wider",
      "select-none",
      "whitespace-nowrap",
      "transition-all",
      "duration-200",
      "focus:outline-none",
      "focus-visible:ring-2",
      "focus-visible:ring-cyan-400/70",
      "focus-visible:ring-offset-2",
      "focus-visible:ring-offset-black",
      "hover:-translate-y-px",
      "active:translate-y-0",
      "active:scale-[0.98]",
      sizeClass,
      VARIANT_CLASSES[variant],
      isDisabled
        ? "opacity-50 cursor-not-allowed pointer-events-none"
        : "cursor-pointer",
      className,
    ]
      .filter(Boolean)
      .join(" ");

    const content = (
      <>
        {loading && (
          <span
            className={[
              "h-3.5 w-3.5 shrink-0 rounded-full border-2 animate-spin",
              SPINNER_CLASSES[variant],
            ].join(" ")}
            aria-hidden="true"
          />
        )}

        {!loading && icon && iconPosition === "left" && (
          <span
            className="flex shrink-0 items-center justify-center"
            aria-hidden={isIconOnly ? undefined : true}
          >
            {icon}
          </span>
        )}

        {children && (
          <span className="min-w-0 truncate">
            {children}
          </span>
        )}

        {!loading && icon && iconPosition === "right" && (
          <span
            className="flex shrink-0 items-center justify-center"
            aria-hidden="true"
          >
            {icon}
          </span>
        )}

        {loading && (
          <span className="sr-only">Loading</span>
        )}
      </>
    );

    if (href && !isDisabled) {
      return (
        <a
          href={href}
          target={target}
          rel={rel}
          aria-label={ariaLabel}
          className={baseClasses}
        >
          {content}
        </a>
      );
    }

    if (href && isDisabled) {
      return (
        <span
          aria-disabled="true"
          aria-label={ariaLabel}
          className={baseClasses}
        >
          {content}
        </span>
      );
    }

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        onClick={onClick}
        aria-label={ariaLabel}
        aria-busy={loading || undefined}
        className={baseClasses}
        {...props}
      >
        {content}
      </button>
    );
  }
);

Button.displayName = "Button";
