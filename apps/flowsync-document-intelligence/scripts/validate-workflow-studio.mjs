import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (name) => readFileSync(resolve(root, name), "utf8");
const failures = [];
const app = read("src/App.tsx");
const routes = read("src/app/routes.ts");
const list = read("src/pages/WorkflowStudioPage.tsx");
const detail = read("src/pages/WorkflowDetailPage.tsx");
const editor = read("src/pages/WorkflowEditorPage.tsx");
const service = read("src/services/workflowStudioApi.ts");
const types = read("src/types/workflowStudio.ts");
const ruleEditor = read("src/components/workflows/RuleEditor.tsx");
const validation = read("src/components/workflows/ValidationPanel.tsx");
const preview = read("src/components/workflows/PreviewPanel.tsx");
const operations = read("src/components/workflows/OperationCatalogPanel.tsx");
const workflowSource = [list, detail, editor, service, types, ruleEditor, validation, preview, operations].join("\n");

for (const route of ["workflows/new", "workflows/:workflowId", "workflows/:workflowId/versions/:versionId/edit", "workflow-runs"]) {
  if (!app.includes(route)) failures.push(`missing route integration: ${route}`);
}
if (!routes.includes("Business Workflows")) failures.push("missing Business Workflows navigation label");
for (const name of ["listWorkflowDefinitions", "createWorkflow", "replaceWorkflowDraft", "validateWorkflowVersion", "testWorkflowVersion", "submitWorkflowVersion", "approveWorkflowVersion", "publishWorkflowVersion", "deactivateWorkflow", "archiveWorkflow"]) {
  if (!service.includes(name)) failures.push(`missing guarded service call: ${name}`);
}
for (const prohibited of ["tenant_id", "actor_id", "access_token", "raw_claims", "stack_trace", "backend_config", "runtime_operation", "localStorage", "sessionStorage", "console.log", "eval(", "new Function", "CodeEditor"] ) {
  if (workflowSource.includes(prohibited)) failures.push(`unsafe Workflow Studio source token: ${prohibited}`);
}
for (const copy of [
  "No workflows yet", "The draft changed elsewhere", "Validation not yet run",
  "Preview execution adapter is not connected in this environment.",
  "Published definition governance only. Production execution activation is not enabled.",
  "No previous version was automatically activated", "Immutable history was preserved",
]) {
  if (![workflowSource, read("src/api/errors.ts")].join("\n").includes(copy)) failures.push(`missing safe UI state: ${copy}`);
}
if (!ruleEditor.includes("availability !== \"available\"") || !ruleEditor.includes("disabled={operation.availability !== \"available\"}")) failures.push("unavailable operation selection guard is missing");
if (!editor.includes("expected_revision: version.revision") || !editor.includes("rules")) failures.push("full optimistic draft replacement is missing");
if (!validation.includes("blocking") || !validation.includes("warning") || !validation.includes("info")) failures.push("validation severity rendering is incomplete");
if (!preview.includes("Structured value") || !preview.includes("No successful execution is implied")) failures.push("privacy-safe preview rendering is incomplete");
if (/fetch\s*\(/.test(service)) failures.push("Workflow Studio service bypasses the centralized API client");
if (/from\s+["'][^"']*(?:workflow_runtime|repository|document_state|security|competitor|streamlit|erp|export_runtime)/i.test(workflowSource)) failures.push("forbidden backend or adjacent module import found");

if (failures.length) { console.error(failures.join("\n")); process.exit(1); }
console.log("Validated FlowSync Workflow Studio routes, guarded API calls, editor, lifecycle, permissions, privacy, and governance messaging.");
