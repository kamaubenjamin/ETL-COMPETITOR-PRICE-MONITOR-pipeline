import json

import pytest

from src.review_runtime import (
    ControlledValue,
    ControlledValueType,
    CorrectionOperation,
    FieldCorrection,
    ReprocessRequest,
    ReviewAuditEvent,
    ReviewCase,
    ReviewCaseType,
    ReviewPriority,
    ReviewRuntimeError,
    ReviewerDecision,
    ReviewerDecisionType,
    ReviewStatus,
    SourceRuntime,
)
from src.review_runtime.exceptions import InvalidReviewStateError, ReviewItemNotFoundError

NOW = "2026-07-10T10:00:00+00:00"


def review_case_payload() -> dict:
    return {
        "contract_version": 1,
        "review_case_id": "case-001",
        "case_type": "validation_failure",
        "source_runtime": "transforms",
        "source_stage": "validate_data",
        "source_artifact_id": "artifact-001",
        "source_artifact_version": "version-3",
        "parent_review_case_id": None,
        "correlation_id": "corr-001",
        "assigned_reviewer_id": None,
        "status": "review_required",
        "reason_code": "required_field_missing",
        "priority": "high",
        "created_at": NOW,
        "updated_at": NOW,
        "version": 1,
        "metadata": {"issue_count": 2, "confidence_bucket": "low"},
    }


def test_required_enums_are_complete():
    assert {item.value for item in ReviewStatus} == {
        "review_required", "in_review", "corrected", "approved", "rejected",
        "skipped", "reprocess_requested", "resolved",
    }
    assert {item.value for item in ReviewerDecisionType} == {
        "approve", "reject", "correct", "skip", "request_reprocess",
    }


def test_review_case_round_trips_as_json_compatible_dict():
    case = ReviewCase.from_dict(review_case_payload())

    assert case.review_case_id == "case-001"
    assert case.status is ReviewStatus.REVIEW_REQUIRED
    assert case.case_type is ReviewCaseType.VALIDATION_FAILURE
    assert case.priority is ReviewPriority.HIGH
    assert case.source_runtime is SourceRuntime.TRANSFORMS
    assert ReviewCase.from_dict(case.to_dict()) == case
    json.dumps(case.to_dict())


@pytest.mark.parametrize(
    "case_type",
    [
        "validation_failure", "extraction_uncertainty", "matching_ambiguity",
        "duplicate_detection", "blocked_customer", "invalid_data", "export_error",
        "manual_escalation",
    ],
)
def test_review_case_accepts_every_trigger_type(case_type):
    payload = review_case_payload()
    payload["case_type"] = case_type
    assert ReviewCase.from_dict(payload).case_type.value == case_type


def test_legacy_pending_status_maps_to_review_required():
    payload = review_case_payload()
    payload["status"] = "pending"

    case = ReviewCase.from_dict(payload)

    assert case.status is ReviewStatus.REVIEW_REQUIRED
    assert case.to_dict()["status"] == "review_required"


def test_review_case_rejects_unknown_fields_without_exposing_values():
    payload = review_case_payload()
    payload["unexpected"] = "private-customer-value"

    with pytest.raises(ReviewRuntimeError) as caught:
        ReviewCase.from_dict(payload)

    assert caught.value.code == "unknown_field"
    assert caught.value.path == "$.unexpected"
    assert "private-customer-value" not in str(caught.value)


@pytest.mark.parametrize(
    "metadata",
    [
        {"raw_document": "full private document"},
        {"rows": [{"customer": "Private Name"}]},
        {"issue_count": [1, 2]},
    ],
)
def test_review_case_rejects_unsafe_or_nonscalar_metadata(metadata):
    payload = review_case_payload()
    payload["metadata"] = metadata

    with pytest.raises(ReviewRuntimeError) as caught:
        ReviewCase.from_dict(payload)

    message = str(caught.value)
    assert "full private document" not in message
    assert "Private Name" not in message


def test_metadata_is_defensively_copied_and_immutable():
    metadata = {"issue_count": 1}
    payload = review_case_payload()
    payload["metadata"] = metadata
    case = ReviewCase.from_dict(payload)
    metadata["issue_count"] = 99

    assert case.metadata["issue_count"] == 1
    with pytest.raises(TypeError):
        case.metadata["issue_count"] = 2


def test_field_correction_supports_controlled_value_and_lineage():
    correction = FieldCorrection(
        correction_id="correction-001",
        review_case_id="case-001",
        field_path="line_items[0].unit_price",
        operation=CorrectionOperation.REPLACE,
        old_value_reference="sha256:abc123",
        new_value=ControlledValue(ControlledValueType.NUMBER, 125.5),
        reason_code="price_verified",
        corrected_by="reviewer-007",
        created_at=NOW,
        source_runtime="entity",
        source_stage="entity_extract",
        source_artifact_id="entity-set-4",
        source_artifact_version="version-2",
        metadata={"correlation_id": "corr-001"},
    )

    serialized = correction.to_dict()
    assert serialized["field_path"] == "line_items[0].unit_price"
    assert serialized["old_value_reference"] == "sha256:abc123"
    assert serialized["new_value"] == {"value_type": "number", "value": 125.5}
    assert FieldCorrection.from_dict(serialized) == correction
    json.dumps(serialized)


def test_field_correction_old_value_reference_is_optional():
    correction = FieldCorrection(
        correction_id="correction-002",
        review_case_id="case-001",
        field_path="customer.status",
        new_value=ControlledValue("string", "active"),
        reason_code="status_verified",
        corrected_by="reviewer-007",
        created_at=NOW,
        source_runtime="entity",
        source_stage="entity_extract",
        source_artifact_id="entity-set-4",
    )
    assert correction.old_value_reference is None


def test_set_null_requires_null_controlled_value():
    kwargs = {
        "correction_id": "correction-003",
        "review_case_id": "case-001",
        "field_path": "customer.middle_name",
        "operation": "set_null",
        "reason_code": "value_removed",
        "corrected_by": "reviewer-007",
        "created_at": NOW,
        "source_runtime": "entity",
        "source_stage": "entity_extract",
        "source_artifact_id": "entity-set-4",
    }
    with pytest.raises(ReviewRuntimeError):
        FieldCorrection(new_value=ControlledValue("string", "sensitive"), **kwargs)

    correction = FieldCorrection(new_value=ControlledValue("null", None), **kwargs)
    assert correction.operation is CorrectionOperation.SET_NULL


@pytest.mark.parametrize("field_path", ["", "customer..name", "rows[*].value", "../secret"])
def test_field_correction_rejects_invalid_field_paths(field_path):
    with pytest.raises(ReviewRuntimeError) as caught:
        FieldCorrection(
            correction_id="correction-004",
            review_case_id="case-001",
            field_path=field_path,
            new_value=ControlledValue("string", "private-value"),
            reason_code="field_verified",
            corrected_by="reviewer-007",
            created_at=NOW,
            source_runtime="entity",
            source_stage="entity_extract",
            source_artifact_id="entity-set-4",
        )
    assert "private-value" not in str(caught.value)


@pytest.mark.parametrize("decision", ["approve", "reject", "correct", "skip", "request_reprocess"])
def test_reviewer_decision_supports_required_decisions(decision):
    kwargs = {}
    if decision == "correct":
        kwargs["correction_ids"] = ("correction-001",)
    if decision == "skip":
        kwargs["reason_code"] = "review_deferred"
    if decision == "request_reprocess":
        kwargs["reprocess_request_id"] = "request-001"

    record = ReviewerDecision(
        decision_id=f"decision-{decision}",
        review_case_id="case-001",
        decision=decision,
        reviewer_id="reviewer-007",
        occurred_at=NOW,
        expected_case_version=2,
        idempotency_key=f"idem-{decision}",
        **kwargs,
    )

    assert record.decision.value == decision
    assert ReviewerDecision.from_dict(record.to_dict()) == record
    json.dumps(record.to_dict())


def test_decision_preconditions_are_validated():
    base = {
        "decision_id": "decision-001",
        "review_case_id": "case-001",
        "reviewer_id": "reviewer-007",
        "occurred_at": NOW,
        "expected_case_version": 2,
        "idempotency_key": "idem-001",
    }
    with pytest.raises(ReviewRuntimeError):
        ReviewerDecision(decision="correct", **base)
    with pytest.raises(ReviewRuntimeError):
        ReviewerDecision(decision="skip", **base)
    with pytest.raises(ReviewRuntimeError):
        ReviewerDecision(decision="request_reprocess", **base)


def test_audit_event_round_trip_contains_safe_status_lineage():
    event = ReviewAuditEvent(
        event_id="event-001",
        review_case_id="case-001",
        event_type="case.assigned",
        actor_id="reviewer-007",
        occurred_at=NOW,
        previous_status="review_required",
        new_status="in_review",
        sequence=2,
        case_version=2,
        metadata={"correlation_id": "corr-001", "reason_code": "manual_assignment"},
    )
    assert ReviewAuditEvent.from_dict(event.to_dict()) == event
    json.dumps(event.to_dict())


def test_reprocess_request_round_trip_is_declarative():
    request = ReprocessRequest(
        request_id="request-001",
        review_case_id="case-001",
        requested_from_stage="validate_data",
        requested_target_stage="entity_extract",
        reason_code="corrected_fields",
        requested_by="reviewer-007",
        created_at=NOW,
        expected_case_version=3,
        idempotency_key="idem-reprocess-001",
        metadata={"attempt": 1, "workflow_id": "workflow-001"},
    )
    assert ReprocessRequest.from_dict(request.to_dict()) == request
    json.dumps(request.to_dict())


def test_contract_errors_are_json_compatible_and_privacy_safe():
    payload = review_case_payload()
    payload["status"] = "private-sensitive-status-value"
    with pytest.raises(ReviewRuntimeError) as caught:
        ReviewCase.from_dict(payload)

    assert caught.value.to_dict() == {
        "code": "invalid_value",
        "path": "$.status",
        "message": "Unsupported status code.",
    }
    assert "private-sensitive-status-value" not in str(caught.value)
    json.dumps(caught.value.to_dict())


def test_legacy_exception_classes_remain_compatible():
    assert isinstance(ReviewItemNotFoundError("missing"), ReviewRuntimeError)
    assert isinstance(InvalidReviewStateError("invalid"), ReviewRuntimeError)
