"""Immutable provider-neutral principal identities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .contracts import (
    SecurityContract,
    TenantScope,
    bounded_string,
    optional_string,
    stable_id,
    validate_safe_metadata,
)
from .permissions import Permission, normalize_permissions
from .roles import Role, normalize_roles, resolve_role_permissions


class PrincipalType(str, Enum):
    USER = "user"
    SERVICE_ACCOUNT = "service_account"
    SYSTEM = "system"
    ANONYMOUS = "anonymous"


@dataclass(frozen=True, slots=True)
class Principal(SecurityContract):
    principal_id: str
    principal_type: PrincipalType | str
    is_authenticated: bool
    tenant_scope: TenantScope = field(default_factory=TenantScope)
    roles: tuple[Role | str, ...] = ()
    explicit_permissions: tuple[Permission | str, ...] = ()
    display_name: str | None = None
    authentication_method: str = "unspecified"
    metadata: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "principal_id", stable_id(self.principal_id, "principal_id"))
        try:
            principal_type = self.principal_type if isinstance(self.principal_type, PrincipalType) else PrincipalType(self.principal_type)
        except (TypeError, ValueError):
            raise ValueError("principal_type is invalid") from None
        object.__setattr__(self, "principal_type", principal_type)
        if not isinstance(self.is_authenticated, bool):
            raise ValueError("is_authenticated must be a boolean")
        if not isinstance(self.tenant_scope, TenantScope):
            raise ValueError("tenant_scope must be a TenantScope")
        roles = normalize_roles(self.roles)
        explicit = normalize_permissions(self.explicit_permissions)
        if principal_type == PrincipalType.ANONYMOUS:
            if self.is_authenticated or roles or explicit or self.tenant_scope.tenant_ids:
                raise ValueError("anonymous principal cannot carry authenticated scope")
        elif not self.is_authenticated:
            raise ValueError("non-anonymous principal must be authenticated")
        if principal_type == PrincipalType.SERVICE_ACCOUNT and any(role != Role.SERVICE_ACCOUNT for role in roles):
            raise ValueError("service account roles are invalid")
        if principal_type != PrincipalType.SERVICE_ACCOUNT and Role.SERVICE_ACCOUNT in roles:
            raise ValueError("service_account role requires service account identity")
        object.__setattr__(self, "roles", roles)
        object.__setattr__(self, "explicit_permissions", explicit)
        object.__setattr__(self, "display_name", optional_string(self.display_name, "display_name"))
        object.__setattr__(
            self,
            "authentication_method",
            bounded_string(self.authentication_method, "authentication_method", maximum=64),
        )
        object.__setattr__(self, "metadata", validate_safe_metadata(self.metadata))

    @property
    def effective_permissions(self) -> tuple[Permission, ...]:
        if self.principal_type == PrincipalType.SERVICE_ACCOUNT:
            return tuple(self.explicit_permissions)
        return normalize_permissions((*resolve_role_permissions(self.roles), *self.explicit_permissions))


def anonymous_principal() -> Principal:
    return Principal(
        principal_id="anonymous",
        principal_type=PrincipalType.ANONYMOUS,
        is_authenticated=False,
        authentication_method="none",
    )


def service_account_principal(
    principal_id: str,
    *,
    tenant_scope: TenantScope | None = None,
    permissions: tuple[Permission | str, ...] = (),
) -> Principal:
    return Principal(
        principal_id=principal_id,
        principal_type=PrincipalType.SERVICE_ACCOUNT,
        is_authenticated=True,
        tenant_scope=tenant_scope or TenantScope(),
        roles=(Role.SERVICE_ACCOUNT,),
        explicit_permissions=permissions,
        authentication_method="service_account",
    )


def system_principal(principal_id: str, *, tenant_scope: TenantScope) -> Principal:
    return Principal(
        principal_id=principal_id,
        principal_type=PrincipalType.SYSTEM,
        is_authenticated=True,
        tenant_scope=tenant_scope,
        authentication_method="trusted_system",
    )

