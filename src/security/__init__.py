"""Public provider-neutral security contract surface."""

from .context import AuthorizationContext, AuthorizationMode
from .contracts import ActorAttribution, ResourceScope, SecurityContract, TenantScope
from .decisions import AuthorizationDecision, DecisionReason, PolicyResult
from .errors import SecurityError, SecurityErrorCode
from .guards import AuthorizationGuard, PermissionGuard
from .permissions import PERMISSION_CATALOG, Permission, normalize_permissions, permission_value
from .policies import POLICY_VERSION, evaluate_authorization, is_allowed
from .principals import (
    Principal,
    PrincipalType,
    anonymous_principal,
    service_account_principal,
    system_principal,
)
from .roles import ROLE_CATALOG, ROLE_PERMISSIONS, Role, permissions_for_role, resolve_role_permissions
from .requests import AuthorizationRequest

__all__ = [
    "ActorAttribution",
    "AuthorizationContext",
    "AuthorizationDecision",
    "AuthorizationGuard",
    "AuthorizationMode",
    "AuthorizationRequest",
    "DecisionReason",
    "PERMISSION_CATALOG",
    "POLICY_VERSION",
    "Permission",
    "PermissionGuard",
    "PolicyResult",
    "Principal",
    "PrincipalType",
    "ROLE_CATALOG",
    "ROLE_PERMISSIONS",
    "ResourceScope",
    "Role",
    "SecurityContract",
    "SecurityError",
    "SecurityErrorCode",
    "TenantScope",
    "anonymous_principal",
    "evaluate_authorization",
    "is_allowed",
    "normalize_permissions",
    "permission_value",
    "permissions_for_role",
    "resolve_role_permissions",
    "service_account_principal",
    "system_principal",
]
