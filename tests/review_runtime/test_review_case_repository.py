from dataclasses import replace

import pytest

from src.review_runtime.contracts import ReviewAuditEvent, ReviewCase
from src.review_runtime.errors import (
    ReviewAuditConflictError,
    ReviewCaseAlreadyExistsError,
    ReviewCaseIdempotencyConflictError,
    ReviewCaseNotFoundError,
    ReviewCaseVersionConflictError,
)
from src.review_runtime.repositories import InMemoryReviewCaseRepository

NOW = "2026-07-11T08:00:00+00:00"
LATER = "2026-07-11T08:05:00+00:00"


def make_case(case_id="case-001", status="review_required", version=1, updated_at=NOW):
    return ReviewCase(
        review_case_id=case_id,
        source_runtime="matching",
        source_stage="matching",
        source_artifact_id="match-set-001",
        status=status,
        reason_code="ambiguous_match",
        priority="normal",
        created_at=NOW,
        updated_at=updated_at,
        version=version,
        metadata={"candidate_count": 2},
        case_type="matching_ambiguity",
    )


def create_event(case):
    return ReviewAuditEvent(
        event_id="event-001",
        review_case_id=case.review_case_id,
        event_type="case_created",
        actor_id="system",
        occurred_at=NOW,
        previous_status=None,
        new_status=case.status,
        sequence=1,
        case_version=1,
        metadata={"reason_code": case.reason_code},
    )


def update_event(current, updated):
    return ReviewAuditEvent(
        event_id=f"event-{updated.version}",
        review_case_id=updated.review_case_id,
        event_type="status_changed",
        actor_id="reviewer-001",
        occurred_at=updated.updated_at,
        previous_status=current.status,
        new_status=updated.status,
        sequence=updated.version,
        case_version=updated.version,
        metadata={},
    )


def store_case(repository, case=None, key="idem-001", fingerprint="fingerprint-001"):
    case = case or make_case()
    return repository.create_case(
        case,
        create_event(case),
        idempotency_key=key,
        creation_fingerprint=fingerprint,
    )


def test_repository_create_get_and_list():
    repository = InMemoryReviewCaseRepository()
    result = store_case(repository)

    assert result.created is True
    assert repository.get_case("case-001") == result.review_case
    assert repository.list_cases() == (result.review_case,)


def test_repository_missing_case_raises_typed_error():
    repository = InMemoryReviewCaseRepository()
    with pytest.raises(ReviewCaseNotFoundError) as caught:
        repository.get_case("missing-case")
    assert "missing-case" not in str(caught.value)


def test_repository_rejects_duplicate_case_id():
    repository = InMemoryReviewCaseRepository()
    store_case(repository)

    with pytest.raises(ReviewCaseAlreadyExistsError):
        store_case(repository, key="idem-002", fingerprint="fingerprint-001")


def test_repository_idempotent_create_returns_existing_without_new_audit():
    repository = InMemoryReviewCaseRepository()
    first = store_case(repository)
    replay = store_case(repository, case=make_case("case-retry"))

    assert replay.created is False
    assert replay.review_case == first.review_case
    assert len(repository.list_audit_events("case-001")) == 1


def test_repository_idempotency_conflict_is_privacy_safe():
    repository = InMemoryReviewCaseRepository()
    store_case(repository)

    with pytest.raises(ReviewCaseIdempotencyConflictError) as caught:
        store_case(repository, case=make_case("case-other"), fingerprint="private-payload-fingerprint")

    assert "private-payload-fingerprint" not in str(caught.value)


def test_repository_optimistic_update_success():
    repository = InMemoryReviewCaseRepository()
    current = store_case(repository).review_case
    updated = replace(current, status="in_review", version=2, updated_at=LATER)

    stored = repository.update_case(
        updated,
        update_event(current, updated),
        expected_version=1,
    )

    assert stored.status.value == "in_review"
    assert stored.version == 2


def test_repository_optimistic_version_conflict_preserves_state_and_audit():
    repository = InMemoryReviewCaseRepository()
    current = store_case(repository).review_case
    updated = replace(current, status="in_review", version=2, updated_at=LATER)

    with pytest.raises(ReviewCaseVersionConflictError):
        repository.update_case(updated, update_event(current, updated), expected_version=2)

    assert repository.get_case("case-001") == current
    assert len(repository.list_audit_events("case-001")) == 1


def test_repository_rejects_inconsistent_audit_atomically():
    repository = InMemoryReviewCaseRepository()
    current = store_case(repository).review_case
    updated = replace(current, status="in_review", version=2, updated_at=LATER)
    invalid_event = replace(update_event(current, updated), new_status="approved")

    with pytest.raises(ReviewAuditConflictError):
        repository.update_case(updated, invalid_event, expected_version=1)

    assert repository.get_case("case-001") == current
    assert len(repository.list_audit_events("case-001")) == 1


def test_repository_returns_defensive_copies():
    repository = InMemoryReviewCaseRepository()
    original = store_case(repository).review_case
    retrieved = repository.get_case("case-001")
    object.__setattr__(retrieved, "reason_code", "changed_outside_repository")

    listed = repository.list_cases()[0]
    assert listed.reason_code == original.reason_code
    assert listed is not retrieved


def test_audit_events_are_ordered_append_only_defensive_copies():
    repository = InMemoryReviewCaseRepository()
    current = store_case(repository).review_case
    updated = replace(current, status="in_review", version=2, updated_at=LATER)
    repository.update_case(updated, update_event(current, updated), expected_version=1)

    events = repository.list_audit_events("case-001")
    assert [event.sequence for event in events] == [1, 2]
    assert [event.event_type for event in events] == ["case_created", "status_changed"]
    object.__setattr__(events[0], "event_type", "changed_outside_repository")
    assert repository.list_audit_events("case-001")[0].event_type == "case_created"

