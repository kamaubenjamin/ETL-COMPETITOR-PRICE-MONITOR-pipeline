import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";
import {
  accessTokenProviderForSession,
  AUTH_DIAGNOSTIC_CODES,
  mapSupabaseSignInError,
  performPasswordSignIn,
  resolveSupabasePublicConfiguration,
  resolveSessionProfile,
  sessionFailureStatus,
  staleAuthFragmentReplacement,
  SupabaseBrowserConfigurationError,
} from "../../src/auth/authCore.mjs";
import { containsPrivilegedKeyPattern } from "../auth-bundle-scan.mjs";

test("successful password sign-in preserves entered credentials and retains the confirmed session", async () => {
  const session = { access_token: "synthetic-access-token" };
  let captured;
  const result = await performPasswordSignIn({
    async signInWithPassword(credentials) {
      captured = credentials;
      return { data: { session }, error: null };
    },
  }, " User@Example.test ", " exact password ");
  assert.deepEqual(captured, { email: " User@Example.test ", password: " exact password " });
  assert.equal(result.success, true);
  assert.equal(result.session, session);
  assert.equal(await accessTokenProviderForSession(result.session)(), "synthetic-access-token");
});

test("invalid credentials map to a safe fixed code without leaking provider text", async () => {
  const secretText = "provider detail containing a credential";
  const result = await performPasswordSignIn({
    async signInWithPassword() {
      return { data: { session: null }, error: { code: "invalid_credentials", message: secretText, status: 400 } };
    },
  }, "synthetic@example.test", "fixture-password");
  assert.deepEqual(result, { success: false, session: null, code: AUTH_DIAGNOSTIC_CODES.invalidCredentials });
  assert.equal(JSON.stringify(result).includes(secretText), false);
  assert.equal(mapSupabaseSignInError({ status: 429 }), AUTH_DIAGNOSTIC_CODES.rateLimited);
});

test("public Supabase configuration accepts VITE-style public values and rejects malformed or privileged values", () => {
  const valid = resolveSupabasePublicConfiguration(
    "https://project-ref.supabase.co",
    "sb_publishable_fixture",
    "uat",
    false,
  );
  assert.equal(valid.url, "https://project-ref.supabase.co");
  for (const [url, key] of [
    [undefined, "sb_publishable_fixture"],
    ["http://project-ref.supabase.co", "sb_publishable_fixture"],
    ["https://wrong.example", "sb_publishable_fixture"],
    ["https://project-ref.supabase.co", "sb_secret_fixture"],
    ["https://project-ref.supabase.co", "service_role"],
  ]) {
    assert.throws(() => resolveSupabasePublicConfiguration(url, key, "uat", false), SupabaseBrowserConfigurationError);
  }
});

test("stale recovery and token fragments are removed without changing path or query", () => {
  assert.equal(
    staleAuthFragmentReplacement({ pathname: "/documents", search: "?view=recent", hash: "#type=recovery&access_token=fixture" }),
    "/documents?view=recent",
  );
  assert.equal(staleAuthFragmentReplacement({ pathname: "/documents", hash: "#section" }), undefined);
});

test("privileged key patterns are rejected by bundle scans", () => {
  const serviceRolePayload = Buffer.from(JSON.stringify({ role: "service_role" })).toString("base64url");
  for (const value of ["sb_secret_abcdefghijklmnopqrstuvwxyz", "postgresql://db.example", "SUPABASE_JWT_SECRET", `eyJhbGciOiJIUzI1NiJ9.${serviceRolePayload}.fixture`]) {
    assert.equal(containsPrivilegedKeyPattern(value), true);
  }
  assert.equal(containsPrivilegedKeyPattern("the literal service_role is not itself a credential"), false);
  assert.equal(containsPrivilegedKeyPattern("the bare sb_secret_ guard prefix is not itself a credential"), false);
  assert.equal(containsPrivilegedKeyPattern("sb_publishable_fixture"), false);
});

test("confirmed session composition calls the protected API with the correct VITE configuration", () => {
  const root = resolve(import.meta.dirname, "../..");
  const provider = readFileSync(resolve(root, "src/auth/AuthProvider.tsx"), "utf8");
  const client = readFileSync(resolve(root, "src/auth/supabaseClient.ts"), "utf8");
  assert.match(client, /import\.meta\.env\.VITE_SUPABASE_URL/);
  assert.match(client, /import\.meta\.env\.VITE_SUPABASE_PUBLISHABLE_KEY/);
  assert.match(provider, /createApiClient\(accessTokenProviderForSession\(session\)\)\.get<SafeSessionProfile>\(API_ENDPOINTS\.session\)/);
  assert.doesNotMatch(provider, /createApiClient\(\)\.get<SafeSessionProfile>\(API_ENDPOINTS\.session\)/);
});

test("authenticated owner session survives one transient protected-route failure", async () => {
  const owner = {
    authenticated: true,
    role: "owner",
    tenant_name: "FlowSync UAT",
    permissions: ["workflow:read", "workflow:admin"],
  };
  let attempts = 0;
  const resolved = await resolveSessionProfile(async () => {
    attempts += 1;
    if (attempts === 1) throw new Error("transient session request failure");
    return { data: owner };
  });
  assert.equal(attempts, 2);
  assert.equal(resolved.data, owner);
  assert.equal(resolved.data.authenticated, true);
  assert.equal(resolved.data.role, "owner");
});

test("only a genuine API forbidden result becomes the protected-route unauthorized state", async () => {
  assert.equal(sessionFailureStatus({ safe: { kind: "forbidden" } }), "unauthorized");
  assert.equal(sessionFailureStatus({ safe: { kind: "unauthorized" } }), "unauthenticated");
  assert.equal(sessionFailureStatus({ safe: { kind: "unavailable" } }), "unavailable");
  assert.equal(sessionFailureStatus(new Error("timeout")), "unavailable");
  const forbidden = { safe: { kind: "forbidden" } };
  let attempts = 0;
  await assert.rejects(resolveSessionProfile(async () => {
    attempts += 1;
    throw forbidden;
  }), (error) => error === forbidden);
  assert.equal(attempts, 1);
});
