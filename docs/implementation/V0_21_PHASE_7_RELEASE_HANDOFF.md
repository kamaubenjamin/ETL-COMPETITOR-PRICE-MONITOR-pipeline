# v0.21 Phase 7 Release Handoff

**Milestone:** v0.21 Zero-Budget Vercel + Supabase UAT  
**Phase:** 7 - Closure and Tag  
**Status:** Locally prepared; owner approval required for commit, push, and tag

## Final v0.21 State

Phase 6 hosted verification is complete at `28dea72`. The stable frontend and API expose a read-only UAT / Technical Preview for synthetic, non-confidential data. Supabase sign-in, active owner membership resolution, asymmetric JWT verification, fixed permissions, strict CORS, protected session bootstrap, Firefox browser fetch, and the protected empty Documents listing are verified.

Hosted endpoints:

- Frontend: `https://flowsync-document-intelligence-uat.vercel.app`
- API: `https://flowsync-document-intelligence-api.vercel.app`

The final verified hosted application code is `e4b497e`. Phase 7 changes release governance and documentation only.

## Tag Target Recommendation

Create one owner-approved documentation commit containing the Phase 7 release notes, changelog, debt/status alignment, indexes, ADR status, and this handoff. Tag that new commit—not the pre-closure `28dea72` parent—so the release tag contains its own final release record.

Recommended annotated tag: `v0.21-zero-budget-hosted-uat`.

Because this task is not authorized to commit, the final tag-target hash does not yet exist. The owner must capture and verify the exact `HEAD` hash immediately after the approved documentation commit and tag that immutable hash explicitly.

## Owner Checklist

- [ ] Review the Phase 7 diff and confirm it contains documentation/release-governance changes only.
- [ ] Confirm the branch is `platform/intelligent-document-processing` and tracks its origin without divergence.
- [ ] Confirm `v0.21-zero-budget-hosted-uat` does not exist locally or on the remote.
- [ ] Approve and create the documentation commit with the recommended message.
- [ ] Capture the resulting full commit hash and verify its parent includes Phase 6 closeout `28dea72`.
- [ ] Push the branch and confirm the remote branch points to the captured hash.
- [ ] Create the annotated tag against that exact hash and inspect it before pushing.
- [ ] Push only the named tag after final approval.
- [ ] Do not create a GitHub release unless separately approved.
- [ ] Rotate or revoke the temporary privileged Supabase secret key used during diagnosis; do not place its value in chat, Git, reports, frontend variables, or build output.

## Exact Owner Commands After Approval

Run these from the repository root only after approving the Phase 7 diff. The parent check deliberately prevents tagging an unexpected history.

```powershell
$tagName = 'v0.21-zero-budget-hosted-uat'
$phase6Commit = '28dea723b1fec2d06f26f21d95eb2b6c1b80ea20'

git status --short --branch
git diff --check
if (git tag --list $tagName) { throw "Local tag already exists: $tagName" }
if (git ls-remote --tags origin "refs/tags/$tagName" "refs/tags/$tagName^{}") { throw "Remote tag already exists: $tagName" }

git add -- CHANGELOG.md TECHNICAL_DEBT.md docs/README.md docs/ROADMAP.md docs/adr/ADR-026-zero-budget-vercel-supabase-uat.md docs/architecture/README.md docs/architecture/ZERO_BUDGET_UAT_DEPLOYMENT_V1_IMPLEMENTATION_PLAN.md docs/implementation/V0_21_PHASE_6_HOSTED_UAT_CLOSEOUT.md docs/implementation/V0_21_PHASE_7_RELEASE_HANDOFF.md docs/releases/v0.21-zero-budget-hosted-uat.md
git diff --cached --check
git diff --cached --name-only
git commit -m "docs(uat): prepare v0.21 phase 7 release closure"

$tagTarget = git rev-parse HEAD
if ((git rev-parse HEAD^) -ne $phase6Commit) { throw 'Unexpected Phase 7 commit parent' }
git push origin platform/intelligent-document-processing
$remoteBranch = git ls-remote origin refs/heads/platform/intelligent-document-processing
$remoteHead = ($remoteBranch -split '\s+')[0]
if ($remoteHead -ne $tagTarget) { throw 'Remote branch does not match the approved tag target' }

git tag -a $tagName $tagTarget -m "v0.21 Zero-Budget Hosted UAT (UAT / Technical Preview; read-only)"
git show --no-patch --decorate $tagName
git push origin "refs/tags/$tagName"
```

Do not create a GitHub release unless the owner separately approves it.

## Security Cleanup Reminder

The temporary `SUPABASE_SECRET_KEY` used for bounded diagnosis remains an owner-operated rotation item. No automatic rotation, deletion, Supabase mutation, or Vercel configuration change is authorized here. Public Supabase configuration remains intentionally browser-visible; privileged values must remain server-only and untracked.

## Rollback Reference

The hosted application remains verified at `e4b497e`. If the documentation commit needs correction, revert or supersede that documentation commit without redeploying. If an application rollback is separately required, select the verified Vercel deployment for `e4b497e`; preserve CORS and do not mutate Supabase users, memberships, roles, keys, or schema as an automatic rollback step.

## Next Milestone Proposal

Begin with **synthetic document demonstration planning**. Define the demonstration outcome, synthetic fixtures, non-confidential data policy, UX path, read/write boundaries, and explicit approval gates before implementation.

Hosted uploads, object storage, document persistence, OCR, LLM extraction, queues/workers, processing jobs, and all write operations remain deferred. Planning does not authorize activation.

## Invariants To Preserve

- Keep UAT / Technical Preview labeling visible.
- Permit only synthetic, non-confidential data.
- Keep the hosted application read-only until a separately approved activation milestone.
- Keep tenant identity and permission authority in FastAPI, not the browser.
- Keep the Supabase secret/service-role class out of FlowSync and Git.
- Preserve strict exact-origin CORS and genuine 401/403 fail-closed behavior.
- Treat process-local state as ephemeral and free-tier operation as best-effort without a production SLA.
