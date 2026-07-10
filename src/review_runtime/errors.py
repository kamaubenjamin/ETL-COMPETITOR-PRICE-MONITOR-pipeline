"""Stable errors for Review Runtime contracts and lifecycle transitions."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

PathComponent = str | int


def format_path(path: Iterable[PathComponent]) -> str:
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


class ReviewRuntimeError(ValueError):
    """Path-aware error that never includes rejected payload values."""

    def __init__(
        self,
        code: str,
        message: str | None = None,
        path: Iterable[PathComponent] = (),
    ) -> None:
        if message is None:
            message = code
            code = "review_runtime_error"
        self.code = code
        self.message = message
        self.path_components = tuple(path)
        self.path = format_path(self.path_components)
        super().__init__(f"{code} at {self.path}: {message}")

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "path": self.path, "message": self.message}


INVALID_TYPE = "invalid_type"
INVALID_VALUE = "invalid_value"
MISSING_FIELD = "missing_field"
UNKNOWN_FIELD = "unknown_field"
UNSUPPORTED_VERSION = "unsupported_version"
UNSAFE_METADATA = "unsafe_metadata"
INVALID_TRANSITION = "invalid_transition"
