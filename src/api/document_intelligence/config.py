"""Explicit authentication configuration for the read-only API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.platform_runtime import (
    AuthConfig as RuntimeAuthConfig,
    AuthMode as RuntimeAuthMode,
    RuntimeErrorCode,
    RuntimeValidationError,
)


class APIAuthMode(str, Enum):
    DISABLED = "disabled"
    LOCAL_DEMO = "local_demo"
    AUTHENTICATED = "authenticated"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class APIAuthConfig:
    mode: APIAuthMode | str = APIAuthMode.DISABLED
    allow_cross_tenant: bool = False
    identity_header: str = "x-local-identity"
    tenant_header: str = "x-tenant-id"

    def __post_init__(self) -> None:
        try:
            mode = self.mode if isinstance(self.mode, APIAuthMode) else APIAuthMode(self.mode)
        except (TypeError, ValueError):
            raise ValueError("API auth mode is invalid") from None
        if not isinstance(self.allow_cross_tenant, bool):
            raise ValueError("allow_cross_tenant must be a boolean")
        for name in ("identity_header", "tenant_header"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or len(value) > 64 or value.lower() != value:
                raise ValueError(f"{name} must be a bounded lowercase header name")
        object.__setattr__(self, "mode", mode)

    @property
    def enabled(self) -> bool:
        return self.mode != APIAuthMode.DISABLED


def api_auth_config_from_runtime(config: RuntimeAuthConfig) -> APIAuthConfig:
    """Map only API-supported runtime auth modes; placeholders fail closed."""

    if not isinstance(config, RuntimeAuthConfig):
        raise RuntimeValidationError(RuntimeErrorCode.INVALID_CONFIG, field="auth")
    if config.mode == RuntimeAuthMode.DISABLED:
        return APIAuthConfig(APIAuthMode.DISABLED)
    if config.mode == RuntimeAuthMode.LOCAL_DEMO:
        return APIAuthConfig(APIAuthMode.LOCAL_DEMO)
    raise RuntimeValidationError(RuntimeErrorCode.COMPOSITION_FAILED, field="auth")
