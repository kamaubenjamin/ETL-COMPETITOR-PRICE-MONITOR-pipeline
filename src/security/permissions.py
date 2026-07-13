"""Fixed v1 permission catalog."""

from __future__ import annotations

from enum import Enum
from typing import Any


class Permission(str, Enum):
    DOCUMENT_READ = "document:read"
    DOCUMENT_LIST = "document:list"
    DOCUMENT_INGEST = "document:ingest"
    DOCUMENT_REVIEW = "document:review"
    DOCUMENT_APPROVE = "document:approve"
    DOCUMENT_EXPORT = "document:export"
    DOCUMENT_ADMIN = "document:admin"
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_RUN = "workflow:run"
    AUDIT_READ = "audit:read"
    TENANT_ADMIN = "tenant:admin"
    USER_ADMIN = "user:admin"


PERMISSION_CATALOG = tuple(permission.value for permission in Permission)


def permission_value(value: Any) -> Permission:
    try:
        return value if isinstance(value, Permission) else Permission(value)
    except (TypeError, ValueError):
        raise ValueError("permission is invalid") from None


def normalize_permissions(values: Any) -> tuple[Permission, ...]:
    if isinstance(values, (str, Permission)):
        raise ValueError("permissions must be a collection")
    try:
        permissions = {permission_value(item) for item in values}
    except TypeError:
        raise ValueError("permissions must be a collection") from None
    return tuple(sorted(permissions, key=lambda permission: permission.value))

