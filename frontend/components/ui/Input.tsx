import React, { useId } from "react";

export type InputVariant = "default" | "glass" | "holographic";
export type InputSize = "sm" | "md" | "lg";
export type IconPosition = "left" | "right";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  icon?: React.ReactNode;
  iconPosition?: IconPosition;
  loading?: boolean;
  variant?: InputVariant;
  inputSize?: InputSize;
  fullWidth?: boolean;
}

const SIZE_CLASSES: Record<InputSize, string> = {
  sm: "min-h-8 px-3 py-1.5 text-xs",
  md: "min-h-10 px-3.5 py-2.5 text-xs sm:text-sm",
  lg: "min-h-12 px-4 py-3 text-sm sm:text-base",
};

const VARIANT_CLASSES: Record<InputVariant, string> = {
  default:
    "bg-black/80 backdrop-blur-md border-cyan-500/25 text-white placeholder:text-cyan-400/35 hover:border-cyan-500/50 focus:border-cyan-400 focus:shadow-[0_0_20px_rgba(6,182,212,0.18)]",

  glass:
    "bg-black/55 backdrop-blur-2xl border-cyan-500/30 text-white placeholder:text-cyan-400/35 hover:border-cyan-400/50 focus:border-cyan-400 focus:shadow-[0_0_24px_rgba(6,182,212,0.20)]",

  holographic:
    "bg-black/70 backdrop-blur-2xl border-cyan-400/45 text-white placeholder:text-cyan-300/35 shadow-[0_0_20px_rgba(6,182,212,0.10)] hover:border-cyan-300/65 focus:border-cyan-300 focus:shadow-[0_0_28px_rgba(6,182,212,0.28)]",
};

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      id: providedId,
      label,
      hint,
      error,
      icon,
      iconPosition = "left",
      loading = false,
      variant = "default",
      inputSize = "md",
      fullWidth = true,
      disabled = false,
      readOnly = false,
      className = "",
      "aria-describedby": providedAriaDescribedBy,
      "aria-invalid": providedAriaInvalid,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();

    const inputId = providedId || generatedId;
    const hintId = hint ? `${inputId}-hint` : undefined;
    const errorId = error ? `${inputId}-error` : undefined;

    const describedBy = [
      providedAriaDescribedBy,
      hintId,
      errorId,
    ]
      .filter(Boolean)
      .join(" ");

    const hasLeftIcon = Boolean(icon && iconPosition === "left");
    const hasRightIcon = Boolean(icon && iconPosition === "right");
    const hasRightElement = hasRightIcon || loading;

    const wrapperClasses = [
      "flex",
      "min-w-0",
      "flex-col",
      "gap-1.5",
      fullWidth ? "w-full" : "w-auto",
      className,
    ]
      .filter(Boolean)
      .join(" ");

    const inputClasses = [
      "relative",
      "w-full",
      "rounded-xl",
      "border",
      "font-mono",
      "outline-none",
      "transition-all",
      "duration-200",
      "selection:bg-cyan-400/20",
      "selection:text-cyan-100",
      "focus:outline-none",
      "focus-visible:ring-2",
      "focus-visible:ring-cyan-400/25",
      "motion-reduce:transition-none",
      SIZE_CLASSES[inputSize],

      hasLeftIcon ? "pl-10" : "",
      hasRightElement ? "pr-10" : "",

      error
        ? "border-red-500/60 bg-red-950/20 text-red-100 placeholder:text-red-400/40 focus:border-red-400 focus-visible:ring-red-400/20 focus:shadow-[0_0_20px_rgba(239,68,68,0.16)]"
        : VARIANT_CLASSES[variant],

      disabled
        ? "cursor-not-allowed opacity-50"
        : "",

      readOnly
        ? "bg-neutral-900/50 cursor-default"
        : "",

      className ? "" : "",
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <div className={wrapperClasses}>
        {label && (
          <label
            htmlFor={inputId}
            className="text-[11px] font-mono font-semibold uppercase tracking-wider text-cyan-300/90 sm:text-xs"
          >
            {label}
          </label>
        )}

        <div className="relative flex min-w-0 w-full items-center">
          {variant === "holographic" && (
            <>
              <span
                className="pointer-events-none absolute left-0 top-0 z-20 h-2.5 w-2.5 border-l border-t border-cyan-400/70"
                aria-hidden="true"
              />

              <span
                className="pointer-events-none absolute bottom-0 right-0 z-20 h-2.5 w-2.5 border-b border-r border-cyan-400/70"
                aria-hidden="true"
              />
            </>
          )}

          {hasLeftIcon && (
            <span
              className="pointer-events-none absolute left-3 z-10 flex items-center justify-center text-cyan-400/70"
              aria-hidden="true"
            >
              {icon}
            </span>
          )}

          <input
            {...props}
            ref={ref}
            id={inputId}
            disabled={disabled}
            readOnly={readOnly}
            aria-invalid={
              error
                ? true
                : providedAriaInvalid
            }
            aria-describedby={describedBy || undefined}
            className={inputClasses}
          />

          {hasRightElement && (
            <span
              className="pointer-events-none absolute right-3 z-10 flex items-center justify-center text-cyan-400/70"
              aria-hidden="true"
            >
              {loading ? (
                <span
                  className="h-4 w-4 animate-spin rounded-full border-2 border-cyan-400/25 border-t-cyan-400 motion-reduce:animate-none"
                />
              ) : (
                icon
              )}
            </span>
          )}
        </div>

        {(error || hint) && (
          <div className="min-h-4">
            {error ? (
              <p
                id={errorId}
                className="font-mono text-[10px] tracking-wide text-red-400 sm:text-[11px]"
              >
                {error}
              </p>
            ) : (
              <p
                id={hintId}
                className="font-mono text-[10px] tracking-wide text-cyan-400/55 sm:text-[11px]"
              >
                {hint}
              </p>
            )}
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
