import json
from dataclasses import FrozenInstanceError

import pytest

from src.document_state.lifecycle import LifecycleRecoveryPolicy, LifecycleTransitionRequest


NOW = "2026-07-13T09:00:00+00:00"


def request(**overrides):
    values = {
        "document_id": "doc-001",
        "source_status": "received",
        "target_status": "classified",
        "lifecycle_event_id": "event-001",
        "expected_version": 1,
        "reason_code": "classification_completed",
        "actor_id": "system",
        "occurred_at": NOW,
        "metadata": {"source_stage": "classification"},
    }
    values.update(overrides)
    return LifecycleTransitionRequest(**values)


def test_transition_request_is_immutable_and_json_compatible():
    transition = request()
    assert json.loads(json.dumps(transition.to_dict()))["target_status"] == "classified"
    with pytest.raises(FrozenInstanceError):
        transition.target_status = "failed"


def test_request_copies_and_freezes_metadata():
    metadata = {"source_stage": "classification"}
    transition = request(metadata=metadata)
    metadata["source_stage"] = "changed"
    assert transition.metadata["source_stage"] == "classification"
    with pytest.raises(TypeError):
        transition.metadata["source_stage"] = "changed"


@pytest.mark.parametrize(
    "metadata",
    [
        {"raw_document": "private"},
        {"raw_rows": "private"},
        {"new_value": "private"},
        {"artifact_payload": "private"},
        {"storage_path": "C:/private"},
        {"credentials": "private"},
        {"stack_trace": "private"},
        {"raw_exception": "private"},
    ],
)
def test_transition_request_rejects_unsafe_metadata(metadata):
    with pytest.raises(ValueError):
        request(metadata=metadata)


def test_request_validates_version_statuses_and_timestamp():
    with pytest.raises(ValueError):
        request(expected_version=0)
    with pytest.raises(ValueError):
        request(target_status="structured")
    with pytest.raises(ValueError):
        request(occurred_at="2026-07-13")


def test_recovery_policy_requires_explicit_target_and_authorization():
    with pytest.raises(ValueError):
        LifecycleRecoveryPolicy("validated")
    with pytest.raises(ValueError):
        LifecycleRecoveryPolicy("exported", reprocess_plan_id="plan-001")
    policy = LifecycleRecoveryPolicy("validated", reprocess_plan_id="plan-001")
    transition = request(source_status="failed", target_status="validated", recovery_policy=policy)
    assert transition.to_dict()["recovery_policy"]["reprocess_plan_id"] == "plan-001"


def test_recovery_policy_target_must_match_request_target():
    policy = LifecycleRecoveryPolicy("matched", governed_reason_code="approved_recovery")
    with pytest.raises(ValueError):
        request(source_status="failed", target_status="validated", recovery_policy=policy)
