import pytest

from src.security import Permission, PrincipalType, Role
from src.security.providers import (
    IdentityResolutionReason,
    IdentityResolutionStatus,
    LocalIdentityProvider,
    LocalProviderMode,
    create_local_demo_provider,
    local_demo_principals,
)


def test_known_identity_resolves_deterministically():
    provider = create_local_demo_provider("tenant-a")
    first = provider.resolve("viewer")
    second = provider.resolve("viewer")
    assert first == second
    assert first.resolved
    assert first.principal.roles == (Role.VIEWER,)
    assert first.principal.tenant_scope.tenant_ids == ("tenant-a",)


def test_unknown_and_invalid_identity_fail_closed_without_echo():
    provider = create_local_demo_provider()
    unknown = provider.resolve("does-not-exist")
    invalid = provider.resolve("bad identity with spaces")
    assert (unknown.status, unknown.reason) == (
        IdentityResolutionStatus.DENIED,
        IdentityResolutionReason.UNKNOWN_IDENTITY,
    )
    assert invalid.reason == IdentityResolutionReason.INVALID_REQUEST
    assert "does-not-exist" not in str(unknown.to_dict())
    assert "bad identity" not in str(invalid.to_dict())


def test_explicit_anonymous_resolution_is_unauthenticated():
    result = create_local_demo_provider().resolve(None)
    assert result.status == IdentityResolutionStatus.UNAUTHENTICATED
    assert result.principal.principal_type == PrincipalType.ANONYMOUS
    assert not result.principal.is_authenticated


def test_local_provider_rejects_production_or_unknown_mode():
    with pytest.raises(ValueError, match="invalid or not allowed"):
        LocalIdentityProvider(local_demo_principals(), mode="production")


def test_demo_catalog_has_explicit_least_privilege_service_account():
    principals = local_demo_principals("tenant-a")
    service = principals["service-account"]
    assert service.principal_type == PrincipalType.SERVICE_ACCOUNT
    assert service.explicit_permissions == (Permission.DOCUMENT_INGEST,)
    assert service.tenant_scope.tenant_ids == ("tenant-a",)
    assert principals["platform-admin"].roles == (Role.PLATFORM_ADMIN,)


def test_provider_defensively_copies_configuration():
    configured = dict(local_demo_principals())
    provider = LocalIdentityProvider(configured, mode=LocalProviderMode.TEST)
    configured.clear()
    assert provider.resolve("viewer").resolved
