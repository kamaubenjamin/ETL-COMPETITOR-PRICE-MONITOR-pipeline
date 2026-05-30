# Status
Accepted

# Context
The platform requires an external interface for document ingestion, workflow execution, and status queries. API Runtime must define a stable boundary for client integrations while remaining decoupled from core runtime internals.

# Decision
API Runtime v1 is defined as the external platform interface layer. It owns request and response modeling, versioning strategy, authentication assumptions, error handling, and runtime ownership for external clients.

# Consequences
Benefits:
- Creates a clear public contract for external integrations.
- Separates internal runtime execution from client-facing API concerns.
- Enables future API versioning and backward compatibility.

Tradeoffs:
- Adds an integration layer that requires coordination with workflow and document runtimes.
- Does not itself implement workflow logic; it delegates to runtime components.

Future implications:
- API Runtime can evolve into a gateway for monitoring, telemetry, and extensibility.

# API Runtime responsibilities
- Accept external requests for ingestion, processing, status, and results
- Validate client payloads and version-specific schemas
- Forward requests to Workflow Runtime and retrieve results
- Return structured responses and error information

# External platform interface
- Exposes HTTP/REST or equivalent endpoint contracts
- Defines request payloads for document ingestion and processing initiation
- Supports response payloads with workflow status, result summaries, and error details

# Request/response model
- Requests contain structured JSON describing the document source, metadata, and desired processing flow
- Responses include request identifiers, processing state, outcome data, and error metadata
- Versioning is encoded in the API path or headers to support future evolution

# Runtime ownership
- Owned by the platform integration layer
- Responsible for maintaining API contracts and external-facing behavior
- Delegates business processing to Workflow Runtime and lower runtimes

# Authentication assumptions
- Assumes token-based authentication for v1 (API keys, bearer tokens, or similar)
- Does not prescribe a full authorization engine in v1
- Stores authentication configuration outside runtime internals

# Versioning strategy
- Use explicit API versioning in request paths or headers
- Maintain backward compatibility for existing clients
- Increment major version on breaking contract changes

# Error handling model
- Return structured error payloads with codes, messages, and details
- Distinguish client errors from server/runtime errors
- Propagate workflow and runtime error context when safe

# Runtime boundaries
- Upstream: external clients and systems
- Downstream: Workflow Runtime and, indirectly, Document and Entity runtimes
- API Runtime must not directly access Document Runtime internals or master data stores

# Tradeoffs
- Delegating execution allows API Runtime to remain lightweight, but increases dependence on workflow runtimes.
- Keeping authentication assumptions simple enables faster delivery but requires future hardening.

# Future evolution
- Add formal API gateway capabilities and rate limiting
- Support additional integration patterns such as event/webhook callbacks
- Introduce API discovery and schema validation tooling
- Expand authentication to OAuth/OpenID Connect and RBAC
