# v0.22 Purchase-Order Demonstration Plan

**Milestone:** v0.22 Controlled Purchase-Order Demonstration
**Status:** Complete; owner closeout commit and tag pending
**Prepared:** 2026-07-21

## Goal

Prove the smallest safe, deterministic path from a machine-readable purchase-order PDF to a canonical, validated purchase-order projection and a read-only FlowSync presentation.

## Scope

Reuse the existing PDF loader, ingestion pipeline, structural parser, lineage conventions, validation boundary, read-only API provider, response envelope, and Documents UI. Add only the missing purchase-order-specific canonical contract, deterministic extraction and validation service, a fictional synthetic demonstration record, a read-only result route, and a compact detail presentation.

Uploads, cloud storage, OCR, LLM extraction, queues, workers, database persistence, mutations, approvals, exports, and navigation redesign remain out of scope.

## Source-Document Handling Rules

- The controlled local acceptance document remains under `.local-uat-input/`, ignored and untracked.
- It is read only during a local acceptance run and is never copied into fixtures, tracked output, build output, logs, telemetry, or cloud storage.
- Acceptance reporting is limited to field presence, line-item count, validation status, warning count, and boolean reconciliation results.
- Names, references, barcodes, line descriptions, commercial terms, raw text, and individual monetary values from the controlled document are not printed or persisted.
- Automated tests and the committed UI/API demonstration use clearly fictional synthetic data only.

## Architecture Flow

`local PDF -> existing PdfDocumentLoader -> existing IngestionPipeline -> existing DocumentParser -> purchase-order classifier/extractor -> canonical PurchaseOrder -> deterministic validator -> safe serializer`

The committed demonstration continues from a synthetic canonical fixture:

`synthetic PurchaseOrder -> deterministic validator -> local read-only provider -> GET result endpoint -> FlowSync document detail`

## Existing Components Reused

- `PdfDocumentLoader` for machine-readable PDF text extraction.
- `DocumentIngestionEngine` and `IngestionPipeline` for loader selection, normalization, structural parsing, structural validation, and run identity.
- `DocumentParser` and canonical structural tables as extraction inputs.
- `SourceLineage` semantics, adapted to a safe projection that never exposes a local path.
- Local/facade provider selection, API authorization, response envelopes, and GET-only frontend client.
- Documents and document-detail pages, tables, status components, and the FlowSync visual system.

## Missing Capability Identified

The current classifier labels a PDF by container type, while the generic entity extractor is invoice-oriented, uses binary floating point for amounts, and does not provide a complete canonical purchase-order result or purchase-order arithmetic validation. The smallest missing capability is a document-type adapter that classifies purchase-order content, extracts its canonical fields and table rows with exact decimals, and returns structured validation findings.

## Canonical Schema

The canonical result contains `document_type`, `purchase_order_number`, `buyer`, `supplier`, `ship_to`, `order_date`, `delivery_date`, `currency`, `subtotal`, `tax`, `total`, `line_items`, `terms`, `source_lineage`, `validation`, and `extraction_warnings`.

Each line item contains `item_code`, `barcode`, `description`, `unit`, `quantity`, `unit_price`, `net_amount`, and row lineage. Monetary values and quantities are `Decimal` internally and fixed-point strings at the JSON boundary.

## Deterministic Extraction Rules

- Classify as `purchase_order` only when purchase-order labels and supporting order/table signals are present.
- Match bounded label variants for the PO reference, order date, delivery date, buyer, supplier, ship-to, currency, totals, and terms.
- Detect line-item headers by semantic aliases rather than fixed column positions.
- Rejoin continuation rows into the preceding description when numeric line fields are absent.
- Normalize dates to ISO dates, currencies to supported ISO codes, and numeric tokens to exact decimals.
- Return `null` and a structured warning when a value cannot be established safely; never invent a value.

## Validation Rules

The validator checks the required PO number, parseable dates, delivery chronology, presence of line items, positive quantities, non-negative unit prices, line arithmetic, subtotal reconciliation, tax/total reconciliation, duplicate item codes, and supported currency. Arithmetic uses `Decimal` and an explicit `0.01` tolerance.

## Synthetic Fixture Strategy

One fictional purchase order with invented organizations, identifiers, barcodes, products, terms, dates, and monetary values is constructed through the same canonical contract and validator. It is the only result exposed by the committed demonstration boundary. Focused malformed variants exercise warnings and errors without relying on the controlled document.

## UI/API Demonstration Boundary

Add a GET-only canonical-result subresource for a document already visible through the existing provider. The local provider returns the fictional canonical result; providers without a result return `404`. FlowSync renders the result within document detail, with no edit, upload, approval, persistence, or export action.

## Security and Privacy Notes

- No endpoint serves PDFs or raw extracted text.
- The API projection uses a synthetic source label and bounded metadata, not a filesystem path.
- The controlled acceptance document is not required at runtime or build time.
- Existing API authorization and tenant scoping remain authoritative.
- Secret/confidential scans and tracked-file checks are part of completion verification.

## Known Limitations

- Machine-readable PDFs only; scanned images require a separately approved OCR milestone.
- Deterministic layout rules support common label and text-table patterns, not every supplier layout.
- No persistence or hosted ingestion; the hosted demonstration remains synthetic and read-only.
- Ambiguous fields are warnings for operator review, not inferred values.

## Definition of Done

- [x] Canonical exact-decimal contract, classifier, extractor, validator, and safe serializer implemented.
- [x] Fictional synthetic API result available through a GET-only route.
- [x] FlowSync detail view renders header fields, totals, line items, validation, warnings, and safe lineage.
- [x] Focused backend and frontend contract/rendering tests pass.
- [x] Controlled local acceptance document produces six line items and reconciled expected totals without disclosure or persistence.
- [x] Repository, privacy, diff, frontend, and production-build checks pass.
- [x] No commit, push, deploy, or tag is performed.

## Local Acceptance-Test Results

The controlled local acceptance document was read directly from its ignored location with debug persistence disabled and a no-op telemetry sink. It contained machine-readable text, classified as `purchase_order`, produced six line items, passed every line arithmetic check, reconciled line net amounts to subtotal, reconciled subtotal plus VAT to total, and matched all three owner-supplied expected totals.

The extracted text did not provide a safely recognizable currency, buyer, or ship-to association. Those fields were not invented: buyer and ship-to are extraction warnings, and currency remains a validation error. The overall local result is therefore `invalid` while its dates, required reference, rows, and all monetary reconciliation checks pass. No raw text, identifiers, names, barcodes, descriptions, terms, individual values, or result artifact was printed or persisted.

## Next Milestone Recommendations

After owner review, broaden deterministic layout coverage using additional synthetic fixtures and establish a governed accuracy corpus. OCR, persistence, hosted uploads, and probabilistic extraction should remain separately approved milestones.

Closeout: `docs/implementation/V0_22_PURCHASE_ORDER_DEMONSTRATION_CLOSEOUT.md`.
