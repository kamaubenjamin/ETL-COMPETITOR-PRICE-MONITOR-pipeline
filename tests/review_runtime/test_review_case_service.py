import pytest

from src.review_runtime.contracts import ReviewStatus
from src.review_runtime.errors import (
    ReviewCaseIdempotencyConflictError,
    ReviewCaseNotFoundError,
    ReviewCaseVersionConflictError,
    ReviewRuntimeError,
)
from src.review_runtime.repositories import InMemoryReviewCaseRepository
from src.review_runtime.services import ReviewCaseService

NOW = "2026-07-11T09:00:00+00:00"
LATER = "2026-07-11T09:05:00+00:00"
FINAL = "2026-07-11T09:10:00+00:00"


class DeterministicIds:
    def __init__(self):
        self.counts = {}

    def __call__(self, prefix):
        count = self.counts.get(prefix, 0) + 1
        self.counts[prefix] = count
        return f"{prefix}-{count:03d}"


def make_service(repository=None, clock=lambda: NOW, ids=None):
    repository = repository or InMemoryReviewCaseRepository()
    return ReviewCaseService(
        repository,
        clock=clock,
        id_factory=ids or DeterministicIds(),
    )


def create_case(service, **overrides):
    values = {
        "source_runtime": "matching",
        "source_stage": "matching",
        "source_artifact_id": "match-set-001",
        "reason_code": "ambiguous_match",
        "priority": "normal",
        "case_type": "matching_ambiguity",
        "metadata": {"candidate_count": 2},
    }
    values.update(overrides)
    return service.create_case(**values)


def test_create_case_sets_canonical_defaults_and_audit():
    service = make_service()
    review_case = create_case(service)

    assert review_case.review_case_id == "review-case-001"
    assert review_case.status is ReviewStatus.REVIEW_REQUIRED
    assert review_case.version == 1
    assert review_case.created_at == NOW
    assert review_case.updated_at == NOW
    events = service.list_audit_events(review_case.review_case_id)
    assert len(events) == 1
    assert events[0].event_type == "case_created"
    assert events[0].previous_status is None
    assert events[0].new_status is ReviewStatus.REVIEW_REQUIRED


@pytest.mark.parametrize(
    "overrides",
    [
        {"source_stage": ""},
        {"source_artifact_id": ""},
        {"reason_code": "Invalid Reason"},
        {"status": "in_review"},
    ],
)
def test_create_case_validation_failure(overrides):
    with pytest.raises(ReviewRuntimeError):
        create_case(make_service(), **overrides)


def test_create_case_enforces_safe_metadata_without_exposing_values():
    with pytest.raises(ReviewRuntimeError) as caught:
        create_case(
            make_service(),
            metadata={"raw_document": "private customer row contents"},
        )
    assert "private customer row contents" not in str(caught.value)


def test_get_missing_case_is_typed_and_privacy_safe():
    with pytest.raises(ReviewCaseNotFoundError) as caught:
        make_service().get_case("private-customer-case")
    assert "private-customer-case" not in str(caught.value)


def test_list_cases_orders_by_created_at_then_case_id():
    repository = InMemoryReviewCaseRepository()
    create_case(make_service(repository, lambda: "2026-07-11T10:00:00+00:00"), review_case_id="case-b")
    create_case(make_service(repository, lambda: "2026-07-11T08:00:00+00:00"), review_case_id="case-z")
    create_case(make_service(repository, lambda: "2026-07-11T10:00:00+00:00"), review_case_id="case-a")

    listed = make_service(repository).list_cases()
    assert [item.review_case_id for item in listed] == ["case-z", "case-a", "case-b"]


def test_list_cases_supports_all_filters_and_legacy_pending():
    repository = InMemoryReviewCaseRepository()
    service = make_service(repository)
    matching = create_case(service, review_case_id="case-match")
    create_case(
        service,
        review_case_id="case-validation",
        source_runtime="transforms",
        source_stage="validate_data",
        source_artifact_id="table-001",
        reason_code="invalid_data",
        priority="high",
        case_type="validation_failure",
        metadata={"issue_count": 3},
    )

    assert [item.review_case_id for item in service.list_cases(status="pending")] == [
        matching.review_case_id,
        "case-validation",
    ]
    assert service.list_cases(reason_code="invalid_data")[0].review_case_id == "case-validation"
    assert service.list_cases(source_runtime="transforms")[0].review_case_id == "case-validation"
    assert service.list_cases(source_stage="validate_data")[0].review_case_id == "case-validation"
    assert service.list_cases(priority="high")[0].review_case_id == "case-validation"


def test_transition_uses_state_machine_and_does_not_mutate_previous_projection():
    service = make_service()
    original = create_case(service)
    updated = service.mark_in_review(
        original.review_case_id,
        reviewer_id="reviewer-001",
        expected_version=1,
        occurred_at=LATER,
    )

    assert original.status is ReviewStatus.REVIEW_REQUIRED
    assert original.version == 1
    assert updated.status is ReviewStatus.IN_REVIEW
    assert updated.version == 2
    assert updated.updated_at == LATER
    assert updated.assigned_reviewer_id == "reviewer-001"


def test_invalid_transition_fails_without_audit_append():
    service = make_service()
    review_case = create_case(service)

    with pytest.raises(ReviewRuntimeError) as caught:
        service.transition_case(
            review_case.review_case_id,
            "approved",
            expected_version=1,
            actor_id="reviewer-001",
            occurred_at=LATER,
        )

    assert caught.value.code == "invalid_transition"
    assert len(service.list_audit_events(review_case.review_case_id)) == 1


def test_optimistic_version_success_and_conflict():
    service = make_service()
    review_case = create_case(service)
    updated = service.mark_in_review(
        review_case.review_case_id,
        reviewer_id="reviewer-001",
        expected_version=1,
        occurred_at=LATER,
    )
    assert updated.version == 2

    with pytest.raises(ReviewCaseVersionConflictError) as caught:
        service.transition_case(
            review_case.review_case_id,
            "skipped",
            expected_version=1,
            actor_id="reviewer-001",
            occurred_at=FINAL,
        )
    assert "private" not in str(caught.value)
    assert service.get_case(review_case.review_case_id).version == 2


def test_audit_event_ordering_and_resolve_event():
    service = make_service()
    review_case = create_case(service)
    in_review = service.mark_in_review(
        review_case.review_case_id,
        reviewer_id="reviewer-001",
        expected_version=1,
        occurred_at=LATER,
    )
    approved = service.transition_case(
        review_case.review_case_id,
        "approved",
        expected_version=in_review.version,
        actor_id="reviewer-001",
        occurred_at=FINAL,
    )
    resolved = service.resolve_case(
        review_case.review_case_id,
        expected_version=approved.version,
        actor_id="system",
        occurred_at="2026-07-11T09:15:00+00:00",
    )

    assert resolved.status is ReviewStatus.RESOLVED
    events = service.list_audit_events(review_case.review_case_id)
    assert [event.sequence for event in events] == [1, 2, 3, 4]
    assert [event.event_type for event in events] == [
        "case_created", "status_changed", "status_changed", "case_resolved",
    ]


def test_legacy_pending_normalizes_to_review_required():
    review_case = create_case(make_service(), status="pending")
    assert review_case.status is ReviewStatus.REVIEW_REQUIRED


def test_idempotent_create_returns_original_case_and_single_audit():
    service = make_service()
    first = create_case(service, idempotency_key="idem-create-001")
    replay = create_case(service, idempotency_key="idem-create-001")

    assert replay == first
    assert len(service.list_cases()) == 1
    assert len(service.list_audit_events(first.review_case_id)) == 1


def test_idempotency_conflict_does_not_expose_payload():
    service = make_service()
    create_case(service, idempotency_key="idem-create-001")

    with pytest.raises(ReviewCaseIdempotencyConflictError) as caught:
        create_case(
            service,
            idempotency_key="idem-create-001",
            reason_code="different_reason",
            metadata={"correlation_id": "private-correlation-id"},
        )
    assert "private-correlation-id" not in str(caught.value)


def test_create_case_does_not_mutate_input_metadata():
    metadata = {"candidate_count": 2}
    review_case = create_case(make_service(), metadata=metadata)
    metadata["candidate_count"] = 99

    assert review_case.metadata["candidate_count"] == 2


def test_create_from_trigger_and_escalation_are_bounded():
    service = make_service()
    trigger = {
        "source_runtime": "entity",
        "source_stage": "entity_extract",
        "source_artifact_id": "entity-set-001",
        "reason_code": "blocked_customer",
        "case_type": "blocked_customer",
        "metadata": {"issue_count": 1},
    }
    created = service.create_case_from_trigger(trigger)
    escalated = service.escalate_case(
        {**trigger, "review_case_id": "manual-case-001", "idempotency_key": "manual-idem-001"},
        actor_id="operator-001",
    )

    assert created.case_type.value == "blocked_customer"
    assert escalated.case_type.value == "manual_escalation"
    assert escalated.priority.value == "high"


def test_trigger_rejects_unknown_raw_payload_without_echoing_value():
    service = make_service()
    trigger = {
        "source_runtime": "entity",
        "source_stage": "entity_extract",
        "source_artifact_id": "entity-set-001",
        "reason_code": "invalid_data",
        "raw_rows": "private customer rows",
    }
    with pytest.raises(ReviewRuntimeError) as caught:
        service.create_case_from_trigger(trigger)
    assert "private customer rows" not in str(caught.value)
