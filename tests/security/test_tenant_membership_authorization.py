import pytest

from src.api.document_intelligence.supabase_auth import UAT_ROLE_PERMISSIONS
from src.security import Permission
from tests.api.document_intelligence.asgi_client import asgi_request
from tests.api.document_intelligence.supabase_auth_helpers import TENANT_ID, application, membership, token


@pytest.mark.parametrize("rows", [[], membership(status="inactive"), membership(tenant_status="inactive"), membership(role="unknown"), membership() * 2])
def test_invalid_or_ambiguous_membership_fails_closed(rows):
    response = asgi_request(
        application(rows=rows), "GET", "/api/v1/session", headers={"Authorization": f"Bearer {token()}"}
    )
    assert response.status_code == 403


def test_role_permission_mapping_is_centralized_and_bounded():
    assert set(UAT_ROLE_PERMISSIONS) == {"owner", "reviewer", "viewer"}
    assert Permission.WORKFLOW_ADMIN in UAT_ROLE_PERMISSIONS["owner"]
    assert Permission.WORKFLOW_TEST in UAT_ROLE_PERMISSIONS["reviewer"]
    assert Permission.WORKFLOW_CREATE not in UAT_ROLE_PERMISSIONS["reviewer"]
    assert UAT_ROLE_PERMISSIONS["viewer"] >= {Permission.WORKFLOW_READ}
    assert Permission.WORKFLOW_TEST not in UAT_ROLE_PERMISSIONS["viewer"]


def test_browser_role_and_permission_headers_never_expand_authority():
    response = asgi_request(
        application(rows=membership(role="viewer")),
        "POST",
        "/api/v1/workflow-definitions",
        headers={
            "Authorization": f"Bearer {token()}",
            "x-role": "owner",
            "x-permissions": "workflow:admin",
        },
        json_body={"name": "Unauthorized", "description": "Must remain denied"},
    )
    assert response.status_code == 403
