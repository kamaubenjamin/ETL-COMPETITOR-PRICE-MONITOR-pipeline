"""Immutable authorization context contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .contracts import ActorAttribution, SecurityContract, optional_string, stable_id, validate_safe_metadata
from .principals import Principal


class AuthorizationMode(str, Enum):
    LOCAL_PREVIEW = "local_preview"
    AUTHENTICATED = "authenticated"
    PRODUCTION = "production"
    INTERNAL = "internal"


@dataclass(frozen=True, slots=True)
class AuthorizationContext(SecurityContract):
    principal: Principal | None
    active_tenant_id: str | None = None
    mode: AuthorizationMode | str = AuthorizationMode.AUTHENTICATED
    allow_cross_tenant: bool = False
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.principal is not None and not isinstance(self.principal, Principal):
            raise ValueError("principal must be a Principal or null")
        if self.active_tenant_id is not None:
            object.__setattr__(self, "active_tenant_id", stable_id(self.active_tenant_id, "active_tenant_id"))
        try:
            mode = self.mode if isinstance(self.mode, AuthorizationMode) else AuthorizationMode(self.mode)
        except (TypeError, ValueError):
            raise ValueError("mode is invalid") from None
        object.__setattr__(self, "mode", mode)
        if not isinstance(self.allow_cross_tenant, bool):
            raise ValueError("allow_cross_tenant must be a boolean")
        object.__setattr__(self, "request_id", optional_string(self.request_id, "request_id", maximum=128))
        object.__setattr__(self, "metadata", validate_safe_metadata(self.metadata))

    def actor_attribution(self) -> ActorAttribution | None:
        if self.principal is None or not self.principal.is_authenticated or self.active_tenant_id is None:
            return None
        return ActorAttribution(
            principal_id=self.principal.principal_id,
            principal_type=self.principal.principal_type.value,
            tenant_id=self.active_tenant_id,
            request_id=self.request_id,
        )

