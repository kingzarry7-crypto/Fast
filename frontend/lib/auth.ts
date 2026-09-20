// Fast/frontend/lib/auth.ts
// Authentication state and helpers.
// Types come from "@/types" — no re-exporting from "./api".

import type { AuthUser } from "@/types";
import { ApiError } from "./api";

export type { AuthUser };

export interface AuthSessionState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export const initialAuthState: AuthSessionState = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
};

export function isAuthError(err: unknown): err is ApiError {
  return err instanceof ApiError;
}

export function getAuthErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 0) return "Cannot reach the server. Check your connection.";
    if (err.status === 401) return "Session expired. Please sign in again.";
    if (err.status === 403) return "Access denied.";
    if (err.status === 404) return "Account not found.";
    return err.detail || err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong. Please try again.";
}
