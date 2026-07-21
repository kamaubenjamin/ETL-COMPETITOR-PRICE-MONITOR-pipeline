# v0.21 Phase 6 Hosted UAT Closeout

**Milestone:** v0.21 Zero-Budget Vercel + Supabase UAT  
**Phase:** 6 - Hosted Verification and Handoff  
**Status:** Complete  
**Verified:** 2026-07-21

## Scope

Phase 6 proves the zero-budget hosted foundation for the read-only FlowSync Document Intelligence UAT. It covers the deployed frontend and API, Supabase email/password authentication, tenant membership resolution, asymmetric JWT verification, fixed owner permissions, protected document reads, exact-origin CORS, browser compatibility, and privacy-safe failure handling.

This closeout does not activate uploads, object storage, OCR, LLM extraction, document persistence, or any write operation.

## Deployed URLs

| Surface | Stable URL | Verified result |
| --- | --- | --- |
| FlowSync frontend | `https://flowsync-document-intelligence-uat.vercel.app` | HTTP 200 |
| FastAPI health | `https://flowsync-document-intelligence-api.vercel.app/health` | HTTP 200 |
| Versioned API health | `https://flowsync-document-intelligence-api.vercel.app/api/v1/health` | HTTP 200 |
| FastAPI documentation | `https://flowsync-document-intelligence-api.vercel.app/docs` | Reachable |

## Deployment Architecture

1. Vercel serves the Vite/React single-page application from the stable FlowSync UAT domain.
2. The browser uses the official Supabase client with the deployed project URL and publishable key to perform email/password authentication.
3. The browser keeps the Supabase-managed session and sends its access token as an in-memory bearer credential to the separate Vercel FastAPI deployment.
4. FastAPI verifies the asymmetric Supabase JWT against bounded JWKS, issuer, audience, signature, and time checks.
5. The API resolves one active tenant membership through the RLS-constrained Supabase Data API and maps its fixed UAT role to fixed permissions.
6. The API remains the authorization authority and returns only tenant-scoped, read-only protected data. Exact-origin CORS permits the stable frontend origin.

No privileged Supabase key is embedded in or required by the browser bundle.

## Smoke-Test Matrix

| Check | Result | Evidence |
| --- | --- | --- |
| Frontend root | Pass | HTTP 200 |
| API `/health` | Pass | HTTP 200 and healthy response |
| API `/api/v1/health` | Pass | HTTP 200 and healthy response |
| API `/docs` | Pass | HTTP 200 |
| Direct Supabase password sign-in | Pass | HTTP 200; session returned without logging its contents |
| Authenticated API session | Pass | HTTP 200; `authenticated=true`; role `owner` |
| Owner permission catalog | Pass | All 10 expected permissions returned |
| Protected document listing | Pass | HTTP 200; valid empty read-only listing |
| Stable frontend bundle identity | Pass | Live asset `index-BBrKbPpu.js` matches the verified local production asset |
| Public host binding | Pass | Expected Supabase and API hostnames embedded |
| Browser public configuration | Pass | No literal `VITE_` placeholder |
| Bundle credential scan | Pass | No credential-shaped Supabase secret key, service-role JWT, database URL, JWT secret, configured password, temporary secret value, or token candidate |
| Firefox fetch compatibility | Pass | Live bundle includes commit `e4b497e` and matches the local bound-fetch build |

The owner permission set is `document:list`, `document:read`, `workflow:admin`, `workflow:approve`, `workflow:create`, `workflow:deactivate`, `workflow:edit`, `workflow:publish`, `workflow:read`, and `workflow:test`.

The bundled Supabase client contains one bare `sb_secret_` rejection-guard string. It has no key suffix and is not a credential. The credential-shaped scan returned zero findings.

## Final Working Authentication Flow

1. A synthetic UAT owner signs in through the hosted FlowSync page.
2. `signInWithPassword` calls the configured Supabase Auth project and establishes a Supabase-managed browser session.
3. `AuthProvider` serializes the session bootstrap, retains a confirmed session, and requests `/api/v1/session` once for the current auth generation.
4. The API verifies the bearer JWT and resolves the active `flowsync-uat` owner membership.
5. The API maps the owner to the 10 fixed UAT permissions and returns the safe session profile.
6. `RequireAuth` accepts the authenticated owner profile, and the Documents route requests its protected read-only listing.
7. The API returns a tenant-scoped response. A current empty list is a valid hosted-foundation result, not an authorization failure.

Supabase Auth, the active membership, JWT verification, permission composition, the protected API, and exact-origin CORS were all proven healthy.

## Production Commit References

| Commit | Purpose |
| --- | --- |
| `e4b497e` | Bind native browser fetch before protected requests; final deployed Firefox fix |
| `db13c14` | Serialize and cancel session bootstrap requests |
| `8c5580f` | Distinguish transient session failures from forbidden access |
| `74e0fd3` | Validate Supabase public configuration and preserve confirmed sessions |
| `759d34f` | Keep the hosted API package within the serverless bundle budget |
| `ed8ed2c` | Remove obsolete bundled runtime dependency weight |

At closeout, `platform/intelligent-document-processing` and its tracked origin both point to `e4b497e`.

## Resolved Incidents

### Incorrect literal publishable-key deployment

An earlier frontend deployment embedded an incorrect literal value instead of the intended Supabase publishable key. Public configuration validation and the corrected Vercel build now bind the expected Supabase project and publishable-key class. The live bundle contains no unresolved `VITE_` placeholder.

### False forbidden classification

A transient protected-session bootstrap failure was previously rendered as a tenant authorization denial. Authentication status handling now distinguishes unavailable from genuine HTTP 403 and preserves fail-closed 401/403 behavior.

### Duplicate session bootstrap requests

Supabase auth event ordering and React lifecycle behavior could start competing session bootstrap work. Bootstrap requests are now serialized, bounded, generation-aware, and cancellable, preventing a stale result from overriding a valid owner profile.

### Unbound native browser fetch under Firefox

The API client passed the native browser `fetch` function as an unbound callback. Firefox rejected the call before `/api/v1/session` reached the network. The client now binds native fetch to `globalThis`; the final deployed bundle contains this fix, and the owner reaches the protected Documents workspace in Firefox.

## Security Notes

- Only the Supabase project URL and publishable key are browser-public.
- Tokens were held in memory for bounded verification and were not printed or written to disk.
- No credentials are tracked or present in the closeout diff.
- No service-role credential, database URL, JWT secret, password, or token is present in the live bundle.
- Membership and permission enforcement remains API-authoritative and tenant-scoped.
- Hosted mutations remain disabled; no authorization control was bypassed or weakened.
- The temporary `SUPABASE_SECRET_KEY` remains an owner rotation item after diagnosis and closeout. It was not rotated or deleted automatically.

## Known Limitations

- UAT / Technical Preview only.
- Synthetic and non-confidential data only.
- Read-only hosted foundation.
- No hosted uploads.
- No object-storage workflow.
- No OCR or LLM extraction.
- No document persistence.
- No production SLA.
- Free-tier operational limits, cold starts, pauses, quotas, and provider availability apply.
- The missing favicon is cosmetic and non-blocking.
- The frontend bundle-size warning remains non-blocking technical debt.
- The current protected document listing is empty by design because persistence and ingestion are not active.
- Process-local state is ephemeral across serverless recycle or redeployment.

## Deferred Capabilities

Uploads, object-storage activation, content staging, OCR, LLM extraction, durable document persistence, write workflows, production data, production identity, production scaling, and production support commitments remain deferred. They require separately approved architecture, security, data-handling, cost, and operational work.

## Phase 6 Definition of Done

- [x] Stable frontend, health, versioned health, and API documentation endpoints are reachable.
- [x] Direct Supabase password authentication succeeds for the synthetic UAT user.
- [x] The authenticated session resolves one active owner membership and the complete fixed owner permission set.
- [x] Protected document listing succeeds without enabling writes or persistence.
- [x] Supabase, membership, JWT, permissions, API, and CORS boundaries are proven healthy.
- [x] The live asset matches the locally verified production asset and contains the bound-fetch fix.
- [x] Public configuration and credential-pattern scans pass, subject only to the non-credential `sb_secret_` rejection guard noted above.
- [x] Frontend validation, typecheck, production build, auth/dist checks, Vercel/dist checks, and affected API tests pass.
- [x] Known limitations, security cleanup, resolved incidents, and deferred capabilities are documented.
- [x] Phase 7 closure and tag work is identified as the next milestone step.

## Handoff Into Phase 7

Phase 7 is the next step. It should align the final architecture and implementation summary, release notes, verification evidence, roadmap, debt register, and changelog; confirm the zero-budget and synthetic-data constraints; obtain owner approval for credential rotation and release actions; and recommend the v0.21 tag.

No commit, push, deployment, credential rotation, or tag is part of this Phase 6 closeout task.
