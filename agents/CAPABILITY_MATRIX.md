# Agent Capability Matrix
Date: 2026-06-01

This matrix maps repository agents to their primary capabilities, allowed actions, and recommended ownership for milestone planning.

| Agent | Governance & DOD | Architecture & ADRs | Runtime Implementation | Testing | Performance | Documentation | CI/PR Ops | Code Changes | Boundary Enforcement | Escalation Owner | Suggested v0.5 Owner |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ETL Platform Governance | Primary | Support | Support (governance) | Verify | Review | Primary (docs & DOD) | Allowed (test/contract CI) | No (docs only) | Enforce DOD | Repository Owner | Support |
| Platform Architect | Support | Primary | Support / Owner (design) | Define acceptance | Review | Primary (architecture) | Recommend only | No direct (propose PR) | Primary (design-time) | Repository Owner | Primary |
| Runtime Engineer | Support | Support | Primary | Primary | Primary | Support (implementation docs) | Allowed (tests & CI) | Yes (via PRs) | Follow architect rules | Platform Architect / Governance | Implementer |
| Release Manager | Support | Support | Support | Verify | Verify | Support (release docs) | Primary (release CI) | No | Follow DOD | Repository Owner | N/A |

Notes:
- "Primary" indicates ownership responsibility. "Support" indicates an assisting role.
- CI/PR Ops: agents may create branches/PRs when explicitly requested; otherwise they should commit docs directly when permitted by governance.

Recommendation for v0.5 Runtime Hardening:
- Primary owner: `Platform Architect` — owns planning, architecture changes, and risk analysis.
- Implementation owner: `Runtime Engineer` — executes implementation, tests, and performance work.
- Governance oversight: `ETL Platform Governance` — enforces DOD, documentation, and release readiness.

End of file.