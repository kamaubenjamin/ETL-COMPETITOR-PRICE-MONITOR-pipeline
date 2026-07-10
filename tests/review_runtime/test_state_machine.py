from dataclasses import FrozenInstanceError

import pytest

from src.review_runtime import (
    ALLOWED_TRANSITIONS,
    ReviewCase,
    ReviewRuntimeError,
    ReviewStatus,
    can_transition,
    status_for_decision,
    transition_review_case,
    transition_status,
)

NOW = "2026-07-10T10:00:00+00:00"
LATER = "2026-07-10T10:05:00+00:00"

ALLOWED = {
    ("review_required", "in_review"),
    ("review_required", "skipped"),
    ("in_review", "corrected"),
    ("in_review", "approved"),
    ("in_review", "rejected"),
    ("in_review", "skipped"),
    ("in_review", "reprocess_requested"),
    ("corrected", "approved"),
    ("corrected", "in_review"),
    ("corrected", "reprocess_requested"),
    ("approved", "resolved"),
    ("rejected", "resolved"),
    ("skipped", "resolved"),
    ("reprocess_requested", "resolved"),
}


def make_case(status="review_required", version=1, updated_at=NOW):
    return ReviewCase(
        review_case_id="case-001",
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


def test_allowed_transition_table_matches_architecture():
    actual = {
        (source.value, target.value)
        for source, targets in ALLOWED_TRANSITIONS.items()
        for target in targets
    }
    assert actual == ALLOWED


@pytest.mark.parametrize("current,target", sorted(ALLOWED))
def test_every_allowed_transition_succeeds(current, target):
    result = transition_status(current, target, 4, occurred_at=LATER)

    assert result.previous_status.value == current
    assert result.new_status.value == target
    assert result.previous_version == 4
    assert result.new_version == 5
    assert result.occurred_at == LATER
    assert can_transition(current, target) is True


@pytest.mark.parametrize(
    "current,target",
    [
        (source.value, target.value)
        for source in ReviewStatus
        for target in ReviewStatus
        if (source.value, target.value) not in ALLOWED
    ],
)
def test_every_undefined_transition_fails_deterministically(current, target):
    with pytest.raises(ReviewRuntimeError) as caught:
        transition_status(current, target, 1, occurred_at=LATER)

    assert caught.value.code == "invalid_transition"
    assert caught.value.path == "$.status"
    assert can_transition(current, target) is False


def test_transition_review_case_returns_new_projection_without_mutating_input():
    original = make_case()

    updated = transition_review_case(original, "in_review", occurred_at=LATER)

    assert updated is not original
    assert original.status is ReviewStatus.REVIEW_REQUIRED
    assert original.version == 1
    assert original.updated_at == NOW
    assert updated.status is ReviewStatus.IN_REVIEW
    assert updated.version == 2
    assert updated.updated_at == LATER
    assert updated.review_case_id == original.review_case_id


def test_review_case_and_transition_result_are_immutable():
    case = make_case()
    result = transition_status("review_required", "in_review", 1, occurred_at=LATER)

    with pytest.raises(FrozenInstanceError):
        case.version = 9
    with pytest.raises(FrozenInstanceError):
        result.new_version = 9


def test_resolved_is_terminal():
    assert ALLOWED_TRANSITIONS[ReviewStatus.RESOLVED] == frozenset()
    for target in ReviewStatus:
        with pytest.raises(ReviewRuntimeError):
            transition_status("resolved", target, 8, occurred_at=LATER)


@pytest.mark.parametrize(
    "decision,target",
    [
        ("approve", "approved"),
        ("reject", "rejected"),
        ("correct", "corrected"),
        ("skip", "skipped"),
        ("request_reprocess", "reprocess_requested"),
    ],
)
def test_decisions_map_to_deterministic_target_status(decision, target):
    assert status_for_decision(decision).value == target


def test_unknown_status_and_decision_errors_do_not_echo_values():
    with pytest.raises(ReviewRuntimeError) as status_error:
        transition_status("private-status-value", "approved", 1, occurred_at=LATER)
    with pytest.raises(ReviewRuntimeError) as decision_error:
        status_for_decision("private-decision-value")

    assert "private-status-value" not in str(status_error.value)
    assert "private-decision-value" not in str(decision_error.value)


@pytest.mark.parametrize("version", [0, -1, True, "1"])
def test_transition_rejects_invalid_versions(version):
    with pytest.raises(ReviewRuntimeError) as caught:
        transition_status("review_required", "in_review", version, occurred_at=LATER)
    assert caught.value.path == "$.version"


def test_transition_timestamp_is_injectable_and_validated():
    assert transition_status("review_required", "in_review", 1, occurred_at=LATER).occurred_at == LATER
    with pytest.raises(ReviewRuntimeError) as caught:
        transition_status("review_required", "in_review", 1, occurred_at="not-a-time")
    assert caught.value.path == "$.occurred_at"
