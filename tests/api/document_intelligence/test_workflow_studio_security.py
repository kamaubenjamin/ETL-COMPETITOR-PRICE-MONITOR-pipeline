import pytest
from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.routers.workflow_studio import create_workflow_definition, get_workflow_definition
from .workflow_studio_helpers import app, create_payload, request


def test_mutations_fail_closed_and_cross_tenant_reads_are_concealed():
    with pytest.raises(DocumentIntelligenceAPIError) as disabled:
        create_workflow_definition(request(create_document_intelligence_app(), identity=None, tenant=None, method="POST"), create_payload())
    assert disabled.value.code == "workflow_management_not_enabled"
    application = app()
    create_workflow_definition(request(application, method="POST"), create_payload())
    with pytest.raises(DocumentIntelligenceAPIError) as denied:
        create_workflow_definition(request(application, "viewer", method="POST"), create_payload("workflow-2", "version-2"))
    assert denied.value.status_code == 403
    with pytest.raises(DocumentIntelligenceAPIError) as concealed:
        get_workflow_definition("workflow-1", request(application, tenant="tenant-other"))
    assert concealed.value.status_code == 404
