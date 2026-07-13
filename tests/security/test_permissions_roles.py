import pytest

from src.security import (
    PERMISSION_CATALOG,
    ROLE_PERMISSIONS,
    Permission,
    Role,
    permissions_for_role,
    resolve_role_permissions,
)


EXPECTED_PERMISSIONS = (
    "document:read",
    "document:list",
    "document:ingest",
    "document:review",
    "document:approve",
    "document:export",
    "document:admin",
    "workflow:read",
    "workflow:run",
    "audit:read",
    "tenant:admin",
    "user:admin",
)


def test_permission_catalog_is_exact():
    assert PERMISSION_CATALOG == EXPECTED_PERMISSIONS


def test_viewer_reviewer_manager_and_tenant_admin_resolve_exactly():
    viewer = set(permissions_for_role(Role.VIEWER))
    assert viewer == {Permission.DOCUMENT_READ, Permission.DOCUMENT_LIST, Permission.WORKFLOW_READ}
    assert set(permissions_for_role(Role.REVIEWER)) == viewer | {Permission.DOCUMENT_REVIEW}
    manager = set(permissions_for_role(Role.OPERATIONS_MANAGER))
    assert manager == viewer | {Permission.DOCUMENT_REVIEW, Permission.DOCUMENT_APPROVE, Permission.WORKFLOW_RUN}
    assert set(permissions_for_role(Role.TENANT_ADMIN)) == manager | {
        Permission.DOCUMENT_INGEST,
        Permission.DOCUMENT_EXPORT,
        Permission.AUDIT_READ,
        Permission.TENANT_ADMIN,
        Permission.USER_ADMIN,
    }


def test_platform_admin_has_catalog_and_service_account_has_none():
    assert set(ROLE_PERMISSIONS[Role.PLATFORM_ADMIN]) == set(Permission)
    assert permissions_for_role(Role.SERVICE_ACCOUNT) == ()


def test_multi_role_resolution_is_sorted_and_deduplicated():
    resolved = resolve_role_permissions((Role.REVIEWER, Role.VIEWER, Role.REVIEWER))
    assert resolved == tuple(sorted(set(resolved), key=lambda permission: permission.value))


def test_unknown_role_rejects():
    with pytest.raises(ValueError, match="role is invalid"):
        permissions_for_role("owner")

