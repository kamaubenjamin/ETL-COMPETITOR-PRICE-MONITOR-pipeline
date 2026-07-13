import json

import pytest

from src.security import AuthorizationRequest, Permission


def test_authorization_request_is_immutable_json_safe_and_bounded():
    request = AuthorizationRequest(
        Permission.DOCUMENT_READ,
        requested_tenant_id="tenant-a",
        resource_tenant_id="tenant-a",
        resource_id="doc-001",
        resource_type="document",
        operation="read",
        action="read",
        metadata={"source": "test"},
    )
    assert request.required_permission == Permission.DOCUMENT_READ
    assert json.loads(json.dumps(request.to_dict()))["resource_id"] == "doc-001"
    with pytest.raises(Exception):
        request.resource_id = "doc-002"


@pytest.mark.parametrize("key", ["token", "credential_value", "stack_trace", "storage_path"])
def test_authorization_request_rejects_unsafe_metadata(key):
    with pytest.raises(ValueError, match="not allowed"):
        AuthorizationRequest(Permission.DOCUMENT_READ, metadata={key: "unsafe"})


def test_missing_and_unknown_permissions_remain_safe_guard_inputs():
    missing = AuthorizationRequest(None)
    unknown = AuthorizationRequest("document:delete")
    assert missing.to_dict()["required_permission"] is None
    assert unknown.to_dict()["required_permission"] == "document:delete"


def test_operation_and_action_cannot_conflict():
    with pytest.raises(ValueError, match="must agree"):
        AuthorizationRequest(Permission.DOCUMENT_READ, operation="read", action="approve")
