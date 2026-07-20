import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { resolveDeploymentEnvironment } from "../config/deploymentEnvironment";

export class SupabaseBrowserConfigurationError extends Error {
  constructor() {
    super("Supabase browser authentication is not configured");
    this.name = "SupabaseBrowserConfigurationError";
  }
}

let browserClient: SupabaseClient | undefined;

function configuration(): { url: string; publishableKey: string } {
  const rawUrl = import.meta.env.VITE_SUPABASE_URL?.trim() ?? "";
  const publishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim() ?? "";
  const environment = resolveDeploymentEnvironment(import.meta.env.VITE_DEPLOYMENT_ENVIRONMENT);
  if (!rawUrl || !publishableKey || publishableKey.length > 2048 || /\s/.test(publishableKey)) {
    throw new SupabaseBrowserConfigurationError();
  }
  if (/service[_-]?role|secret/i.test(publishableKey)) {
    throw new SupabaseBrowserConfigurationError();
  }
  let url: URL;
  try {
    url = new URL(rawUrl);
  } catch {
    throw new SupabaseBrowserConfigurationError();
  }
  const loopback = ["localhost", "127.0.0.1", "::1"].includes(url.hostname);
  const localDevelopment = import.meta.env.DEV && (!environment || environment === "local" || environment === "test");
  if (
    (url.protocol !== "https:" && !(localDevelopment && loopback && url.protocol === "http:"))
    || url.username
    || url.password
    || url.pathname !== "/"
    || url.search
    || url.hash
  ) {
    throw new SupabaseBrowserConfigurationError();
  }
  return { url: url.origin, publishableKey };
}

export function getSupabaseBrowserClient(): SupabaseClient {
  if (!browserClient) {
    const { url, publishableKey } = configuration();
    browserClient = createClient(url, publishableKey, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
    });
  }
  return browserClient;
}

export async function getSupabaseAccessToken(): Promise<string> {
  const { data, error } = await getSupabaseBrowserClient().auth.getSession();
  const token = data.session?.access_token;
  if (error || !token || token.length > 16384 || /\s/.test(token)) {
    throw new Error("Authentication is required");
  }
  return token;
}
