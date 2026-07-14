declare const endpointBrand: unique symbol;

export type ApiEndpoint = string & { readonly [endpointBrand]: true };

function endpoint(path: string): ApiEndpoint {
  if (!path.startsWith("/api/v1/") && path !== "/health") {
    throw new Error("API endpoint must use the approved versioned boundary");
  }
  return path as ApiEndpoint;
}

function segment(value: string): string {
  if (!value || value.length > 128) {
    throw new Error("Route identifier must be a bounded non-empty string");
  }
  return encodeURIComponent(value);
}

export const API_ENDPOINTS = Object.freeze({
  health: endpoint("/api/v1/health"),
  status: endpoint("/api/v1/status"),
  documents: endpoint("/api/v1/documents"),
  uploads: endpoint("/api/v1/uploads"),
  upload: (uploadId: string) => endpoint(`/api/v1/uploads/${segment(uploadId)}`),
  uploadProgress: (uploadId: string) => endpoint(`/api/v1/uploads/${segment(uploadId)}/progress`),
  uploadTimeline: (uploadId: string) => endpoint(`/api/v1/uploads/${segment(uploadId)}/timeline`),
  uploadValidationPreview: endpoint("/api/v1/documents/upload"),
  documentProcessingStatus: (documentId: string) =>
    endpoint(`/api/v1/documents/${segment(documentId)}/processing-status`),
  document: (documentId: string) => endpoint(`/api/v1/documents/${segment(documentId)}`),
  processing: (documentId: string) =>
    endpoint(`/api/v1/documents/${segment(documentId)}/processing`),
  validation: (documentId: string) =>
    endpoint(`/api/v1/documents/${segment(documentId)}/validation`),
  matching: (documentId: string) =>
    endpoint(`/api/v1/documents/${segment(documentId)}/matching`),
  documentExports: (documentId: string) => endpoint(`/api/v1/documents/${segment(documentId)}/exports`),
  exportAttempts: endpoint("/api/v1/export-attempts"),
  exportAttempt: (attemptId: string) => endpoint(`/api/v1/export-attempts/${segment(attemptId)}`),
  reviewCases: endpoint("/api/v1/review-cases"),
  reviewCase: (reviewCaseId: string) =>
    endpoint(`/api/v1/review-cases/${segment(reviewCaseId)}`),
  corrections: (reviewCaseId: string) =>
    endpoint(`/api/v1/review-cases/${segment(reviewCaseId)}/corrections`),
  reprocessPlans: endpoint("/api/v1/reprocess-plans"),
  workflowRuns: endpoint("/api/v1/workflow-runs"),
  auditEvents: endpoint("/api/v1/audit-events"),
});
