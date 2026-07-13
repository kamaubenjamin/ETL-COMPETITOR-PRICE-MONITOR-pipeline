"""API-owned deterministic preview records with defensive read methods."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_DOCUMENTS = (
    {"document_id": "doc-001", "filename": "invoice_001.pdf", "document_type": "invoice", "status": "validated", "confidence": 0.98, "current_stage": "validate_data", "received_at": "2026-07-01T08:00:00+00:00"},
    {"document_id": "doc-002", "filename": "purchase_order_002.pdf", "document_type": "purchase_order", "status": "review_required", "confidence": 0.72, "current_stage": "matching", "received_at": "2026-07-01T08:05:00+00:00"},
    {"document_id": "doc-003", "filename": "receipt_003.pdf", "document_type": "receipt", "status": "export_ready", "confidence": 0.94, "current_stage": "export", "received_at": "2026-07-01T08:10:00+00:00"},
)

_PROCESSING = {
    "doc-001": ({"stage": "ingest", "status": "succeeded", "occurred_at": "2026-07-01T08:00:01+00:00"}, {"stage": "validate_data", "status": "succeeded", "occurred_at": "2026-07-01T08:00:04+00:00"}),
    "doc-002": ({"stage": "ingest", "status": "succeeded", "occurred_at": "2026-07-01T08:05:01+00:00"}, {"stage": "matching", "status": "review_required", "occurred_at": "2026-07-01T08:05:05+00:00"}),
    "doc-003": ({"stage": "ingest", "status": "succeeded", "occurred_at": "2026-07-01T08:10:01+00:00"}, {"stage": "export", "status": "ready", "occurred_at": "2026-07-01T08:10:06+00:00"}),
}

_VALIDATION = {
    "doc-001": (),
    "doc-002": ({"issue_id": "issue-001", "severity": "error", "field": "supplier_id", "rule_id": "required_supplier", "code": "required", "message": "Required field is missing."},),
    "doc-003": ({"issue_id": "issue-002", "severity": "warning", "field": "receipt_date", "rule_id": "date_range", "code": "range", "message": "Field requires operator confirmation."},),
}

_MATCHING = {
    "doc-001": ({"match_id": "match-001", "entity_type": "supplier", "candidate_id": "supplier-100", "confidence": 0.97, "status": "matched"},),
    "doc-002": ({"match_id": "match-002", "entity_type": "supplier", "candidate_id": "supplier-200", "confidence": 0.72, "status": "ambiguous"},),
    "doc-003": (),
}

_REVIEW_CASES = (
    {"review_case_id": "review-001", "document_id": "doc-002", "reason_code": "matching_ambiguity", "priority": "high", "status": "in_review", "assigned_reviewer": "reviewer-01", "correction_count": 1, "decision_code": None, "reprocess_state": "not_requested", "created_at": "2026-07-01T08:06:00+00:00"},
    {"review_case_id": "review-002", "document_id": "doc-003", "reason_code": "validation_warning", "priority": "normal", "status": "resolved", "assigned_reviewer": "reviewer-02", "correction_count": 0, "decision_code": "approve", "reprocess_state": "not_requested", "created_at": "2026-07-01T08:11:00+00:00"},
)

_CORRECTIONS = {
    "review-001": ({"correction_id": "correction-001", "review_case_id": "review-001", "field_path": "supplier_id", "operation": "replace", "reason_code": "operator_verified", "actor_id": "reviewer-01", "occurred_at": "2026-07-01T08:08:00+00:00", "source_stage": "matching"},),
    "review-002": (),
}

_REPROCESS_PLANS = (
    {"plan_id": "plan-001", "review_case_id": "review-001", "requested_from_stage": "matching", "requested_target_stage": "validate_data", "invalidated_artifact_count": 1, "retained_artifact_count": 2, "reason_code": "operator_verified", "requested_by": "reviewer-01", "created_at": "2026-07-01T08:09:00+00:00", "mode": "dry_run"},
)

_WORKFLOW_RUNS = (
    {"run_id": "run-001", "workflow_name": "invoice_processing", "status": "succeeded", "started_at": "2026-07-01T08:00:00+00:00", "duration_ms": 4200},
    {"run_id": "run-002", "workflow_name": "purchase_order_processing", "status": "running", "started_at": "2026-07-01T08:05:00+00:00", "duration_ms": None},
    {"run_id": "run-003", "workflow_name": "receipt_processing", "status": "failed", "started_at": "2026-07-01T08:10:00+00:00", "duration_ms": 6100},
)

_AUDIT_EVENTS = (
    {"event_id": "audit-001", "event_type": "document_received", "actor_id": "system", "document_id": "doc-001", "review_case_id": None, "occurred_at": "2026-07-01T08:00:00+00:00", "metadata": {"document_type": "invoice"}},
    {"event_id": "audit-002", "event_type": "review_case_created", "actor_id": "system", "document_id": "doc-002", "review_case_id": "review-001", "occurred_at": "2026-07-01T08:06:00+00:00", "metadata": {"reason_code": "matching_ambiguity"}},
    {"event_id": "audit-003", "event_type": "reprocess_plan_created", "actor_id": "reviewer-01", "document_id": "doc-002", "review_case_id": "review-001", "occurred_at": "2026-07-01T08:09:00+00:00", "metadata": {"plan_count": 1, "mode": "dry_run"}},
)


class LocalDocumentIntelligenceProvider:
    """Read-only local provider; every public result is a deep copy."""

    @staticmethod
    def _copy(records: Any) -> Any:
        return deepcopy(records)

    def list_documents(self, *, status: str | None = None, document_type: str | None = None) -> list[dict[str, Any]]:
        rows = [row for row in _DOCUMENTS if (status is None or row["status"] == status) and (document_type is None or row["document_type"] == document_type)]
        return self._copy(rows)

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        return self._copy(next((row for row in _DOCUMENTS if row["document_id"] == document_id), None))

    def list_processing(self, document_id: str) -> list[dict[str, Any]]:
        return self._copy(list(_PROCESSING.get(document_id, ())))

    def list_validation(self, document_id: str) -> list[dict[str, Any]]:
        return self._copy(list(_VALIDATION.get(document_id, ())))

    def list_matching(self, document_id: str) -> list[dict[str, Any]]:
        return self._copy(list(_MATCHING.get(document_id, ())))

    def list_review_cases(self, *, status: str | None = None, priority: str | None = None) -> list[dict[str, Any]]:
        rows = [row for row in _REVIEW_CASES if (status is None or row["status"] == status) and (priority is None or row["priority"] == priority)]
        return self._copy(rows)

    def get_review_case(self, review_case_id: str) -> dict[str, Any] | None:
        return self._copy(next((row for row in _REVIEW_CASES if row["review_case_id"] == review_case_id), None))

    def list_corrections(self, review_case_id: str) -> list[dict[str, Any]]:
        return self._copy(list(_CORRECTIONS.get(review_case_id, ())))

    def list_reprocess_plans(self) -> list[dict[str, Any]]:
        return self._copy(list(_REPROCESS_PLANS))

    def list_workflow_runs(self, *, status: str | None = None) -> list[dict[str, Any]]:
        return self._copy([row for row in _WORKFLOW_RUNS if status is None or row["status"] == status])

    def list_audit_events(self, *, event_type: str | None = None) -> list[dict[str, Any]]:
        return self._copy([row for row in _AUDIT_EVENTS if event_type is None or row["event_type"] == event_type])


local_provider = LocalDocumentIntelligenceProvider()
