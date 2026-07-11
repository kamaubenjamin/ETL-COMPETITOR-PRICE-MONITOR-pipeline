import json

import pytest

from src.review_runtime.contracts import ControlledValue, FieldCorrection, ReviewStatus
from src.review_runtime.errors import (
    ReviewCaseVersionConflictError,
    ReviewCorrectionLineageConflictError,
    ReviewReviewerConflictError,
    ReviewRuntimeError,
)
from src.review_runtime.repositories import InMemoryReviewCaseRepository
from src.review_runtime.services import CorrectionDecisionService, ReviewCaseService

NOW = "2026-07-11T10:00:00+00:00"
ASSIGNED = "2026-07-11T10:05:00+00:00"
ACTION = "2026-07-11T10:10:00+00:00"


class DeterministicIds:
    def __init__(self):
        self.counts = {}

    def __call__(self, prefix):
        count = self.counts.get(prefix, 0) + 1
        self.counts[prefix] = count
        return f"{prefix}-{count:03d}"


def setup_services(*, assign=True):
    repository = InMemoryReviewCaseRepository()
    ids = DeterministicIds()
    case_service = ReviewCaseService(repository, clock=lambda: NOW, id_factory=ids)
    action_service = CorrectionDecisionService(repository, clock=lambda: ACTION, id_factory=ids)
    review_case = case_service.create_case(
        review_case_id="case-001",
        source_runtime="entity",
        source_stage="entity_extract",
        source_artifact_id="entity-set-001",
        source_artifact_version="version-1",
        reason_code="invalid_data",
        priority="high",
        case_type="validation_failure",
        metadata={"issue_count": 2},
    )
    if assign:
        review_case = case_service.mark_in_review(
            review_case.review_case_id,
            reviewer_id="reviewer-001",
            expected_version=1,
            occurred_at=ASSIGNED,
        )
    return repository, case_service, action_service, review_case


def correction_spec(field_path="customer.status", value="active", **overrides):
    spec = {
        "field_path": field_path,
        "new_value": {"value_type": "string", "value": value},
        "reason_code": "field_verified",
        "old_value_reference": "sha256:abc123",
        "metadata": {"correlation_id": "corr-001"},
    }
    spec.update(overrides)
    return spec


def test_submit_single_correction_success_without_status_transition():
    repository, _, service, review_case = setup_services()

    correction = service.submit_correction(
        review_case.review_case_id,
        field_path="customer.status",
        new_value=ControlledValue("string", "active"),
        reason_code="field_verified",
        corrected_by="reviewer-001",
        expected_version=2,
        old_value_reference="sha256:abc123",
        occurred_at=ACTION,
    )

    assert correction.field_path == "customer.status"
    assert correction.source_artifact_id == "entity-set-001"
    assert correction.source_artifact_version == "version-1"
    stored_case = repository.get_case(review_case.review_case_id)
    assert stored_case.status is ReviewStatus.IN_REVIEW
    assert stored_case.version == 3
    assert [event.event_type for event in repository.list_audit_events("case-001")] == [
        "case_created", "status_changed", "correction_submitted",
    ]


def test_submit_correction_validation_failure_is_atomic_and_private():
    repository, _, service, review_case = setup_services()
    audit_before = repository.list_audit_events(review_case.review_case_id)

    with pytest.raises(ReviewRuntimeError) as caught:
        service.submit_correction(
            review_case.review_case_id,
            field_path="customer..status",
            new_value=ControlledValue("string", "private-sensitive-value"),
            reason_code="field_verified",
            corrected_by="reviewer-001",
            expected_version=2,
        )

    assert "private-sensitive-value" not in str(caught.value)
    assert repository.get_case(review_case.review_case_id).version == 2
    assert repository.list_audit_events(review_case.review_case_id) == audit_before
    assert repository.list_corrections(review_case.review_case_id) == ()


def test_submit_multiple_corrections_uses_one_deterministic_batch_event():
    repository, _, service, review_case = setup_services()

    corrections = service.submit_corrections(
        review_case.review_case_id,
        [
            correction_spec("customer.status", "active", correction_id="correction-b"),
            correction_spec("customer.category", "retail", correction_id="correction-a"),
        ],
        corrected_by="reviewer-001",
        expected_version=2,
        occurred_at=ACTION,
    )

    assert [item.correction_id for item in corrections] == ["correction-b", "correction-a"]
    events = repository.list_audit_events(review_case.review_case_id)
    assert events[-1].event_type == "correction_submitted"
    assert events[-1].metadata["field_count"] == 2
    assert repository.get_case(review_case.review_case_id).version == 3


def test_list_corrections_is_deterministically_ordered_and_defensive():
    repository, _, service, review_case = setup_services()
    service.submit_corrections(
        review_case.review_case_id,
        [
            correction_spec("customer.status", "active", correction_id="correction-b"),
            correction_spec("customer.category", "retail", correction_id="correction-a"),
        ],
        corrected_by="reviewer-001",
        expected_version=2,
        occurred_at=ACTION,
    )

    listed = service.list_corrections(review_case.review_case_id)
    assert [item.correction_id for item in listed] == ["correction-a", "correction-b"]
    object.__setattr__(listed[0], "reason_code", "changed_outside_repository")
    assert service.list_corrections(review_case.review_case_id)[0].reason_code == "field_verified"


def test_correction_history_is_append_only_across_submissions():
    _, _, service, review_case = setup_services()
    first = service.submit_correction(
        review_case.review_case_id,
        field_path="customer.status",
        new_value=ControlledValue("string", "active"),
        reason_code="field_verified",
        corrected_by="reviewer-001",
        expected_version=2,
        correction_id="correction-001",
        occurred_at=ACTION,
    )
    second = service.submit_correction(
        review_case.review_case_id,
        field_path="customer.category",
        new_value=ControlledValue("string", "retail"),
        reason_code="field_verified",
        corrected_by="reviewer-001",
        expected_version=3,
        correction_id="correction-002",
        occurred_at="2026-07-11T10:11:00+00:00",
    )

    assert service.list_corrections(review_case.review_case_id) == (first, second)


def test_correction_metadata_safety_and_lineage_mismatch():
    repository, _, service, review_case = setup_services()
    with pytest.raises(ReviewRuntimeError):
        service.submit_correction(
            review_case.review_case_id,
            field_path="customer.status",
            new_value=ControlledValue("string", "active"),
            reason_code="field_verified",
            corrected_by="reviewer-001",
            expected_version=2,
            metadata={"raw_rows": "private row"},
        )
    with pytest.raises(ReviewCorrectionLineageConflictError):
        service.submit_correction(
            review_case.review_case_id,
            field_path="customer.status",
            new_value=ControlledValue("string", "active"),
            reason_code="field_verified",
            corrected_by="reviewer-001",
            expected_version=2,
            source_artifact_id="different-artifact",
        )
    assert repository.get_case(review_case.review_case_id).version == 2
    assert len(repository.list_audit_events(review_case.review_case_id)) == 2


@pytest.mark.parametrize(
    "method,target,extra",
    [
        ("approve_case", ReviewStatus.APPROVED, {}),
        ("reject_case", ReviewStatus.REJECTED, {"reason_code": "invalid_match"}),
        ("skip_case", ReviewStatus.SKIPPED, {"reason_code": "review_deferred"}),
    ],
)
def test_standard_decision_success(method, target, extra):
    repository, _, service, review_case = setup_services()
    updated = getattr(service, method)(
        review_case.review_case_id,
        reviewer_id="reviewer-001",
        expected_version=2,
        occurred_at=ACTION,
        **extra,
    )

    assert updated.status is target
    assert updated.version == 3
    assert len(repository.list_decisions(review_case.review_case_id)) == 1
    assert [event.event_type for event in repository.list_audit_events("case-001")][-2:] == [
        "decision_submitted", "status_changed",
    ]


def test_request_reprocess_records_intent_without_execution():
    repository, _, service, review_case = setup_services()
    updated = service.request_reprocess(
        review_case.review_case_id,
        requested_target_stage="entity_extract",
        reason_code="corrected_fields",
        reviewer_id="reviewer-001",
        expected_version=2,
        request_id="request-001",
        idempotency_key="reprocess-idem-001",
        occurred_at=ACTION,
    )

    assert updated.status is ReviewStatus.REPROCESS_REQUESTED
    requests = repository.list_reprocess_requests(review_case.review_case_id)
    assert len(requests) == 1
    assert requests[0].requested_target_stage == "entity_extract"
    assert [event.event_type for event in repository.list_audit_events("case-001")][-3:] == [
        "decision_submitted", "reprocess_requested", "status_changed",
    ]


def test_correct_case_atomically_records_corrections_decision_and_transition():
    repository, _, service, review_case = setup_services()
    updated = service.correct_case(
        review_case.review_case_id,
        [correction_spec(correction_id="correction-001")],
        reviewer_id="reviewer-001",
        expected_version=2,
        reason_code="fields_corrected",
        decision_id="decision-001",
        idempotency_key="decision-idem-001",
        occurred_at=ACTION,
    )

    assert updated.status is ReviewStatus.CORRECTED
    assert updated.version == 3
    assert len(repository.list_corrections("case-001")) == 1
    assert len(repository.list_decisions("case-001")) == 1
    assert [event.event_type for event in repository.list_audit_events("case-001")][-3:] == [
        "correction_submitted", "decision_submitted", "status_changed",
    ]


def test_correct_decision_can_reference_previously_submitted_correction():
    repository, _, service, review_case = setup_services()
    correction = service.submit_correction(
        review_case.review_case_id,
        field_path="customer.status",
        new_value=ControlledValue("string", "active"),
        reason_code="field_verified",
        corrected_by="reviewer-001",
        expected_version=2,
        occurred_at=ACTION,
    )
    updated = service.submit_decision(
        review_case.review_case_id,
        "correct",
        reviewer_id="reviewer-001",
        expected_version=3,
        reason_code="fields_corrected",
        correction_ids=(correction.correction_id,),
        occurred_at="2026-07-11T10:11:00+00:00",
    )
    assert updated.status is ReviewStatus.CORRECTED
    assert len(repository.list_corrections("case-001")) == 1


def test_invalid_transition_and_version_conflict_append_nothing():
    repository, _, service, review_case = setup_services(assign=False)
    before = repository.list_audit_events(review_case.review_case_id)
    with pytest.raises(ReviewRuntimeError):
        service.approve_case(
            review_case.review_case_id,
            reviewer_id="reviewer-001",
            expected_version=1,
            occurred_at=ACTION,
        )
    assert repository.list_audit_events(review_case.review_case_id) == before

    assigned_repository, _, assigned_service, assigned_case = setup_services()
    assigned_before = assigned_repository.list_audit_events(assigned_case.review_case_id)
    with pytest.raises(ReviewCaseVersionConflictError):
        assigned_service.approve_case(
            assigned_case.review_case_id,
            reviewer_id="reviewer-001",
            expected_version=1,
            occurred_at=ACTION,
        )
    assert assigned_repository.list_audit_events(assigned_case.review_case_id) == assigned_before


def test_resolved_case_is_terminal_for_corrections_and_decisions():
    repository, case_service, service, review_case = setup_services()
    approved = service.approve_case(
        review_case.review_case_id,
        reviewer_id="reviewer-001",
        expected_version=2,
        occurred_at=ACTION,
    )
    resolved = case_service.resolve_case(
        approved.review_case_id,
        expected_version=approved.version,
        actor_id="system",
        occurred_at="2026-07-11T10:15:00+00:00",
    )
    before = repository.list_audit_events(resolved.review_case_id)

    with pytest.raises(ReviewRuntimeError):
        service.submit_correction(
            resolved.review_case_id,
            field_path="customer.status",
            new_value=ControlledValue("string", "active"),
            reason_code="field_verified",
            corrected_by="reviewer-001",
            expected_version=resolved.version,
        )
    with pytest.raises(ReviewRuntimeError):
        service.approve_case(
            resolved.review_case_id,
            reviewer_id="reviewer-001",
            expected_version=resolved.version,
        )
    assert repository.list_audit_events(resolved.review_case_id) == before


def test_wrong_reviewer_and_private_payload_errors_are_safe():
    repository, _, service, review_case = setup_services()
    with pytest.raises(ReviewReviewerConflictError):
        service.approve_case(
            review_case.review_case_id,
            reviewer_id="private-other-reviewer",
            expected_version=2,
        )
    with pytest.raises(ReviewReviewerConflictError):
        service.submit_correction(
            review_case.review_case_id,
            field_path="customer.status",
            new_value=ControlledValue("string", "active"),
            reason_code="field_verified",
            corrected_by="private-other-reviewer",
            expected_version=2,
        )
    with pytest.raises(ReviewRuntimeError) as caught:
        service.correct_case(
            review_case.review_case_id,
            [correction_spec(value="private-sensitive-corrected-value", field_path="bad..path")],
            reviewer_id="reviewer-001",
            expected_version=2,
            reason_code="fields_corrected",
        )
    assert "private-sensitive-corrected-value" not in str(caught.value)
    assert len(repository.list_audit_events(review_case.review_case_id)) == 2


def test_audit_metadata_never_contains_controlled_values():
    repository, _, service, review_case = setup_services()
    service.correct_case(
        review_case.review_case_id,
        [correction_spec(value="private-sensitive-corrected-value")],
        reviewer_id="reviewer-001",
        expected_version=2,
        reason_code="fields_corrected",
        occurred_at=ACTION,
    )
    serialized_audit = json.dumps(
        [event.to_dict() for event in repository.list_audit_events(review_case.review_case_id)]
    )
    assert "private-sensitive-corrected-value" not in serialized_audit


def test_repository_correction_copy_does_not_expose_internal_state():
    repository, _, service, review_case = setup_services()
    service.submit_correction(
        review_case.review_case_id,
        field_path="customer.status",
        new_value=ControlledValue("string", "active"),
        reason_code="field_verified",
        corrected_by="reviewer-001",
        expected_version=2,
        occurred_at=ACTION,
    )
    retrieved = repository.list_corrections(review_case.review_case_id)[0]
    object.__setattr__(retrieved, "field_path", "changed.outside")
    assert repository.list_corrections(review_case.review_case_id)[0].field_path == "customer.status"
