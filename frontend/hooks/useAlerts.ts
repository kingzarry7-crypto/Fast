"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { AuthUser } from "@/types";

export function useAuth() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkSession = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const me = await api.getCurrentUser();
      setUser(me);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setUser(null);
      } else {
        setError(err instanceof Error ? err.message : "Session check failed");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkSession();
  }, [checkSession]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const res = await api.login(email, password);
      if (res.user) setUser(res.user);
      else await checkSession();
      return res;
    },
    [checkSession]
  );

  const signUp = useCallback(
    async (
      email: string,
      password: string,
      username?: string,
      displayName?: string
    ) => {
      const res = await api.register(email, password, username, displayName);
      if (res.user) setUser(res.user);
      else await checkSession();
      return res;
    },
    [checkSession]
  );

  const signOut = useCallback(async () => {
    await api.logout();
    setUser(null);
    router.replace("/login");
  }, [router]);

  return {
    user,
    loading,
    error,
    checkSession,
    signIn,
    signUp,
    signOut,
  };
}
