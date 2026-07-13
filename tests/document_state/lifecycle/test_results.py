import json
from dataclasses import FrozenInstanceError

import pytest

from src.document_state.lifecycle import LifecyclePolicyError, LifecycleTransitionResult


def test_advanced_result_is_immutable_json_and_version_safe():
    result = LifecycleTransitionResult("advanced", "doc-001", "event-001", "received", "classified", 2, 3)
    assert json.loads(json.dumps(result.to_dict()))["new_version"] == 3
    with pytest.raises(FrozenInstanceError):
        result.new_version = 4
    with pytest.raises(ValueError):
        LifecycleTransitionResult("advanced", "doc-001", "event-001", "received", "classified", 2, 4)


def test_no_op_result_does_not_advance_version():
    result = LifecycleTransitionResult("no_op", "doc-001", "event-001", "validated", "validated", 3, 3)
    assert result.error_code is None
    with pytest.raises(ValueError):
        LifecycleTransitionResult("no_op", "doc-001", "event-001", "validated", "validated", 3, 4)


@pytest.mark.parametrize(
    ("status", "code"),
    [
        ("rejected", "invalid_transition"),
        ("conflict", "version_conflict"),
        ("projection_pending", "version_conflict"),
        ("failed", "repository_unavailable"),
    ],
)
def test_failure_results_require_safe_error_codes(status, code):
    result = LifecycleTransitionResult(status, "doc-001", "event-001", "validated", "matched", 2, error_code=code)
    assert result.to_dict()["error_code"] == code
    with pytest.raises(ValueError):
        LifecycleTransitionResult(status, "doc-001", "event-001", "validated", "matched", 2)


def test_lifecycle_errors_are_privacy_safe():
    error = LifecyclePolicyError("invalid_transition", field="target_status")
    assert error.to_dict() == {
        "code": "invalid_transition",
        "message": "Lifecycle transition is not allowed.",
        "field": "target_status",
    }
    assert "payload" not in str(error).lower()
    with pytest.raises(TypeError):
        LifecyclePolicyError("internal_error", detail="private")
