from dataclasses import FrozenInstanceError

import pytest

from src.workflow_studio import (
    ActionDefinition,
    RuleDefinition,
    WorkflowChangeSummary,
    WorkflowDefinition,
    WorkflowOwnership,
    WorkflowReference,
    WorkflowSourceLineage,
    WorkflowVersion,
)


NOW = "2026-07-14T10:00:00+00:00"


def definition(**changes: object) -> WorkflowDefinition:
    values = dict(
        workflow_id="workflow-1", tenant_id="tenant-1", name="Invoice review", description="",
        business_domain="finance", document_type="invoice", status="draft",
        current_draft_version=WorkflowReference("workflow-1", "version-1", 1), active_published_version=None,
        ownership=WorkflowOwnership("actor-1", "actor-1"), created_at=NOW, updated_at=NOW,
        metadata={"region": "east"},
    )
    values.update(changes)
    return WorkflowDefinition(**values)


def version(status: str = "published") -> WorkflowVersion:
    action = ActionDefinition("action-1", "runtime", "filter", "1", arguments={})
    rule = RuleDefinition("rule-1", "Rule", "filter", "", (), 0, True, False, None, (action,))
    return WorkflowVersion(
        "version-1", "workflow-1", "1.0.0", status, (rule,), None,
        WorkflowChangeSummary("Initial version", ("rules",)), "actor-1", "reviewer-1", "approver-1",
        NOW, NOW, NOW if status == "published" else None,
        WorkflowSourceLineage("studio", "draft-1", NOW), {"release": "initial"},
    )


def test_workflow_definition_serializes_to_json_safe_shape() -> None:
    payload = definition().to_dict()
    assert payload["status"] == "draft"
    assert payload["current_draft_version"]["version"] == 1
    assert payload["metadata"] == {"region": "east"}


def test_published_version_contract_is_immutable_and_serializes() -> None:
    published = version()
    assert published.to_dict()["status"] == "published"
    assert published.to_dict()["rules"][0]["rule_id"] == "rule-1"
    with pytest.raises(FrozenInstanceError):
        published.status = "inactive"
    with pytest.raises(TypeError):
        published.metadata["release"] = "changed"


def test_definition_rejects_cross_workflow_reference() -> None:
    with pytest.raises(ValueError):
        definition(current_draft_version=WorkflowReference("workflow-2", "version-1", 1))
