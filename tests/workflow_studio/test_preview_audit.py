import pytest
from src.workflow_studio import WorkflowPreviewAuditIntent
NOW="2026-07-14T10:00:00+00:00"
def test_preview_audit_contains_only_safe_identifiers():
    payload=WorkflowPreviewAuditIntent("preview_completed","tenant-1","workflow-1","version-1","actor-1","fixture-1","completed","preview_completed",NOW,"request-1").to_dict(); assert "fixture" not in payload; assert payload["fixture_label"]=="fixture-1"
def test_preview_audit_rejects_unknown_free_text():
    with pytest.raises(ValueError): WorkflowPreviewAuditIntent("preview_completed","tenant-1","workflow-1","version-1","actor-1","fixture-1","completed","raw exception /secret",NOW)
