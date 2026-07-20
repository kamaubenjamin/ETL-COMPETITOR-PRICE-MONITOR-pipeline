const DEFAULT_LABEL = "Local Development";
const UAT_LABEL = "UAT / Technical Preview";
const SAFE_LABEL = /^[A-Za-z0-9][A-Za-z0-9 /._-]{0,47}$/;

function normalized(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const candidate = value.trim();
  return candidate && SAFE_LABEL.test(candidate) ? candidate : undefined;
}

export function resolveDeploymentEnvironmentLabel(
  configuredLabel: unknown,
  configuredEnvironment: unknown,
): string {
  const label = normalized(configuredLabel);
  if (label) return label;

  const environment = normalized(configuredEnvironment)?.toLowerCase();
  if (environment === "uat" || environment === "technical-preview" || environment === "technical_preview") {
    return UAT_LABEL;
  }
  return DEFAULT_LABEL;
}

export function deploymentEnvironmentLabel(): string {
  return resolveDeploymentEnvironmentLabel(
    import.meta.env.VITE_UAT_LABEL,
    import.meta.env.VITE_DEPLOYMENT_ENVIRONMENT,
  );
}
