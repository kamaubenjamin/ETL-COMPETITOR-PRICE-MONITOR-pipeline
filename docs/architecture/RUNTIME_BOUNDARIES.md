# Runtime Boundaries

This document defines runtime boundaries for the Intelligent Document Processing Platform. It documents purpose, responsibilities, inputs, outputs, dependencies, forbidden dependencies, and owned data for each runtime.

## Runtime Interaction Diagram

```
 External Clients
       |
       v
   +------------------+
   |   API Runtime    |
   +------------------+
            |
            v
   +------------------+
   | Workflow Runtime |<---------------------+
   +------------------+                      |
      |      |      |       |                |
      v      v      v       v                |
+-----------+ +-------------+ +-----------+  |
| Document  | |  Entity     | | Matching  |  |
| Runtime   | |  Runtime    | | Runtime   |  |
+-----------+ +-------------+ +-----------+  |
            \      |      /                  |
             \     v     /                   |
              +------------+                  |
              | Review     |                  |
              | Runtime    |                  |
              +------------+                  |
                     ^                         |
                     |                         |
              +------------------+            |
              | Monitoring Runtime|<-----------+
              +------------------+
```

## Document Runtime

Purpose
- Ingest raw source documents and produce normalized document artifacts.

Responsibilities
- Parse document structure into sections, tables, and fields
- Normalize text and metadata
- Track provenance and parsing state
- Emit a normalized document model

Inputs
- Raw documents (PDF, image, text, HTML)
- Source metadata
- Ingestion configuration

Outputs
- Normalized document artifact
- Parsed sections and tables
- Document metadata and processing state

Dependencies
- Shared parser and normalization utilities only

Forbidden Dependencies
- Entity Runtime
- Matching Runtime
- Review Runtime
- API Runtime
- Monitoring Runtime may observe but not depend

Owned Data
- Raw document content
- Document parsing metadata
- Normalized document model
- Document state and provenance

## Workflow Runtime

Purpose
- Orchestrate runtime stages and execute platform workflows.

Responsibilities
- Register and execute runtime stages
- Resolve stage dependencies and data flow
- Manage workflow execution context and artifact handoff

Inputs
- Workflow definitions
- Runtime stage artifacts
- External execution requests from API Runtime

Outputs
- Workflow stage results
- Orchestrated runtime artifacts
- Status and execution metadata

Dependencies
- Document Runtime
- Entity Runtime
- Matching Runtime
- Review Runtime
- API Runtime for external request handling
- Monitoring Runtime for observability

Forbidden Dependencies
- Direct dependency on Document Runtime internals beyond declared inputs
- Circular dependencies between runtimes

Owned Data
- Workflow definitions and stage registry
- Execution metadata
- Runtime artifacts in transit

## Entity Runtime

Purpose
- Convert normalized documents into immutable business entities.

Responsibilities
- Extract structured entities from document output
- Validate and normalize entity data
- Compute extraction confidence
- Emit `EntitySet` artifacts

Inputs
- Normalized document artifacts from Document Runtime

Outputs
- `EntitySet` containing entities like Customer, Supplier, LineItem, Address
- Entity validation metadata

Dependencies
- Document Runtime
- Shared normalization utilities

Forbidden Dependencies
- Matching Runtime
- Review Runtime
- API Runtime

Owned Data
- Entity contracts and extracted entity state
- Entity validation and confidence metadata

## Matching Runtime

Purpose
- Reconcile extracted entities against master data sources.

Responsibilities
- Generate candidate matches
- Apply exact, normalized, fuzzy, and historical strategies
- Compute explainable confidence scores
- Emit match results and audit explanations

Inputs
- `EntitySet` from Entity Runtime
- Candidate master data sources

Outputs
- `MatchSet` containing matched entities and statistics
- Match explanations and confidence metadata

Dependencies
- Entity Runtime
- Workflow Runtime
- Monitoring Runtime

Forbidden Dependencies
- Document Runtime
- API Runtime
- Direct ERP adapters in v1
- Review Runtime for runtime logic

Owned Data
- Match requests, candidates, and results
- Historical match artifacts scoped to a workflow execution

## Review Runtime

Purpose
- Capture human review and correction feedback for low-confidence or unmatched entities.

Responsibilities
- Manage review queues
- Capture correction lifecycle and review metadata
- Emit review completion events

Inputs
- Match results from Matching Runtime
- Workflow stage review triggers

Outputs
- Review task state
- Correction artifacts and feedback metadata
- Review audit trail

Dependencies
- Matching Runtime
- Workflow Runtime
- Monitoring Runtime

Forbidden Dependencies
- Document Runtime
- Entity Runtime
- API Runtime for review logic

Owned Data
- Review tasks and states
- Correction metadata and review history

## API Runtime

Purpose
- Provide the external interface for clients to submit documents, request processing, and query results.

Responsibilities
- Expose request/response contracts
- Validate external payloads
- Forward execution requests to Workflow Runtime
- Respond with structured status and error payloads

Inputs
- External API requests
- Authentication and versioning metadata

Outputs
- API responses
- Request identifiers and status objects
- Error payloads

Dependencies
- Workflow Runtime
- Monitoring Runtime

Forbidden Dependencies
- Entity Runtime
- Matching Runtime
- Review Runtime
- Document Runtime internals

Owned Data
- API contract definitions
- Request and response metadata

## Monitoring Runtime

Purpose
- Observe platform execution and provide telemetry and health information.

Responsibilities
- Collect runtime metrics and logs
- Monitor workflow execution, document processing, and review activity
- Report on platform health and performance

Inputs
- Runtime execution events
- Workflow and stage metadata

Outputs
- Observability artifacts
- Health and status dashboards
- Alerts and diagnostic summaries

Dependencies
- All runtimes as an observer only

Forbidden Dependencies
- Runtime execution logic or control flow

Owned Data
- Performance metrics
- Logging metadata
- Diagnostic context

## Allowed dependency directions
- Data flows from Document Runtime → Entity Runtime → Matching Runtime → Review Runtime
- Control and orchestration flow through Workflow Runtime
- API Runtime delegates to Workflow Runtime only
- Monitoring Runtime observes all runtimes without coupling

## Forbidden coupling
- No cycles between runtimes
- Entity Runtime must not depend on Matching or Review runtimes
- Matching Runtime must not depend on Document Runtime directly
- Review Runtime must not implement document parsing or entity extraction
- API Runtime must not access internal runtime state directly
