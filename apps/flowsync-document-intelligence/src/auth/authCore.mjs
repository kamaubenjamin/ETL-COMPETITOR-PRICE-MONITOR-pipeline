const PUBLIC_KEY_MAX_LENGTH = 2048;
const ACCESS_TOKEN_MAX_LENGTH = 16384;

export class SupabaseBrowserConfigurationError extends Error {
  constructor() {
    super("Supabase browser authentication is not configured");
    this.name = "SupabaseBrowserConfigurationError";
  }
}

function isLegacyAnonKey(value) {
  return value.split(".").length === 3 && value.split(".").every((part) => /^[A-Za-z0-9_-]+$/.test(part));
}

export function resolveSupabasePublicConfiguration(rawUrl, rawKey, environment, developmentMode) {
  const configuredUrl = typeof rawUrl === "string" ? rawUrl.trim() : "";
  const publishableKey = typeof rawKey === "string" ? rawKey.trim() : "";
  const localEnvironment = !environment || environment === "local" || environment === "test";
  const localDevelopment = developmentMode && localEnvironment;
  if (
    !configuredUrl
    || !publishableKey
    || publishableKey.length > PUBLIC_KEY_MAX_LENGTH
    || /\s/.test(publishableKey)
    || (!publishableKey.startsWith("sb_publishable_") && !isLegacyAnonKey(publishableKey))
  ) {
    throw new SupabaseBrowserConfigurationError();
  }

  let url;
  try {
    url = new URL(configuredUrl);
  } catch {
    throw new SupabaseBrowserConfigurationError();
  }
  const loopback = ["localhost", "127.0.0.1", "::1"].includes(url.hostname);
  if (
    (url.protocol !== "https:" && !(localDevelopment && loopback && url.protocol === "http:"))
    || (!loopback && !url.hostname.endsWith(".supabase.co"))
    || url.username
    || url.password
    || url.pathname !== "/"
    || url.search
    || url.hash
  ) {
    throw new SupabaseBrowserConfigurationError();
  }
  return Object.freeze({ url: url.origin, publishableKey });
}

export const AUTH_DIAGNOSTIC_CODES = Object.freeze({
  success: "AUTH_OK",
  invalidCredentials: "AUTH_INVALID_CREDENTIALS",
  emailUnconfirmed: "AUTH_EMAIL_UNCONFIRMED",
  rateLimited: "AUTH_RATE_LIMITED",
  sessionMissing: "AUTH_SESSION_MISSING",
  configuration: "AUTH_CONFIGURATION",
  unavailable: "AUTH_UNAVAILABLE",
});

export function sessionFailureStatus(error) {
  const kind = typeof error === "object" && error && typeof error.safe?.kind === "string"
    ? error.safe.kind
    : undefined;
  if (kind === "unauthorized") return "unauthenticated";
  if (kind === "forbidden") return "unauthorized";
  if (kind === "configuration" || kind === "auth_configuration" || kind === "auth_mismatch") {
    return "configuration_error";
  }
  return "unavailable";
}

export function isRetryableSessionFailure(error) {
  const kind = typeof error === "object" && error && typeof error.safe?.kind === "string"
    ? error.safe.kind
    : undefined;
  return kind === undefined || kind === "unavailable";
}

export class SessionBootstrapTimeoutError extends Error {
  constructor() {
    super("Session bootstrap timed out");
    this.name = "SessionBootstrapTimeoutError";
  }
}

const delay = (milliseconds) => new Promise((resolve) => globalThis.setTimeout(resolve, milliseconds));

async function boundedSessionAttempt(operation, timeoutMs) {
  const controller = new AbortController();
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = globalThis.setTimeout(() => {
      controller.abort();
      reject(new SessionBootstrapTimeoutError());
    }, timeoutMs);
  });
  try {
    return await Promise.race([operation(controller.signal), timeout]);
  } finally {
    globalThis.clearTimeout(timer);
  }
}

export async function resolveSessionProfile(
  operation,
  { attempts = 2, timeoutMs = 8000, retryDelayMs = 250 } = {},
) {
  if (!Number.isInteger(attempts) || attempts < 1 || attempts > 3 || timeoutMs < 1 || retryDelayMs < 0) {
    throw new TypeError("Invalid session bootstrap policy");
  }
  let failure;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await boundedSessionAttempt(operation, timeoutMs);
    } catch (error) {
      failure = error;
      if (!isRetryableSessionFailure(error) || attempt === attempts) throw error;
      if (retryDelayMs) await delay(retryDelayMs);
    }
  }
  throw failure;
}

export function createKeyedSingleFlight(operation) {
  const inFlight = new Map();
  return (key, ...args) => {
    const existing = inFlight.get(key);
    if (existing) return existing;
    const request = Promise.resolve().then(() => operation(key, ...args));
    inFlight.set(key, request);
    void request.then(
      () => { if (inFlight.get(key) === request) inFlight.delete(key); },
      () => { if (inFlight.get(key) === request) inFlight.delete(key); },
    );
    return request;
  };
}

export function mapSupabaseSignInError(error) {
  const code = typeof error?.code === "string" ? error.code.toLowerCase() : "";
  if (code === "invalid_credentials" || code === "invalid_grant") {
    return AUTH_DIAGNOSTIC_CODES.invalidCredentials;
  }
  if (code === "email_not_confirmed") return AUTH_DIAGNOSTIC_CODES.emailUnconfirmed;
  if (error?.status === 429 || code.includes("rate_limit")) return AUTH_DIAGNOSTIC_CODES.rateLimited;
  return AUTH_DIAGNOSTIC_CODES.unavailable;
}

export async function performPasswordSignIn(auth, email, password) {
  const { data, error } = await auth.signInWithPassword({ email, password });
  if (error) {
    return Object.freeze({ success: false, session: null, code: mapSupabaseSignInError(error) });
  }
  if (!data?.session) {
    return Object.freeze({ success: false, session: null, code: AUTH_DIAGNOSTIC_CODES.sessionMissing });
  }
  return Object.freeze({ success: true, session: data.session, code: AUTH_DIAGNOSTIC_CODES.success });
}

export function accessTokenProviderForSession(session) {
  return async () => {
    const token = session?.["access" + "_token"];
    if (typeof token !== "string" || !token || token.length > ACCESS_TOKEN_MAX_LENGTH || /\s/.test(token)) {
      throw new Error("Authentication is required");
    }
    return token;
  };
}

export function staleAuthFragmentReplacement(location) {
  const hash = typeof location?.hash === "string" ? location.hash : "";
  if (!hash || !/(?:^|[#&])(?:access_token|refresh_token|type=recovery|error_code)=/i.test(hash)) return undefined;
  const pathname = typeof location?.pathname === "string" && location.pathname.startsWith("/")
    ? location.pathname
    : "/";
  const search = typeof location?.search === "string" && location.search.startsWith("?")
    ? location.search
    : "";
  return `${pathname}${search}`;
}
