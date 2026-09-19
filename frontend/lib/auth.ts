import type { AuthUser } from "./api";
import { ApiError } from "./api";

export type { AuthUser } from "./api";

// -----------------------------------------------------------------------------
// Type guards
// -----------------------------------------------------------------------------

function isRecord(value: unknown): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}

export function isAuthenticatedUser(
  user: unknown
): user is AuthUser {
  if (!isRecord(user)) {
    return false;
  }

  const id = user.id;
  const email = user.email;

  return (
    typeof id === "string" &&
    id.trim().length > 0 &&
    typeof email === "string" &&
    email.trim().includes("@")
  );
}

// -----------------------------------------------------------------------------
// User normalization
// -----------------------------------------------------------------------------

export function normalizeAuthUser(
  user: unknown
): AuthUser | null {
  if (!isRecord(user)) {
    return null;
  }

  const id = user.id;
  const email = user.email;

  if (typeof id !== "string" || !id.trim()) {
    return null;
  }

  if (typeof email !== "string" || !email.trim()) {
    return null;
  }

  const username = user.username;

  const displayName =
    typeof user.display_name === "string"
      ? user.display_name
      : typeof user.displayName === "string"
        ? user.displayName
        : null;

  const accountStatus =
    typeof user.account_status === "string"
      ? user.account_status
      : typeof user.accountStatus === "string"
        ? user.accountStatus
        : typeof user.status === "string"
          ? user.status
          : null;

  const createdAt =
    typeof user.created_at === "string"
      ? user.created_at
      : typeof user.createdAt === "string"
        ? user.createdAt
        : null;

  return {
    id: id.trim(),
    email: email.trim().toLowerCase(),

    username:
      typeof username === "string"
        ? username.trim() || null
        : null,

    display_name:
      typeof displayName === "string"
        ? displayName.trim() || null
        : null,

    account_status:
      typeof accountStatus === "string"
        ? accountStatus.trim() || null
        : null,

    created_at: createdAt,
  };
}

// -----------------------------------------------------------------------------
// Account state
// -----------------------------------------------------------------------------

export function isActiveAccount(
  user: AuthUser | null | undefined
): boolean {
  if (!user) {
    return false;
  }

  const status = user.account_status?.trim().toLowerCase();

  if (!status) {
    return true;
  }

  return status === "active";
}

// -----------------------------------------------------------------------------
// Authentication error handling
// -----------------------------------------------------------------------------

function containsSensitiveServerDetail(message: string): boolean {
  return /token|secret|api[_\s-]?key|database|sql|neon|telegram|stack trace/i.test(
    message
  );
}

export function getAuthErrorMessage(
  error: unknown
): string {
  if (error instanceof ApiError) {
    const status = error.status;
    const message = error.message.trim();

    if (status === 401) {
      if (
        /invalid|incorrect|password|credential/i.test(
          message
        )
      ) {
        return message.slice(0, 500);
      }

      return "Invalid credentials. Please check your email and password.";
    }

    if (status === 403) {
      if (/suspended|inactive|disabled|active/i.test(message)) {
        return message.slice(0, 500);
      }

      return "Account unavailable. Please contact support.";
    }

    if (status === 409) {
      return message.slice(0, 500) || "An account already exists.";
    }

    if (status === 422) {
      return message.slice(0, 500) || "Please check your information.";
    }

    if (status === 429) {
      return "Too many requests. Please try again later.";
    }

    if (status === 0) {
      return "Network error. Please check your connection.";
    }

    if (
      message &&
      !containsSensitiveServerDetail(message)
    ) {
      return message.slice(0, 500);
    }

    return "Authentication error. Please try again.";
  }

  if (error instanceof Error) {
    const message = error.message.trim();

    if (!message) {
      return "Authentication error. Please try again.";
    }

    if (containsSensitiveServerDetail(message)) {
      return "Authentication error. Please try again.";
    }

    return message.slice(0, 500);
  }

  if (typeof error === "string" && error.trim()) {
    return error.trim().slice(0, 500);
  }

  return "Authentication error. Please try again.";
}

// -----------------------------------------------------------------------------
// Lightweight validation
// -----------------------------------------------------------------------------

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export interface ValidationResult {
  valid: boolean;
  error?: string;
  normalizedEmail?: string;
}

export function validateEmail(
  email: unknown
): ValidationResult {
  if (typeof email !== "string") {
    return {
      valid: false,
      error: "Email is required",
    };
  }

  const normalizedEmail = email.trim().toLowerCase();

  if (!normalizedEmail) {
    return {
      valid: false,
      error: "Email is required",
    };
  }

  if (!EMAIL_REGEX.test(normalizedEmail)) {
    return {
      valid: false,
      error: "Please enter a valid email address",
    };
  }

  return {
    valid: true,
    normalizedEmail,
  };
}

// -----------------------------------------------------------------------------
// Login validation
// -----------------------------------------------------------------------------

export function validateLoginInput(
  email: unknown,
  password: unknown
): ValidationResult {
  const emailResult = validateEmail(email);

  if (!emailResult.valid) {
    return emailResult;
  }

  if (
    typeof password !== "string" ||
    password.length === 0
  ) {
    return {
      valid: false,
      error: "Password is required",
    };
  }

  return {
    valid: true,
    normalizedEmail: emailResult.normalizedEmail,
  };
}

// -----------------------------------------------------------------------------
// Registration validation
// -----------------------------------------------------------------------------

export interface RegisterValidationResult
  extends ValidationResult {
  normalizedUsername?: string | null;
  normalizedDisplayName?: string | null;
}

export function validateRegisterInput(
  email: unknown,
  password: unknown,
  username?: unknown,
  displayName?: unknown
): RegisterValidationResult {
  const emailResult = validateEmail(email);

  if (!emailResult.valid) {
    return emailResult;
  }

  if (
    typeof password !== "string" ||
    password.length === 0
  ) {
    return {
      valid: false,
      error: "Password is required",
    };
  }

  // Keep frontend validation lightweight.
  // The backend remains authoritative for password policy.
  if (password.length < 8) {
    return {
      valid: false,
      error: "Password must be at least 8 characters",
    };
  }

  let normalizedUsername: string | null = null;

  if (
    username !== undefined &&
    username !== null &&
    typeof username === "string"
  ) {
    const value = username.trim().toLowerCase();

    if (value) {
      if (!/^[a-z0-9_]{3,100}$/.test(value)) {
        return {
          valid: false,
          error:
            "Username must be 3-100 characters using letters, numbers, and underscores",
        };
      }

      normalizedUsername = value;
    }
  }

  let normalizedDisplayName: string | null = null;

  if (
    displayName !== undefined &&
    displayName !== null &&
    typeof displayName === "string"
  ) {
    const value = displayName.trim();

    if (value.length > 255) {
      return {
        valid: false,
        error: "Display name is too long",
      };
    }

    normalizedDisplayName = value || null;
  }

  return {
    valid: true,
    normalizedEmail: emailResult.normalizedEmail,
    normalizedUsername,
    normalizedDisplayName,
  };
}

// -----------------------------------------------------------------------------
// Session helpers
// -----------------------------------------------------------------------------

export function shouldRedirectToLogin(
  error: unknown
): boolean {
  if (!(error instanceof ApiError)) {
    return false;
  }

  return error.status === 401 || error.status === 403;
}

export function getDisplayName(
  user: AuthUser | null | undefined
): string {
  if (!user) {
    return "";
  }

  const displayName = user.display_name?.trim();

  if (displayName) {
    return displayName;
  }

  const username = user.username?.trim();

  if (username) {
    return username;
  }

  const email = user.email?.trim();

  if (email) {
    const localPart = email.split("@")[0]?.trim();

    if (localPart) {
      return localPart;
    }
  }

  return "";
}
