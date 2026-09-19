"use client";

import React, {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";

export type ModalSize = "sm" | "md" | "lg" | "xl" | "full";
export type ModalVariant = "default" | "glass" | "holographic";

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  title?: string;
  description?: string;
  size?: ModalSize;
  variant?: ModalVariant;
  closeOnBackdrop?: boolean;
  closeOnEscape?: boolean;
  showCloseButton?: boolean;
  footer?: React.ReactNode;
  className?: string;
  ariaLabel?: string;
}

export interface ModalHeaderProps {
  children?: React.ReactNode;
  title?: string;
  description?: string;
  showCloseButton?: boolean;
  onClose?: () => void;
  className?: string;
  titleId?: string;
  descriptionId?: string;
  closeButtonRef?: React.RefObject<HTMLButtonElement | null>;
}

export interface ModalBodyProps {
  children: React.ReactNode;
  className?: string;
}

export interface ModalFooterProps {
  children: React.ReactNode;
  className?: string;
}

const SIZE_CLASSES: Record<ModalSize, string> = {
  sm: "w-[calc(100vw-32px)] max-w-[420px]",
  md: "w-[calc(100vw-32px)] max-w-[560px]",
  lg: "w-[calc(100vw-32px)] max-w-[720px]",
  xl: "w-[calc(100vw-32px)] max-w-[960px]",
  full: "w-[calc(100vw-24px)] max-w-[1200px] min-h-[min(90vh,900px)]",
};

const VARIANT_CLASSES: Record<ModalVariant, string> = {
  default:
    "bg-gradient-to-b from-[#121A2B] to-[#080B14] border-white/[0.08] shadow-[0_24px_80px_rgba(0,0,0,0.65),inset_0_1px_0_rgba(255,255,255,0.07)]",

  glass:
    "bg-[#0E1524]/80 backdrop-blur-[24px] border-white/[0.10] shadow-[0_24px_80px_rgba(0,0,0,0.7),inset_0_1px_0_rgba(255,255,255,0.08)]",

  holographic:
    "bg-gradient-to-b from-[#101B30] via-[#0C1424] to-[#080B14] border-cyan-300/20 shadow-[0_0_0_1px_rgba(34,211,238,0.15),0_24px_80px_rgba(0,0,0,0.75),0_0_40px_rgba(34,211,238,0.10),inset_0_1px_0_rgba(255,255,255,0.08)]",
};

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(", ");

function getFocusableElements(container: HTMLElement | null): HTMLElement[] {
  if (!container) return [];

  return Array.from(
    container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
  ).filter((element) => {
    const style = window.getComputedStyle(element);

    return (
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      element.getAttribute("aria-hidden") !== "true"
    );
  });
}

function useBodyScrollLock(locked: boolean) {
  useEffect(() => {
    if (!locked) return;

    const body = document.body;
    const documentElement = document.documentElement;

    const originalOverflow = body.style.overflow;
    const originalPaddingRight = body.style.paddingRight;

    const scrollbarWidth =
      window.innerWidth - documentElement.clientWidth;

    body.style.overflow = "hidden";

    if (scrollbarWidth > 0) {
      body.style.paddingRight = `${scrollbarWidth}px`;
    }

    return () => {
      body.style.overflow = originalOverflow;
      body.style.paddingRight = originalPaddingRight;
    };
  }, [locked]);
}

function CloseIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M3.5 3.5L10.5 10.5M10.5 3.5L3.5 10.5"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function ModalHeader({
  children,
  title,
  description,
  showCloseButton = true,
  onClose,
  className = "",
  titleId,
  descriptionId,
  closeButtonRef,
}: ModalHeaderProps) {
  return (
    <div
      className={[
        "relative shrink-0 border-b border-white/[0.06]",
        "px-6 pb-5 pt-6 md:px-7",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-0 right-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-300/20 to-transparent"
      />

      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {title && (
            <h2
              id={titleId}
              className="pr-2 text-[14px] font-semibold leading-[1.3] tracking-[-0.01em] text-white md:text-[15px]"
            >
              {title}
            </h2>
          )}

          {children && (
            <div className={title ? "mt-3" : ""}>
              {children}
            </div>
          )}

          {description && (
            <p
              id={descriptionId}
              className="mt-2 max-w-[52ch] text-[12.5px] leading-[1.5] text-white/50"
            >
              {description}
            </p>
          )}
        </div>

        {showCloseButton && onClose && (
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className={[
              "flex h-8 w-8 shrink-0 items-center justify-center",
              "rounded-full border border-white/[0.06]",
              "bg-white/[0.04] text-white/60",
              "transition-colors duration-200",
              "hover:bg-white/[0.08] hover:text-white/90",
              "focus-visible:outline-none",
              "focus-visible:ring-2 focus-visible:ring-cyan-300/40",
              "motion-reduce:transition-none",
            ].join(" ")}
          >
            <CloseIcon />
          </button>
        )}
      </div>
    </div>
  );
}

export function ModalBody({
  children,
  className = "",
}: ModalBodyProps) {
  return (
    <div
      className={[
        "min-h-0 flex-1 overflow-y-auto overscroll-contain",
        "px-6 py-6 md:px-7",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </div>
  );
}

export function ModalFooter({
  children,
  className = "",
}: ModalFooterProps) {
  return (
    <div
      className={[
        "flex shrink-0 items-center justify-end gap-2",
        "border-t border-white/[0.06]",
        "bg-white/[0.015]",
        "px-6 py-4 md:gap-3 md:px-7 md:py-5",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </div>
  );
}

export default function Modal({
  open,
  onClose,
  children,
  title,
  description,
  size = "md",
  variant = "default",
  closeOnBackdrop = true,
  closeOnEscape = true,
  showCloseButton = true,
  footer,
  className = "",
  ariaLabel,
}: ModalProps) {
  const id = useId();

  const titleId = `${id}-title`;
  const descriptionId = `${id}-description`;

  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previousActiveRef = useRef<HTMLElement | null>(null);

  const [mounted, setMounted] = useState(false);

  useBodyScrollLock(open);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;

    previousActiveRef.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;

    const focusTimer = window.setTimeout(() => {
      if (closeButtonRef.current) {
        closeButtonRef.current.focus();
        return;
      }

      const focusable = getFocusableElements(panelRef.current);

      if (focusable.length > 0) {
        focusable[0].focus();
        return;
      }

      panelRef.current?.focus();
    }, 0);

    return () => {
      window.clearTimeout(focusTimer);
    };
  }, [open]);

  useEffect(() => {
    if (open) return;

    const previousElement = previousActiveRef.current;

    if (!previousElement) return;

    const restoreTimer = window.setTimeout(() => {
      if (document.contains(previousElement)) {
        previousElement.focus();
      }
    }, 0);

    return () => {
      window.clearTimeout(restoreTimer);
    };
  }, [open]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!open || !panelRef.current) return;

      if (event.key === "Escape" && closeOnEscape) {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== "Tab") return;

      const focusable = getFocusableElements(panelRef.current);

      if (focusable.length === 0) {
        event.preventDefault();
        panelRef.current.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const activeElement = document.activeElement;

      if (event.shiftKey) {
        if (
          activeElement === first ||
          !panelRef.current.contains(activeElement)
        ) {
          event.preventDefault();
          last.focus();
        }

        return;
      }

      if (
        activeElement === last ||
        !panelRef.current.contains(activeElement)
      ) {
        event.preventDefault();
        first.focus();
      }
    },
    [open, closeOnEscape, onClose]
  );

  useEffect(() => {
    if (!open) return;

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, handleKeyDown]);

  if (!mounted || !open) {
    return null;
  }

  const modalContent = (
    <div
      className={[
        "fixed inset-0 z-[80]",
        "flex items-start justify-center",
        "overflow-y-auto",
        "p-3 md:items-center md:p-6",
      ].join(" ")}
    >
      <div
        className="fixed inset-0 bg-[#05070B]/70 backdrop-blur-[12px]"
        aria-hidden="true"
        onClick={closeOnBackdrop ? onClose : undefined}
        style={{
          background:
            "radial-gradient(1200px 600px at 20% -10%, rgba(34,211,238,0.12), transparent), radial-gradient(900px 500px at 80% 0%, rgba(139,92,246,0.10), transparent), rgba(5,7,11,0.72)",
        }}
      />

      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        aria-describedby={description ? descriptionId : undefined}
        aria-label={!title ? ariaLabel || "Dialog" : undefined}
        tabIndex={-1}
        className={[
          "relative flex max-h-[calc(100vh-24px)] flex-col",
          "overflow-hidden rounded-[20px] border",
          "md:max-h-[calc(100vh-48px)] md:rounded-[24px]",
          SIZE_CLASSES[size],
          VARIANT_CLASSES[variant],
          "animate-[kz-modal-in_180ms_ease-out]",
          "motion-reduce:animate-none",
          className,
        ]
          .filter(Boolean)
          .join(" ")}
          onClick={(event) => event.stopPropagation()}
      >
        {variant === "holographic" && (
          <>
            <span
              aria-hidden="true"
              className="pointer-events-none absolute left-4 top-4 h-5 w-5 rounded-tl-[10px] border-l border-t border-cyan-300/25"
            />

            <span
              aria-hidden="true"
              className="pointer-events-none absolute right-4 top-4 h-5 w-5 rounded-tr-[10px] border-r border-t border-cyan-300/25"
            />

            <span
              aria-hidden="true"
              className="pointer-events-none absolute bottom-4 left-4 h-5 w-5 rounded-bl-[10px] border-b border-l border-white/10"
            />

            <span
              aria-hidden="true"
              className="pointer-events-none absolute bottom-4 right-4 h-5 w-5 rounded-br-[10px] border-b border-r border-white/10"
            />

            <span
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 opacity-[0.12]"
              style={{
                backgroundImage:
                  "linear-gradient(to right, rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.035) 1px, transparent 1px)",
                backgroundSize: "32px 32px",
                maskImage:
                  "radial-gradient(ellipse at center, black 40%, transparent 80%)",
                WebkitMaskImage:
                  "radial-gradient(ellipse at center, black 40%, transparent 80%)",
              }}
            />
          </>
        )}

        <span
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 rounded-[inherit] bg-[radial-gradient(600px_200px_at_20%_0%,rgba(34,211,238,0.08),transparent),radial-gradient(500px_200px_at_80%_0%,rgba(139,92,246,0.06),transparent)] opacity-80"
        />

        {(title || description) && (
          <div className="relative z-10">
            <ModalHeader
              title={title}
              description={description}
              showCloseButton={showCloseButton}
              onClose={onClose}
              titleId={title ? titleId : undefined}
              descriptionId={description ? descriptionId : undefined}
              closeButtonRef={closeButtonRef}
            />
          </div>
        )}

        {!title && !description && showCloseButton && (
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className={[
              "absolute right-4 top-4 z-20",
              "flex h-8 w-8 items-center justify-center",
              "rounded-full border border-white/[0.06]",
              "bg-white/[0.04] text-white/60",
              "transition-colors duration-200",
              "hover:bg-white/[0.08] hover:text-white/90",
              "focus-visible:outline-none",
              "focus-visible:ring-2 focus-visible:ring-cyan-300/40",
              "motion-reduce:transition-none",
            ].join(" ")}
          >
            <CloseIcon />
          </button>
        )}

        <div className="relative z-10 flex min-h-0 flex-1 flex-col overflow-hidden">
          <div
            className={[
              "min-h-0 flex-1 overflow-y-auto overscroll-contain",
              !title && !description ? "pt-2" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {children}
          </div>
        </div>

        {footer && (
          <div className="relative z-10 shrink-0">
            {footer}
          </div>
        )}
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
