import {
  DeploymentConfigurationError,
  normalizeDocumentIntelligenceApiOrigin,
  resolveDeploymentEnvironment,
  resolveDeploymentEnvironmentLabel,
  resolveDocumentIntelligenceApiBaseUrl,
} from "./deploymentEnvironmentCore.mjs";

export {
  DeploymentConfigurationError,
  normalizeDocumentIntelligenceApiOrigin,
  resolveDeploymentEnvironment,
  resolveDeploymentEnvironmentLabel,
  resolveDocumentIntelligenceApiBaseUrl,
};

const DEFAULT_LOCAL_API_URL = "http://127.0.0.1:8001";

export function deploymentEnvironmentLabel(): string {
  return resolveDeploymentEnvironmentLabel(
    import.meta.env.VITE_UAT_LABEL,
    import.meta.env.VITE_DEPLOYMENT_ENVIRONMENT,
  );
}

export function documentIntelligenceApiBaseUrl(): string {
  return resolveDocumentIntelligenceApiBaseUrl(
    import.meta.env.VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL,
    import.meta.env.VITE_DEPLOYMENT_ENVIRONMENT,
    import.meta.env.DEV,
    import.meta.env.DEV ? DEFAULT_LOCAL_API_URL : undefined,
  );
}

export function hasValidDocumentIntelligenceApiConfiguration(): boolean {
  try {
    documentIntelligenceApiBaseUrl();
    return true;
  } catch (error) {
    if (error instanceof DeploymentConfigurationError) return false;
    return false;
  }
}
