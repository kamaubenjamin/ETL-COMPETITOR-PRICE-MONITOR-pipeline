export type RouteId =
  | "documents"
  | "uploads"
  | "document-detail"
  | "document-validation"
  | "document-matching"
  | "review"
  | "review-detail"
  | "workflows"
  | "workflow-new"
  | "workflow-detail"
  | "workflow-editor"
  | "workflow-runs"
  | "audit"
  | "runtime-preview"
  | "unauthorized"
  | "unavailable";

export interface AppRouteDefinition {
  id: RouteId;
  path: string;
  label: string;
  description: string;
  navigation: "primary" | "secondary" | "contextual" | "hidden";
}

export const APP_ROUTES = Object.freeze([
  { id: "documents", path: "/documents", label: "Documents", description: "Document workload", navigation: "primary" },
  { id: "uploads", path: "/uploads", label: "Uploads", description: "Guarded validation preview and processing status", navigation: "primary" },
  { id: "document-detail", path: "/documents/:documentId", label: "Document detail", description: "Document status and metadata", navigation: "contextual" },
  { id: "document-validation", path: "/documents/:documentId/validation", label: "Validation", description: "Field-level validation", navigation: "contextual" },
  { id: "document-matching", path: "/documents/:documentId/matching", label: "Matching", description: "Candidate matching", navigation: "contextual" },
  { id: "review", path: "/review", label: "Review", description: "Review workload", navigation: "primary" },
  { id: "review-detail", path: "/review/:reviewCaseId", label: "Review case", description: "Review case history", navigation: "contextual" },
  { id: "workflows", path: "/workflows", label: "Business Workflows", description: "Governed workflow and rules definitions", navigation: "primary" },
  { id: "workflow-new", path: "/workflows/new", label: "Create workflow", description: "Create a governed workflow draft", navigation: "contextual" },
  { id: "workflow-detail", path: "/workflows/:workflowId", label: "Workflow detail", description: "Definition, versions, operations, and audit", navigation: "contextual" },
  { id: "workflow-editor", path: "/workflows/:workflowId/versions/:versionId/edit", label: "Draft editor", description: "Structured workflow rules editor", navigation: "contextual" },
  { id: "workflow-runs", path: "/workflow-runs", label: "Workflow runs", description: "Read-only runtime activity", navigation: "hidden" },
  { id: "audit", path: "/audit", label: "Audit", description: "Safe audit history", navigation: "primary" },
  { id: "runtime-preview", path: "/settings/runtime-preview", label: "Runtime preview", description: "Non-authoritative runtime status", navigation: "secondary" },
  { id: "unauthorized", path: "/unauthorized", label: "Access required", description: "Authentication or authorization required", navigation: "hidden" },
  { id: "unavailable", path: "/unavailable", label: "Unavailable", description: "Service unavailable", navigation: "hidden" },
] satisfies readonly AppRouteDefinition[]);

export const NAVIGATION_ROUTES = APP_ROUTES.filter(
  (route) => route.navigation === "primary" || route.navigation === "secondary",
);
