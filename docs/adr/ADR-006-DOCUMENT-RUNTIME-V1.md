# Status
Accepted

# Context
Document Runtime is the foundation of the Intelligent Document Processing Platform. It must provide a reliable first layer that ingests raw documents, extracts structure, and produces normalized document artifacts for downstream runtimes.

# Decision
Document Runtime v1 is defined as the first runtime layer responsible for raw document ingestion, parsing, normalization, metadata enrichment, and state management. It outputs a normalized document model with structured sections, tables, field values, and provenance metadata.

# Consequences
Benefits:
- Establishes a clear boundary between raw document input and entity extraction.
- Enables deterministic upstream processing for later runtimes.
- Centralizes document normalization and metadata handling.

Tradeoffs:
- Early-stage implementation may rely on heuristics rather than exhaustive parsing.
- Does not include entity-level extraction or master data matching.

Future implications:
- Future versions should formalize the internal document model and add richer parser adapters for additional document types.

# Purpose of Document Runtime
Document Runtime is responsible for ingesting raw source documents, extracting structural content, normalizing text, and raising document-level metadata for downstream consumption.

# Responsibilities
- Accept raw document inputs and source metadata
- Parse document structure into sections, tables, and blocks
- Normalize text fields and document metadata
- Attach provenance and source lineage information
- Emit a normalized internal document model for next-stage consumption

# Inputs
- Raw document files (PDF, image, text, HTML)
- Source metadata such as origin, document type, and ingestion timestamp
- Ingestion configuration and parser rules

# Outputs
- Normalized document model
- Parsed sections and tables
- Document metadata and validation flags
- Provenance information for source text and parsed fields

# Internal document model
The Document Runtime internal model includes:
- `NormalizedDocument`: top-level document artifact
- `ParsedSection`: logical sections of the document
- `ParsedTable`: tabular data extracted from document visuals or text
- `FieldValue`: extracted key/value pairs and normalized text values
- `Provenance`: source location and confidence metadata for each artifact

# Document lifecycle
1. Ingest raw document and metadata.
2. Execute document parsing and structure extraction.
3. Normalize extracted content and annotate metadata.
4. Generate normalized document output.
5. Pass normalized document artifact to downstream runtimes.

# Document states
- `raw`: received but not yet processed
- `parsed`: structure extracted, but not normalized
- `normalized`: text and fields normalized
- `validated`: document-level checks completed
- `error`: document parsing or normalization failed

# Normalization strategy
- Normalize whitespace, punctuation, and case
- Canonicalize currency symbols and date formats
- Standardize labels and document field names
- Preserve provenance while normalizing values

# Metadata handling
- Capture source metadata such as file path, ingestion timestamp, and document type
- Track parsing status, confidence indicators, and error details
- Record field-level provenance for downstream auditability

# Error handling strategy
- Fail document processing with structured error metadata when parsing or normalization fails
- Preserve a `document_state` of `error` for diagnostics
- Allow workflow-level handling of failed document artifacts

# Runtime boundaries
- Upstream: raw document sources and ingestion adapters
- Downstream: Entity Runtime and Workflow Runtime
- Document Runtime must not perform entity extraction, matching, or ERP operations

# Dependencies
- No internal runtime dependencies for core parsing behavior
- May depend on shared parser utilities and normalization helpers

# Non-goals
- Entity extraction
- Master data matching
- Human review workflows
- ERP synchronization

# Tradeoffs
- Choosing a dedicated document runtime simplifies downstream contracts but defers entity extraction complexity to Entity Runtime.
- Early heuristic parsing enables progress but may require future rework for edge-case documents.

# Future evolution
- Add document-type-specific parser adapters
- Support richer document schemas and table detection
- Improve error categorization and recovery
- Add formal document validation against input schemas
