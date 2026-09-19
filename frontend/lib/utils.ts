// Fast/frontend/lib/utils.ts
// Pure, reusable utilities for KING ZARRY AI frontend.
// No React, no side effects, no secrets, no network requests.


// ─────────────────────────────────────────────────────────────
// Class names
// ─────────────────────────────────────────────────────────────

type ClassValue =
  | string
  | boolean
  | null
  | undefined
  | ClassValue[];

export function cn(...values: ClassValue[]): string {
  const classes: string[] = [];

  const walk = (items: ClassValue[]): void => {
    for (const item of items) {
      if (!item) continue;

      if (typeof item === "string") {
        const value = item.trim();
        if (value) classes.push(value);
        continue;
      }

      if (Array.isArray(item)) {
        walk(item);
      }
    }
  };

  walk(values);

  return classes.join(" ");
}


// ─────────────────────────────────────────────────────────────
// String utilities
// ─────────────────────────────────────────────────────────────

export function isNonEmptyString(
  value: unknown
): value is string {
  return (
    typeof value === "string" &&
    value.trim().length > 0
  );
}

export function capitalize(value: string): string {
  if (!value) return "";

  return (
    value.charAt(0).toUpperCase() +
    value.slice(1)
  );
}

export function truncate(
  value: string,
  maxLength: number,
  ellipsis = "…"
): string {
  if (!value) return "";

  if (
    !Number.isFinite(maxLength) ||
    maxLength <= 0
  ) {
    return "";
  }

  if (value.length <= maxLength) {
    return value;
  }

  if (!ellipsis) {
    return value.slice(0, maxLength).trimEnd();
  }

  if (ellipsis.length >= maxLength) {
    return ellipsis.slice(0, maxLength);
  }

  const contentLength =
    maxLength - ellipsis.length;

  return (
    value
      .slice(0, contentLength)
      .trimEnd() + ellipsis
  );
}

export function normalizeWhitespace(
  value: string
): string {
  if (!value) return "";

  return value
    .replace(/\s+/g, " ")
    .trim();
}


// ─────────────────────────────────────────────────────────────
// Number utilities
// ─────────────────────────────────────────────────────────────

export function isFiniteNumber(
  value: unknown
): value is number {
  return (
    typeof value === "number" &&
    Number.isFinite(value)
  );
}

export function clamp(
  value: number,
  min: number,
  max: number
): number {
  if (!isFiniteNumber(value)) {
    return min;
  }

  if (
    !isFiniteNumber(min) ||
    !isFiniteNumber(max)
  ) {
    return value;
  }

  if (min > max) {
    return value;
  }

  return Math.min(
    Math.max(value, min),
    max
  );
}

export function formatNumber(
  value: number | null | undefined,
  options: Intl.NumberFormatOptions = {}
): string {
  if (!isFiniteNumber(value)) {
    return "—";
  }

  try {
    return new Intl.NumberFormat(
      undefined,
      {
        maximumFractionDigits: 2,
        ...options,
      }
    ).format(value);
  } catch {
    return String(value);
  }
}

export function formatPercent(
  value: number | null | undefined,
  options: {
    digits?: number;
    includeSign?: boolean;
  } = {}
): string {
  if (!isFiniteNumber(value)) {
    return "—";
  }

  const digits = Number.isInteger(
    options.digits
  )
    ? Math.max(0, Math.min(20, options.digits!))
    : 2;

  const includeSign =
    options.includeSign === true;

  const formatted =
    `${value.toFixed(digits)}%`;

  if (
    includeSign &&
    value > 0
  ) {
    return `+${formatted}`;
  }

  return formatted;
}

export function formatCurrency(
  value: number | null | undefined,
  currency = "USD",
  options: Intl.NumberFormatOptions = {}
): string {
  if (!isFiniteNumber(value)) {
    return "—";
  }

  try {
    return new Intl.NumberFormat(
      undefined,
      {
        style: "currency",
        currency,
        maximumFractionDigits: 2,
        ...options,
      }
    ).format(value);
  } catch {
    return formatNumber(value);
  }
}


// ─────────────────────────────────────────────────────────────
// Date / time utilities
// ─────────────────────────────────────────────────────────────

function toDate(
  value: Date | string | number
): Date | null {
  if (value instanceof Date) {
    return Number.isNaN(value.getTime())
      ? null
      : value;
  }

  if (
    typeof value === "string" ||
    typeof value === "number"
  ) {
    const date = new Date(value);

    return Number.isNaN(date.getTime())
      ? null
      : date;
  }

  return null;
}

export function formatDate(
  value:
    | Date
    | string
    | number
    | null
    | undefined
): string {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  const date = toDate(value);

  if (!date) {
    return "—";
  }

  try {
    return new Intl.DateTimeFormat(
      undefined,
      {
        dateStyle: "medium",
      }
    ).format(date);
  } catch {
    return date
      .toISOString()
      .slice(0, 10);
  }
}

export function formatDateTime(
  value:
    | Date
    | string
    | number
    | null
    | undefined
): string {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  const date = toDate(value);

  if (!date) {
    return "—";
  }

  try {
    return new Intl.DateTimeFormat(
      undefined,
      {
        dateStyle: "medium",
        timeStyle: "short",
      }
    ).format(date);
  } catch {
    return date.toISOString();
  }
}

export function formatRelativeTime(
  value:
    | Date
    | string
    | number
    | null
    | undefined
): string {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  const date = toDate(value);

  if (!date) {
    return "—";
  }

  const difference =
    date.getTime() - Date.now();

  const seconds =
    Math.round(difference / 1000);

  const absoluteSeconds =
    Math.abs(seconds);

  try {
    const formatter =
      new Intl.RelativeTimeFormat(
        undefined,
        {
          numeric: "auto",
        }
      );

    if (absoluteSeconds < 60) {
      return formatter.format(
        seconds,
        "second"
      );
    }

    const minutes =
      Math.round(seconds / 60);

    if (Math.abs(minutes) < 60) {
      return formatter.format(
        minutes,
        "minute"
      );
    }

    const hours =
      Math.round(minutes / 60);

    if (Math.abs(hours) < 24) {
      return formatter.format(
        hours,
        "hour"
      );
    }

    const days =
      Math.round(hours / 24);

    return formatter.format(
      days,
      "day"
    );
  } catch {
    const days =
      Math.round(
        difference /
          (1000 * 60 * 60 * 24)
      );

    if (days === 0) {
      return "today";
    }

    return days < 0
      ? `${Math.abs(days)}d ago`
      : `in ${days}d`;
  }
}


// ─────────────────────────────────────────────────────────────
// Array utilities
// ─────────────────────────────────────────────────────────────

export function isArray<T>(
  value: unknown
): value is T[] {
  return Array.isArray(value);
}

export function uniqueBy<T, K>(
  array: readonly T[],
  keyFn: (item: T) => K
): T[] {
  if (!Array.isArray(array)) {
    return [];
  }

  const seen = new Set<K>();
  const result: T[] = [];

  for (const item of array) {
    const key = keyFn(item);

    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    result.push(item);
  }

  return result;
}

export function groupBy<
  T,
  K extends PropertyKey
>(
  array: readonly T[],
  keyFn: (item: T) => K
): Partial<Record<K, T[]>> {
  const result: Partial<Record<K, T[]>> = {};

  if (!Array.isArray(array)) {
    return result;
  }

  for (const item of array) {
    const key = keyFn(item);

    const existing = result[key];

    if (existing) {
      existing.push(item);
    } else {
      result[key] = [item];
    }
  }

  return result;
}


// ─────────────────────────────────────────────────────────────
// Object / type guards
// ─────────────────────────────────────────────────────────────

export function isRecord(
  value: unknown
): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}


// ─────────────────────────────────────────────────────────────
// Generic error utilities
// ─────────────────────────────────────────────────────────────

export function getErrorMessage(
  error: unknown
): string {
  if (typeof error === "string") {
    const message = error
      .trim()
      .slice(0, 500);

    return message || "Unknown error";
  }

  if (error instanceof Error) {
    const message = error.message
      .trim()
      .slice(0, 500);

    if (!message) {
      return "An error occurred";
    }

    if (
      /api[_\s-]?key|secret|password|token|database[_\s-]?url|neon/i.test(
        message
      )
    ) {
      return "An error occurred";
    }

    return message;
  }

  if (isRecord(error)) {
    const message = error.message;

    if (
      typeof message === "string" &&
      message.trim()
    ) {
      return message
        .trim()
        .slice(0, 500);
    }

    const detail = error.detail;

    if (
      typeof detail === "string" &&
      detail.trim()
    ) {
      return detail
        .trim()
        .slice(0, 500);
    }
  }

  return "An error occurred";
}


// ─────────────────────────────────────────────────────────────
// URL utilities
// ─────────────────────────────────────────────────────────────

export function isExternalUrl(
  url: string
): boolean {
  if (
    typeof url !== "string" ||
    !url.trim()
  ) {
    return false;
  }

  try {
    const parsed =
      new URL(url);

    return (
      parsed.protocol === "http:" ||
      parsed.protocol === "https:"
    );
  } catch {
    return false;
  }
}

export function joinUrl(
  base: string,
  path: string
): string {
  const cleanBase =
    base.trim();

  const cleanPath =
    path.trim();

  if (!cleanBase) {
    return cleanPath;
  }

  if (!cleanPath) {
    return cleanBase;
  }

  return (
    cleanBase.replace(/\/+$/, "") +
    "/" +
    cleanPath.replace(/^\/+/, "")
  );
}


// ─────────────────────────────────────────────────────────────
// UI-only ID generation
// Not cryptographically secure.
// Never use for authentication, sessions, payments, or security.
// ─────────────────────────────────────────────────────────────

export function generateId(
  prefix = ""
): string {
  const randomPart =
    Math.random()
      .toString(36)
      .slice(2, 9);

  const timestamp =
    Date.now().toString(36);

  return prefix
    ? `${prefix}-${timestamp}-${randomPart}`
    : `${timestamp}-${randomPart}`;
}
