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
      ...props
    },
    ref
  ) => {
    // Size mapping
    const getSizeStyles = (s: ButtonSize, hasIconOnly: boolean) => {
      switch (s) {
        case "sm":
          return hasIconOnly ? "p-1.5 text-xs" : "px-3 py-1.5 text-xs gap-1.5";
        case "lg":
          return hasIconOnly ? "p-3 text-base" : "px-6 py-3 text-sm gap-2.5";
        case "icon":
          return "p-2.5 text-sm aspect-square justify-center";
        case "md":
        default:
          return hasIconOnly ? "p-2 text-sm" : "px-4 py-2 text-xs sm:text-sm gap-2";
      }
    };

    // Variant styling mapping for KING ZARRY AI visual system
    const getVariantStyles = (v: ButtonVariant) => {
      switch (v) {
        case "primary":
          return "bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-200 border border-cyan-400/50 shadow-[0_0_20px_rgba(6,182,212,0.25)] hover:shadow-[0_0_25px_rgba(6,182,212,0.4)] active:scale-[0.98]";
        case "secondary":
          return "bg-black/70 hover:bg-cyan-950/40 text-cyan-300 border border-cyan-500/30 hover:border-cyan-400/50 shadow-[inset_0_0_15px_rgba(6,182,212,0.05)] active:scale-[0.98]";
        case "ghost":
          return "bg-transparent hover:bg-cyan-500/10 text-cyan-300/80 hover:text-cyan-200 border border-transparent active:scale-[0.98]";
        case "outline":
          return "bg-black/40 backdrop-blur-md hover:bg-cyan-500/10 text-cyan-300 border border-cyan-500/40 hover:border-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.1)] active:scale-[0.98]";
        case "danger":
          return "bg-red-950/40 hover:bg-red-900/50 text-red-200 border border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.2)] active:scale-[0.98]";
        case "success":
          return "bg-cyan-950/60 hover:bg-cyan-900/60 text-cyan-200 border border-cyan-400/60 shadow-[0_0_15px_rgba(6,182,212,0.25)] active:scale-[0.98]";
        case "ai":
          return "bg-cyan-950/90 hover:bg-cyan-900 text-cyan-100 border border-cyan-400/70 shadow-[0_0_25px_rgba(6,182,212,0.4)] hover:shadow-[0_0_30px_rgba(6,182,212,0.6)] active:scale-[0.98]";
        case "neutral":
        default:
          return "bg-neutral-900 hover:bg-neutral-800 text-neutral-200 border border-neutral-700/60 active:scale-[0.98]";
      }
    };

    const isIconOnly = Boolean(icon && !children);
    const sizeClasses = getSizeStyles(size, isIconOnly);
    const variantClasses = getVariantStyles(variant);
    const widthClass = fullWidth ? "w-full flex" : "inline-flex";

    const content = (
      <>
        {loading && (
          <span
            className="w-3.5 h-3.5 rounded-full border-2 border-cyan-400/30 border-t-cyan-400 animate-spin shrink-0"
            aria-hidden="true"
          />
        )}
        {!loading && icon && iconPosition === "left" && (
          <span className="shrink-0 flex items-center">{icon}</span>
        )}
        {children && <span className="truncate font-mono tracking-wider">{children}</span>}
        {!loading && icon && iconPosition === "right" && (
          <span className="shrink-0 flex items-center">{icon}</span>
        )}
      </>
    );

    const commonClassName = `${widthClass} items-center justify-center font-mono font-bold rounded-xl uppercase transition-all select-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-cyan-400/70 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none ${sizeClasses} ${variantClasses} ${className}`;

    if (href) {
      return (
        <a
          href={href}
          target={target}
          rel={rel}
          className={commonClassName}
          aria-disabled={disabled || loading}
        >
          {content}
        </a>
      );
    }

    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || loading}
        onClick={onClick}
        className={commonClassName}
        {...props}
      >
        {content}
      </button>
    );
  }
);

Button.displayName = "Button";
