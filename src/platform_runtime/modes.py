"""Fixed platform runtime mode catalogs and compatibility helpers."""

from __future__ import annotations

from enum import Enum


class RuntimeMode(str, Enum):
    LOCAL = "local"
    TEST = "test"
    DEMO = "demo"
    LOCAL_API_AUTH = "local_api_auth"
    PILOT = "pilot"
    PRODUCTION = "production"


class BackendMode(str, Enum):
    IN_MEMORY = "in_memory"
    SQLITE = "sqlite"
    FUTURE_POSTGRES = "future_postgres"


class AuthMode(str, Enum):
    DISABLED = "disabled"
    LOCAL_DEMO = "local_demo"
    AUTHENTICATED = "authenticated"
    PRODUCTION = "production"


class IdentityProviderMode(str, Enum):
    NONE = "none"
    LOCAL_DEMO = "local_demo"
    EXTERNAL = "external"


class ApiRuntimeMode(str, Enum):
    DISABLED = "disabled"
    READ_ONLY_UNGUARDED = "read_only_unguarded"
    READ_ONLY_GUARDED = "read_only_guarded"


class StreamlitRuntimeMode(str, Enum):
    DISABLED = "disabled"
    LOCAL_PREVIEW = "local_preview"
    API_PREVIEW = "api_preview"


_LOCAL_LIKE = frozenset(
    {RuntimeMode.LOCAL, RuntimeMode.TEST, RuntimeMode.DEMO, RuntimeMode.LOCAL_API_AUTH}
)
_PRODUCTION_LIKE = frozenset({RuntimeMode.PILOT, RuntimeMode.PRODUCTION})
_BACKENDS = {
    RuntimeMode.LOCAL: frozenset({BackendMode.IN_MEMORY, BackendMode.SQLITE}),
    RuntimeMode.TEST: frozenset({BackendMode.IN_MEMORY, BackendMode.SQLITE}),
    RuntimeMode.DEMO: frozenset({BackendMode.IN_MEMORY, BackendMode.SQLITE}),
    RuntimeMode.LOCAL_API_AUTH: frozenset({BackendMode.IN_MEMORY, BackendMode.SQLITE}),
    RuntimeMode.PILOT: frozenset({BackendMode.SQLITE}),
    RuntimeMode.PRODUCTION: frozenset({BackendMode.FUTURE_POSTGRES}),
}
_AUTHS = {
    RuntimeMode.LOCAL: frozenset({AuthMode.DISABLED, AuthMode.LOCAL_DEMO}),
    RuntimeMode.TEST: frozenset({AuthMode.DISABLED, AuthMode.LOCAL_DEMO}),
    RuntimeMode.DEMO: frozenset({AuthMode.LOCAL_DEMO}),
    RuntimeMode.LOCAL_API_AUTH: frozenset({AuthMode.LOCAL_DEMO}),
    RuntimeMode.PILOT: frozenset({AuthMode.AUTHENTICATED}),
    RuntimeMode.PRODUCTION: frozenset({AuthMode.PRODUCTION}),
}


def _runtime_mode(value: RuntimeMode | str) -> RuntimeMode:
    try:
        return value if isinstance(value, RuntimeMode) else RuntimeMode(value)
    except (TypeError, ValueError):
        raise ValueError("runtime mode is invalid") from None


def is_local_like(mode: RuntimeMode | str) -> bool:
    return _runtime_mode(mode) in _LOCAL_LIKE


def is_production_like(mode: RuntimeMode | str) -> bool:
    return _runtime_mode(mode) in _PRODUCTION_LIKE


def allowed_backend_modes(mode: RuntimeMode | str) -> frozenset[BackendMode]:
    return _BACKENDS[_runtime_mode(mode)]


def allowed_auth_modes(mode: RuntimeMode | str) -> frozenset[AuthMode]:
    return _AUTHS[_runtime_mode(mode)]

