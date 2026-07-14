from dataclasses import FrozenInstanceError

import pytest

from src.workflow_studio import WorkflowStudioAuditIntent


NOW = "2026-07-14T10:00:00+00:00"


def test_audit_intent_is_immutable_bounded_and_json_safe() -> None:
    intent = WorkflowStudioAuditIntent(
        "workflow_published", "tenant-1", "workflow-1", "version-1", "publication-1",
        "actor-1", "active", "governed_definition_published", NOW, "request-1", {"environment": "production"},
    )
    assert intent.to_dict()["metadata"] == {"environment": "production"}
    with pytest.raises(FrozenInstanceError):
        intent.status = "changed"


@pytest.mark.parametrize("metadata", [
    {"token": "secret"}, {"raw_rules": "value"}, {"stack_trace": "value"},
    {"payload": {"rules": []}}, {"file_path": "C:\\private"},
])
def test_audit_intent_rejects_sensitive_or_complete_payload_metadata(metadata: object) -> None:
    with pytest.raises(ValueError):
        WorkflowStudioAuditIntent("draft_updated", "tenant-1", "workflow-1", "version-1", None, "actor-1", "draft", "draft_content_updated", NOW, metadata=metadata)


def test_audit_intent_contains_identifiers_not_workflow_body() -> None:
    payload = WorkflowStudioAuditIntent("draft_created", "tenant-1", "workflow-1", "version-1", None, "actor-1", "draft", "initial_draft", NOW).to_dict()
    assert set(payload) == {"event_type", "tenant_id", "workflow_id", "version_id", "publication_id", "actor_id", "status", "reason_code", "occurred_at", "correlation_id", "metadata"}
