"""Explicit authentication configuration for the read-only API."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from os import environ as process_environment
from urllib.parse import urlsplit

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


class APIDeploymentEnvironment(str, Enum):
    LOCAL = "local"
    TEST = "test"
    UAT = "uat"
    PILOT = "pilot"
    PRODUCTION = "production"


_ENVIRONMENT_ALIASES = {
    "dev": APIDeploymentEnvironment.LOCAL,
    "development": APIDeploymentEnvironment.LOCAL,
    "technical-preview": APIDeploymentEnvironment.UAT,
    "technical_preview": APIDeploymentEnvironment.UAT,
}


def _deployment_environment(value: object) -> APIDeploymentEnvironment:
    if value is None or value == "":
        return APIDeploymentEnvironment.LOCAL
    if not isinstance(value, str):
        raise ValueError("APP_ENV is invalid")
    candidate = value.strip().lower()
    if candidate in _ENVIRONMENT_ALIASES:
        return _ENVIRONMENT_ALIASES[candidate]
    try:
        return APIDeploymentEnvironment(candidate)
    except ValueError:
        raise ValueError("APP_ENV is invalid") from None


def _cors_origins(value: object) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    if not isinstance(value, str) or len(value) > 4096:
        raise ValueError("CORS allowed origins are invalid")
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if len(parts) > 16:
        raise ValueError("CORS allowed origins are invalid")
    origins: list[str] = []
    for part in parts:
        if part == "*" or any(character.isspace() for character in part):
            raise ValueError("CORS allowed origins are invalid")
        parsed = urlsplit(part)
        try:
            parsed.port
        except ValueError:
            raise ValueError("CORS allowed origins are invalid") from None
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("CORS allowed origins are invalid")
        origin = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
        if origin not in origins:
            origins.append(origin)
    return tuple(origins)


def _validate_cors_for_environment(
    environment: APIDeploymentEnvironment,
    origins: tuple[str, ...],
) -> tuple[str, ...]:
    for origin in origins:
        parsed = urlsplit(origin)
        if parsed.scheme == "https":
            continue
        is_loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        is_local_environment = environment in {
            APIDeploymentEnvironment.LOCAL,
            APIDeploymentEnvironment.TEST,
        }
        if not (parsed.scheme == "http" and is_loopback and is_local_environment):
            raise ValueError("CORS allowed origins are invalid for APP_ENV")
    return origins


@dataclass(frozen=True, slots=True)
class APIEnvironmentConfig:
    """Server-only environment descriptors; parsing does not enable CORS or auth."""

    app_env: APIDeploymentEnvironment | str = APIDeploymentEnvironment.LOCAL
    cors_allowed_origins: tuple[str, ...] | str = ()

    def __post_init__(self) -> None:
        environment = _deployment_environment(self.app_env)
        object.__setattr__(self, "app_env", environment)
        origins = (
            _cors_origins(self.cors_allowed_origins)
            if isinstance(self.cors_allowed_origins, str)
            else self.cors_allowed_origins
        )
        if not isinstance(origins, tuple) or any(not isinstance(item, str) for item in origins):
            raise ValueError("CORS allowed origins are invalid")
        normalized_origins = _cors_origins(",".join(origins))
        object.__setattr__(
            self,
            "cors_allowed_origins",
            _validate_cors_for_environment(environment, normalized_origins),
        )

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "APIEnvironmentConfig":
        source = process_environment if environment is None else environment
        return cls(
            app_env=source.get("APP_ENV", APIDeploymentEnvironment.LOCAL.value),
            cors_allowed_origins=source.get("DOCUMENT_INTELLIGENCE_CORS_ALLOWED_ORIGINS", ""),
        )

    def to_safe_dict(self) -> dict[str, str | int | bool]:
        return {
            "app_env": self.app_env.value,
            "cors_configured": bool(self.cors_allowed_origins),
            "cors_origin_count": len(self.cors_allowed_origins),
        }


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
