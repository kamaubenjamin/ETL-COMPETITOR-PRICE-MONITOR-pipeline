# Codex Operating Guide

Status: Active
Repository: Intelligent Document Processing Platform

## Purpose

This guide defines how to use Codex efficiently and safely in this repository. The preferred AI workflow is:

- ChatGPT Plus for planning, prompt design, architecture reasoning, and milestone decision support.
- Codex for repository inspection, code changes, test execution, documentation updates, and verification.

The goal is narrow scope, minimal token usage, short execution time, and safe repository changes.

## 1. Roles

### ChatGPT Plus

Use ChatGPT Plus for work that benefits from discussion, comparison, and planning before touching the repository.

Responsibilities:

- Milestone planning.
- Prompt design for Codex sessions.
- Architecture reasoning.
- Risk analysis.
- Phase sequencing.
- Definition of Done review.
- Deciding whether the next task should be audit, plan, implementation, verification, or release documentation.

### Codex

Use Codex for work that requires direct repository access.

Responsibilities:

- Repository inspection.
- Targeted code changes.
- Targeted test additions or updates.
- Test execution.
- Documentation updates.
- Verification commands.
- Git status inspection.
- Producing concise summaries of changed files, verification results, and next readiness.

Codex should not independently expand scope beyond the prompt.

## 2. Core Codex Rules

1. One task per session.
2. One phase per session.
3. Review only the listed files first.
4. Avoid broad repository scans unless explicitly requested.
5. Avoid unrelated refactors.
6. Preserve runtime boundaries.
7. Preserve public contracts unless explicitly instructed.
8. Do not commit unless explicitly instructed.
9. Do not push unless explicitly instructed.
10. Stop after producing the requested summary.
11. Never proceed to the next phase automatically.
12. If scope is unclear, ask a short clarification question before editing.

## 3. Standard Codex Prompt Format

Use this structure for most Codex sessions:

```text
Context:
- <short milestone or task context>

Relevant files:
- <specific files or directories>

Task:
- <one task only>

Objectives:
- <specific outcomes>

Constraints:
- <scope boundaries>
- Do not commit.
- Do not push.

Verification commands:
- <targeted commands>

Output required:
- <exact summary headings>

Stop condition:
- Stop after <audit/plan/implementation/tests/docs>.
```

## 4. Token-Efficiency Rules

Use short prompts and rely on repository documents for context.

Rules:

- Reference existing docs instead of repeating project history.
- Ask Codex for summaries, not full file dumps.
- Avoid scanning unrelated runtimes.
- Inspect tests only when the task involves tests.
- Prefer targeted grep/search over reading whole directories.
- Avoid architecture-wide analysis unless explicitly requested.
- List exact files whenever possible.
- Ask for concise status reports.
- Split large milestones into phases.
- Stop after each phase and return to ChatGPT Plus for next-step planning.

## 5. Safe Workflow

Recommended workflow:

1. Plan in ChatGPT Plus.
2. Create one narrow Codex prompt.
3. Run one Codex task.
4. Paste the Codex summary back to ChatGPT Plus.
5. Decide the next step.
6. Run targeted tests in Codex when needed.
7. Commit manually after reviewing changes.
8. Tag manually after milestone close.

Codex should perform repository work. ChatGPT Plus should coordinate the work.

## 6. Standard Templates

### Audit-Only Prompt

```text
Context:
- <brief context>

Relevant files:
- <specific files>

Task:
- Inspect only. Do not modify files.

Objectives:
- Determine current state.
- Identify completed work.
- Identify exact next action.

Constraints:
- No code changes.
- No documentation changes.
- No commits.
- No pushes.

Verification commands:
- git status --short --branch
- <targeted inspection commands>

Output required:
# Current State
# Findings
# Risks
# Exact Next Action

Stop condition:
- Stop after audit summary.
```

### Architecture-Plan Prompt

```text
Context:
- <milestone context>

Relevant files:
- docs/ROADMAP.md
- TECHNICAL_DEBT.md
- docs/architecture/<relevant-doc>.md

Task:
- Create or update the architecture plan only.

Objectives:
- Define problem, scope, architecture, risks, deliverables, and Definition of Done.

Constraints:
- Docs only.
- Do not modify production code.
- Do not modify tests.
- Do not commit.
- Do not push.

Verification commands:
- git status --short

Output required:
# File Created
# Summary
# Follow-Up

Stop condition:
- Stop after architecture plan.
```

### Implementation-Phase Prompt

```text
Context:
- <phase context>

Relevant files:
- <specific plan files>
- <specific source files>
- <specific test files>

Task:
- Implement Phase <N> only.

Objectives:
- <phase-specific objectives>

Constraints:
- No unrelated refactors.
- No public contract changes unless listed.
- No runtime boundary violations.
- Do not commit.
- Do not push.

Verification commands:
- pytest <targeted-tests> -q
- python scripts/verify_boundaries.py

Output required:
# Files Created
# Files Modified
# Tests Added
# Verification Results
# Boundary Results
# Readiness For Next Phase

Stop condition:
- Stop after Phase <N>.
```

### Verification Prompt

```text
Context:
- <what was implemented>

Relevant files:
- <changed files or test directories>

Task:
- Verify only. Do not modify files unless a verification command creates normal caches.

Objectives:
- Run targeted tests.
- Run boundary checks.
- Report failures clearly.

Constraints:
- No code changes.
- No documentation changes.
- No commits.
- No pushes.

Verification commands:
- pytest <targeted-tests> -q
- python scripts/verify_boundaries.py

Output required:
# Verification Results
# Boundary Results
# Failures
# Recommended Next Action

Stop condition:
- Stop after verification.
```

### Documentation/Release Prompt

```text
Context:
- <completed milestone or phase>

Relevant files:
- docs/ROADMAP.md
- TECHNICAL_DEBT.md
- docs/architecture/<milestone-docs>
- docs/adr/<adr-file>

Task:
- Create release documentation only.

Objectives:
- Create summary, handoff, and release notes.
- Update roadmap and technical debt only if requested.

Constraints:
- Docs only.
- No code changes.
- No tests changes.
- Do not commit.
- Do not push.

Verification commands:
- git status --short

Output required:
# Files Created
# Files Modified
# Summary
# Recommended Commit Message

Stop condition:
- Stop after documentation update.
```

### Review-Only Prompt

```text
Context:
- <change or milestone to review>

Relevant files:
- <specific files>

Task:
- Review only. Do not modify files.

Objectives:
- Identify bugs, risks, missing tests, contract issues, and boundary concerns.

Constraints:
- No edits.
- No commits.
- No pushes.

Verification commands:
- <optional read-only commands>

Output required:
# Findings
# Risks
# Missing Tests
# Boundary Concerns
# Recommended Next Action

Stop condition:
- Stop after review.
```

### Bug-Fix Prompt

```text
Context:
- <bug description>

Relevant files:
- <specific failing test or source files>

Task:
- Fix this bug only.

Objectives:
- Make the targeted failing test pass.
- Preserve existing behavior outside the bug.

Constraints:
- No broad refactors.
- No unrelated formatting.
- No public contract changes unless required and explained.
- Do not commit.
- Do not push.

Verification commands:
- pytest <failing-test> -q
- pytest <nearest-regression-tests> -q

Output required:
# Files Modified
# Root Cause
# Fix Summary
# Verification Results
# Remaining Risk

Stop condition:
- Stop after bug fix and verification.
```

## 7. Stop Conditions

Codex must stop after the requested unit of work:

- Stop after audit.
- Stop after plan.
- Stop after implementation.
- Stop after tests.
- Stop after documentation.
- Stop after review.

Codex must never proceed to the next phase automatically.

Examples:

- If asked to inspect, do not implement.
- If asked to plan, do not create code.
- If asked to implement Phase 1, do not start Phase 2.
- If asked to verify, do not fix unless explicitly instructed.
- If asked to create docs, do not update code or tests.

## 8. Forbidden Default Behavior

Unless explicitly requested, Codex must not:

- Perform broad refactors.
- Build UI.
- Change API behavior.
- Add OCR integration.
- Add LLM integration.
- Change unrelated runtimes.
- Add dependencies without justification.
- Modify public contracts.
- Rewrite architecture documents outside the requested files.
- Commit.
- Push.
- Tag.
- Run long, broad, or unrelated test suites.
- Scan the whole repository when targeted files are provided.

## Practical Defaults

When using Codex in this repository, prefer:

- Targeted file reads.
- Targeted `rg` searches.
- Targeted tests.
- Small patches.
- Clear summaries.
- Manual commit and tag control.

End of document.
