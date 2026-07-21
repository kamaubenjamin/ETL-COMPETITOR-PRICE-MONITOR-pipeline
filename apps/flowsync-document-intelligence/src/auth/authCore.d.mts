import type { Session } from "@supabase/supabase-js";

export class SupabaseBrowserConfigurationError extends Error {}
export const AUTH_DIAGNOSTIC_CODES: Readonly<{
  success: string;
  invalidCredentials: string;
  emailUnconfirmed: string;
  rateLimited: string;
  sessionMissing: string;
  configuration: string;
  unavailable: string;
}>;
export type SessionFailureStatus = "unauthenticated" | "unauthorized" | "configuration_error" | "unavailable";
export function sessionFailureStatus(error: unknown): SessionFailureStatus;
export function isRetryableSessionFailure(error: unknown): boolean;
export class SessionBootstrapTimeoutError extends Error {}
export function resolveSessionProfile<T>(
  operation: (signal: AbortSignal) => Promise<T>,
  options?: Readonly<{ attempts?: number; timeoutMs?: number; retryDelayMs?: number }>,
): Promise<T>;
export function createKeyedSingleFlight<Key, Args extends unknown[], Result>(
  operation: (key: Key, ...args: Args) => Promise<Result>,
): (key: Key, ...args: Args) => Promise<Result>;
export function resolveSupabasePublicConfiguration(
  rawUrl: unknown,
  rawKey: unknown,
  environment: string | undefined,
  developmentMode: boolean,
): Readonly<{ url: string; publishableKey: string }>;
export function mapSupabaseSignInError(error: unknown): string;
export function performPasswordSignIn(
  auth: { signInWithPassword(credentials: { email: string; password: string }): Promise<{ data: { session: Session | null } | null; error: unknown }> },
  email: string,
  password: string,
): Promise<Readonly<{ success: boolean; session: Session | null; code: string }>>;
export function accessTokenProviderForSession(session: Session): () => Promise<string>;
export function staleAuthFragmentReplacement(location: { hash?: string; pathname?: string; search?: string }): string | undefined;
