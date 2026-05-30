# Entity Runtime v1 Architecture

## Purpose
Entity Runtime v1 provides deterministic extraction of structured business entities from Document Runtime output. It converts parsed document content into immutable entity contracts that can be consumed by workflow stages for comparison, reporting, and downstream transformation.

## Runtime Boundaries
- **Document Runtime**: produces an `IngestionPipelineResult` containing a normalized document, parsing sections, tables, and validation metadata.
- **Entity Runtime**: consumes the `IngestionPipelineResult` and produces an `EntitySet` containing extracted entities.
- **Workflow Runtime**: executes a stage-based pipeline including `entity_extract` and uses the `EntitySet` for downstream stages.

## Contracts
Entity Runtime v1 defines immutable typed contracts in `src/entity_runtime/contracts/`:
- `SourceLineage`: provenance metadata linking extracted entities to source document location.
- `DocumentReference`: document header fields such as invoice number, purchase order, dates, currency.
- `DocumentFinancials`: financial totals such as subtotal, tax, grand total, net total.
- `Supplier`: supplier/vendor contact information.
- `Customer`: buyer/customer contact information.
- `LineItem`: product/service line item details, including quantity, price, SKU.
- `EntitySet`: the top-level immutable container for extracted entities.

## Extraction Lifecycle
1. A workflow stage receives `IngestionPipelineResult` from Document Runtime.
2. `EntityExtractionEngine.extract()` delegates extraction tasks to `src/entity_runtime/extraction/EntityExtractor`.
3. The extractor uses parsed sections and OCR/text content to build entity objects.
4. Extracted entities are assembled into an `EntitySet`.
5. Extraction metadata and confidence are attached before output.

## Validation Architecture
The `src/entity_runtime/validation/EntityValidator` module validates the extracted `EntitySet`:
- ensures at least one entity was extracted
- checks presence of reference numbers for document headers
- verifies financial totals when financial entities exist
- reports structured validation results as metadata

## Normalization Architecture
The `src/entity_runtime/normalization/TextNormalizer` module provides deterministic text normalization:
- whitespace normalization
- label normalization
- currency canonicalization

## Confidence Architecture
The `src/entity_runtime/confidence/ConfidenceScorer` module computes an aggregate confidence score by averaging entity confidence values. This score is attached to the final `EntitySet` as `extraction_confidence`.

## Workflow Integration
`Entity Runtime` integrates with Workflow Runtime through the `entity_extract` stage defined in `src/workflow_runtime/operations/entity_extract_stage.py`.
- The stage instantiates `EntityExtractionEngine`
- It returns a `StageResult` containing the extracted `EntitySet`
- The stage is registered in `STAGE_REGISTRY` and validated as a supported workflow stage type

## Future Evolution
Future versions may add:
- richer normalization and entity reconciliation rules
- a dedicated table-to-entity schema mapper
- configurable extraction strategies per document type
- entity-level confidence calibration
- support for additional document types beyond invoices, purchase orders, and receipts
