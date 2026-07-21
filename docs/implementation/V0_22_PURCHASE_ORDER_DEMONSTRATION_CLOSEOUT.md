# v0.22 Deterministic Purchase-Order Demonstration Closeout

**Milestone:** v0.22 Deterministic Purchase-Order Demonstration

**Status:** Implemented and hosted-UAT verified; owner closeout commit and tag pending

**Closeout baseline:** `ccca2af`

**Prepared:** 2026-07-21

## Outcome

v0.22 proves a bounded, deterministic path from a machine-readable purchase-order PDF to an exact-decimal canonical projection and a protected, tenant-scoped, read-only FlowSync presentation. Hosted UAT exposes one fictional purchase-order record, `doc-002`, without enabling upload, persistence, object storage, OCR, LLM extraction, background work, approval, export, or any document mutation.

Owner verification at `ccca2af` confirms authenticated session bootstrap, normal document listing and filtering, base detail, the canonical purchase-order panel, two fictional line items, exact totals, valid canonical validation, and tenant isolation. The final local closeout change converts the intentionally absent upload-linked processing-status subresource from a generic access-scope warning into a neutral technical-preview state. The protected API continues returning its concealed `404`; only the optional presentation changes.

## Delivered Capability

- A canonical purchase-order contract covering identity, parties, dates, currency, totals, line items, terms, source lineage, validation, and extraction warnings.
- Deterministic classification and extraction from machine-readable text and structural table evidence.
- `Decimal` arithmetic for line, subtotal, tax, and total validation with explicit tolerance and fixed-point serialization.
- A fictional, non-confidential `doc-002` fixture using `document_type=purchase_order`.
- Tenant-scoped GET endpoints for the base document, lifecycle history, validation, matching, and canonical purchase-order result.
- A FlowSync document filter, normal detail route, canonical PO panel, validation summaries, two-line-item table, and read-only lifecycle presentation.
- A neutral optional state when upload-linked processing status is absent in the technical preview.

## Controlled Local Acceptance Document

The controlled real PDF remains in the ignored `.local-uat-input/` boundary and is never committed, copied into fixtures, persisted, uploaded, logged, or included in build output. It was read locally with debug persistence disabled and a no-op telemetry sink. Closeout evidence records only bounded facts: machine-readable input, six extracted rows, successful line/subtotal/tax/total reconciliation, and deliberately unresolved fields. No raw text, names, identifiers, barcodes, descriptions, terms, or individual commercial values were recorded.

## Synthetic Hosted Fixture Strategy

Hosted UAT does not process or store a document. The base record, lifecycle events, validation/matching summaries, and canonical purchase-order result are deterministic fictional fixtures. The fixture namespace is `tenant-uat`; API authorization remains based on the active Supabase membership UUID. Only the UAT read-only provider may translate the authoritative Supabase tenant slug `flowsync-uat` to that synthetic namespace.

The mapping is not accepted from request headers, does not replace the UUID permission decision, and is not installed in ordinary, composed, pilot, or production providers. Other tenants and nonexistent documents remain concealed.

## Tenant-Context Incidents Resolved

1. `doc-002` initially used the demonstration tenant rather than the hosted UAT fixture namespace.
2. Hosted authentication returned the authoritative tenant UUID, while the in-memory fixture used a synthetic string namespace.
3. The first bounded alias used the tenant display name, but Supabase defines the stable identity as a separate required slug.
4. The final implementation selects, validates, and propagates the authoritative slug while retaining UUID authorization and limiting fixture translation to UAT read-only composition.

No Supabase user, membership, key, RLS policy, CORS rule, or Vercel variable was changed to resolve these incidents.

## Optional Processing-Status Finding

The lower **Current processing status** panel requests `GET /api/v1/documents/doc-002/processing-status`. That endpoint belongs to the upload-progress boundary, whose hosted provider is intentionally empty because uploads and processing activation are not part of v0.22. It correctly returns `404 document_processing_status_not_found` for `doc-002`.

The document lifecycle endpoint is separate: `GET /api/v1/documents/doc-002/processing` returns two fictional read-only events. Because the base document is already authorized before the optional panel mounts, FlowSync now maps only the panel's not-found state to **Processing status is not available in this technical preview.** Required base-document 401/403/404 handling and tenant concealment are unchanged.

## Hosted Verification Evidence

| Surface | Expected closeout result |
|---|---|
| Frontend root | UAT / Technical Preview loads |
| `/health` and `/api/v1/health` | `200`, read-only foundation healthy |
| `/api/v1/session` | Authenticated owner session |
| `/api/v1/documents` | `200`, includes `doc-002` |
| `?document_type=purchase_order` | `200`, returns `doc-002` |
| `/documents/doc-002` | Normal detail route loads |
| `/api/v1/documents/doc-002` | `200`, `purchase_order` |
| `/api/v1/documents/doc-002/purchase-order` | `200`, canonical fictional result |
| `/api/v1/documents/doc-002/processing-status` | Protected `404`; neutral optional UI state |
| `/api/v1/documents/doc-002/processing` | `200`, two lifecycle events |
| Validation and matching endpoints | `200`, tenant-scoped summaries |
| Wrong tenant and nonexistent document | Concealed by regression tests |

Do not capture tokens, credentials, emails, keys, or full session objects during owner smoke verification.

## Security and Privacy Posture

- Hosted data is synthetic and non-confidential.
- The controlled local document remains private, ignored, and untracked.
- Supabase membership UUID remains authorization authority.
- The tenant slug is selected from the RLS-constrained membership relation, not a browser header.
- Required protected resources preserve fail-closed and concealed behavior.
- No raw PDF, extracted text, local path, secret, token, or privileged key is returned by the demonstration API.
- The milestone remains read-only and adds no product mutation capability.

## Known Limitations

- Machine-readable PDFs only.
- Deterministic layout coverage only; supplier layouts outside the supported rules may warn or fail.
- No hosted upload, document persistence, or object storage.
- No OCR or LLM extraction.
- No queues, workers, background processing, or scheduled jobs.
- Read-only UAT / Technical Preview with synthetic, non-confidential hosted data only.
- Vercel and Supabase free-tier limits, cold starts, pauses, quotas, and retention constraints apply.
- The frontend favicon is missing.
- The frontend bundle remains above Vite's advisory size threshold.
- No production SLA, monitoring/on-call commitment, recovery guarantee, or backup commitment.

## Rollback

The last owner-verified hosted application commit before the local closeout presentation change is `ccca2af`. If the neutral optional-state change causes a regression, redeploy that immutable commit. Rollback must not mutate Supabase identity, tenant membership, RLS, keys, CORS, or Vercel variables.

## Release Recommendation

- Commit: `docs(document-intelligence): close v0.22 purchase-order demonstration`
- Annotated tag: `v0.22-deterministic-purchase-order-demo`
- Tag message: `v0.22 Deterministic Purchase-Order Demonstration (UAT / Technical Preview; read-only)`

The owner should tag the reviewed closeout commit, not `ccca2af`, so the tag contains this final record and the neutral optional-state presentation.

## Owner Commands After Approval

Run from the repository root only after reviewing the complete diff and verification results:

```powershell
$tagName = 'v0.22-deterministic-purchase-order-demo'
$expectedParent = 'ccca2aff66bdb335a5ada4b6f87ad945b61141df'

git status --short --branch
git diff --check
if (git tag --list $tagName) { throw "Local tag already exists: $tagName" }
if (git ls-remote --tags origin "refs/tags/$tagName" "refs/tags/$tagName^{}") { throw "Remote tag already exists: $tagName" }

git add -- CHANGELOG.md TECHNICAL_DEBT.md docs/README.md docs/ROADMAP.md docs/implementation/V0_22_PURCHASE_ORDER_DEMONSTRATION_PLAN.md docs/implementation/V0_22_PURCHASE_ORDER_DEMONSTRATION_CLOSEOUT.md docs/releases/v0.22-deterministic-purchase-order-demonstration.md apps/flowsync-document-intelligence/src/components/ProcessingStatusPanel.tsx apps/flowsync-document-intelligence/scripts/tests/purchase-order-core.test.mjs tests/api/document_intelligence/test_purchase_order_demo.py
git diff --cached --check
git diff --cached --name-only
git commit -m "docs(document-intelligence): close v0.22 purchase-order demonstration"

if ((git rev-parse HEAD^) -ne $expectedParent) { throw 'Unexpected v0.22 closeout parent' }
$tagTarget = git rev-parse HEAD
git push origin platform/intelligent-document-processing
git tag -a $tagName $tagTarget -m "v0.22 Deterministic Purchase-Order Demonstration (UAT / Technical Preview; read-only)"
git show --no-patch --decorate $tagName
git push origin "refs/tags/$tagName"
```

Do not create a GitHub release unless separately approved.

## Recommended Next Milestone

Plan v0.23 as a governed deterministic layout-coverage and accuracy-corpus milestone using additional synthetic purchase-order layouts, explicit expected-field matrices, and measurable extraction/validation acceptance criteria. Keep OCR, probabilistic extraction, persistence, hosted upload, workers, and production activation behind separate design, privacy, security, and operational approval.
