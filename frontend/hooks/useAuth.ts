"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthContext } from "@/components/providers/AppProviders";

export function useAuth() {
  const router = useRouter();
  const { user, isLoading, error, refresh, setUser } = useAuthContext();

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.login(email, password);
      if (res.user) setUser(res.user);
      else await refresh();
      return res;
    },
    [refresh, setUser]
  );

  const register = useCallback(
    async (
      email: string,
      password: string,
      username?: string,
      displayName?: string
    ) => {
      const res = await api.register(email, password, username, displayName);
      if (res.user) setUser(res.user);
      else await refresh();
      return res;
    },
    [refresh, setUser]
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // ignore
    }
    setUser(null);
    router.replace("/login");
  }, [router, setUser]);

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
