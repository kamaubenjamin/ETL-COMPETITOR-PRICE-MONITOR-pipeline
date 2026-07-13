from src.security import (
    AuthorizationContext,
    AuthorizationRequest,
    DecisionReason,
    Permission,
    PermissionGuard,
    TenantScope,
    service_account_principal,
)
from src.security.providers import create_local_demo_provider


def resolved(identity):
    return create_local_demo_provider("tenant-a").resolve(identity).principal


def request(permission, tenant="tenant-a", **kwargs):
    return AuthorizationRequest(
        permission,
        requested_tenant_id=tenant,
        resource_tenant_id=kwargs.pop("resource_tenant_id", tenant),
        resource_type="document",
        resource_id="doc-001",
        **kwargs,
    )


def test_viewer_and_reviewer_permissions_are_tenant_scoped():
    guard = PermissionGuard()
    viewer = resolved("viewer")
    reviewer = resolved("reviewer")
    assert guard(viewer, request(Permission.DOCUMENT_LIST)).allowed
    assert guard(viewer, request(Permission.DOCUMENT_READ)).allowed
    assert guard(viewer, request(Permission.DOCUMENT_APPROVE)).reason == DecisionReason.PERMISSION_DENIED
    assert guard(reviewer, request(Permission.DOCUMENT_REVIEW)).allowed


def test_tenant_admin_allows_admin_permission_only_within_tenant():
    guard = PermissionGuard()
    admin = resolved("tenant-admin")
    assert guard(admin, request(Permission.TENANT_ADMIN)).allowed
    denied = guard(admin, request(Permission.TENANT_ADMIN, "tenant-b"))
    assert denied.reason == DecisionReason.TENANT_DENIED


def test_platform_admin_cross_tenant_requires_explicit_context_flag():
    guard = PermissionGuard()
    admin = resolved("platform-admin")
    cross_tenant = request(Permission.AUDIT_READ, "tenant-b")
    denied = guard(AuthorizationContext(admin, "tenant-b"), cross_tenant)
    allowed = guard(
        AuthorizationContext(admin, "tenant-b", allow_cross_tenant=True),
        cross_tenant,
    )
    assert denied.reason == DecisionReason.CROSS_TENANT_NOT_ENABLED
    assert allowed.allowed and allowed.requires_audit


def test_service_account_requires_explicit_permission_and_tenant_scope():
    guard = PermissionGuard()
    empty = service_account_principal("svc-empty")
    assert guard(empty, request(Permission.DOCUMENT_INGEST)).reason == DecisionReason.SERVICE_ACCOUNT_SCOPE_REQUIRED

    scoped = service_account_principal(
        "svc-ingest",
        tenant_scope=TenantScope(("tenant-a",)),
        permissions=(Permission.DOCUMENT_INGEST,),
    )
    assert guard(scoped, request(Permission.DOCUMENT_INGEST)).allowed
    assert guard(scoped, request(Permission.DOCUMENT_READ)).reason == DecisionReason.PERMISSION_DENIED
    assert guard(scoped, request(Permission.DOCUMENT_INGEST, "tenant-b")).reason == DecisionReason.TENANT_DENIED


def test_missing_anonymous_and_missing_permission_default_deny():
    guard = PermissionGuard()
    assert guard(None, request(Permission.DOCUMENT_READ)).reason == DecisionReason.MISSING_IDENTITY
    anonymous = create_local_demo_provider().resolve(None).principal
    assert guard(anonymous, request(Permission.DOCUMENT_READ)).reason == DecisionReason.UNAUTHENTICATED
    assert guard(resolved("viewer"), request(None)).reason == DecisionReason.INVALID_PERMISSION


def test_requested_tenant_cannot_disagree_with_resource_tenant():
    denied = PermissionGuard()(resolved("viewer"), request(Permission.DOCUMENT_READ, resource_tenant_id="tenant-b"))
    assert denied.reason == DecisionReason.TENANT_DENIED


def test_unknown_permission_denies_through_phase1_policy():
    decision = PermissionGuard()(resolved("viewer"), request("document:delete"))
    assert decision.reason == DecisionReason.INVALID_PERMISSION
    assert decision.to_dict()["principal_id"] == "viewer"
