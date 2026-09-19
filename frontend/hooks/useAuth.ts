"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface AuthUser {
  id: string;
  email: string;
  username?: string | null;
  display_name?: string | null;
  account_status?: string | null;
  status?: string | null;
  created_at?: string | null;
}

export interface UseAuthReturn {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  refresh: () => Promise<void>;

  login: (
    email: string,
    password: string
  ) => Promise<{
    success: boolean;
    user?: AuthUser;
    error?: string;
  }>;

  register: (
    email: string,
    password: string,
    username?: string,
    displayName?: string
  ) => Promise<{
    success: boolean;
    user?: AuthUser;
    error?: string;
  }>;

  logout: () => Promise<{
    success: boolean;
    error?: string;
  }>;
}

interface ApiResponse<T = unknown> {
  ok: boolean;
  status: number;
  data: T | null;
}

interface AuthResponse {
  user?: AuthUser | null;
  id?: string | number;
  email?: string;
  username?: string | null;
  display_name?: string | null;
  account_status?: string | null;
  status?: string | null;
  created_at?: string | null;
}

interface ErrorResponse {
  detail?: string;
  message?: string;
}

function getApiBase(): string {
  const configuredBase =
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "";

  return configuredBase.replace(/\/$/, "");
}

async function request<T>(
  path: string,
  init: RequestInit = {}
): Promise<ApiResponse<T>> {
  const base = getApiBase();

  const response = await fetch(`${base}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
  });

  const text = await response.text();

  let data: T | null = null;

  if (text) {
    try {
      data = JSON.parse(text) as T;
    } catch {
      data = null;
    }
  }

  return {
    ok: response.ok,
    status: response.status,
    data,
  };
}

function getErrorMessage(
  data: ErrorResponse | null,
  fallback: string
): string {
  if (data?.detail) {
    return data.detail;
  }

  if (data?.message) {
    return data.message;
  }

  return fallback;
}

function normalizeUser(
  value: AuthUser | null | undefined
): AuthUser | null {
  if (!value) {
    return null;
  }

  if (!value.id || !value.email) {
    return null;
  }

  const accountStatus =
    value.account_status ??
    value.status ??
    null;

  return {
    id: String(value.id),
    email: value.email,
    username: value.username ?? null,
    display_name: value.display_name ?? null,
    account_status: accountStatus,
    status: accountStatus,
    created_at: value.created_at ?? null,
  };
}

function extractUser(
  data: AuthResponse | null
): AuthUser | null {
  if (!data) {
    return null;
  }

  if (data.user) {
    return normalizeUser(data.user);
  }

  if (data.id && data.email) {
    return normalizeUser({
      id: String(data.id),
      email: data.email,
      username: data.username,
      display_name: data.display_name,
      account_status: data.account_status,
      status: data.status,
      created_at: data.created_at,
    });
  }

  return null;
}

export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const mountedRef = useRef(true);
  const requestIdRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
    };
  }, []);

  const refresh = useCallback(async () => {
    const requestId = ++requestIdRef.current;

    if (mountedRef.current) {
      setIsLoading(true);
      setError(null);
    }

    try {
      const response = await request<AuthResponse | ErrorResponse>(
        "/api/auth/me",
        {
          method: "GET",
        }
      );

      if (
        requestId !== requestIdRef.current ||
        !mountedRef.current
      ) {
        return;
      }

      if (response.status === 401 || response.status === 403) {
        setUser(null);
        setError(null);
        return;
      }

      if (!response.ok) {
        const message = getErrorMessage(
          response.data as ErrorResponse | null,
          `Session check failed (${response.status})`
        );

        setUser(null);
        setError(message);
        return;
      }

      const currentUser = extractUser(
        response.data as AuthResponse | null
      );

      setUser(currentUser);
      setError(null);
    } catch (error) {
      if (
        requestId !== requestIdRef.current ||
        !mountedRef.current
      ) {
        return;
      }

      setUser(null);

      setError(
        error instanceof Error
          ? error.message
          : "Failed to check authentication session"
      );
    } finally {
      if (
        requestId === requestIdRef.current &&
        mountedRef.current
      ) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback<
    UseAuthReturn["login"]
  >(async (email, password) => {
    const requestId = ++requestIdRef.current;

    if (mountedRef.current) {
      setIsLoading(true);
      setError(null);
    }

    try {
      const response = await request<
        AuthResponse | ErrorResponse
      >("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
        }),
      });

      if (
        requestId !== requestIdRef.current ||
        !mountedRef.current
      ) {
        return {
          success: false,
          error: "Authentication request was interrupted",
        };
      }

      if (!response.ok) {
        const message = getErrorMessage(
          response.data as ErrorResponse | null,
          "Invalid email or password"
        );

        setUser(null);
        setError(message);

        return {
          success: false,
          error: message,
        };
      }

      let authenticatedUser = extractUser(
        response.data as AuthResponse | null
      );

      /*
       * The backend may successfully create the session
       * without returning the complete public user object.
       *
       * In that case, ask /me for the authenticated user.
       */
      if (!authenticatedUser) {
        const meResponse = await request<
          AuthResponse | ErrorResponse
        >("/api/auth/me", {
          method: "GET",
        });

        if (
          requestId !== requestIdRef.current ||
          !mountedRef.current
        ) {
          return {
            success: false,
            error: "Authentication request was interrupted",
          };
        }

        if (!meResponse.ok) {
          const message = getErrorMessage(
            meResponse.data as ErrorResponse | null,
            "Login succeeded but the session could not be verified"
          );

          setUser(null);
          setError(message);

          return {
            success: false,
            error: message,
          };
        }

        authenticatedUser = extractUser(
          meResponse.data as AuthResponse | null
        );
      }

      if (!authenticatedUser) {
        const message =
          "Login succeeded, but no authenticated user was returned";

        setUser(null);
        setError(message);

        return {
          success: false,
          error: message,
        };
      }

      setUser(authenticatedUser);
      setError(null);

      return {
        success: true,
        user: authenticatedUser,
      };
    } catch (error) {
      if (
        requestId !== requestIdRef.current ||
        !mountedRef.current
      ) {
        return {
          success: false,
          error: "Authentication request was interrupted",
        };
      }

      const message =
        error instanceof Error
          ? error.message
          : "Login failed";

      setUser(null);
      setError(message);

      return {
        success: false,
        error: message,
      };
    } finally {
      if (
        requestId === requestIdRef.current &&
        mountedRef.current
      ) {
        setIsLoading(false);
      }
    }
  }, []);

  const register = useCallback<
    UseAuthReturn["register"]
  >(
    async (
      email,
      password,
      username,
      displayName
    ) => {
      const requestId = ++requestIdRef.current;

      if (mountedRef.current) {
        setIsLoading(true);
        setError(null);
      }

      try {
        const body: {
          email: string;
          password: string;
          username?: string;
          display_name?: string;
        } = {
          email,
          password,
        };

        if (username?.trim()) {
          body.username = username.trim();
        }

        if (displayName?.trim()) {
          body.display_name = displayName.trim();
        }

        const response = await request<
          AuthResponse | ErrorResponse
        >("/api/auth/register", {
          method: "POST",
          body: JSON.stringify(body),
        });

        if (
          requestId !== requestIdRef.current ||
          !mountedRef.current
        ) {
          return {
            success: false,
            error: "Registration request was interrupted",
          };
        }

        if (!response.ok) {
          const message = getErrorMessage(
            response.data as ErrorResponse | null,
            "Registration failed"
          );

          setError(message);

          return {
            success: false,
            error: message,
          };
        }

        const registeredUser = extractUser(
          response.data as AuthResponse | null
        );

        /*
         * If registration automatically creates a session,
         * use the returned user.
         *
         * Otherwise verify the session through /me.
         */
        if (registeredUser) {
          setUser(registeredUser);
          setError(null);

          return {
            success: true,
            user: registeredUser,
          };
        }

        const meResponse = await request<
          AuthResponse | ErrorResponse
        >("/api/auth/me", {
          method: "GET",
        });

        if (
          requestId !== requestIdRef.current ||
          !mountedRef.current
        ) {
          return {
            success: false,
            error: "Registration request was interrupted",
          };
        }

        if (meResponse.ok) {
          const currentUser = extractUser(
            meResponse.data as AuthResponse | null
          );

          if (currentUser) {
            setUser(currentUser);
            setError(null);

            return {
              success: true,
              user: currentUser,
            };
          }
        }

        /*
         * Registration itself succeeded, but the backend
         * did not automatically authenticate the new user.
         */
        setUser(null);
        setError(null);

        return {
          success: true,
        };
      } catch (error) {
        if (
          requestId !== requestIdRef.current ||
          !mountedRef.current
        ) {
          return {
            success: false,
            error: "Registration request was interrupted",
          };
        }

        const message =
          error instanceof Error
            ? error.message
            : "Registration failed";

        setError(message);

        return {
          success: false,
          error: message,
        };
      } finally {
        if (
          requestId === requestIdRef.current &&
          mountedRef.current
        ) {
          setIsLoading(false);
        }
      }
    },
    []
  );

  const logout = useCallback<
    UseAuthReturn["logout"]
  >(async () => {
    const requestId = ++requestIdRef.current;

    if (mountedRef.current) {
      setIsLoading(true);
      setError(null);
    }

    try {
      const response = await request<
        ErrorResponse
      >("/api/auth/logout", {
        method: "POST",
      });

      if (
        requestId !== requestIdRef.current ||
        !mountedRef.current
      ) {
        return {
          success: false,
          error: "Logout request was interrupted",
        };
      }

      if (!response.ok) {
        const message = getErrorMessage(
          response.data,
          "Logout failed"
        );

        /*
         * Keep the local user when the server logout
         * failed. This prevents the UI from claiming that
         * the session ended when it may still be active.
         */
        setError(message);

        return {
          success: false,
          error: message,
        };
      }

      setUser(null);
      setError(null);

      return {
        success: true,
      };
    } catch (error) {
      if (
        requestId !== requestIdRef.current ||
        !mountedRef.current
      ) {
        return {
          success: false,
          error: "Logout request was interrupted",
        };
      }

      const message =
        error instanceof Error
          ? error.message
          : "Logout failed";

      setError(message);

      return {
        success: false,
        error: message,
      };
    } finally {
      if (
        requestId === requestIdRef.current &&
        mountedRef.current
      ) {
        setIsLoading(false);
      }
    }
  }, []);

  return {
    user,
    isAuthenticated: Boolean(user),
    isLoading,
    error,
    refresh,
    login,
    register,
    logout,
  };
}

export default useAuth;
