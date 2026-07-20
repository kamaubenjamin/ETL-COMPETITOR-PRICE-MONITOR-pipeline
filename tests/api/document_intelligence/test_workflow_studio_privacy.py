import pytest
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.routers.workflow_studio import create_workflow_definition, get_workflow_audit
from .workflow_studio_helpers import app, create_payload, request


def test_code_like_fields_and_raw_authority_are_rejected_without_reflection():
    application = app()
    unsafe = {**create_payload(), "rules": [{"rule_id": "r", "name": "x", "stage": "s", "order": 0, "actions": [{"action_id": "a", "action_type": "filter", "operation_name": "filter", "operation_version": "1", "arguments": {"command": "powershell secret"}}]}]}
    with pytest.raises(DocumentIntelligenceAPIError) as error:
        create_workflow_definition(request(application, method="POST"), unsafe)
    assert error.value.message == "Request body is invalid."
    assert "powershell" not in error.value.message
    create_workflow_definition(request(application, method="POST"), create_payload())
    audit = get_workflow_audit("workflow-1", request(application), 100, 0)
    assert "tenant_id" not in str(audit["data"])
    assert "rules" not in str(audit["data"])
