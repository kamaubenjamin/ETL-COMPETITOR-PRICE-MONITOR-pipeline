import json

import pytest

from src.security import (
    AuthorizationContext,
    Permission,
    Principal,
    ResourceScope,
    Role,
    SecurityError,
    TenantScope,
    evaluate_authorization,
)


@pytest.mark.parametrize(
    "key",
    ("token", "access_token", "password", "credential", "authorization", "stack_trace", "storage_path"),
)
def test_principal_metadata_rejects_sensitive_keys(key):
    with pytest.raises(ValueError, match="metadata key"):
        Principal(
            "user-001",
            "user",
            True,
            TenantScope(("tenant-a",)),
            roles=(Role.VIEWER,),
            metadata={key: "sensitive-value"},
        )


def test_metadata_rejects_nested_or_non_json_values():
    with pytest.raises(ValueError, match="JSON scalars"):
        Principal("user-001", "user", True, metadata={"claims": {"group": "admin"}})


def test_decision_serialization_contains_only_safe_bounded_fields():
    principal = Principal(
        "user-001",
        "user",
        True,
        TenantScope(("tenant-a",)),
        roles=(Role.VIEWER,),
        authentication_method="test",
    )
    decision = evaluate_authorization(
        AuthorizationContext(principal, "tenant-a", request_id="request-001"),
        Permission.DOCUMENT_READ,
        ResourceScope("document", tenant_id="tenant-a", resource_id="doc-001"),
    )
    payload = json.dumps(decision.to_dict()).lower()
    assert decision.allowed
    for forbidden in ("token", "credential", "password", "stack", "storage_path", "exception"):
        assert forbidden not in payload


def test_security_error_discards_unknown_or_raw_detail():
    error = SecurityError("provider said token=secret")
    assert error.to_dict() == {
        "code": "internal_error",
        "message": "Security operation could not be completed.",
    }
    assert "secret" not in str(error)

