import pytest
from src.api.document_intelligence.errors import DocumentIntelligenceAPIError
from src.api.document_intelligence.routers.workflow_studio import create_workflow_definition, update_workflow_version
from .workflow_studio_helpers import RULES, app, create_payload, request


def test_full_draft_replacement_requires_optimistic_revision_and_rejects_authority_fields():
    application = app()
    create_workflow_definition(request(application, method="POST"), create_payload())
    updated = update_workflow_version("workflow-1", "version-1", request(application, method="PATCH"), {"expected_revision": 1, "change_summary": "Safe replacement.", "rules": RULES})
    assert updated["data"]["revision"] == 2
    with pytest.raises(DocumentIntelligenceAPIError) as conflict:
        update_workflow_version("workflow-1", "version-1", request(application, method="PATCH"), {"expected_revision": 1, "change_summary": "Stale.", "rules": RULES})
    assert conflict.value.code == "revision_conflict"
    with pytest.raises(DocumentIntelligenceAPIError) as authority:
        create_workflow_definition(request(application, method="POST"), {**create_payload("workflow-2", "version-2"), "tenant_id": "tenant-other"})
    assert authority.value.code == "invalid_request"
