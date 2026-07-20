export type DeploymentEnvironment = "local" | "test" | "uat" | "pilot" | "production";

export class DeploymentConfigurationError extends Error {}

export function resolveDeploymentEnvironment(value: unknown): DeploymentEnvironment | undefined;
export function resolveDeploymentEnvironmentLabel(
  configuredLabel: unknown,
  configuredEnvironment: unknown,
): string;
export function normalizeDocumentIntelligenceApiOrigin(
  value: unknown,
  allowLocalHttp?: boolean,
): string;
export function resolveDocumentIntelligenceApiBaseUrl(
  configuredBaseUrl: unknown,
  configuredEnvironment: unknown,
  developmentMode: boolean,
  localFallback?: string,
): string;
