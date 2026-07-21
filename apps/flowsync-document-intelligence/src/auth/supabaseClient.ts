import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { resolveDeploymentEnvironment } from "../config/deploymentEnvironment";
import {
  resolveSupabasePublicConfiguration,
  staleAuthFragmentReplacement,
  SupabaseBrowserConfigurationError,
} from "./authCore.mjs";

export { SupabaseBrowserConfigurationError } from "./authCore.mjs";

let browserClient: SupabaseClient | undefined;

function configuration(): { url: string; publishableKey: string } {
  return resolveSupabasePublicConfiguration(
    import.meta.env.VITE_SUPABASE_URL,
    import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
    resolveDeploymentEnvironment(import.meta.env.VITE_DEPLOYMENT_ENVIRONMENT),
    import.meta.env.DEV,
  );
}

export function getSupabaseBrowserClient(): SupabaseClient {
  if (!browserClient) {
    const { url, publishableKey } = configuration();
    const replacement = staleAuthFragmentReplacement(window.location);
    if (replacement) window.history.replaceState(null, "", replacement);
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
