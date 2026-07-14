"""Public contracts for explicit platform runtime selection."""

from .config import ApiConfig, AuthConfig, BackendConfig, RuntimeConfig, StreamlitConfig
from .contracts import RuntimeValidationResult
from .errors import RuntimeErrorCode, RuntimeValidationError
from .modes import (
    ApiRuntimeMode,
    AuthMode,
    BackendMode,
    IdentityProviderMode,
    RuntimeMode,
    StreamlitRuntimeMode,
    allowed_auth_modes,
    allowed_backend_modes,
    is_local_like,
    is_production_like,
)
from .validation import assert_runtime_config_valid, validate_runtime_config

__all__ = [
    "ApiConfig",
    "ApiRuntimeMode",
    "AuthConfig",
    "AuthMode",
    "BackendConfig",
    "BackendMode",
    "IdentityProviderMode",
    "RuntimeConfig",
    "RuntimeErrorCode",
    "RuntimeMode",
    "RuntimeValidationError",
    "RuntimeValidationResult",
    "StreamlitConfig",
    "StreamlitRuntimeMode",
    "allowed_auth_modes",
    "allowed_backend_modes",
    "assert_runtime_config_valid",
    "is_local_like",
    "is_production_like",
    "validate_runtime_config",
]

