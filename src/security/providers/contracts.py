"""Provider-neutral identity resolution contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from ..contracts import SecurityContract, validate_safe_metadata
from ..principals import Principal, PrincipalType


class IdentityResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    UNAUTHENTICATED = "unauthenticated"
    DENIED = "denied"


class IdentityResolutionReason(str, Enum):
    IDENTITY_RESOLVED = "identity_resolved"
    ANONYMOUS_IDENTITY = "anonymous_identity"
    UNKNOWN_IDENTITY = "unknown_identity"
    PROVIDER_DISABLED = "provider_disabled"
    INVALID_REQUEST = "invalid_request"
    PROVIDER_UNAVAILABLE = "provider_unavailable"


@dataclass(frozen=True, slots=True)
class IdentityProviderResult(SecurityContract):
    status: IdentityResolutionStatus | str
    reason: IdentityResolutionReason | str
    principal: Principal | None = None
    metadata: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        try:
            status = self.status if isinstance(self.status, IdentityResolutionStatus) else IdentityResolutionStatus(self.status)
            reason = self.reason if isinstance(self.reason, IdentityResolutionReason) else IdentityResolutionReason(self.reason)
        except (TypeError, ValueError):
            raise ValueError("identity provider result is invalid") from None
        if self.principal is not None and not isinstance(self.principal, Principal):
            raise ValueError("principal must be a Principal or null")
        if status == IdentityResolutionStatus.RESOLVED:
            if self.principal is None or not self.principal.is_authenticated:
                raise ValueError("resolved identity requires an authenticated principal")
            if reason != IdentityResolutionReason.IDENTITY_RESOLVED:
                raise ValueError("resolved identity reason is invalid")
        elif status == IdentityResolutionStatus.UNAUTHENTICATED:
            if self.principal is None or self.principal.principal_type != PrincipalType.ANONYMOUS:
                raise ValueError("unauthenticated identity requires an anonymous principal")
            if reason != IdentityResolutionReason.ANONYMOUS_IDENTITY:
                raise ValueError("unauthenticated identity reason is invalid")
        elif self.principal is not None:
            raise ValueError("denied identity cannot include a principal")
        elif reason in (IdentityResolutionReason.IDENTITY_RESOLVED, IdentityResolutionReason.ANONYMOUS_IDENTITY):
            raise ValueError("denied identity reason is invalid")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "metadata", validate_safe_metadata(self.metadata))

    @property
    def resolved(self) -> bool:
        return self.status == IdentityResolutionStatus.RESOLVED


@runtime_checkable
class IdentityProvider(Protocol):
    """Read-only identity resolution boundary."""

    def resolve(self, identity_id: str | None) -> IdentityProviderResult:
        ...
