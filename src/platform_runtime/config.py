"""Immutable explicit configuration contracts with redacted serialization."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar

from .errors import RuntimeErrorCode, RuntimeValidationError
from .modes import (
    ApiRuntimeMode,
    AuthMode,
    BackendMode,
    IdentityProviderMode,
    RuntimeMode,
    StreamlitRuntimeMode,
)


ModeValue = TypeVar("ModeValue", bound=Enum)


def _mode(value: object, enum_type: type[ModeValue], field_name: str) -> ModeValue:
    try:
        return value if isinstance(value, enum_type) else enum_type(value)
    except (TypeError, ValueError):
        raise RuntimeValidationError(RuntimeErrorCode.INVALID_CONFIG, field=field_name) from None


def _optional_bounded(value: object, field_name: str, *, maximum: int = 1024) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise RuntimeValidationError(RuntimeErrorCode.INVALID_CONFIG, field=field_name)
    if value.strip() != value or any(ord(character) < 32 for character in value):
        raise RuntimeValidationError(RuntimeErrorCode.INVALID_CONFIG, field=field_name)
    return value


@dataclass(frozen=True, slots=True)
class BackendConfig:
    mode: BackendMode | str
    sqlite_path: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", _mode(self.mode, BackendMode, "backend"))
        object.__setattr__(self, "sqlite_path", _optional_bounded(self.sqlite_path, "sqlite_path"))

    def to_redacted_dict(self) -> dict[str, str | bool]:
        return {
            "mode": self.mode.value,
            "sqlite_path_configured": self.sqlite_path is not None,
        }


@dataclass(frozen=True, slots=True)
class AuthConfig:
    mode: AuthMode | str
    identity_provider: IdentityProviderMode | str = IdentityProviderMode.NONE
    identity_provider_available: bool = False
    identity_provider_reference: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", _mode(self.mode, AuthMode, "auth"))
        object.__setattr__(
            self,
            "identity_provider",
            _mode(self.identity_provider, IdentityProviderMode, "identity_provider"),
        )
        if not isinstance(self.identity_provider_available, bool):
            raise RuntimeValidationError(RuntimeErrorCode.INVALID_CONFIG, field="identity_provider")
        object.__setattr__(
            self,
            "identity_provider_reference",
            _optional_bounded(self.identity_provider_reference, "identity_provider", maximum=256),
        )

    def to_redacted_dict(self) -> dict[str, str | bool]:
        return {
            "mode": self.mode.value,
            "identity_provider": self.identity_provider.value,
            "identity_provider_available": self.identity_provider_available,
            "identity_provider_reference_configured": self.identity_provider_reference is not None,
        }


@dataclass(frozen=True, slots=True)
class ApiConfig:
    mode: ApiRuntimeMode | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", _mode(self.mode, ApiRuntimeMode, "api"))

    def to_redacted_dict(self) -> dict[str, str]:
        return {"mode": self.mode.value}


@dataclass(frozen=True, slots=True)
class StreamlitConfig:
    mode: StreamlitRuntimeMode | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", _mode(self.mode, StreamlitRuntimeMode, "streamlit"))

    def to_redacted_dict(self) -> dict[str, str]:
        return {"mode": self.mode.value}


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    runtime_mode: RuntimeMode | str
    backend: BackendConfig | None
    auth: AuthConfig | None
    api: ApiConfig
    streamlit: StreamlitConfig
    lifecycle_truth_required: bool = True
    writers_enabled: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "runtime_mode", _mode(self.runtime_mode, RuntimeMode, "runtime_mode"))
        if self.backend is not None and not isinstance(self.backend, BackendConfig):
            raise RuntimeValidationError(RuntimeErrorCode.INVALID_CONFIG, field="backend")
        if self.auth is not None and not isinstance(self.auth, AuthConfig):
            raise RuntimeValidationError(RuntimeErrorCode.INVALID_CONFIG, field="auth")
        if not isinstance(self.api, ApiConfig):
            raise RuntimeValidationError(RuntimeErrorCode.INVALID_CONFIG, field="api")
        if not isinstance(self.streamlit, StreamlitConfig):
            raise RuntimeValidationError(RuntimeErrorCode.INVALID_CONFIG, field="streamlit")
        if not isinstance(self.lifecycle_truth_required, bool) or not isinstance(self.writers_enabled, bool):
            raise RuntimeValidationError(RuntimeErrorCode.INVALID_CONFIG, field="runtime_mode")

    def to_redacted_dict(self) -> dict[str, object]:
        return {
            "runtime_mode": self.runtime_mode.value,
            "backend": self.backend.to_redacted_dict() if self.backend else None,
            "auth": self.auth.to_redacted_dict() if self.auth else None,
            "api": self.api.to_redacted_dict(),
            "streamlit": self.streamlit.to_redacted_dict(),
            "lifecycle_truth_required": self.lifecycle_truth_required,
            "writers_enabled": self.writers_enabled,
        }

