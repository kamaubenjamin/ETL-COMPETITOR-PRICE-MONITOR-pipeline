"""Deterministic local data provider for the Streamlit operator console."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.review_runtime.contracts import (
    ControlledValue,
    FieldCorrection,
    ReviewAuditEvent,
    ReviewCase,
    ReviewerDecision,
)
from src.review_runtime.reprocess import ReprocessPlan


Record = dict[str, Any]
PROVIDER_MODES = ("local_preview", "api_preview")
DEFAULT_PROVIDER_MODE = "local_preview"

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

_WORKFLOW_RUNS: tuple[Record, ...] = (
    {"run_id": "RUN-8807", "workflow_name": "Invoice Standard", "status": "completed", "started_at": "2026-07-11 09:15 UTC", "duration": "00:02:14"},
    {"run_id": "RUN-8808", "workflow_name": "Purchase Order Standard", "status": "review_required", "started_at": "2026-07-11 09:18 UTC", "duration": "00:01:42"},
    {"run_id": "RUN-8809", "workflow_name": "Statement Reconciliation", "status": "completed", "started_at": "2026-07-11 09:21 UTC", "duration": "00:00:36"},
    {"run_id": "RUN-8810", "workflow_name": "Receipt Standard", "status": "failed", "started_at": "2026-07-11 09:24 UTC", "duration": "00:00:08"},
)


def _review_runtime_samples() -> tuple[
    tuple[ReviewCase, ...],
    tuple[FieldCorrection, ...],
    tuple[ReviewerDecision, ...],
    tuple[ReviewAuditEvent, ...],
    tuple[ReprocessPlan, ...],
]:
    cases = (
        ReviewCase("REV-2198", "transforms", "validate_data", "DOC-1042", "resolved", "validation_failure", "normal", "2026-07-11T09:10:00+00:00", "2026-07-11T09:17:00+00:00", 4, assigned_reviewer_id="reviewer-003"),
        ReviewCase("REV-2199", "matching", "matching", "DOC-1046", "corrected", "duplicate_detection", "normal", "2026-07-11T09:12:00+00:00", "2026-07-11T09:28:00+00:00", 3, assigned_reviewer_id="reviewer-002"),
        ReviewCase("REV-2201", "matching", "matching", "DOC-1043", "in_review", "matching_ambiguity", "high", "2026-07-11T09:20:00+00:00", "2026-07-11T09:31:00+00:00", 2, assigned_reviewer_id="reviewer-001"),
        ReviewCase("REV-2202", "document", "parsed", "DOC-1045", "review_required", "invalid_data", "critical", "2026-07-11T09:24:00+00:00", "2026-07-11T09:24:00+00:00", 1),
        ReviewCase("REV-2204", "transforms", "validate_data", "DOC-1044", "reprocess_requested", "corrected_fields", "high", "2026-07-11T09:25:00+00:00", "2026-07-11T09:34:00+00:00", 4, assigned_reviewer_id="reviewer-004"),
    )
    corrections = (
        FieldCorrection("COR-1001", "REV-2199", "supplier.reference", ControlledValue("string", "corrected-reference"), "corrected_fields", "reviewer-002", "2026-07-11T09:27:00+00:00", "matching", "matching", "DOC-1046"),
        FieldCorrection("COR-1002", "REV-2204", "account.currency", ControlledValue("string", "KES"), "corrected_fields", "reviewer-004", "2026-07-11T09:32:00+00:00", "transforms", "validate_data", "DOC-1044"),
    )
    decisions = (
        ReviewerDecision("DEC-1001", "REV-2198", "approve", "reviewer-003", "2026-07-11T09:16:00+00:00", 3, "IDEM-DEC-1001", reason_code="validation_confirmed"),
        ReviewerDecision("DEC-1002", "REV-2199", "correct", "reviewer-002", "2026-07-11T09:28:00+00:00", 2, "IDEM-DEC-1002", reason_code="corrected_fields", correction_ids=("COR-1001",)),
        ReviewerDecision("DEC-1004", "REV-2204", "request_reprocess", "reviewer-004", "2026-07-11T09:33:00+00:00", 3, "IDEM-DEC-1004", reason_code="corrected_fields", reprocess_request_id="REQ-1004"),
    )
    audit_events = (
        ReviewAuditEvent("EVT-2001", "REV-2201", "review_assigned", "reviewer-001", "2026-07-11T09:31:12+00:00", "review_required", "in_review", {"reason_code": "matching_ambiguity"}, sequence=2, case_version=2),
        ReviewAuditEvent("EVT-2002", "REV-2199", "correction_recorded", "reviewer-002", "2026-07-11T09:28:00+00:00", "in_review", "corrected", {"field_count": 1, "reason_code": "corrected_fields"}, sequence=3, case_version=3),
        ReviewAuditEvent("EVT-2003", "REV-2204", "reprocess_plan_created", "reviewer-004", "2026-07-11T09:34:00+00:00", "reprocess_requested", "reprocess_requested", {"invalidated_count": 1, "retained_count": 1, "requested_from_stage": "validate_data", "requested_target_stage": "transform", "dry_run": True}, sequence=5, case_version=4),
    )
    plans = (
        ReprocessPlan("PLAN-1004", "REV-2204", "validate_data", "transform", ("ART-1044-VALIDATED",), ("ART-1044-PARSED",), "corrected_fields", "reviewer-004", "2026-07-11T09:34:00+00:00", {"dry_run": True}),
    )
    return cases, corrections, decisions, audit_events, plans

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
        cases, corrections, decisions, _, plans = _review_runtime_samples()
        correction_counts = {
            case.review_case_id: sum(item.review_case_id == case.review_case_id for item in corrections)
            for case in cases
        }
        decision_by_case = {item.review_case_id: item for item in decisions}
        planned_cases = {item.review_case_id for item in plans}
        rows = []
        for case in cases:
            decision = decision_by_case.get(case.review_case_id)
            rows.append(
                {
                    "review_case_id": case.review_case_id,
                    "document_id": case.source_artifact_id,
                    "reason_code": decision.reason_code if decision and decision.reason_code else case.reason_code,
                    "priority": case.priority.value,
                    "status": case.status.value,
                    "assigned_reviewer": case.assigned_reviewer_id or "Unassigned",
                    "correction_count": correction_counts[case.review_case_id],
                    "decision": decision.decision.value if decision else "pending",
                    "reprocess_state": "planned" if case.review_case_id in planned_cases else (
                        "requested" if case.status.value == "reprocess_requested" else "not_requested"
                    ),
                }
            )
        return [row for row in rows if row["status"] == status] if status else rows

    def workflow_runs(self, *, workflow_name: str | None = None) -> list[Record]:
        rows = _copy(_WORKFLOW_RUNS)
        return [row for row in rows if row["workflow_name"] == workflow_name] if workflow_name else rows

    def audit_events(self) -> list[Record]:
        _, _, _, review_events, _ = _review_runtime_samples()
        rows = _copy(_AUDIT_EVENTS)
        rows.extend(
            {
                "timestamp": event.occurred_at,
                "event_type": event.event_type,
                "actor": event.actor_id,
                "safe_metadata": (
                    f"case={event.review_case_id}; status={event.new_status.value}; "
                    f"sequence={event.sequence}"
                ),
                "source_runtime": "review",
            }
            for event in review_events
        )
        return sorted(rows, key=lambda row: (row["timestamp"], row["event_type"]), reverse=True)

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
