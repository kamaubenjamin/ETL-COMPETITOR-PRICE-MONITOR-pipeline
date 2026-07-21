import { readFileSync, readdirSync, statSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const sourceRoot = join(root, "src");
const failures = [];
const packageJson = JSON.parse(readFileSync(join(root, "package.json"), "utf8"));

for (const script of ["validate", "typecheck", "build", "dev"]) {
  if (typeof packageJson.scripts?.[script] !== "string") failures.push(`missing package script: ${script}`);
}

const trackedFiles = execFileSync("git", ["ls-files"], { cwd: root, encoding: "utf8" })
  .split(/\r?\n/)
  .filter(Boolean)
  .map((name) => name.replaceAll("\\", "/"));
for (const name of trackedFiles) {
  if (name.includes("/node_modules/") || name.includes("/dist/") || name.includes("/coverage/")) {
    failures.push(`generated directory is tracked: ${name}`);
  }
}

function walk(directory) {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

const sourceFiles = walk(sourceRoot).filter((path) => /\.(?:ts|tsx|mjs)$/.test(path));
const source = sourceFiles.map((path) => ({
  path,
  name: relative(root, path).replaceAll("\\", "/"),
  content: readFileSync(path, "utf8"),
}));

const requiredFiles = [
  "src/pages/DocumentsPage.tsx",
  "src/pages/DocumentDetailPage.tsx",
  "src/api/documents.ts",
  "src/app/routes.ts",
  "src/pages/DocumentValidationPage.tsx",
  "src/pages/DocumentMatchingPage.tsx",
  "src/pages/ReviewCasesPage.tsx",
  "src/pages/ReviewCaseDetailPage.tsx",
  "src/pages/WorkflowsPage.tsx",
  "src/pages/AuditPage.tsx",
  "src/components/AccessScopeNotice.tsx",
  "src/components/SafeAlert.tsx",
  "src/state/requestState.ts",
  "src/api/exports.ts",
  "src/types/export.ts",
  "src/components/ExportReadinessPanel.tsx",
  "src/pages/UploadsPage.tsx",
  "src/api/uploads.ts",
  "src/types/upload.ts",
  "src/state/uploadViewModels.ts",
  "src/components/UploadDocumentPanel.tsx",
  "src/components/UploadValidationSummary.tsx",
  "src/components/UploadProgressTimeline.tsx",
  "src/components/RecentUploadsPanel.tsx",
  "src/components/ProcessingStatusPanel.tsx",
  "src/pages/WorkflowStudioPage.tsx",
  "src/pages/WorkflowDetailPage.tsx",
  "src/pages/WorkflowEditorPage.tsx",
  "src/services/workflowStudioApi.ts",
  "src/types/workflowStudio.ts",
  "src/components/workflows/RuleEditor.tsx",
  "src/components/workflows/ValidationPanel.tsx",
  "src/components/workflows/PreviewPanel.tsx",
  "src/components/workflows/OperationCatalogPanel.tsx",
  "src/config/deploymentEnvironment.ts",
  "src/config/deploymentEnvironmentCore.mjs",
  "src/auth/supabaseClient.ts",
  "src/auth/AuthProvider.tsx",
  "src/auth/RequireAuth.tsx",
  "src/pages/SignInPage.tsx",
];
for (const name of requiredFiles) {
  if (!source.some((file) => file.name === name)) failures.push(`missing required source: ${name}`);
}

const routeSource = source.find((file) => file.name === "src/app/routes.ts")?.content ?? "";
for (const route of [
  "/documents",
  "/documents/:documentId",
  "/documents/:documentId/validation",
  "/documents/:documentId/matching",
  "/review",
  "/review/:reviewCaseId",
  "/workflows",
  "/workflows/new",
  "/workflows/:workflowId",
  "/workflows/:workflowId/versions/:versionId/edit",
  "/workflow-runs",
  "/audit",
  "/uploads",
]) {
  if (!routeSource.includes(route)) failures.push(`missing route contract: ${route}`);
}

const apiRequirements = {
  "src/api/reviews.ts": ["listReviewCases", "getReviewCase", "listCorrectionHistory"],
  "src/api/workflows.ts": ["listWorkflowRuns"],
  "src/api/audit.ts": ["listAuditEvents"],
  "src/api/uploads.ts": [
    "listUploads", "getUploadProgress", "getUploadTimeline",
    "getDocumentProcessingStatus", "validateUploadMetadataPreview",
  ],
};
apiRequirements["src/services/workflowStudioApi.ts"] = [
  "listWorkflowDefinitions", "getWorkflowDefinition", "listWorkflowVersions",
  "getWorkflowVersion", "listWorkflowAudit", "listWorkflowOperations",
  "createWorkflow", "createWorkflowVersion", "replaceWorkflowDraft",
  "validateWorkflowVersion", "testWorkflowVersion", "submitWorkflowVersion",
  "approveWorkflowVersion", "publishWorkflowVersion", "deactivateWorkflow", "archiveWorkflow",
];
for (const [name, functions] of Object.entries(apiRequirements)) {
  const content = source.find((file) => file.name === name)?.content ?? "";
  for (const apiFunction of functions) {
    if (!content.includes(`function ${apiFunction}`) && !content.includes(`const ${apiFunction}`)) failures.push(`missing API function: ${apiFunction}`);
  }
}

const documentApi = source.find((file) => file.name === "src/api/documents.ts")?.content ?? "";
for (const apiFunction of [
  "listDocuments",
  "getDocument",
  "getDocumentProcessing",
  "getDocumentValidation",
  "getDocumentMatching",
]) {
  if (!documentApi.includes(`function ${apiFunction}`)) failures.push(`missing API function: ${apiFunction}`);
}

const forbiddenPatterns = [
  { pattern: /from\s+["'][^"']*(?:document_state|platform_runtime|ui\/streamlit|competitor)/i, label: "forbidden import" },
  { pattern: /\b(?:Authorization|Bearer|localStorage|sessionStorage|document\.cookie)\b/, label: "credential or browser storage" },
  { pattern: /\b(?:tenant_id|raw_document|raw_rows|correction_value|artifact_payload|storage_path|stack_trace|backend_config|access_token|raw_claims)\b/i, label: "sensitive field" },
  { pattern: /\b(?:fixture|mock)_fallback\b/i, label: "fixture fallback" },
];

const phaseThreePages = new Set([
  "src/pages/DocumentValidationPage.tsx", "src/pages/DocumentMatchingPage.tsx",
  "src/pages/ReviewCasesPage.tsx", "src/pages/ReviewCaseDetailPage.tsx",
  "src/pages/WorkflowsPage.tsx", "src/pages/AuditPage.tsx",
]);

for (const file of source) {
  for (const { pattern, label } of forbiddenPatterns) {
    const approvedBearerBoundary = label === "credential or browser storage" && ["src/api/client.ts", "src/auth/supabaseClient.ts"].includes(file.name);
    const approvedSessionBoundary = label === "sensitive field"
      && ["src/auth/supabaseClient.ts", "src/auth/authCore.mjs"].includes(file.name);
    if (!approvedBearerBoundary && !approvedSessionBoundary && pattern.test(file.content)) failures.push(`${label} found in ${file.name}`);
  }
  if (phaseThreePages.has(file.name) && /onClick=|<form|type=["']submit["']/.test(file.content)) {
    failures.push(`interactive mutation surface found in ${file.name}`);
  }
}

const actionSources = source.filter((file) => phaseThreePages.has(file.name)).map((file) => file.content).join("\n");
if (/method:\s*["'](?:POST|PUT|PATCH|DELETE)["']/i.test(actionSources)) failures.push("Phase 3 mutation request found");

const requestStateSource = source.find((file) => file.name === "src/state/requestState.ts")?.content ?? "";
for (const status of ["idle", "loading", "success", "empty", "unauthorized", "forbidden", "not_found", "conflict", "unavailable", "malformed", "safe_error"]) {
  if (!requestStateSource.includes(`"${status}"`)) failures.push(`missing request state: ${status}`);
}

const safeCopy = source
  .filter((file) => ["src/api/errors.ts", "src/components/AccessScopeNotice.tsx", "src/pages/RuntimePreviewPage.tsx"].includes(file.name))
  .map((file) => file.content)
  .join("\n");
for (const message of [
  "Sign in is required to continue.",
  "You do not have access to this view.",
  "not found or is unavailable to your access scope",
  "temporarily unavailable",
  "runtime is currently unavailable",
  "access is not configured for this environment",
  "invalid response",
  "API-enforced visibility",
]) {
  if (!safeCopy.includes(message)) failures.push(`missing fixed safe copy: ${message}`);
}

const permissionDecisionPattern = /if\s*\([^)]*\b(?:role|permission|organization)\b|\.filter\s*\([^)]*\b(?:tenant|permission)\b/i;
for (const file of source) {
  if (file.name !== "src/auth/supabaseClient.ts" && permissionDecisionPattern.test(file.content)) failures.push(`frontend access decision logic found in ${file.name}`);
}

const clientSource = source.find((file) => file.name === "src/api/client.ts")?.content ?? "";
if (!clientSource.includes('method: "GET"')) failures.push("GET-only client method is missing");
if (!clientSource.includes("async mutate<T>") || !clientSource.includes('method: "POST"')) failures.push("centralized guarded mutation client is missing");
if (!clientSource.includes("documentIntelligenceApiBaseUrl") || !clientSource.includes("ApiClientError.configuration")) failures.push("environment-safe API URL composition is missing");

const environmentSource = source.find((file) => file.name === "src/config/deploymentEnvironment.ts")?.content ?? "";
const environmentCoreSource = source.find((file) => file.name === "src/config/deploymentEnvironmentCore.mjs")?.content ?? "";
const headerSource = source.find((file) => file.name === "src/components/Header.tsx")?.content ?? "";
for (const value of ["Local Development", "UAT / Technical Preview", "resolveDeploymentEnvironmentLabel"]) {
  if (![environmentSource, environmentCoreSource].join("\n").includes(value)) failures.push(`missing safe deployment label behavior: ${value}`);
}
if (!headerSource.includes("deploymentEnvironmentLabel") || !headerSource.includes("environment-indicator")) failures.push("environment label is not rendered in the header");
for (const value of ["resolveDocumentIntelligenceApiBaseUrl", "hasValidDocumentIntelligenceApiConfiguration", "import.meta.env.DEV"]) {
  if (!environmentSource.includes(value) && !environmentCoreSource.includes(value)) failures.push(`missing hosted API configuration guard: ${value}`);
}
const frontendSource = source.map((file) => file.content).join("\n");
for (const serverOnlyName of ["SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY", "DATABASE_URL", "JWT_JWKS_URL"]) {
  if (frontendSource.includes(serverOnlyName)) failures.push(`server-only environment name found in frontend source: ${serverOnlyName}`);
}
for (const file of source) {
  if (file.name !== "src/api/client.ts" && /method:\s*["'](?:POST|PUT|PATCH|DELETE)["']/i.test(file.content)) {
    failures.push(`unapproved mutation method found in ${file.name}`);
  }
}

const uploadBoundarySource = source
  .filter((file) => file.name.includes("upload") || file.name.includes("Upload"))
  .map((file) => file.content)
  .join("\n");
for (const [pattern, label] of [
  [/FormData/i, "form data transmission"],
  [/multipart\/form-data/i, "multipart transmission"],
  [/FileReader/i, "file content reader"],
  [/readAsDataURL/i, "data URL reader"],
  [/arrayBuffer/i, "byte buffer reader"],
  [/base64/i, "encoded file content"],
  [/\bBlob\b/i, "binary payload"],
]) {
  if (pattern.test(uploadBoundarySource)) failures.push(`${label} found in upload sources`);
}
for (const message of [
  "Upload validation preview",
  "File staging is not enabled yet",
  "The selected file will not leave this browser in the current release",
  "Processing will become available after the staging boundary is activated",
  "Validate upload",
]) {
  if (!uploadBoundarySource.includes(message)) failures.push(`missing governed upload copy: ${message}`);
}
for (const unsafeClaim of ["Upload and process", "Upload successful", "File uploaded"]) {
  if (uploadBoundarySource.includes(unsafeClaim)) failures.push(`unsafe upload claim found: ${unsafeClaim}`);
}

const exportSource = source.filter((file) => file.name.includes("Export") || file.name.endsWith("/exports.ts")).map((file) => file.content).join("\n");
for (const message of ["Export boundary planned", "Export execution is disabled until API mutation activation is approved", "ERP adapters are not connected"]) {
  if (!exportSource.includes(message)) failures.push(`missing export placeholder copy: ${message}`);
}
if (/method:\s*["']POST["']|\.post\s*\(/i.test(exportSource)) failures.push("export mutation request found");

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`Validated ${sourceFiles.length} frontend source files: Phase 6 Workflow Studio, existing routes, API boundaries, and privacy checks passed.`);
