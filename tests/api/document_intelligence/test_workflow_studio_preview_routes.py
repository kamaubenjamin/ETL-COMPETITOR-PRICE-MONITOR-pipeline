from src.api.document_intelligence.routers.workflow_studio import create_workflow_definition, test_workflow_version as run_preview, validate_workflow_version
from .workflow_studio_helpers import app, create_payload, request


def test_preview_is_bounded_and_honestly_unavailable_without_runtime_execution():
    application = app()
    create_workflow_definition(request(application, method="POST"), create_payload())
    validation = validate_workflow_version("workflow-1", "version-1", request(application, method="POST"))
    preview = run_preview("workflow-1", "version-1", request(application, method="POST"), {"inline_sample": {"items": [1]}})
    assert validation["data"]["structurally_valid"] is True
    assert preview["data"]["status"] == "preview_unavailable"
    assert "audit_intents" not in preview["data"]
    assert "tenant_id" not in str(preview["data"])
