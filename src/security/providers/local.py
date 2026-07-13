"""Deterministic local, demo, and test identity provider."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from types import MappingProxyType

from ..contracts import TenantScope, stable_id
from ..permissions import Permission
from ..principals import Principal, PrincipalType, anonymous_principal, service_account_principal
from ..roles import Role
from .contracts import (
    IdentityProviderResult,
    IdentityResolutionReason,
    IdentityResolutionStatus,
)


class LocalProviderMode(str, Enum):
    LOCAL_DEVELOPMENT = "local_development"
    DEMO = "demo"
    TEST = "test"


def _local_user(principal_id: str, role: Role, tenant_id: str) -> Principal:
    return Principal(
        principal_id=principal_id,
        principal_type=PrincipalType.USER,
        is_authenticated=True,
        tenant_scope=TenantScope((tenant_id,)),
        roles=(role,),
        display_name=role.value.replace("_", " ").title(),
        authentication_method="local_demo",
        metadata={"provider_mode": "local"},
    )


def local_demo_principals(tenant_id: str = "tenant-demo") -> Mapping[str, Principal]:
    """Return a fresh, deterministic local-only principal catalog."""

    safe_tenant = stable_id(tenant_id, "tenant_id")
    principals = {
        "platform-admin": Principal(
            principal_id="platform-admin",
            principal_type=PrincipalType.USER,
            is_authenticated=True,
            tenant_scope=TenantScope((safe_tenant,)),
            roles=(Role.PLATFORM_ADMIN,),
            display_name="Platform Admin",
            authentication_method="local_demo",
            metadata={"provider_mode": "local"},
        ),
        "tenant-admin": _local_user("tenant-admin", Role.TENANT_ADMIN, safe_tenant),
        "reviewer": _local_user("reviewer", Role.REVIEWER, safe_tenant),
        "viewer": _local_user("viewer", Role.VIEWER, safe_tenant),
        "service-account": service_account_principal(
            "service-account",
            tenant_scope=TenantScope((safe_tenant,)),
            permissions=(Permission.DOCUMENT_INGEST,),
        ),
    }
    return MappingProxyType(principals)


class LocalIdentityProvider:
    """Explicit local-only provider with no credential or token behavior."""

    def __init__(
        self,
        principals: Mapping[str, Principal],
        *,
        mode: LocalProviderMode | str,
    ) -> None:
        try:
            safe_mode = mode if isinstance(mode, LocalProviderMode) else LocalProviderMode(mode)
        except (TypeError, ValueError):
            raise ValueError("local provider mode is invalid or not allowed") from None
        if not isinstance(principals, Mapping):
            raise ValueError("principals must be a mapping")
        validated: dict[str, Principal] = {}
        for identity_id, principal in principals.items():
            safe_id = stable_id(identity_id, "identity_id")
            if not isinstance(principal, Principal) or principal.principal_type == PrincipalType.ANONYMOUS:
                raise ValueError("local provider principals must be authenticated principals")
            validated[safe_id] = principal
        self._mode = safe_mode
        self._principals = MappingProxyType(dict(sorted(validated.items())))

    @property
    def mode(self) -> LocalProviderMode:
        return self._mode

    def resolve(self, identity_id: str | None) -> IdentityProviderResult:
        metadata = {"provider_mode": self._mode.value}
        if identity_id is None or identity_id == "anonymous":
            return IdentityProviderResult(
                status=IdentityResolutionStatus.UNAUTHENTICATED,
                reason=IdentityResolutionReason.ANONYMOUS_IDENTITY,
                principal=anonymous_principal(),
                metadata=metadata,
            )
        try:
            safe_id = stable_id(identity_id, "identity_id")
        except ValueError:
            return IdentityProviderResult(
                status=IdentityResolutionStatus.DENIED,
                reason=IdentityResolutionReason.INVALID_REQUEST,
                metadata=metadata,
            )
        principal = self._principals.get(safe_id)
        if principal is None:
            return IdentityProviderResult(
                status=IdentityResolutionStatus.DENIED,
                reason=IdentityResolutionReason.UNKNOWN_IDENTITY,
                metadata=metadata,
            )
        return IdentityProviderResult(
            status=IdentityResolutionStatus.RESOLVED,
            reason=IdentityResolutionReason.IDENTITY_RESOLVED,
            principal=principal,
            metadata=metadata,
        )


def create_local_demo_provider(
    tenant_id: str = "tenant-demo",
    *,
    mode: LocalProviderMode | str = LocalProviderMode.DEMO,
) -> LocalIdentityProvider:
    return LocalIdentityProvider(local_demo_principals(tenant_id), mode=mode)
