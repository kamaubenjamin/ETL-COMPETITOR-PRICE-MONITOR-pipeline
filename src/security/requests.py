"""Pure authorization request contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .contracts import SecurityContract, bounded_string, optional_string, stable_id, validate_safe_metadata
from .permissions import Permission, permission_value


@dataclass(frozen=True, slots=True)
class AuthorizationRequest(SecurityContract):
    required_permission: Permission | str | None
    requested_tenant_id: str | None = None
    resource_tenant_id: str | None = None
    resource_id: str | None = None
    resource_type: str | None = None
    operation: str | None = None
    action: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.required_permission is not None:
            try:
                required = permission_value(self.required_permission)
            except ValueError:
                required = bounded_string(self.required_permission, "required_permission", maximum=64)
            object.__setattr__(self, "required_permission", required)
        for name in ("requested_tenant_id", "resource_tenant_id", "resource_id"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, stable_id(value, name))
        object.__setattr__(self, "resource_type", optional_string(self.resource_type, "resource_type", maximum=64))
        object.__setattr__(self, "operation", optional_string(self.operation, "operation", maximum=64))
        object.__setattr__(self, "action", optional_string(self.action, "action", maximum=64))
        if self.operation is not None and self.action is not None and self.operation != self.action:
            raise ValueError("operation and action must agree")
        object.__setattr__(self, "metadata", validate_safe_metadata(self.metadata))
