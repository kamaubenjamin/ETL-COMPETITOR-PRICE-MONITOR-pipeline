"""Deterministic local data provider for the Streamlit operator console."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


Record = dict[str, Any]

DOCUMENT_STATUSES = (
    "received", "ingested", "classified", "parsed", "extracted", "transformed",
    "validated", "matched", "review_required", "approved", "export_ready",
    "exported", "failed",
)

REVIEW_STATUSES = (
    "review_required", "in_review", "corrected", "approved", "rejected",
    "skipped", "reprocess_requested", "resolved",
)

_DOCUMENTS: tuple[Record, ...] = (
    {"document_id": "DOC-1042", "filename": "acme_invoice_1042.pdf", "document_type": "Invoice", "status": "export_ready", "confidence": 0.98, "current_stage": "export"},
    {"document_id": "DOC-1043", "filename": "northwind_po_771.pdf", "document_type": "Purchase Order", "status": "review_required", "confidence": 0.71, "current_stage": "matching"},
    {"document_id": "DOC-1044", "filename": "contoso_statement_jun.pdf", "document_type": "Bank Statement", "status": "validated", "confidence": 0.94, "current_stage": "validation"},
    {"document_id": "DOC-1045", "filename": "fabrikam_receipt_88.png", "document_type": "Receipt", "status": "failed", "confidence": 0.42, "current_stage": "parsing"},
    {"document_id": "DOC-1046", "filename": "tailspin_invoice_309.pdf", "document_type": "Invoice", "status": "matched", "confidence": 0.91, "current_stage": "matching"},
    {"document_id": "DOC-1047", "filename": "wideworld_po_551.pdf", "document_type": "Purchase Order", "status": "received", "confidence": 0.00, "current_stage": "intake"},
    {"document_id": "DOC-1048", "filename": "adatum_invoice_204.pdf", "document_type": "Invoice", "status": "exported", "confidence": 0.97, "current_stage": "complete"},
)

_PROCESSING: tuple[Record, ...] = (
    {"document_id": "DOC-1043", "stage": "matching", "status": "review_required", "started_at": "2026-07-11 09:18 UTC", "elapsed": "00:01:42"},
    {"document_id": "DOC-1044", "stage": "validation", "status": "validated", "started_at": "2026-07-11 09:21 UTC", "elapsed": "00:00:36"},
    {"document_id": "DOC-1045", "stage": "parsing", "status": "failed", "started_at": "2026-07-11 09:24 UTC", "elapsed": "00:00:08"},
    {"document_id": "DOC-1046", "stage": "matching", "status": "matched", "started_at": "2026-07-11 09:26 UTC", "elapsed": "00:00:51"},
    {"document_id": "DOC-1047", "stage": "intake", "status": "received", "started_at": "2026-07-11 09:30 UTC", "elapsed": "00:00:02"},
)

_VALIDATION_ISSUES: tuple[Record, ...] = (
    {"document_id": "DOC-1043", "severity": "error", "field": "supplier.tax_id", "rule": "required", "message": "Required field is missing."},
    {"document_id": "DOC-1043", "severity": "warning", "field": "invoice.total", "rule": "max", "message": "Value exceeds the configured review threshold."},
    {"document_id": "DOC-1044", "severity": "warning", "field": "account.currency", "rule": "allowed_values", "message": "Currency requires operator confirmation."},
    {"document_id": "DOC-1045", "severity": "error", "field": "document.structure", "rule": "required", "message": "Expected tabular structure was not found."},
)

_MATCHING_RESULTS: tuple[Record, ...] = (
    {"document_id": "DOC-1043", "entity": "Northwind Traders", "candidate_match": "Northwind Trading Ltd", "confidence": 0.74, "match_status": "ambiguous"},
    {"document_id": "DOC-1043", "entity": "Northwind Traders", "candidate_match": "Northwind Wholesale", "confidence": 0.68, "match_status": "candidate"},
    {"document_id": "DOC-1044", "entity": "Contoso Bank", "candidate_match": "Contoso Bank PLC", "confidence": 0.93, "match_status": "matched"},
    {"document_id": "DOC-1046", "entity": "Tailspin Toys", "candidate_match": "Tailspin Toys Ltd", "confidence": 0.96, "match_status": "matched"},
)

_REVIEW_CASES: tuple[Record, ...] = (
    {"review_case_id": "REV-2198", "document_id": "DOC-1042", "reason": "validation_failure", "priority": "normal", "status": "resolved", "assigned_reviewer": "A. Kamau"},
    {"review_case_id": "REV-2199", "document_id": "DOC-1046", "reason": "duplicate_detection", "priority": "normal", "status": "corrected", "assigned_reviewer": "J. Njeri"},
    {"review_case_id": "REV-2201", "document_id": "DOC-1043", "reason": "matching_ambiguity", "priority": "high", "status": "in_review", "assigned_reviewer": "M. Otieno"},
    {"review_case_id": "REV-2202", "document_id": "DOC-1045", "reason": "invalid_data", "priority": "urgent", "status": "review_required", "assigned_reviewer": "Unassigned"},
)

_WORKFLOW_RUNS: tuple[Record, ...] = (
    {"run_id": "RUN-8807", "workflow_name": "Invoice Standard", "status": "completed", "started_at": "2026-07-11 09:15 UTC", "duration": "00:02:14"},
    {"run_id": "RUN-8808", "workflow_name": "Purchase Order Standard", "status": "review_required", "started_at": "2026-07-11 09:18 UTC", "duration": "00:01:42"},
    {"run_id": "RUN-8809", "workflow_name": "Statement Reconciliation", "status": "completed", "started_at": "2026-07-11 09:21 UTC", "duration": "00:00:36"},
    {"run_id": "RUN-8810", "workflow_name": "Receipt Standard", "status": "failed", "started_at": "2026-07-11 09:24 UTC", "duration": "00:00:08"},
)

_AUDIT_EVENTS: tuple[Record, ...] = (
    {"timestamp": "2026-07-11 09:31:12 UTC", "event_type": "review_assigned", "actor": "M. Otieno", "safe_metadata": "case=REV-2201; priority=high"},
    {"timestamp": "2026-07-11 09:29:48 UTC", "event_type": "validation_completed", "actor": "transform_runtime", "safe_metadata": "document=DOC-1044; issues=1"},
    {"timestamp": "2026-07-11 09:27:03 UTC", "event_type": "matching_completed", "actor": "matching_runtime", "safe_metadata": "document=DOC-1046; candidates=1"},
    {"timestamp": "2026-07-11 09:24:19 UTC", "event_type": "stage_failed", "actor": "workflow_runtime", "safe_metadata": "document=DOC-1045; stage=parsing"},
    {"timestamp": "2026-07-11 09:20:06 UTC", "event_type": "review_created", "actor": "workflow_runtime", "safe_metadata": "case=REV-2201; reason=matching_ambiguity"},
)


def _copy(records: tuple[Record, ...]) -> list[Record]:
    return deepcopy(list(records))


class LocalOperatorConsoleProvider:
    """Read-only provider boundary for deterministic operator-console fixtures."""

    def documents(self, *, document_type: str | None = None, status: str | None = None) -> list[Record]:
        rows = _copy(_DOCUMENTS)
        if document_type:
            rows = [row for row in rows if row["document_type"] == document_type]
        if status:
            rows = [row for row in rows if row["status"] == status]
        return rows

    def processing_statuses(self, *, status: str | None = None) -> list[Record]:
        rows = _copy(_PROCESSING)
        return [row for row in rows if row["status"] == status] if status else rows

    def validation_issues(self) -> list[Record]:
        return _copy(_VALIDATION_ISSUES)

    def matching_results(self) -> list[Record]:
        return _copy(_MATCHING_RESULTS)

    def review_cases(self, *, status: str | None = None) -> list[Record]:
        rows = _copy(_REVIEW_CASES)
        return [row for row in rows if row["status"] == status] if status else rows

    def workflow_runs(self, *, workflow_name: str | None = None) -> list[Record]:
        rows = _copy(_WORKFLOW_RUNS)
        return [row for row in rows if row["workflow_name"] == workflow_name] if workflow_name else rows

    def audit_events(self) -> list[Record]:
        return _copy(_AUDIT_EVENTS)

    def summary_metrics(self, *, documents: list[Record] | None = None) -> Record:
        rows = deepcopy(documents) if documents is not None else self.documents()
        processed = {"validated", "matched", "review_required", "approved", "export_ready", "exported"}
        return {
            "documents_received": len(rows),
            "processed": sum(row["status"] in processed for row in rows),
            "review_required": sum(row["status"] == "review_required" for row in rows),
            "failed": sum(row["status"] == "failed" for row in rows),
            "export_ready": sum(row["status"] == "export_ready" for row in rows),
        }

