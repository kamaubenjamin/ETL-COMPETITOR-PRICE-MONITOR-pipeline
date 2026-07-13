from dataclasses import FrozenInstanceError
import json

import pytest

from src.security import (
    Permission,
    Principal,
    PrincipalType,
    Role,
    TenantScope,
    anonymous_principal,
    service_account_principal,
    system_principal,
)


def test_user_principal_is_immutable_json_safe_and_deterministic():
    principal = Principal(
        "user-001",
        PrincipalType.USER,
        True,
        TenantScope(("tenant-b", "tenant-a", "tenant-a")),
        roles=(Role.VIEWER,),
        display_name="Operator One",
        authentication_method="local_test",
        metadata={"provider_code": "local"},
    )
    assert principal.tenant_scope.tenant_ids == ("tenant-a", "tenant-b")
    assert principal.effective_permissions == (
        Permission.DOCUMENT_LIST,
        Permission.DOCUMENT_READ,
        Permission.WORKFLOW_READ,
    )
    json.dumps(principal.to_dict())
    with pytest.raises(FrozenInstanceError):
        principal.principal_id = "changed"


def test_anonymous_principal_is_an_explicit_denied_identity():
    principal = anonymous_principal()
    assert principal.principal_type == PrincipalType.ANONYMOUS
    assert principal.is_authenticated is False
    assert principal.tenant_scope.tenant_ids == ()
    assert principal.effective_permissions == ()


def test_invalid_anonymous_and_unauthenticated_user_scope_reject():
    with pytest.raises(ValueError, match="anonymous"):
        Principal("anonymous", "anonymous", True, TenantScope(("tenant-a",)))
    with pytest.raises(ValueError, match="authenticated"):
        Principal("user-001", "user", False)


def test_service_account_has_only_explicit_permissions_and_scope():
    principal = service_account_principal(
        "svc-ingest",
        tenant_scope=TenantScope(("tenant-a",)),
        permissions=(Permission.DOCUMENT_INGEST,),
    )
    assert principal.principal_type == PrincipalType.SERVICE_ACCOUNT
    assert principal.roles == (Role.SERVICE_ACCOUNT,)
    assert principal.effective_permissions == (Permission.DOCUMENT_INGEST,)


def test_system_actor_is_explicit_and_has_no_implicit_permissions():
    principal = system_principal("system-workflow", tenant_scope=TenantScope(("tenant-a",)))
    assert principal.principal_type == PrincipalType.SYSTEM
    assert principal.authentication_method == "trusted_system"
    assert principal.effective_permissions == ()


def test_service_account_cannot_claim_interactive_role():
    with pytest.raises(ValueError, match="service account roles"):
        Principal(
            "svc-001",
            "service_account",
            True,
            TenantScope(("tenant-a",)),
            roles=(Role.TENANT_ADMIN,),
        )

