from src.api.document_intelligence.routers.workflow_studio import (
    create_workflow_definition, get_workflow_definition, get_workflow_version,
    list_workflow_definitions, list_workflow_operations, list_workflow_versions,
)
from .workflow_studio_helpers import app, create_payload, request


def test_read_routes_use_safe_envelopes_and_tenant_scoped_records():
    application = app()
    create_workflow_definition(request(application, "tenant-admin", method="POST"), create_payload())
    collection = list_workflow_definitions(request(application), 50, 0)
    detail = get_workflow_definition("workflow-1", request(application))
    versions = list_workflow_versions("workflow-1", request(application), 50, 0)
    version = get_workflow_version("workflow-1", "version-1", request(application))
    operations = list_workflow_operations(request(application))
    assert collection["metadata"]["pagination"]["total"] == 1
    assert detail["data"]["workflow_id"] == "workflow-1"
    assert versions["data"][0]["version_id"] == version["data"]["version_id"]
    assert operations["data"] and "runtime_operation" not in operations["data"][0]
    assert "tenant_id" not in str(detail["data"])
