from dataclasses import FrozenInstanceError
import json

import pytest

from src.security import (
    AuthorizationContext,
    AuthorizationMode,
    Principal,
    PrincipalType,
    Role,
    TenantScope,
    anonymous_principal,
)


def _user():
    return Principal(
        "user-001",
        PrincipalType.USER,
        True,
        TenantScope(("tenant-a",)),
        roles=(Role.REVIEWER,),
        authentication_method="local_test",
    )


def test_context_and_actor_attribution_are_immutable_and_json_safe():
    context = AuthorizationContext(
        _user(),
        "tenant-a",
        AuthorizationMode.AUTHENTICATED,
        request_id="request-001",
        metadata={"correlation_id": "correlation-001"},
    )
    actor = context.actor_attribution()
    assert actor.to_dict() == {
        "principal_id": "user-001",
        "principal_type": "user",
        "tenant_id": "tenant-a",
        "request_id": "request-001",
    }
    json.dumps(context.to_dict())
    with pytest.raises(FrozenInstanceError):
        context.active_tenant_id = "tenant-b"


def test_missing_and_anonymous_contexts_have_no_actor_attribution():
    assert AuthorizationContext(None, "tenant-a").actor_attribution() is None
    assert AuthorizationContext(anonymous_principal(), None).actor_attribution() is None


def test_active_tenant_is_validated_but_not_treated_as_membership_proof():
    context = AuthorizationContext(_user(), "tenant-b")
    assert context.active_tenant_id == "tenant-b"


def test_context_rejects_unsafe_mode_and_metadata():
    with pytest.raises(ValueError, match="mode"):
        AuthorizationContext(_user(), "tenant-a", "browser")
    with pytest.raises(ValueError, match="metadata key"):
        AuthorizationContext(_user(), "tenant-a", metadata={"access_token": "secret-value"})

