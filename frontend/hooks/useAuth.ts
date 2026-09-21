"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { AuthUser } from "@/types";

export function useAuth() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const me = await api.getCurrentUser();
      setUser(me);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 0)) {
        setUser(null);
      } else {
        setError(err instanceof Error ? err.message : "Session check failed");
        setUser(null);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.login(email, password);
      if (res.user) setUser(res.user);
      else await refresh();
      return res;
    },
    [refresh]
  );

  const register = useCallback(
    async (email: string, password: string, username?: string, displayName?: string) => {
      const res = await api.register(email, password, username, displayName);
      if (res.user) setUser(res.user);
      else await refresh();
      return res;
    },
    [refresh]
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // ignore
    }
    setUser(null);
    router.replace("/login");
  }, [router]);

  return {
    user,
    isAuthenticated: !!user,
    isLoading,
    error,
    refresh,
    login,
    register,
    logout,
  };
}
