from src.api.document_intelligence.providers.workflow_studio_provider import GOVERNANCE_ONLY_NOTICE, WorkflowStudioAPIProvider
from src.workflow_studio import SuccessfulWorkflowPreviewAdapter
from .workflow_studio_helpers import create_payload


def test_publication_is_governance_only_and_deactivation_does_not_reactivate():
    provider = WorkflowStudioAPIProvider(preview_adapter=SuccessfulWorkflowPreviewAdapter())
    provider.create_workflow("tenant-demo", "platform-admin", create_payload(), "r1")
    provider.validate("tenant-demo", "workflow-1", "version-1", "platform-admin")
    provider.test("tenant-demo", "workflow-1", "version-1", "platform-admin", {"inline_sample": {"items": [1]}}, "r2")
    provider.submit("tenant-demo", "workflow-1", "version-1", "platform-admin", "r3")
    provider.approve("tenant-demo", "workflow-1", "version-1", "tenant-admin", {"expected_revision": 3})
    result = provider.publish("tenant-demo", "workflow-1", "version-1", "tenant-admin", {"expected_version_revision": 4, "expected_definition_revision": 1}, "r4")
    assert result["notice"] == GOVERNANCE_ONLY_NOTICE
    deactivated = provider.deactivate("tenant-demo", "workflow-1", "tenant-admin", {"expected_publication_revision": 1, "expected_definition_revision": 2}, "r5")
    assert deactivated["publication"]["status"] == "inactive"
    assert provider.store.find_active_publication("tenant-demo", "workflow-1") is None
