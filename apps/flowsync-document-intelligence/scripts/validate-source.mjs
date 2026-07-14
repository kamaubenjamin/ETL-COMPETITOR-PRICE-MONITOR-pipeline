import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const sourceRoot = join(root, "src");
const failures = [];

function walk(directory) {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

const sourceFiles = walk(sourceRoot).filter((path) => /\.(ts|tsx)$/.test(path));
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
  "/audit",
]) {
  if (!routeSource.includes(route)) failures.push(`missing route contract: ${route}`);
}

const apiRequirements = {
  "src/api/reviews.ts": ["listReviewCases", "getReviewCase", "listCorrectionHistory"],
  "src/api/workflows.ts": ["listWorkflowRuns"],
  "src/api/audit.ts": ["listAuditEvents"],
};
for (const [name, functions] of Object.entries(apiRequirements)) {
  const content = source.find((file) => file.name === name)?.content ?? "";
  for (const apiFunction of functions) {
    if (!content.includes(`function ${apiFunction}`)) failures.push(`missing API function: ${apiFunction}`);
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
  { pattern: /method:\s*["'](?:POST|PUT|PATCH|DELETE)["']/i, label: "mutation method" },
  { pattern: /from\s+["'][^"']*(?:document_state|platform_runtime|ui\/streamlit|competitor)/i, label: "forbidden import" },
  { pattern: /\b(?:Authorization|Bearer|localStorage|sessionStorage|document\.cookie)\b/, label: "credential or browser storage" },
  { pattern: /\b(?:tenant_id|raw_document|raw_rows|correction_value|artifact_payload|storage_path|stack_trace|backend_config|access_token|raw_claims)\b/i, label: "sensitive field" },
  { pattern: /\b(?:fixture|mock)_?(?:fallback)?\b/i, label: "fixture fallback" },
];

const phaseThreePages = new Set([
  "src/pages/DocumentValidationPage.tsx", "src/pages/DocumentMatchingPage.tsx",
  "src/pages/ReviewCasesPage.tsx", "src/pages/ReviewCaseDetailPage.tsx",
  "src/pages/WorkflowsPage.tsx", "src/pages/AuditPage.tsx",
]);

for (const file of source) {
  for (const { pattern, label } of forbiddenPatterns) {
    if (pattern.test(file.content)) failures.push(`${label} found in ${file.name}`);
  }
  if (phaseThreePages.has(file.name) && /onClick=|<form|type=["']submit["']/.test(file.content)) {
    failures.push(`interactive mutation surface found in ${file.name}`);
  }
}

const actionSources = source.filter((file) => phaseThreePages.has(file.name)).map((file) => file.content).join("\n");
if (/method:\s*["'](?:POST|PUT|PATCH|DELETE)["']/i.test(actionSources)) failures.push("Phase 3 mutation request found");

const requestStateSource = source.find((file) => file.name === "src/state/requestState.ts")?.content ?? "";
for (const status of ["idle", "loading", "success", "empty", "unauthorized", "forbidden", "not_found", "unavailable", "malformed", "safe_error"]) {
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
  if (permissionDecisionPattern.test(file.content)) failures.push(`frontend access decision logic found in ${file.name}`);
}

const clientSource = source.find((file) => file.name === "src/api/client.ts")?.content ?? "";
if (!clientSource.includes('method: "GET"')) failures.push("GET-only client method is missing");

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`Validated ${sourceFiles.length} frontend source files: Phase 4 auth states, GET-only API, boundaries, and privacy checks passed.`);
