import pytest

from src.document_state.lifecycle import (
    ALLOWED_TRANSITIONS,
    STRUCTURED_EQUIVALENT,
    LifecycleRecoveryPolicy,
    LifecycleTransitionRequest,
    evaluate_transition,
    order_transition_candidates,
)


NOW = "2026-07-13T09:00:00+00:00"


def request(source, target, *, event_id="event-001", occurred_at=NOW, recovery=None):
    return LifecycleTransitionRequest(
        "doc-001",
        source,
        target,
        event_id,
        1,
        "safe_reason",
        "system",
        occurred_at,
        recovery_policy=recovery,
    )


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("received", "classified"),
        ("classified", "parsed"),
        ("parsed", "validated"),
        ("validated", "matched"),
        ("matched", "review_required"),
        ("review_required", "approved"),
        ("approved", "exported"),
    ],
)
def test_required_progression_is_allowed(source, target):
    assert evaluate_transition(request(source, target)).outcome == "allowed"


def test_structured_equivalent_is_existing_parsed_status():
    assert STRUCTURED_EQUIVALENT == "parsed"


def test_any_non_terminal_state_can_fail():
    for source, targets in ALLOWED_TRANSITIONS.items():
        if source not in {"failed", "exported"}:
            assert "failed" in targets
            assert evaluate_transition(request(source, "failed")).outcome == "allowed"


def test_same_status_replay_is_no_op():
    decision = evaluate_transition(request("validated", "validated"))
    assert decision.outcome == "no_op"
    assert decision.reason_code == "already_applied"


@pytest.mark.parametrize("source", ["exported", "failed"])
def test_terminal_states_reject_normal_advancement(source):
    decision = evaluate_transition(request(source, "approved"))
    assert decision.outcome == "rejected"


def test_failed_recovery_requires_explicit_policy():
    assert evaluate_transition(request("failed", "validated")).reason_code == "recovery_required"
    policy = LifecycleRecoveryPolicy("validated", reprocess_plan_id="plan-001")
    decision = evaluate_transition(request("failed", "validated", recovery=policy))
    assert decision.outcome == "allowed"
    assert decision.reason_code == "recovery_allowed"


@pytest.mark.parametrize("target", ["validated", "matched", "approved"])
def test_governed_failed_recovery_targets_are_allowed(target):
    policy = LifecycleRecoveryPolicy(target, governed_reason_code="approved_recovery")
    assert evaluate_transition(request("failed", target, recovery=policy)).outcome == "allowed"


def test_invalid_backward_transition_is_rejected_safely():
    decision = evaluate_transition(request("matched", "parsed"))
    assert decision.to_dict()["reason_code"] == "invalid_transition"
    assert "payload" not in decision.to_dict()


def test_recovery_policy_is_rejected_for_non_failed_source():
    policy = LifecycleRecoveryPolicy("validated", reprocess_plan_id="plan-001")
    decision = evaluate_transition(request("parsed", "validated", recovery=policy))
    assert decision.reason_code == "recovery_not_applicable"


def test_candidate_ordering_is_deterministic_by_time_priority_and_event_id():
    candidates = (
        request("validated", "review_required", event_id="event-b"),
        request("validated", "matched", event_id="event-c"),
        request("validated", "matched", event_id="event-a"),
        request("classified", "parsed", event_id="event-z", occurred_at="2026-07-13T08:59:00+00:00"),
    )
    ordered = order_transition_candidates(reversed(candidates))
    assert [item.lifecycle_event_id for item in ordered] == ["event-z", "event-a", "event-c", "event-b"]


def test_policy_rejects_non_contract_input_without_repository_behavior():
    with pytest.raises(ValueError):
        evaluate_transition({"source_status": "received"})
