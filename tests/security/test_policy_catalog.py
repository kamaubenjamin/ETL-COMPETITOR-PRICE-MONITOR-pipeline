from src.security import (
    AuthorizationContext,
    DecisionReason,
    Permission,
    Principal,
    PrincipalType,
    ResourceScope,
    Role,
    TenantScope,
    anonymous_principal,
    evaluate_authorization,
    service_account_principal,
)


def principal(role, tenants=("tenant-a",), *, principal_type=PrincipalType.USER, permissions=()):
    return Principal(
        f"principal-{role}",
        principal_type,
        True,
        TenantScope(tenants),
        roles=(role,),
        explicit_permissions=permissions,
        authentication_method="test",
    )


def scope(tenant="tenant-a"):
    return ResourceScope("document", tenant_id=tenant, resource_id="doc-001")


def test_missing_and_anonymous_identity_default_deny():
    missing = evaluate_authorization(AuthorizationContext(None, "tenant-a"), Permission.DOCUMENT_READ, scope())
    anonymous = evaluate_authorization(
        AuthorizationContext(anonymous_principal(), "tenant-a"), Permission.DOCUMENT_READ, scope()
    )
    assert (missing.allowed, missing.reason) == (False, DecisionReason.MISSING_IDENTITY)
    assert (anonymous.allowed, anonymous.reason) == (False, DecisionReason.UNAUTHENTICATED)


def test_viewer_allows_scoped_read_and_denies_review():
    context = AuthorizationContext(principal(Role.VIEWER), "tenant-a")
    assert evaluate_authorization(context, Permission.DOCUMENT_READ, scope()).allowed
    denied = evaluate_authorization(context, Permission.DOCUMENT_REVIEW, scope())
    assert (denied.allowed, denied.reason) == (False, DecisionReason.PERMISSION_DENIED)


def test_empty_tenant_scope_and_client_scope_broadening_deny():
    empty = AuthorizationContext(principal(Role.VIEWER, tenants=()), "tenant-a")
    denied_empty = evaluate_authorization(empty, Permission.DOCUMENT_READ, scope())
    assert denied_empty.reason == DecisionReason.EMPTY_TENANT_SCOPE

    broadened = AuthorizationContext(principal(Role.VIEWER), "tenant-b")
    denied_broadened = evaluate_authorization(broadened, Permission.DOCUMENT_READ, scope("tenant-b"))
    assert denied_broadened.reason == DecisionReason.TENANT_DENIED


def test_platform_admin_cross_tenant_requires_explicit_flag_and_audit():
    admin = principal(Role.PLATFORM_ADMIN, tenants=("tenant-a",))
    denied = evaluate_authorization(
        AuthorizationContext(admin, "tenant-b"), Permission.AUDIT_READ, scope("tenant-b")
    )
    allowed = evaluate_authorization(
        AuthorizationContext(admin, "tenant-b", allow_cross_tenant=True),
        Permission.AUDIT_READ,
        scope("tenant-b"),
    )
    assert denied.reason == DecisionReason.CROSS_TENANT_NOT_ENABLED
    assert allowed.allowed and allowed.requires_audit


def test_service_account_requires_explicit_scope_and_permission():
    empty = service_account_principal("svc-empty")
    denied_scope = evaluate_authorization(
        AuthorizationContext(empty, "tenant-a"), Permission.DOCUMENT_INGEST, scope()
    )
    assert denied_scope.reason == DecisionReason.SERVICE_ACCOUNT_SCOPE_REQUIRED

    scoped = service_account_principal(
        "svc-ingest",
        tenant_scope=TenantScope(("tenant-a",)),
        permissions=(Permission.DOCUMENT_INGEST,),
    )
    context = AuthorizationContext(scoped, "tenant-a")
    assert evaluate_authorization(context, Permission.DOCUMENT_INGEST, scope()).allowed
    assert evaluate_authorization(context, Permission.DOCUMENT_READ, scope()).reason == DecisionReason.PERMISSION_DENIED


def test_missing_resource_tenant_and_unknown_permission_deny_safely():
    context = AuthorizationContext(principal(Role.VIEWER), "tenant-a")
    invalid_scope = evaluate_authorization(context, Permission.DOCUMENT_READ, ResourceScope("document"))
    invalid_permission = evaluate_authorization(context, "document:delete", scope())
    assert invalid_scope.reason == DecisionReason.INVALID_SCOPE
    assert invalid_permission.reason == DecisionReason.INVALID_PERMISSION

