"""Stable configuration errors for deterministic transform contracts."""

from __future__ import annotations

from typing import Any, Iterable

PathComponent = str | int


def format_configuration_path(path: Iterable[PathComponent]) -> str:
    """Format path components using a stable JSONPath-like representation."""
    formatted = "$"
    for component in path:
        if isinstance(component, int):
            formatted += f"[{component}]"
        elif component.isidentifier():
            formatted += f".{component}"
        else:
            escaped = component.replace("\\", "\\\\").replace("'", "\\'")
            formatted += f"['{escaped}']"
    return formatted


class ConfigurationError(ValueError):
    """A path-aware, JSON-serializable configuration validation error."""

    def __init__(
        self,
        code: str,
        message: str,
        path: Iterable[PathComponent] = (),
    ) -> None:
        self.code = code
        self.message = message
        self.path_components = tuple(path)
        self.path = format_configuration_path(self.path_components)
        super().__init__(f"{code} at {self.path}: {message}")

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "path": self.path, "message": self.message}


INVALID_TYPE = "invalid_type"
INVALID_VALUE = "invalid_value"
MISSING_FIELD = "missing_field"
UNKNOWN_FIELD = "unknown_field"
UNSUPPORTED_VERSION = "unsupported_version"
DUPLICATE_ID = "duplicate_id"
DUPLICATE_OUTPUT = "duplicate_output"
INVALID_REGEX = "invalid_regex"

