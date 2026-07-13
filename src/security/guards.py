"""Pure authorization guard over the v1 policy evaluator."""

from __future__ import annotations

from .context import AuthorizationContext, AuthorizationMode
from .contracts import ResourceScope
from .decisions import AuthorizationDecision, DecisionReason, PolicyResult
from .permissions import Permission
from .policies import POLICY_VERSION, evaluate_authorization
from .principals import Principal
from .requests import AuthorizationRequest


def _denied(
    context: AuthorizationContext,
    request: AuthorizationRequest,
    reason: DecisionReason,
) -> AuthorizationDecision:
    principal_id = context.principal.principal_id if context.principal is not None else None
    permission = request.required_permission if isinstance(request.required_permission, Permission) else None
    tenant_id = request.resource_tenant_id or request.requested_tenant_id or context.active_tenant_id
    return AuthorizationDecision(
        result=PolicyResult.DENY,
        reason=reason,
        permission=permission,
        principal_id=principal_id,
        tenant_id=tenant_id,
        policy_version=POLICY_VERSION,
    )


class PermissionGuard:
    """Translate resource intent into one centralized policy decision."""

    def evaluate(
        self,
        subject: Principal | AuthorizationContext | None,
        request: AuthorizationRequest,
    ) -> AuthorizationDecision:
        if not isinstance(request, AuthorizationRequest):
            raise ValueError("request must be an AuthorizationRequest")
        if isinstance(subject, AuthorizationContext):
            context = subject
        elif subject is None or isinstance(subject, Principal):
            active_tenant = request.requested_tenant_id or request.resource_tenant_id
            context = AuthorizationContext(
                principal=subject,
                active_tenant_id=active_tenant,
                mode=AuthorizationMode.AUTHENTICATED,
            )
        else:
            raise ValueError("subject must be a Principal, AuthorizationContext, or null")

        if request.required_permission is None:
            return _denied(context, request, DecisionReason.INVALID_PERMISSION)
        if (
            request.requested_tenant_id is not None
            and request.resource_tenant_id is not None
            and request.requested_tenant_id != request.resource_tenant_id
        ):
            return _denied(context, request, DecisionReason.TENANT_DENIED)

        tenant_id = request.resource_tenant_id or request.requested_tenant_id or context.active_tenant_id
        resource = ResourceScope(
            resource_type=request.resource_type or "resource",
            tenant_id=tenant_id,
            resource_id=request.resource_id,
        )
        return evaluate_authorization(context, request.required_permission, resource)

    def __call__(
        self,
        subject: Principal | AuthorizationContext | None,
        request: AuthorizationRequest,
    ) -> AuthorizationDecision:
        return self.evaluate(subject, request)


AuthorizationGuard = PermissionGuard
