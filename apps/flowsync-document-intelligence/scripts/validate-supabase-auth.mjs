import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { resolve } from "node:path";
import { containsPrivilegedKeyPattern } from "./auth-bundle-scan.mjs";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");
const failures = [];
const assert = (condition, message) => { if (!condition) failures.push(message); };
const packageJson = JSON.parse(read("package.json"));
const client = read("src/auth/supabaseClient.ts");
const provider = read("src/auth/AuthProvider.tsx");
const guard = read("src/auth/RequireAuth.tsx");
const signIn = read("src/pages/SignInPage.tsx");
const authCore = read("src/auth/authCore.mjs");
const apiClient = read("src/api/client.ts");
const app = read("src/App.tsx");
const header = read("src/components/Header.tsx");
const env = read(".env.example");
const authSource = [client, provider, guard, signIn].join("\n");

assert(packageJson.dependencies?.["@supabase/supabase-js"] === "2.110.7", "official Supabase client must be exactly pinned");
assert(client.includes("let browserClient") && client.includes("if (!browserClient)"), "Supabase browser client is not a singleton");
assert(client.includes("persistSession: true") && client.includes("autoRefreshToken: true"), "supported session persistence/refresh is missing");
assert(provider.includes("auth.getSession()") && provider.includes("onAuthStateChange"), "session restoration is incomplete");
assert(authCore.includes("signInWithPassword") && provider.includes("auth.signOut()"), "email/password sign-in or sign-out is missing");
assert(provider.includes("accessTokenProviderForSession(session)"), "confirmed sessions must not re-enter getSession during profile resolution");
assert(provider.includes("window.setTimeout") && provider.includes("onAuthStateChange"), "auth-state processing must be deferred outside the Supabase callback");
assert(signIn.includes("signIn(email, password)") && !signIn.includes("email.trim()"), "entered credentials must be passed without mutation");
assert(signIn.includes("Diagnostic:") && signIn.includes("diagnosticCode"), "safe UAT auth diagnostics are missing");
assert(guard.includes('status === "loading"') && guard.includes("<Outlet"), "protected content loading guard is missing");
assert(app.includes("<RequireAuth"), "application routes are not protected");
assert(apiClient.includes("Authorization: `Bearer ${token}`"), "API bearer propagation is missing");
assert(header.includes("signOut") && header.includes("UAT") === false, "header auth control must use safe runtime state");
for (const forbidden of ["signUp(", "signInWithOAuth", "signInAnonymously", "resetPassword", "localStorage", "sessionStorage", "console.log", "console.error"]) {
  assert(!authSource.includes(forbidden), `unsupported or unsafe auth behavior found: ${forbidden}`);
}
for (const required of ["VITE_SUPABASE_URL=", "VITE_SUPABASE_PUBLISHABLE_KEY="]) {
  assert(env.split(/\r?\n/).includes(required), `missing public auth environment variable: ${required}`);
}
for (const forbidden of ["SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SECRET_KEY", "DATABASE_URL", "x-local-identity", "x-tenant-id"] ) {
  assert(!authSource.includes(forbidden) && !apiClient.includes(forbidden), `server authority leaked into frontend auth: ${forbidden}`);
}

const distRoot = resolve(root, "dist");
if (process.argv.includes("--dist") && existsSync(distRoot)) {
  const files = [];
  const walk = (directory) => {
    for (const name of readdirSync(directory)) {
      const path = resolve(directory, name);
      if (statSync(path).isDirectory()) walk(path);
      else files.push(path);
    }
  };
  walk(distRoot);
  const bundle = files.map((path) => readFileSync(path).toString("utf8")).join("\n");
  assert(!containsPrivilegedKeyPattern(bundle), "privileged key pattern found in dist");
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log("Validated Supabase browser Auth, protected routing, bearer propagation, and secret boundaries.");
