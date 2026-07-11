import inspect
import json

import pytest

from src.review_runtime.contracts import ReprocessRequest
from src.review_runtime.errors import ReviewRuntimeError
from src.review_runtime.reprocess import (
    ReprocessPlan,
    ReprocessPlanner,
    SAFE_REPROCESS_STAGES,
)

NOW = "2026-07-11T12:00:00+00:00"


def request(from_stage="validate_data", target_stage="entity_extract"):
    return ReprocessRequest(
        request_id="request-001",
        review_case_id="case-001",
        requested_from_stage=from_stage,
        requested_target_stage=target_stage,
        reason_code="corrected_fields",
        requested_by="reviewer-001",
        created_at=NOW,
        metadata={"workflow_id": "workflow-001"},
        expected_case_version=2,
        idempotency_key="request-idem-001",
    )


def test_plan_creation_success_and_json_round_trip():
    planner = ReprocessPlanner(
        clock=lambda: NOW,
        id_factory=lambda prefix: f"{prefix}-001",
    )
    plan = planner.create_plan(
        request(),
        invalidated_artifacts=["artifact-003", "artifact-001"],
        retained_artifacts=["artifact-002"],
        metadata={"workflow_id": "workflow-001"},
    )

    assert plan.plan_id == "reprocess-plan-001"
    assert plan.review_case_id == "case-001"
    assert plan.dry_run is True
    assert ReprocessPlan.from_dict(plan.to_dict()) == plan
    json.dumps(plan.to_dict())


@pytest.mark.parametrize("field,value", [("from_stage", "unknown_stage"), ("target_stage", "unknown_stage")])
def test_invalid_stage_is_rejected_without_echoing_payload(field, value):
    kwargs = {field: value}
    with pytest.raises(ReviewRuntimeError) as caught:
        ReprocessPlanner().create_plan(
            request(**kwargs),
            invalidated_artifacts=["artifact-001"],
        )
    assert value not in str(caught.value)


def test_target_stage_cannot_be_downstream_of_requesting_stage():
    with pytest.raises(ReviewRuntimeError) as caught:
        ReprocessPlanner().create_plan(
            request(from_stage="entity_extract", target_stage="matching"),
            invalidated_artifacts=["artifact-001"],
        )
    assert caught.value.path == "$.requested_target_stage"


def test_artifact_lists_are_unique_sorted_and_disjoint():
    plan = ReprocessPlanner(clock=lambda: NOW).create_plan(
        request(),
        invalidated_artifacts=["artifact-z", "artifact-a"],
        retained_artifacts=["artifact-c", "artifact-b"],
        plan_id="plan-001",
    )
    assert plan.invalidated_artifacts == ("artifact-a", "artifact-z")
    assert plan.retained_artifacts == ("artifact-b", "artifact-c")

    with pytest.raises(ReviewRuntimeError):
        ReprocessPlanner().create_plan(
            request(),
            invalidated_artifacts=["artifact-a", "artifact-a"],
        )

    with pytest.raises(ReviewRuntimeError):
        ReprocessPlanner().create_plan(
            request(),
            invalidated_artifacts=["artifact-a"],
            retained_artifacts=["artifact-a"],
        )


def test_plan_requires_invalidated_artifact_reference():
    with pytest.raises(ReviewRuntimeError):
        ReprocessPlanner().create_plan(request(), invalidated_artifacts=[])


def test_plan_is_always_dry_run_only():
    payload = ReprocessPlanner(clock=lambda: NOW).create_plan(
        request(),
        invalidated_artifacts=["artifact-001"],
        plan_id="plan-001",
    ).to_dict()
    payload["dry_run"] = False
    with pytest.raises(ReviewRuntimeError):
        ReprocessPlan.from_dict(payload)


def test_artifact_payloads_and_unsafe_metadata_are_rejected_privately():
    with pytest.raises(ReviewRuntimeError) as artifact_error:
        ReprocessPlanner().create_plan(
            request(),
            invalidated_artifacts=["private customer row payload"],
        )
    with pytest.raises(ReviewRuntimeError) as metadata_error:
        ReprocessPlanner().create_plan(
            request(),
            invalidated_artifacts=["artifact-001"],
            metadata={"raw_document": "private document body"},
        )
    assert "private customer row payload" not in str(artifact_error.value)
    assert "private document body" not in str(metadata_error.value)


def test_safe_stage_allowlist_is_dependency_free_and_contains_current_execution_stages():
    assert {"document_ingest", "entity_extract", "transform", "validate_data", "matching"} <= SAFE_REPROCESS_STAGES
    source = inspect.getsource(ReprocessPlanner)
    assert "WorkflowRunner" not in source
    assert "workflow_runtime" not in source
