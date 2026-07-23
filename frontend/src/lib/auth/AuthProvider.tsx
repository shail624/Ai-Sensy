import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, authClient, refreshOnce, setSessionExpiredHandler } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";
import { clearTokens, hasPersistedSession, setTokens } from "@/lib/auth/tokens";

type Me = components["schemas"]["MeResponse"];
type LoginRequest = components["schemas"]["LoginRequest"];

/** `loading` covers the bootstrap window so guards never redirect before the session is known. */
export type AuthStatus = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  status: AuthStatus;
  user: Me | null;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  /** Whether the signed-in user holds a permission code. Superusers bypass the catalog (FR-AUTH-06). */
  hasPermission: (code: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Session provider (Doc 02 Phase 2). Owns the signed-in identity, bootstraps it on app load from a
 * persisted refresh token, and is the single source of truth for `MeResponse.permissions`.
 */
export function AuthProvider({ children }: { children: ReactNode }): JSX.Element {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<Me | null>(null);
  const queryClient = useQueryClient();

  const endSession = useCallback(() => {
    clearTokens();
    setUser(null);
    setStatus("anonymous");
    // Drop every cached response — the next user must never see the previous one's data.
    queryClient.clear();
  }, [queryClient]);

  // Bootstrap: restore a session from the persisted refresh token, then load the profile.
  useEffect(() => {
    let cancelled = false;

    async function bootstrap(): Promise<void> {
      if (!hasPersistedSession()) {
        if (!cancelled) setStatus("anonymous");
        return;
      }
      const refreshed = await refreshOnce();
      if (cancelled) return;
      if (!refreshed) {
        endSession();
        return;
      }
      try {
        const me = await unwrap(await api.GET("/api/v1/auth/me"));
        if (cancelled) return;
        setUser(me);
        setStatus("authenticated");
      } catch {
        if (!cancelled) endSession();
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [endSession]);

  // A 401 the refresh flow could not recover ends the session here too.
  useEffect(() => {
    setSessionExpiredHandler(endSession);
    return () => setSessionExpiredHandler(null);
  }, [endSession]);

  const login = useCallback(
    async (credentials: LoginRequest) => {
      const tokens = unwrap(await authClient.POST("/api/v1/auth/login", { body: credentials }));
      setTokens(tokens.access_token, tokens.refresh_token);
      const me = await unwrap(await api.GET("/api/v1/auth/me"));
      setUser(me);
      setStatus("authenticated");
    },
    [],
  );

  const logout = useCallback(async () => {
    // Best-effort server-side revocation; the local session ends either way.
    try {
      await api.POST("/api/v1/auth/logout", {});
    } catch {
      /* already invalid server-side — nothing to revoke */
    }
    endSession();
  }, [endSession]);

  const hasPermission = useCallback(
    (code: string) => Boolean(user) && (user!.is_superuser || user!.permissions.includes(code)),
    [user],
  );

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, login, logout, hasPermission }),
    [status, user, login, logout, hasPermission],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}

/** Convenience hook for a single permission code. */
export function useHasPermission(code: string): boolean {
  return useAuth().hasPermission(code);
}
