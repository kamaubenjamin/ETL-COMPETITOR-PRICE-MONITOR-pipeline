import pytest

import src.workflow_runtime.operations  # noqa: F401 - loads implemented stages
from src.workflow_runtime.contracts.workflow_definition import StageDefinition, WorkflowDefinition
from src.workflow_runtime.dsl.workflow_validator import VALID_STAGE_TYPES, WorkflowValidator
from src.workflow_runtime.operations.base import STAGE_REGISTRY, validate_registered_stage_type
from src.workflow_runtime.operations.stage_catalog import (
    IMPLEMENTED_STAGE_TYPES,
    RESERVED_STAGE_TYPES,
    WORKFLOW_STAGE_TYPES,
    is_implemented_stage_type,
    is_workflow_stage_type,
)


def _workflow(stage_type: str) -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id=f"wf-{stage_type}", name="Catalog test", version="1.0.0",
        workspace_id="ws", enabled=True,
        stages=[StageDefinition(name="stage", type=stage_type)],
    )


def test_catalog_has_existing_matching_stage():
    assert "matching" in IMPLEMENTED_STAGE_TYPES
    assert WorkflowValidator.validate(_workflow("matching")).all_passed is True


def test_catalog_reserves_v06_stage_names():
    assert RESERVED_STAGE_TYPES == frozenset({"validate_data", "sort", "aggregate"})
    for stage_type in RESERVED_STAGE_TYPES:
        assert is_workflow_stage_type(stage_type)
        assert not is_implemented_stage_type(stage_type)
        assert WorkflowValidator.validate(_workflow(stage_type)).all_passed is True


def test_validator_uses_authoritative_catalog():
    assert VALID_STAGE_TYPES is WORKFLOW_STAGE_TYPES


def test_implemented_catalog_matches_runtime_registry():
    assert frozenset(STAGE_REGISTRY) == IMPLEMENTED_STAGE_TYPES
    assert not (frozenset(STAGE_REGISTRY) & RESERVED_STAGE_TYPES)


def test_unknown_stage_is_rejected_by_validator_and_registration_guard():
    assert WorkflowValidator.validate(_workflow("execute_python")).all_passed is False
    with pytest.raises(ValueError, match="Unknown workflow stage type"):
        validate_registered_stage_type("execute_python")


def test_registration_guard_accepts_reserved_name_for_future_phase():
    assert validate_registered_stage_type("sort") == "sort"

