import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import { createApiClient } from "../api/client";
import { API_ENDPOINTS } from "../api/endpoints";
import { configureWorkflowPermissionHints } from "../state/workflowPermissions";
import { getSupabaseBrowserClient, SupabaseBrowserConfigurationError } from "./supabaseClient";

export interface SafeSessionProfile {
  authenticated: true;
  email?: string;
  tenant_name: string;
  role: "owner" | "reviewer" | "viewer";
  permissions: string[];
}

export type AuthStatus = "loading" | "unauthenticated" | "authenticated" | "unauthorized" | "configuration_error";

export interface AuthContextValue {
  status: AuthStatus;
  profile?: SafeSessionProfile;
  signIn(email: string, password: string): Promise<boolean>;
  signOut(): Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const SESSION_TIMEOUT_MS = 8000;
const bounded = <T,>(operation: Promise<T>): Promise<T> => Promise.race([
  operation,
  new Promise<T>((_, reject) => window.setTimeout(() => reject(new Error("Authentication unavailable")), SESSION_TIMEOUT_MS)),
]);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [profile, setProfile] = useState<SafeSessionProfile>();

  const clearAccess = useCallback(() => {
    configureWorkflowPermissionHints([]);
    setProfile(undefined);
  }, []);

  const resolveSession = useCallback(async (session: Session | null) => {
    clearAccess();
    if (!session) {
      setStatus("unauthenticated");
      return;
    }
    setStatus("loading");
    try {
      const result = await bounded(createApiClient().get<SafeSessionProfile>(API_ENDPOINTS.session));
      if (!result.data?.authenticated) throw new Error("Session unavailable");
      configureWorkflowPermissionHints(result.data.permissions);
      setProfile(result.data);
      setStatus("authenticated");
    } catch (error) {
      const kind = typeof error === "object" && error && "safe" in error
        ? (error as { safe?: { kind?: string } }).safe?.kind
        : undefined;
      if (kind === "unauthorized") {
        try { await getSupabaseBrowserClient().auth.signOut({ scope: "local" }); } catch { /* fixed safe state below */ }
        setStatus("unauthenticated");
      } else {
        setStatus("unauthorized");
      }
    }
  }, [clearAccess]);

  useEffect(() => {
    let active = true;
    try {
      const client = getSupabaseBrowserClient();
      void bounded(client.auth.getSession())
        .then(({ data, error }) => {
          if (!active) return;
          if (error) setStatus("unauthenticated");
          else void resolveSession(data.session);
        })
        .catch(() => { if (active) setStatus("unauthenticated"); });
      const { data: listener } = client.auth.onAuthStateChange((_event, session) => {
        if (active) void resolveSession(session);
      });
      return () => { active = false; listener.subscription.unsubscribe(); };
    } catch (error) {
      setStatus(error instanceof SupabaseBrowserConfigurationError ? "configuration_error" : "unauthenticated");
      return () => { active = false; };
    }
  }, [resolveSession]);

  const signIn = useCallback(async (email: string, password: string) => {
    try {
      const { data, error } = await bounded(
        getSupabaseBrowserClient().auth.signInWithPassword({ email, password }),
      );
      if (error || !data.session) return false;
      await resolveSession(data.session);
      return true;
    } catch {
      return false;
    }
  }, [resolveSession]);

  const signOut = useCallback(async () => {
    clearAccess();
    try {
      await bounded(getSupabaseBrowserClient().auth.signOut());
    } finally {
      setStatus("unauthenticated");
    }
  }, [clearAccess]);

  const value = useMemo(() => ({ status, profile, signIn, signOut }), [profile, signIn, signOut, status]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
