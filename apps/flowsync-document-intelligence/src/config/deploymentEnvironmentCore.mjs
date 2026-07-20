const DEFAULT_LABEL = "Local Development";
const UAT_LABEL = "UAT / Technical Preview";
const SAFE_LABEL = /^[A-Za-z0-9][A-Za-z0-9 /._-]{0,47}$/;
const HOSTED_ENVIRONMENTS = new Set(["uat", "pilot", "production"]);
const LOCAL_ENVIRONMENTS = new Set(["local", "test"]);
const ENVIRONMENT_ALIASES = new Map([
  ["dev", "local"],
  ["development", "local"],
  ["technical-preview", "uat"],
  ["technical_preview", "uat"],
]);

function normalizedLabel(value) {
  if (typeof value !== "string") return undefined;
  const candidate = value.trim();
  return candidate && SAFE_LABEL.test(candidate) ? candidate : undefined;
}

export class DeploymentConfigurationError extends Error {
  constructor() {
    super("Document Intelligence API deployment configuration is invalid");
    this.name = "DeploymentConfigurationError";
  }
}

export function resolveDeploymentEnvironment(value) {
  const candidate = normalizedLabel(value)?.toLowerCase();
  if (!candidate) return undefined;
  const resolved = ENVIRONMENT_ALIASES.get(candidate) ?? candidate;
  return HOSTED_ENVIRONMENTS.has(resolved) || LOCAL_ENVIRONMENTS.has(resolved)
    ? resolved
    : undefined;
}

export function resolveDeploymentEnvironmentLabel(configuredLabel, configuredEnvironment) {
  const environment = resolveDeploymentEnvironment(configuredEnvironment);
  const label = normalizedLabel(configuredLabel);
  if (label && /\bprod(?:uction)?\b/i.test(label) && environment !== "production") {
    return environment === "uat" ? UAT_LABEL : DEFAULT_LABEL;
  }
  if (environment === "uat") {
    return label ?? UAT_LABEL;
  }
  return label ?? DEFAULT_LABEL;
}

export function normalizeDocumentIntelligenceApiOrigin(value, allowLocalHttp = false) {
  if (typeof value !== "string" || !value.trim() || value.length > 2048) {
    throw new DeploymentConfigurationError();
  }
  let url;
  try {
    url = new URL(value.trim());
  } catch {
    throw new DeploymentConfigurationError();
  }
  const isLoopback = ["localhost", "127.0.0.1", "::1"].includes(url.hostname);
  if (
    (url.protocol !== "https:" && !(allowLocalHttp && url.protocol === "http:" && isLoopback))
    || url.username
    || url.password
    || url.pathname !== "/"
    || url.search
    || url.hash
  ) {
    throw new DeploymentConfigurationError();
  }
  return url.origin;
}

export function resolveDocumentIntelligenceApiBaseUrl(
  configuredBaseUrl,
  configuredEnvironment,
  developmentMode,
  localFallback,
) {
  const rawEnvironment = typeof configuredEnvironment === "string" ? configuredEnvironment.trim() : "";
  const environment = resolveDeploymentEnvironment(configuredEnvironment);
  if (rawEnvironment && !environment) throw new DeploymentConfigurationError();

  const configured = typeof configuredBaseUrl === "string" ? configuredBaseUrl.trim() : "";
  if (!configured) {
    if (developmentMode && (!environment || LOCAL_ENVIRONMENTS.has(environment)) && localFallback) {
      return normalizeDocumentIntelligenceApiOrigin(localFallback, true);
    }
    throw new DeploymentConfigurationError();
  }

  if (!developmentMode && !environment) throw new DeploymentConfigurationError();
  const allowLocalHttp = developmentMode && (!environment || LOCAL_ENVIRONMENTS.has(environment));
  return normalizeDocumentIntelligenceApiOrigin(configured, allowLocalHttp);
}
