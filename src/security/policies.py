"""Pure default-deny v1 authorization policy catalog."""

from __future__ import annotations

from .context import AuthorizationContext
from .contracts import ResourceScope
from .decisions import AuthorizationDecision, DecisionReason, PolicyResult
from .permissions import Permission, permission_value
from .principals import PrincipalType
from .roles import Role


POLICY_VERSION = "security-v1"


def _decision(
    context: AuthorizationContext,
    permission: Permission | None,
    resource: ResourceScope | None,
    reason: DecisionReason,
    *,
    allowed: bool = False,
    requires_audit: bool = False,
) -> AuthorizationDecision:
    principal_id = context.principal.principal_id if context.principal is not None else None
    tenant_id = resource.tenant_id if resource is not None else context.active_tenant_id
    return AuthorizationDecision(
        result=PolicyResult.ALLOW if allowed else PolicyResult.DENY,
        reason=reason,
        permission=permission,
        principal_id=principal_id,
        tenant_id=tenant_id,
        requires_audit=requires_audit,
        policy_version=POLICY_VERSION,
    )


def evaluate_authorization(
    context: AuthorizationContext,
    permission: Permission | str,
    resource: ResourceScope,
) -> AuthorizationDecision:
    """Evaluate one permission against one tenant-scoped resource."""

    if not isinstance(context, AuthorizationContext):
        raise ValueError("context must be an AuthorizationContext")
    try:
        required = permission_value(permission)
    except ValueError:
        return _decision(context, None, resource if isinstance(resource, ResourceScope) else None, DecisionReason.INVALID_PERMISSION)
    if not isinstance(resource, ResourceScope):
        return _decision(context, required, None, DecisionReason.INVALID_SCOPE)
    principal = context.principal
    if principal is None:
        return _decision(context, required, resource, DecisionReason.MISSING_IDENTITY)
    if not principal.is_authenticated or principal.principal_type == PrincipalType.ANONYMOUS:
        return _decision(context, required, resource, DecisionReason.UNAUTHENTICATED)
    if resource.tenant_id is None or context.active_tenant_id is None:
        return _decision(context, required, resource, DecisionReason.INVALID_SCOPE)

    tenant_memberships = principal.tenant_scope.tenant_ids
    is_platform_admin = Role.PLATFORM_ADMIN in principal.roles
    cross_tenant = (
        context.active_tenant_id != resource.tenant_id
        or context.active_tenant_id not in tenant_memberships
        or resource.tenant_id not in tenant_memberships
    )
    if principal.principal_type == PrincipalType.SERVICE_ACCOUNT and not tenant_memberships:
        return _decision(context, required, resource, DecisionReason.SERVICE_ACCOUNT_SCOPE_REQUIRED)
    if not tenant_memberships and not is_platform_admin:
        return _decision(context, required, resource, DecisionReason.EMPTY_TENANT_SCOPE)
    if cross_tenant:
        if not is_platform_admin:
            return _decision(context, required, resource, DecisionReason.TENANT_DENIED)
        if not context.allow_cross_tenant:
            return _decision(context, required, resource, DecisionReason.CROSS_TENANT_NOT_ENABLED)

    if required not in principal.effective_permissions:
        return _decision(context, required, resource, DecisionReason.PERMISSION_DENIED)
    return _decision(
        context,
        required,
        resource,
        DecisionReason.ALLOWED,
        allowed=True,
        requires_audit=cross_tenant,
    )


def is_allowed(context: AuthorizationContext, permission: Permission | str, resource: ResourceScope) -> bool:
    return evaluate_authorization(context, permission, resource).allowed

