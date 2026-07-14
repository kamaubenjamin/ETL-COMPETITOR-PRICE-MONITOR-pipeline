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
]) {
  if (!routeSource.includes(route)) failures.push(`missing route contract: ${route}`);
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
  { pattern: /\b(?:tenant_id|raw_document|raw_rows|correction_value|artifact_payload|storage_path|stack_trace)\b/i, label: "sensitive field" },
  { pattern: /\b(?:fixture|mock)_?(?:fallback)?\b/i, label: "fixture fallback" },
];

for (const file of source) {
  for (const { pattern, label } of forbiddenPatterns) {
    if (pattern.test(file.content)) failures.push(`${label} found in ${file.name}`);
  }
}

const clientSource = source.find((file) => file.name === "src/api/client.ts")?.content ?? "";
if (!clientSource.includes('method: "GET"')) failures.push("GET-only client method is missing");

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`Validated ${sourceFiles.length} frontend source files: routes, GET-only API, boundaries, and privacy checks passed.`);
