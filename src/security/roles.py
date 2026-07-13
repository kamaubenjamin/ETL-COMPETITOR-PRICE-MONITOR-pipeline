"""Deterministic role catalog and permission resolution."""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType
from typing import Any

from .permissions import Permission, normalize_permissions


class Role(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    OPERATIONS_MANAGER = "operations_manager"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
    SERVICE_ACCOUNT = "service_account"


_VIEWER = frozenset(
    {
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_LIST,
        Permission.WORKFLOW_READ,
    }
)
_REVIEWER = _VIEWER | {Permission.DOCUMENT_REVIEW}
_OPERATIONS_MANAGER = _REVIEWER | {
    Permission.DOCUMENT_APPROVE,
    Permission.WORKFLOW_RUN,
}
_TENANT_ADMIN = _OPERATIONS_MANAGER | {
    Permission.DOCUMENT_INGEST,
    Permission.DOCUMENT_EXPORT,
    Permission.AUDIT_READ,
    Permission.TENANT_ADMIN,
    Permission.USER_ADMIN,
}

ROLE_PERMISSIONS = MappingProxyType(
    {
        Role.PLATFORM_ADMIN: frozenset(Permission),
        Role.TENANT_ADMIN: frozenset(_TENANT_ADMIN),
        Role.OPERATIONS_MANAGER: frozenset(_OPERATIONS_MANAGER),
        Role.REVIEWER: frozenset(_REVIEWER),
        Role.VIEWER: frozenset(_VIEWER),
        Role.SERVICE_ACCOUNT: frozenset(),
    }
)
ROLE_CATALOG = tuple(role.value for role in Role)


def role_value(value: Any) -> Role:
    try:
        return value if isinstance(value, Role) else Role(value)
    except (TypeError, ValueError):
        raise ValueError("role is invalid") from None


def normalize_roles(values: Any) -> tuple[Role, ...]:
    if isinstance(values, (str, Role)):
        raise ValueError("roles must be a collection")
    try:
        roles = {role_value(item) for item in values}
    except TypeError:
        raise ValueError("roles must be a collection") from None
    return tuple(sorted(roles, key=lambda role: role.value))


def permissions_for_role(role: Role | str) -> tuple[Permission, ...]:
    return tuple(sorted(ROLE_PERMISSIONS[role_value(role)], key=lambda permission: permission.value))


def resolve_role_permissions(roles: Any) -> tuple[Permission, ...]:
    resolved: set[Permission] = set()
    for role in normalize_roles(roles):
        resolved.update(ROLE_PERMISSIONS[role])
    return normalize_permissions(resolved)

