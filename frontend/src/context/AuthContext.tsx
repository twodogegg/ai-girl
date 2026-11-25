import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { User } from "@/types";
import * as authApi from "@/api/auth";

const AGE_KEY = "plot18:age-confirmed";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  ageConfirmed: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, displayName: string) => Promise<void>;
  guest: () => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  confirmAge: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [ageConfirmed, setAgeConfirmed] = useState(() => localStorage.getItem(AGE_KEY) === "1");

  const refresh = useCallback(async () => {
    try {
      setUser(await authApi.getMe());
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const onUnauthorized = () => setUser(null);
    window.addEventListener("plot18:unauthorized", onUnauthorized);
    return () => window.removeEventListener("plot18:unauthorized", onUnauthorized);
  }, [refresh]);

  const confirmAge = useCallback(async () => {
    localStorage.setItem(AGE_KEY, "1");
    setAgeConfirmed(true);
    if (user && !user.adultConfirmed) {
      const updated = await authApi.confirmAdult();
      setUser(updated);
    }
  }, [user]);

  const login = useCallback(async (username: string, password: string) => {
    let next = await authApi.login(username, password);
    if (localStorage.getItem(AGE_KEY) === "1" && !next.adultConfirmed) {
      next = await authApi.confirmAdult();
    }
    setUser(next);
  }, []);

  const register = useCallback(async (username: string, password: string, displayName: string) => {
    const next = await authApi.register(username, password, displayName);
    setUser(next);
  }, []);

  const guest = useCallback(async () => {
    const next = await authApi.guestLogin();
    setUser(next);
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    user, loading, ageConfirmed, login, register, guest, logout, refresh, confirmAge,
  }), [user, loading, ageConfirmed, login, register, guest, logout, refresh, confirmAge]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
