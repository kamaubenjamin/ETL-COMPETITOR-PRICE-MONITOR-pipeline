"""Privacy-safe authorization decision contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import SecurityContract, optional_string, stable_id
from .permissions import Permission, permission_value


class PolicyResult(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class DecisionReason(str, Enum):
    ALLOWED = "allowed"
    MISSING_IDENTITY = "missing_identity"
    UNAUTHENTICATED = "unauthenticated"
    INVALID_PERMISSION = "invalid_permission"
    INVALID_SCOPE = "invalid_scope"
    EMPTY_TENANT_SCOPE = "empty_tenant_scope"
    TENANT_DENIED = "tenant_denied"
    PERMISSION_DENIED = "permission_denied"
    CROSS_TENANT_NOT_ENABLED = "cross_tenant_not_enabled"
    SERVICE_ACCOUNT_SCOPE_REQUIRED = "service_account_scope_required"


@dataclass(frozen=True, slots=True)
class AuthorizationDecision(SecurityContract):
    result: PolicyResult | str
    reason: DecisionReason | str
    permission: Permission | str | None
    principal_id: str | None = None
    tenant_id: str | None = None
    requires_audit: bool = False
    policy_version: str = "security-v1"

    def __post_init__(self) -> None:
        try:
            result = self.result if isinstance(self.result, PolicyResult) else PolicyResult(self.result)
            reason = self.reason if isinstance(self.reason, DecisionReason) else DecisionReason(self.reason)
        except (TypeError, ValueError):
            raise ValueError("decision result or reason is invalid") from None
        object.__setattr__(self, "result", result)
        object.__setattr__(self, "reason", reason)
        if self.permission is not None:
            object.__setattr__(self, "permission", permission_value(self.permission))
        if self.principal_id is not None:
            object.__setattr__(self, "principal_id", stable_id(self.principal_id, "principal_id"))
        if self.tenant_id is not None:
            object.__setattr__(self, "tenant_id", stable_id(self.tenant_id, "tenant_id"))
        if not isinstance(self.requires_audit, bool):
            raise ValueError("requires_audit must be a boolean")
        object.__setattr__(self, "policy_version", optional_string(self.policy_version, "policy_version", maximum=64))
        if result == PolicyResult.ALLOW and reason != DecisionReason.ALLOWED:
            raise ValueError("allowed decision requires allowed reason")
        if result == PolicyResult.DENY and reason == DecisionReason.ALLOWED:
            raise ValueError("denied decision cannot use allowed reason")

    @property
    def allowed(self) -> bool:
        return self.result == PolicyResult.ALLOW

