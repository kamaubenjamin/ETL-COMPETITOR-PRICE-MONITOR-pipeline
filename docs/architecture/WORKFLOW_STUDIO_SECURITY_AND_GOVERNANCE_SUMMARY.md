# Workflow Studio Security And Governance Summary

## Permission Catalog

- `workflow:read`: read definitions, versions, audit projections, and the operation catalog.
- `workflow:run`: existing runtime execution semantics only; no Studio management authority.
- `workflow:create`: create a governed definition and initial draft.
- `workflow:edit`: create/replace drafts, validate drafts, and submit drafts.
- `workflow:test`: request bounded safe preview/test behavior.
- `workflow:approve`: approve an eligible tested version.
- `workflow:publish`: publish an eligible approved immutable definition.
- `workflow:deactivate`: deactivate the active governed publication.
- `workflow:admin`: archive governed definitions.

`workflow:read` and `workflow:run` do not grant create, edit, test, approve, publish, deactivate, or administrative authority.

## Role Decisions

| Role | Workflow Studio authority |
|---|---|
| Viewer | `workflow:read` |
| Reviewer | No Workflow Studio management rights |
| Operations manager | `workflow:create`, `workflow:edit`, `workflow:test`, `workflow:approve`, `workflow:deactivate` |
| Tenant admin | Operations-manager rights plus `workflow:publish`, `workflow:admin` |
| Platform admin | Full permission catalog |
| Service account | No Workflow Studio management rights |

Role catalogs may include unrelated document/runtime permissions; the table states only Workflow Studio management decisions.

## Tenant And Actor Authority

- The API derives tenant and actor attribution from trusted authentication/security context.
- Requests cannot choose or override tenant ID, actor ID, approval identity, or publication authority.
- Client-supplied authority fields are rejected by bounded request allowlists.
- Resource lookup is tenant-narrowed before disclosure; cross-tenant details are concealed.
- Mutation authorization fails closed and remains API-authoritative.
- FlowSync permission labels are optional build-time usability hints. Hiding or enabling a control never grants authority.

## Governance Controls

- Only drafts accept content replacement, guarded by optimistic `expected_revision`.
- Validation, test evidence, approval, and publication are explicit transitions.
- Published/superseded/inactive/archived history is immutable.
- Rollback produces a new draft/version; no history is overwritten.
- Deactivation has no automatic fallback activation.
- Archive preserves history; no hard deletion exists.
- Audit intents use bounded fixed event types and safe reason/status values.

## Preview And Data Safety

Preview inputs are safe fixtures or bounded inline samples. No production runtime implementation is connected by default. Preview cannot mutate production data, Document State, master data, export, ERP, alerts, staging, or workflow publication. Outputs, traces, issues, and exceptions are bounded or replaced with fixed safe projections, with protected values redacted.

## Publication Governance

**Published definition governance only; production execution activation is not enabled.** Publication records immutable governed state. Runtime binding, scheduler activation, environment/UAT promotion, durable audit, and production activation require separate future policy and implementation review.

