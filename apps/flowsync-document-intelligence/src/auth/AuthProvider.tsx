import { createContext, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import { createApiClient } from "../api/client";
import { API_ENDPOINTS } from "../api/endpoints";
import { configureWorkflowPermissionHints } from "../state/workflowPermissions";
import { getSupabaseBrowserClient, SupabaseBrowserConfigurationError } from "./supabaseClient";
import {
  accessTokenProviderForSession,
  AUTH_DIAGNOSTIC_CODES,
  createKeyedSingleFlight,
  performPasswordSignIn,
  resolveSessionProfile,
  sessionFailureStatus,
} from "./authCore.mjs";

export interface SafeSessionProfile {
  authenticated: true;
  email?: string;
  tenant_name: string;
  role: "owner" | "reviewer" | "viewer";
  permissions: string[];
}

export type AuthStatus = "loading" | "unauthenticated" | "authenticated" | "unauthorized" | "configuration_error" | "unavailable";

export interface AuthContextValue {
  status: AuthStatus;
  profile?: SafeSessionProfile;
  signIn(email: string, password: string): Promise<Readonly<{ success: boolean; code: string }>>;
  signOut(): Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const SESSION_TIMEOUT_MS = 8000;
const SESSION_RETRY_DELAY_MS = 250;
const bounded = <T,>(operation: Promise<T>): Promise<T> => Promise.race([
  operation,
  new Promise<T>((_, reject) => window.setTimeout(() => reject(new Error("Authentication unavailable")), SESSION_TIMEOUT_MS)),
]);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [profile, setProfile] = useState<SafeSessionProfile>();
  const resolutionGeneration = useRef(0);

  const clearAccess = useCallback(() => {
    configureWorkflowPermissionHints([]);
    setProfile(undefined);
  }, []);

  const loadSessionProfile = useMemo(() => createKeyedSingleFlight(
    (_sessionKey: string, session: Session) => {
      const client = createApiClient(accessTokenProviderForSession(session));
      return resolveSessionProfile(
        (signal) => client.get<SafeSessionProfile>(API_ENDPOINTS.session, {}, signal),
        { attempts: 2, timeoutMs: SESSION_TIMEOUT_MS, retryDelayMs: SESSION_RETRY_DELAY_MS },
      );
    },
  ), []);

  const resolveSession = useCallback(async (session: Session | null) => {
    const generation = resolutionGeneration.current + 1;
    resolutionGeneration.current = generation;
    clearAccess();
    if (!session) {
      setStatus("unauthenticated");
      return;
    }
    setStatus("loading");
    try {
      const sessionKey = `${session.user.id}:${session.expires_at ?? 0}`;
      const result = await loadSessionProfile(sessionKey, session);
      if (generation !== resolutionGeneration.current) return;
      if (!result.data?.authenticated) throw new Error("Session unavailable");
      configureWorkflowPermissionHints(result.data.permissions);
      setProfile(result.data);
      setStatus("authenticated");
    } catch (error) {
      if (generation !== resolutionGeneration.current) return;
      const failureStatus = sessionFailureStatus(error);
      if (failureStatus === "unauthenticated") {
        try { await getSupabaseBrowserClient().auth.signOut({ scope: "local" }); } catch { /* fixed safe state below */ }
      }
      setStatus(failureStatus);
    }
  }, [clearAccess, loadSessionProfile]);

  useEffect(() => {
    let active = true;
    try {
      const client = getSupabaseBrowserClient();
      const { data: listener } = client.auth.onAuthStateChange((_event, session) => {
        // Supabase Auth callbacks must return before another auth-dependent operation begins.
        // Deferring also prevents the protected API token provider from re-entering the auth lock.
        if (active) window.setTimeout(() => { if (active) void resolveSession(session); }, 0);
      });
      return () => { active = false; listener.subscription.unsubscribe(); };
    } catch (error) {
      setStatus(error instanceof SupabaseBrowserConfigurationError ? "configuration_error" : "unauthenticated");
      return () => { active = false; };
    }
  }, [resolveSession]);

  const signIn = useCallback(async (email: string, password: string) => {
    try {
      const result = await bounded(performPasswordSignIn(getSupabaseBrowserClient().auth, email, password));
      if (!result.success || !result.session) return { success: false, code: result.code };
      setStatus("loading");
      return { success: true, code: result.code };
    } catch (error) {
      return {
        success: false,
        code: error instanceof SupabaseBrowserConfigurationError
          ? AUTH_DIAGNOSTIC_CODES.configuration
          : AUTH_DIAGNOSTIC_CODES.unavailable,
      };
    }
  }, []);

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
