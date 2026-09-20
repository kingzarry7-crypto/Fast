// Fast/frontend/types/auth.ts
// Auth data contracts for KING ZARRY AI web frontend.
// Types only. No React, logic, API calls, or side effects.

/**
 * Authenticated user.
 *
 * Never contains passwords, password hashes, tokens,
 * API keys, or other secrets.
 */
export interface AuthUser {
  id: string;
  email: string;
  username: string | null;
  display_name: string | null;
  account_status: string | null;
  created_at: string | null;
}

/**
 * Known account statuses.
 *
 * The broader AuthUser.account_status remains a string
 * so the frontend does not reject future backend values.
 */
export type AccountStatus =
  | "active"
  | "inactive"
  | "suspended"
  | "pending";

/**
 * Login form/request data.
 */
export interface LoginInput {
  email: string;
  password: string;
}

/**
 * Registration form/request data.
 */
export interface RegisterInput {
  email: string;
  password: string;
  username?: string;
  display_name?: string;
}

/**
 * Authentication response.
 */
export interface AuthResponse {
  status?: string;
  message?: string;
  user: AuthUser | null;
}

/**
 * Current authenticated-user response.
 */
export interface MeResponse {
  status?: string;
  user: AuthUser | null;
}

/**
 * Logout response.
 */
export interface LogoutResponse {
  status?: string;
  message?: string;
  success?: boolean;
}

/**
 * Shared authentication state shape.
 */
export interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}
