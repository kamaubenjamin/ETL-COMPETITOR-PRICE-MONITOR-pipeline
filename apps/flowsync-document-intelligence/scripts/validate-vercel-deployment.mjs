import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  DeploymentConfigurationError,
  resolveDeploymentEnvironmentLabel,
  resolveDocumentIntelligenceApiBaseUrl,
} from "../src/config/deploymentEnvironmentCore.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(root, "..", "..");
const failures = [];
const read = (path) => readFileSync(join(root, path), "utf8");
const assert = (condition, message) => { if (!condition) failures.push(message); };
const assertThrows = (operation, message) => {
  try {
    operation();
    failures.push(message);
  } catch (error) {
    if (!(error instanceof DeploymentConfigurationError)) failures.push(`${message}: wrong error type`);
  }
};

const vercel = JSON.parse(read("vercel.json"));
assert(vercel.$schema === "https://openapi.vercel.sh/vercel.json", "Vercel schema is missing");
assert(vercel.framework === "vite", "Vercel framework must be Vite");
assert(vercel.installCommand === "npm ci", "Vercel install command must be npm ci");
assert(vercel.buildCommand === "npm run build", "Vercel build command must be npm run build");
assert(vercel.outputDirectory === "dist", "Vercel output directory must be dist");
assert(!("functions" in vercel), "frontend project must not configure backend functions");
assert(Array.isArray(vercel.rewrites) && vercel.rewrites.length === 1, "exactly one SPA rewrite is required");

const rewrite = vercel.rewrites?.[0] ?? {};
assert(rewrite.destination === "/index.html", "SPA rewrite must target index.html");
let rewritePattern;
try {
  rewritePattern = new RegExp(`^${rewrite.source}$`);
} catch {
  failures.push("SPA rewrite source is not a valid grouped pattern");
}
if (rewritePattern) {
  for (const route of [
    "/", "/documents", "/uploads", "/workflow-runs", "/workflows", "/workflows/new",
    "/workflows/workflow-1", "/workflows/workflow-1/versions/version-1/edit",
  ]) {
    assert(rewritePattern.test(route), `SPA route is not rewritten: ${route}`);
  }
  for (const path of ["/api", "/api/v1/health", "/assets/index.js", "/favicon.svg", "/robots.txt"]) {
    assert(!rewritePattern.test(path), `non-SPA request is incorrectly rewritten: ${path}`);
  }
}

const packageJson = JSON.parse(read("package.json"));
assert(packageJson.engines?.node === ">=22.12 <23", "Node runtime range must be compatible with Vite 8");
for (const script of ["validate", "validate:vercel", "validate:vercel:dist", "typecheck", "build", "lint", "test"]) {
  assert(typeof packageJson.scripts?.[script] === "string", `missing package script: ${script}`);
}

const environmentTemplate = read(".env.example");
for (const line of [
  "VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL=",
  "VITE_SUPABASE_URL=",
  "VITE_SUPABASE_PUBLISHABLE_KEY=",
  "VITE_DEPLOYMENT_ENVIRONMENT=uat",
  "VITE_UAT_LABEL=UAT / Technical Preview",
  "VITE_WORKFLOW_STUDIO_PERMISSIONS=",
]) {
  assert(environmentTemplate.split(/\r?\n/).includes(line), `environment template is missing: ${line}`);
}

assert(
  resolveDocumentIntelligenceApiBaseUrl(undefined, "local", true, "http://127.0.0.1:8001") === "http://127.0.0.1:8001",
  "local development fallback is not deterministic",
);
assert(
  resolveDocumentIntelligenceApiBaseUrl("https://api-project.vercel.app/", "uat", false) === "https://api-project.vercel.app",
  "hosted HTTPS API origin is not normalized",
);
for (const [value, environment, development, message] of [
  [undefined, "uat", false, "missing UAT API URL must fail"],
  ["http://api.example.test", "uat", false, "HTTP UAT API URL must fail"],
  ["http://example.test", "local", true, "non-loopback local HTTP must fail"],
  ["https://user:password@api.example.test", "uat", false, "credential-bearing API URL must fail"],
  ["https://api.example.test/path", "uat", false, "API URL path must fail"],
  ["https://api.example.test?query=value", "uat", false, "API URL query must fail"],
  ["https://api.example.test#fragment", "uat", false, "API URL fragment must fail"],
  ["not-a-url", "uat", false, "malformed API URL must fail"],
  ["https://api.example.test", "unknown", false, "unknown deployment environment must fail"],
]) {
  assertThrows(() => resolveDocumentIntelligenceApiBaseUrl(value, environment, development), message);
}
assert(resolveDeploymentEnvironmentLabel(undefined, undefined) === "Local Development", "missing label must fall back safely");
assert(resolveDeploymentEnvironmentLabel("UAT / Technical Preview", "uat") === "UAT / Technical Preview", "UAT label is not deterministic");
assert(resolveDeploymentEnvironmentLabel("Production", "uat") === "UAT / Technical Preview", "UAT must not render a production claim");
assert(resolveDeploymentEnvironmentLabel("Production", undefined) === "Local Development", "unconfigured builds must not render a production claim");

const appSource = read("src/App.tsx");
for (const route of [
  "documents", "uploads", "workflow-runs", "workflows", "workflows/new",
  "workflows/:workflowId", "workflows/:workflowId/versions/:versionId/edit",
]) {
  assert(appSource.includes(`path=\"${route}\"`) || (route === "documents" && appSource.includes("to=\"/documents\"")), `registered route is missing: ${route}`);
}
const sourceFiles = [];
const walk = (directory) => {
  for (const name of readdirSync(directory)) {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) walk(path);
    else if (/\.(?:ts|tsx|mjs)$/.test(path)) sourceFiles.push(path);
  }
};
walk(join(root, "src"));
const frontendSource = sourceFiles.map((path) => readFileSync(path, "utf8")).join("\n");
for (const serverOnly of ["SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY", "DATABASE_URL", "JWT_JWKS_URL"]) {
  assert(!frontendSource.includes(serverOnly), `server-only environment name found in frontend: ${serverOnly}`);
}
for (const authorityToken of ["x-local-identity", "x-tenant-id", "fake_signed_in"]) {
  assert(!frontendSource.includes(authorityToken), `hosted authority token found in frontend: ${authorityToken}`);
}
const errorsSource = read("src/api/errors.ts");
assert(errorsSource.includes('status === 401') && errorsSource.includes('status === 403'), "safe 401/403 handling is missing");
assert(errorsSource.includes("Document Intelligence API is not configured for this environment."), "safe deployment configuration error is missing");
assert(read("src/app/AppShell.tsx").includes("hasValidDocumentIntelligenceApiConfiguration"), "app-wide configuration guard is missing");
assert(read("src/components/Header.tsx").includes("environment-indicator"), "UAT header indicator is missing");
assert(read("src/auth/RequireAuth.tsx").includes("SignInPage"), "hosted authentication guard is missing");
assert(read("vite.config.ts").includes("sourcemap: false"), "production source maps must remain disabled");

const deploymentDoc = readFileSync(
  join(repositoryRoot, "docs", "implementation", "V0_21_PHASE_4_FLOWSYNC_VERCEL_DEPLOYMENT.md"),
  "utf8",
);
for (const setting of [
  "flowsync-document-intelligence-uat", "ETL-COMPETITOR-PRICE-MONITOR-pipeline",
  "platform/intelligent-document-processing", "apps/flowsync-document-intelligence",
  "npm ci", "npm run build", "dist", "22.x",
]) {
  assert(deploymentDoc.includes(setting), `deployment documentation is missing: ${setting}`);
}

if (process.argv.includes("--dist")) {
  const distRoot = join(root, "dist");
  const distFiles = [];
  const walkDist = (directory) => {
    for (const name of readdirSync(directory)) {
      const path = join(directory, name);
      if (statSync(path).isDirectory()) walkDist(path);
      else distFiles.push(path);
    }
  };
  walkDist(distRoot);
  const bundleText = distFiles.map((path) => readFileSync(path).toString("utf8")).join("\n");
  for (const forbidden of [
    "http://127.0.0.1:8001", "http://localhost", "SUPABASE_SECRET_KEY",
    "SUPABASE_SERVICE_ROLE_KEY", "DATABASE_URL", "JWT_JWKS_URL", "x-local-identity", "x-tenant-id",
  ]) {
    assert(!bundleText.includes(forbidden), `forbidden hosted bundle value found: ${forbidden}`);
  }
  assert(bundleText.includes("UAT / Technical Preview"), "UAT label is missing from hosted bundle");
  assert(
    bundleText.includes("Document Intelligence API is not configured for this environment."),
    "safe configuration message is missing from hosted bundle",
  );
  assert(!distFiles.some((path) => path.endsWith(".map")), "source map found in production dist");
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log(`Validated FlowSync Vercel deployment boundaries${process.argv.includes("--dist") ? " and hosted dist" : ""}.`);
