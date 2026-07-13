from dataclasses import FrozenInstanceError, fields
import json

import pytest

from src.workflow_runtime.query_facade.read_models import (
    AuditEventSummary,
    CorrectionHistorySummary,
    DocumentDetail,
    DocumentInboxItem,
    MatchingResult,
    ProcessingStatus,
    ReprocessPlanSummary,
    ReviewCaseSummary,
    ValidationIssue,
    WorkflowRunSummary,
)


TIMESTAMP = "2026-07-01T08:00:00+00:00"


def _models():
    return [
        DocumentInboxItem("doc-001", "invoice.pdf", "invoice", "validated", 0.98, "validate_data", TIMESTAMP),
        DocumentDetail("doc-001", "invoice.pdf", "invoice", "validated", 0.98, "validate_data", TIMESTAMP, TIMESTAMP, "invoice_processing"),
        ProcessingStatus("doc-001", "validate_data", "succeeded", TIMESTAMP),
        ValidationIssue("issue-001", "doc-001", "warning", "supplier_id", "required", "required", "Field requires review."),
        MatchingResult("match-001", "doc-001", "supplier", "supplier-001", 0.9, "matched"),
        ReviewCaseSummary("review-001", "doc-001", "matching_ambiguity", "high", "in_review", "reviewer-01", 1, None, "not_requested", TIMESTAMP, TIMESTAMP),
        CorrectionHistorySummary("correction-001", "review-001", "supplier_id", "replace", "operator_verified", "reviewer-01", TIMESTAMP, "matching"),
        ReprocessPlanSummary("plan-001", "review-001", "matching", "validate_data", 1, 2, "operator_verified", "reviewer-01", TIMESTAMP),
        WorkflowRunSummary("run-001", "invoice_processing", "succeeded", TIMESTAMP, TIMESTAMP, 4000, 3, 3, 0),
        AuditEventSummary("audit-001", "review_case_created", "system", TIMESTAMP, "doc-001", "review-001", {"reason_code": "matching_ambiguity", "count": 1}),
    ]


def test_all_read_models_serialize_to_plain_json_dicts():
    for model in _models():
        payload = model.to_dict()
        assert isinstance(payload, dict)
        json.dumps(payload)


def test_read_models_are_frozen_and_have_ordering_fields():
    for model in _models():
        assert model.ORDERING.fields
        assert model.ORDERING.fields[-1].endswith("id") or model.ORDERING.fields[-1] == "stage"
    with pytest.raises(FrozenInstanceError):
        _models()[0].status = "failed"


def test_privacy_sensitive_contract_fields_do_not_exist():
    unsafe = {"raw_document", "raw_rows", "raw_value", "old_value", "new_value", "artifact_payload", "stack_trace", "storage_path"}
    for model in _models():
        assert not ({item.name for item in fields(model)} & unsafe)
        serialized = json.dumps(model.to_dict()).lower()
        assert "corrected-reference" not in serialized
        assert "traceback" not in serialized


def test_audit_metadata_rejects_non_json_nested_values_and_unsafe_keys():
    with pytest.raises(ValueError, match="JSON scalar"):
        AuditEventSummary("audit-001", "review_case_created", "system", TIMESTAMP, metadata={"safe": {"nested": True}})
    with pytest.raises(ValueError, match="allowlisted"):
        AuditEventSummary("audit-001", "review_case_created", "system", TIMESTAMP, metadata={"raw_value": "private"})


def test_read_models_enforce_confidence_timestamp_counts_and_known_codes():
    with pytest.raises(ValueError, match="confidence"):
        DocumentInboxItem("doc-001", "invoice.pdf", "invoice", "validated", float("nan"), "validate_data", TIMESTAMP)
    with pytest.raises(ValueError, match="timezone"):
        ProcessingStatus("doc-001", "validate_data", "succeeded", "2026-07-01T08:00:00")
    with pytest.raises(ValueError, match="inconsistent"):
        WorkflowRunSummary("run-001", "invoice", "succeeded", TIMESTAMP, TIMESTAMP, 1, 1, 1, 1)
    with pytest.raises(ValueError, match="dry_run"):
        ReprocessPlanSummary("plan-001", "review-001", "matching", "validate_data", 1, 1, "reason", "actor", TIMESTAMP, "execute")


def test_serialized_correction_and_reprocess_models_contain_summaries_only():
    correction = _models()[6].to_dict()
    reprocess = _models()[7].to_dict()
    assert set(correction) == {"correction_id", "review_case_id", "field_path", "operation", "reason_code", "actor_id", "occurred_at", "source_stage"}
    assert set(reprocess) == {"plan_id", "review_case_id", "requested_from_stage", "requested_target_stage", "invalidated_artifact_count", "retained_artifact_count", "reason_code", "requested_by", "created_at", "mode"}
