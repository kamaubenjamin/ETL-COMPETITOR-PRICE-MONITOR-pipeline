import inspect
import json

import pytest

from src.review_runtime.contracts import ReviewStatus
from src.review_runtime.errors import (
    ReviewCaseVersionConflictError,
    ReviewReprocessRequestNotFoundError,
    ReviewRuntimeError,
)
from src.review_runtime.repositories import InMemoryReviewCaseRepository
from src.review_runtime.reprocess import ReprocessPlanner
from src.review_runtime.services import (
    CorrectionDecisionService,
    ReprocessService,
    ReviewCaseService,
)

NOW = "2026-07-11T13:00:00+00:00"
REQUESTED = "2026-07-11T13:05:00+00:00"
PLANNED = "2026-07-11T13:10:00+00:00"


class DeterministicIds:
    def __init__(self):
        self.counts = {}

    def __call__(self, prefix):
        count = self.counts.get(prefix, 0) + 1
        self.counts[prefix] = count
        return f"{prefix}-{count:03d}"


def setup_reprocess_case(*, target_stage="entity_extract"):
    repository = InMemoryReviewCaseRepository()
    ids = DeterministicIds()
    case_service = ReviewCaseService(repository, clock=lambda: NOW, id_factory=ids)
    decision_service = CorrectionDecisionService(repository, clock=lambda: REQUESTED, id_factory=ids)
    planner = ReprocessPlanner(clock=lambda: PLANNED, id_factory=ids)
    service = ReprocessService(repository, planner, id_factory=ids)
    review_case = case_service.create_case(
        review_case_id="case-001",
        source_runtime="transforms",
        source_stage="validate_data",
        source_artifact_id="table-001",
        reason_code="invalid_data",
        priority="high",
        case_type="validation_failure",
        metadata={"issue_count": 2},
    )
    in_review = case_service.mark_in_review(
        review_case.review_case_id,
        reviewer_id="reviewer-001",
        expected_version=1,
        occurred_at=NOW,
    )
    requested_case = decision_service.request_reprocess(
        review_case.review_case_id,
        requested_target_stage=target_stage,
        reason_code="corrected_fields",
        reviewer_id="reviewer-001",
        expected_version=in_review.version,
        request_id="request-001",
        idempotency_key="request-idem-001",
        occurred_at=REQUESTED,
    )
    return repository, service, requested_case


def test_plan_creation_success_emits_audit_without_changing_case_version():
    repository, service, review_case = setup_reprocess_case()
    audit_before = len(repository.list_audit_events(review_case.review_case_id))
    plan = service.create_plan(
        review_case.review_case_id,
        "request-001",
        invalidated_artifacts=["artifact-003", "artifact-001"],
        retained_artifacts=["artifact-002"],
        expected_version=review_case.version,
        metadata={"workflow_id": "workflow-001"},
        plan_id="plan-001",
        created_at=PLANNED,
    )

    assert plan.dry_run is True
    assert repository.get_case(review_case.review_case_id).version == review_case.version
    events = repository.list_audit_events(review_case.review_case_id)
    assert len(events) == audit_before + 1
    assert events[-1].event_type == "reprocess_plan_created"
    assert events[-1].metadata == {
        "requested_from_stage": "validate_data",
        "requested_target_stage": "entity_extract",
        "invalidated_count": 2,
        "retained_count": 1,
        "dry_run": True,
    }


def test_plan_storage_and_listing_are_deterministic_and_defensive():
    repository, service, review_case = setup_reprocess_case()
    service.create_plan(
        review_case.review_case_id,
        "request-001",
        invalidated_artifacts=["artifact-002"],
        expected_version=review_case.version,
        plan_id="plan-b",
        created_at="2026-07-11T13:11:00+00:00",
    )
    service.create_plan(
        review_case.review_case_id,
        "request-001",
        invalidated_artifacts=["artifact-001"],
        expected_version=review_case.version,
        plan_id="plan-a",
        created_at="2026-07-11T13:11:00+00:00",
    )

    listed = service.list_plans(review_case.review_case_id)
    assert [item.plan_id for item in listed] == ["plan-a", "plan-b"]
    object.__setattr__(listed[0], "reason_code", "changed_outside_repository")
    assert service.list_plans(review_case.review_case_id)[0].reason_code == "corrected_fields"


def test_invalid_stage_fails_without_plan_or_audit():
    repository, service, review_case = setup_reprocess_case(target_stage="unknown_stage")
    audit_before = repository.list_audit_events(review_case.review_case_id)
    with pytest.raises(ReviewRuntimeError) as caught:
        service.create_plan(
            review_case.review_case_id,
            "request-001",
            invalidated_artifacts=["artifact-001"],
            expected_version=review_case.version,
        )
    assert "unknown_stage" not in str(caught.value)
    assert service.list_plans(review_case.review_case_id) == ()
    assert repository.list_audit_events(review_case.review_case_id) == audit_before


def test_missing_request_and_version_conflict_append_nothing():
    repository, service, review_case = setup_reprocess_case()
    audit_before = repository.list_audit_events(review_case.review_case_id)
    with pytest.raises(ReviewReprocessRequestNotFoundError):
        service.create_plan(
            review_case.review_case_id,
            "request-missing",
            invalidated_artifacts=["artifact-001"],
            expected_version=review_case.version,
        )
    with pytest.raises(ReviewCaseVersionConflictError):
        service.create_plan(
            review_case.review_case_id,
            "request-001",
            invalidated_artifacts=["artifact-001"],
            expected_version=review_case.version - 1,
        )
    assert repository.list_audit_events(review_case.review_case_id) == audit_before
    assert service.list_plans(review_case.review_case_id) == ()


def test_planning_requires_reprocess_requested_status():
    repository = InMemoryReviewCaseRepository()
    ids = DeterministicIds()
    case_service = ReviewCaseService(repository, clock=lambda: NOW, id_factory=ids)
    review_case = case_service.create_case(
        source_runtime="matching",
        source_stage="matching",
        source_artifact_id="match-set-001",
        reason_code="ambiguous_match",
    )
    service = ReprocessService(
        repository,
        ReprocessPlanner(clock=lambda: PLANNED, id_factory=ids),
        id_factory=ids,
    )
    with pytest.raises(ReviewRuntimeError):
        service.create_plan(
            review_case.review_case_id,
            "request-001",
            invalidated_artifacts=["artifact-001"],
            expected_version=1,
        )


def test_phase3_request_reprocess_contract_remains_compatible():
    repository, service, review_case = setup_reprocess_case()
    requests = repository.list_reprocess_requests(review_case.review_case_id)
    assert len(requests) == 1
    assert requests[0].request_id == "request-001"
    plan = service.create_plan(
        review_case.review_case_id,
        requests[0].request_id,
        invalidated_artifacts=["artifact-001"],
        expected_version=review_case.version,
        plan_id="plan-001",
    )
    assert plan.requested_from_stage == requests[0].requested_from_stage
    assert plan.requested_target_stage == requests[0].requested_target_stage


def test_plan_and_audit_are_privacy_safe():
    repository, service, review_case = setup_reprocess_case()
    with pytest.raises(ReviewRuntimeError) as caught:
        service.create_plan(
            review_case.review_case_id,
            "request-001",
            invalidated_artifacts=["private raw customer row"],
            expected_version=review_case.version,
        )
    assert "private raw customer row" not in str(caught.value)

    plan = service.create_plan(
        review_case.review_case_id,
        "request-001",
        invalidated_artifacts=["artifact-001"],
        expected_version=review_case.version,
        plan_id="plan-001",
    )
    serialized = json.dumps(plan.to_dict()) + json.dumps(
        [item.to_dict() for item in repository.list_audit_events(review_case.review_case_id)]
    )
    assert "raw_document" not in serialized
    assert "artifact payload" not in serialized


def test_service_has_no_workflow_execution_dependency_or_method():
    source = inspect.getsource(ReprocessService)
    assert "WorkflowRunner" not in source
    assert "workflow_runtime" not in source
    assert not hasattr(ReprocessService, "execute")
    assert not hasattr(ReprocessService, "run_workflow")
    _, service, review_case = setup_reprocess_case()
    assert review_case.status is ReviewStatus.REPROCESS_REQUESTED
    assert service.list_plans(review_case.review_case_id) == ()

