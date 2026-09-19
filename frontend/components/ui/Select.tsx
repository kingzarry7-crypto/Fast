"use client";

import React, { useId } from "react";

export type SelectVariant = "default" | "glass" | "holographic";
export type SelectSize = "sm" | "md" | "lg";

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
  error?: string;
  options?: SelectOption[];
  variant?: SelectVariant;
  selectSize?: SelectSize;
  fullWidth?: boolean;
  placeholder?: string;
  icon?: React.ReactNode;
  loading?: boolean;
}

const SIZE_CLASSES: Record<SelectSize, string> = {
  sm: "min-h-8 px-3 py-1.5 text-xs",
  md: "min-h-10 px-3.5 py-2.5 text-xs sm:text-sm",
  lg: "min-h-12 px-4 py-3 text-sm sm:text-base",
};

const VARIANT_CLASSES: Record<SelectVariant, string> = {
  default:
    "bg-black/80 backdrop-blur-md border-cyan-500/25 text-white hover:border-cyan-500/50 focus:border-cyan-400 focus:shadow-[0_0_20px_rgba(6,182,212,0.20)]",

  glass:
    "bg-black/55 backdrop-blur-2xl border-cyan-500/30 text-white shadow-[inset_0_0_15px_rgba(6,182,212,0.03)] hover:border-cyan-400/50 focus:border-cyan-400 focus:shadow-[0_0_24px_rgba(6,182,212,0.20)]",

  holographic:
    "bg-black/70 backdrop-blur-2xl border-cyan-400/45 text-white shadow-[0_0_20px_rgba(6,182,212,0.12)] hover:border-cyan-300/65 focus:border-cyan-300 focus:shadow-[0_0_28px_rgba(6,182,212,0.28)]",
};

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      id: providedId,
      label,
      hint,
      error,
      options,
      variant = "default",
      selectSize = "md",
      fullWidth = true,
      placeholder,
      icon,
      loading = false,
      disabled = false,
      className = "",
      children,
      "aria-describedby": providedAriaDescribedBy,
      "aria-invalid": providedAriaInvalid,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();

    const selectId = providedId || generatedId;
    const hintId = hint ? `${selectId}-hint` : undefined;
    const errorId = error ? `${selectId}-error` : undefined;

    const describedBy = [
      providedAriaDescribedBy,
      hintId,
      errorId,
    ]
      .filter(Boolean)
      .join(" ");

    const isDisabled = disabled || loading;
    const hasIcon = Boolean(icon);
    const hasError = Boolean(error);

    const wrapperClasses = [
      "flex",
      "min-w-0",
      "flex-col",
      "gap-1.5",
      fullWidth ? "w-full" : "w-auto",
    ]
      .filter(Boolean)
      .join(" ");

    const selectClasses = [
      "relative",
      "w-full",
      "rounded-xl",
      "border",
      "font-mono",
      "outline-none",
      "appearance-none",
      "cursor-pointer",
      "transition-all",
      "duration-200",
      "focus:outline-none",
      "focus-visible:ring-2",
      "focus-visible:ring-cyan-400/25",
      "motion-reduce:transition-none",
      SIZE_CLASSES[selectSize],
      hasIcon ? "pl-10" : "",
      "pr-10",
      hasError
        ? [
            "bg-red-950/20",
            "border-red-500/60",
            "text-red-100",
            "shadow-[0_0_15px_rgba(239,68,68,0.12)]",
            "hover:border-red-400/70",
            "focus:border-red-400",
            "focus-visible:ring-red-400/20",
            "focus:shadow-[0_0_20px_rgba(239,68,68,0.16)]",
          ].join(" ")
        : VARIANT_CLASSES[variant],
      isDisabled
        ? "cursor-not-allowed opacity-50"
        : "",
      className,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <div className={wrapperClasses}>
        {label && (
          <label
            htmlFor={selectId}
            className="text-[11px] font-mono font-semibold uppercase tracking-wider text-cyan-300/90 sm:text-xs"
          >
            {label}
          </label>
        )}

        <div className="relative flex min-w-0 w-full items-center">
          {variant === "holographic" && (
            <>
              <span
                aria-hidden="true"
                className="pointer-events-none absolute left-0 top-0 z-20 h-2.5 w-2.5 border-l border-t border-cyan-400/70"
              />

              <span
                aria-hidden="true"
                className="pointer-events-none absolute bottom-0 right-0 z-20 h-2.5 w-2.5 border-b border-r border-cyan-400/70"
              />

              <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 rounded-xl opacity-[0.08] [background-image:linear-gradient(to_right,rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.05)_1px,transparent_1px)] [background-size:20px_20px] motion-reduce:hidden"
              />
            </>
          )}

          {icon && (
            <span
              aria-hidden="true"
              className="pointer-events-none absolute left-3 z-10 flex items-center justify-center text-cyan-400/70"
            >
              {icon}
            </span>
          )}

          <select
            {...props}
            ref={ref}
            id={selectId}
            disabled={isDisabled}
            aria-invalid={
              hasError ? true : providedAriaInvalid
            }
            aria-busy={loading || undefined}
            aria-describedby={
              describedBy || undefined
            }
            className={selectClasses}
          >
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}

            {options
              ? options.map((option) => (
                  <option
                    key={option.value}
                    value={option.value}
                    disabled={option.disabled}
                    className="bg-black font-mono text-white"
                  >
                    {option.label}
                  </option>
                ))
              : children}
          </select>

          <span
            aria-hidden="true"
            className="pointer-events-none absolute right-3 z-10 flex items-center justify-center text-cyan-400/70"
          >
            {loading ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-cyan-400/25 border-t-cyan-400 motion-reduce:animate-none" />
            ) : (
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path
                  d="M19 9l-7 7-7-7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </span>
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

Select.displayName = "Select";
