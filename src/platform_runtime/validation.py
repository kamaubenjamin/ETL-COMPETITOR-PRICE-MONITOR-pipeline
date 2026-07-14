"""Pure deterministic runtime compatibility validation."""

from __future__ import annotations

from .config import RuntimeConfig
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
)


def _error(code: RuntimeErrorCode, field: str) -> RuntimeValidationError:
    return RuntimeValidationError(code, field=field)


def validate_runtime_config(config: object) -> RuntimeValidationResult:
    if not isinstance(config, RuntimeConfig):
        return RuntimeValidationResult((_error(RuntimeErrorCode.INVALID_CONFIG, "runtime_mode"),))

    errors: list[RuntimeValidationError] = []
    mode = config.runtime_mode
    backend = config.backend
    auth = config.auth

    if backend is None:
        errors.append(_error(RuntimeErrorCode.BACKEND_REQUIRED, "backend"))
    else:
        if backend.mode not in allowed_backend_modes(mode):
            errors.append(_error(RuntimeErrorCode.BACKEND_NOT_ALLOWED, "backend"))
        if backend.mode == BackendMode.FUTURE_POSTGRES:
            errors.append(_error(RuntimeErrorCode.BACKEND_DEFERRED, "backend"))
        if backend.mode == BackendMode.SQLITE:
            if backend.sqlite_path is None:
                errors.append(_error(RuntimeErrorCode.SQLITE_PATH_REQUIRED, "sqlite_path"))
            elif backend.sqlite_path == ":memory:":
                errors.append(_error(RuntimeErrorCode.SQLITE_PATH_INVALID, "sqlite_path"))

    if auth is None:
        errors.append(_error(RuntimeErrorCode.AUTH_REQUIRED, "auth"))
    else:
        if auth.mode not in allowed_auth_modes(mode):
            errors.append(_error(RuntimeErrorCode.AUTH_NOT_ALLOWED, "auth"))
        if auth.mode == AuthMode.DISABLED:
            if auth.identity_provider != IdentityProviderMode.NONE or auth.identity_provider_available:
                errors.append(
                    _error(RuntimeErrorCode.IDENTITY_PROVIDER_NOT_ALLOWED, "identity_provider")
                )
        elif auth.mode == AuthMode.LOCAL_DEMO:
            if (
                auth.identity_provider != IdentityProviderMode.LOCAL_DEMO
                or not auth.identity_provider_available
            ):
                errors.append(_error(RuntimeErrorCode.IDENTITY_PROVIDER_REQUIRED, "identity_provider"))
        else:
            if (
                auth.identity_provider != IdentityProviderMode.EXTERNAL
                or not auth.identity_provider_available
            ):
                errors.append(_error(RuntimeErrorCode.IDENTITY_PROVIDER_REQUIRED, "identity_provider"))

    _validate_api(config, errors)
    _validate_streamlit(config, errors)

    if mode == RuntimeMode.PRODUCTION:
        errors.append(_error(RuntimeErrorCode.PRODUCTION_NOT_AVAILABLE, "production"))

    return RuntimeValidationResult(tuple(errors))


def _validate_api(config: RuntimeConfig, errors: list[RuntimeValidationError]) -> None:
    auth = config.auth
    api_mode = config.api.mode
    if api_mode == ApiRuntimeMode.READ_ONLY_GUARDED:
        if auth is None or auth.mode == AuthMode.DISABLED:
            errors.append(_error(RuntimeErrorCode.API_MODE_NOT_ALLOWED, "api"))
    elif api_mode == ApiRuntimeMode.READ_ONLY_UNGUARDED:
        if auth is None or auth.mode != AuthMode.DISABLED:
            errors.append(_error(RuntimeErrorCode.API_MODE_NOT_ALLOWED, "api"))

    if config.runtime_mode in {
        RuntimeMode.DEMO,
        RuntimeMode.LOCAL_API_AUTH,
        RuntimeMode.PILOT,
        RuntimeMode.PRODUCTION,
    } and api_mode != ApiRuntimeMode.READ_ONLY_GUARDED:
        errors.append(_error(RuntimeErrorCode.API_MODE_NOT_ALLOWED, "api"))


def _validate_streamlit(config: RuntimeConfig, errors: list[RuntimeValidationError]) -> None:
    streamlit_mode = config.streamlit.mode
    if config.runtime_mode in {RuntimeMode.LOCAL, RuntimeMode.TEST}:
        return
    if streamlit_mode == StreamlitRuntimeMode.LOCAL_PREVIEW:
        errors.append(_error(RuntimeErrorCode.STREAMLIT_MODE_NOT_ALLOWED, "streamlit"))


def assert_runtime_config_valid(config: object) -> RuntimeConfig:
    result = validate_runtime_config(config)
    if not result.valid:
        first = result.errors[0]
        raise RuntimeValidationError(first.code, field=first.field)
    assert isinstance(config, RuntimeConfig)
    return config

