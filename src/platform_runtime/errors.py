"""Stable privacy-safe errors for platform runtime configuration."""

from __future__ import annotations

from enum import Enum


class RuntimeErrorCode(str, Enum):
    INVALID_CONFIG = "invalid_config"
    BACKEND_REQUIRED = "backend_required"
    BACKEND_NOT_ALLOWED = "backend_not_allowed"
    BACKEND_DEFERRED = "backend_deferred"
    SQLITE_PATH_REQUIRED = "sqlite_path_required"
    SQLITE_PATH_INVALID = "sqlite_path_invalid"
    AUTH_REQUIRED = "auth_required"
    AUTH_NOT_ALLOWED = "auth_not_allowed"
    IDENTITY_PROVIDER_REQUIRED = "identity_provider_required"
    IDENTITY_PROVIDER_NOT_ALLOWED = "identity_provider_not_allowed"
    API_MODE_NOT_ALLOWED = "api_mode_not_allowed"
    STREAMLIT_MODE_NOT_ALLOWED = "streamlit_mode_not_allowed"
    PRODUCTION_NOT_AVAILABLE = "production_not_available"
    COMPOSITION_FAILED = "composition_failed"


_MESSAGES = {
    RuntimeErrorCode.INVALID_CONFIG: "Runtime configuration is invalid.",
    RuntimeErrorCode.BACKEND_REQUIRED: "A runtime backend is required.",
    RuntimeErrorCode.BACKEND_NOT_ALLOWED: "The runtime backend is not allowed for this mode.",
    RuntimeErrorCode.BACKEND_DEFERRED: "The selected runtime backend is not available.",
    RuntimeErrorCode.SQLITE_PATH_REQUIRED: "SQLite requires an explicit file path.",
    RuntimeErrorCode.SQLITE_PATH_INVALID: "SQLite path configuration is invalid.",
    RuntimeErrorCode.AUTH_REQUIRED: "Authentication configuration is required.",
    RuntimeErrorCode.AUTH_NOT_ALLOWED: "Authentication mode is not allowed for this runtime mode.",
    RuntimeErrorCode.IDENTITY_PROVIDER_REQUIRED: "An identity provider is required.",
    RuntimeErrorCode.IDENTITY_PROVIDER_NOT_ALLOWED: "Identity provider configuration is not allowed.",
    RuntimeErrorCode.API_MODE_NOT_ALLOWED: "API exposure mode is not allowed for this configuration.",
    RuntimeErrorCode.STREAMLIT_MODE_NOT_ALLOWED: "Streamlit mode is not allowed for this runtime mode.",
    RuntimeErrorCode.PRODUCTION_NOT_AVAILABLE: "Production runtime is not available.",
    RuntimeErrorCode.COMPOSITION_FAILED: "Runtime composition could not be completed.",
}

_SAFE_FIELDS = frozenset(
    {
        "runtime_mode",
        "backend",
        "sqlite_path",
        "auth",
        "identity_provider",
        "api",
        "streamlit",
        "production",
    }
)


class RuntimeValidationError(Exception):
    """Exception containing only a stable code, field, and fixed message."""

    def __init__(self, code: RuntimeErrorCode | str, *, field: str | None = None) -> None:
        try:
            safe_code = code if isinstance(code, RuntimeErrorCode) else RuntimeErrorCode(code)
        except (TypeError, ValueError):
            safe_code = RuntimeErrorCode.INVALID_CONFIG
        self.code = safe_code
        self.field = field if field in _SAFE_FIELDS else None
        self.message = _MESSAGES[safe_code]
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code.value, "field": self.field, "message": self.message}
