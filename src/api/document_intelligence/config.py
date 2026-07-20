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
    SUPABASE = "supabase"


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


def _https_origin(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ValueError(f"{field_name} is invalid")
    parsed = urlsplit(value.strip())
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"{field_name} is invalid")
    return f"https://{parsed.netloc.lower()}"


def _https_url(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ValueError(f"{field_name} is invalid")
    parsed = urlsplit(value.strip())
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"{field_name} is invalid")
    return value.strip().rstrip("/")


@dataclass(frozen=True, slots=True)
class SupabaseAuthConfig:
    """Public Supabase verification/Data API settings; never contains a secret key."""

    url: str
    publishable_key: str
    jwks_url: str | None = None
    issuer: str | None = None
    audience: str = "authenticated"
    network_timeout_seconds: float = 5.0
    jwks_cache_seconds: int = 300
    jwks_max_keys: int = 8

    def __post_init__(self) -> None:
        origin = _https_origin(self.url, "SUPABASE_URL")
        key = self.publishable_key.strip() if isinstance(self.publishable_key, str) else ""
        if not key or len(key) > 2048 or any(character.isspace() for character in key):
            raise ValueError("SUPABASE_PUBLISHABLE_KEY is invalid")
        issuer = _https_url(self.issuer or f"{origin}/auth/v1", "SUPABASE_JWT_ISSUER")
        jwks_url = _https_url(
            self.jwks_url or f"{issuer}/.well-known/jwks.json",
            "SUPABASE_JWKS_URL",
        )
        if not jwks_url.startswith(f"{origin}/auth/v1/") or issuer != f"{origin}/auth/v1":
            raise ValueError("Supabase JWT endpoints must belong to SUPABASE_URL")
        if not isinstance(self.audience, str) or not self.audience or len(self.audience) > 128:
            raise ValueError("SUPABASE_JWT_AUDIENCE is invalid")
        if not 0.5 <= self.network_timeout_seconds <= 15:
            raise ValueError("SUPABASE_NETWORK_TIMEOUT_SECONDS is invalid")
        if not 30 <= self.jwks_cache_seconds <= 600:
            raise ValueError("SUPABASE_JWKS_CACHE_SECONDS is invalid")
        if not 1 <= self.jwks_max_keys <= 16:
            raise ValueError("SUPABASE_JWKS_MAX_KEYS is invalid")
        object.__setattr__(self, "url", origin)
        object.__setattr__(self, "publishable_key", key)
        object.__setattr__(self, "issuer", issuer)
        object.__setattr__(self, "jwks_url", jwks_url)

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "SupabaseAuthConfig":
        source = process_environment if environment is None else environment
        return cls(
            url=source.get("SUPABASE_URL", ""),
            publishable_key=source.get("SUPABASE_PUBLISHABLE_KEY", ""),
            jwks_url=source.get("SUPABASE_JWKS_URL") or None,
            issuer=source.get("SUPABASE_JWT_ISSUER") or None,
            audience=source.get("SUPABASE_JWT_AUDIENCE", "authenticated"),
            network_timeout_seconds=float(source.get("SUPABASE_NETWORK_TIMEOUT_SECONDS", "5")),
            jwks_cache_seconds=int(source.get("SUPABASE_JWKS_CACHE_SECONDS", "300")),
            jwks_max_keys=int(source.get("SUPABASE_JWKS_MAX_KEYS", "8")),
        )


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
