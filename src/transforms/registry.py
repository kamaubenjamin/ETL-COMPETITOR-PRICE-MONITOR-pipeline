"""Fixed allowlist registry for deterministic transformation operations."""

from __future__ import annotations

from collections.abc import Iterable

from src.transforms.contracts import OPERATION_TYPES
from src.transforms.errors import ConfigurationError


class OperationRegistry:
    """Immutable operation-name registry with no discovery or callback loading."""

    def __init__(self, operation_names: Iterable[str]) -> None:
        names: list[str] = []
        seen: set[str] = set()
        for index, name in enumerate(operation_names):
            if not isinstance(name, str) or not name:
                raise ConfigurationError(
                    "invalid_operation_name",
                    "Operation names must be non-empty strings.",
                    ("operations", index),
                )
            if name in seen:
                raise ConfigurationError(
                    "duplicate_registration",
                    f"Operation '{name}' is already registered.",
                    ("operations", index),
                )
            seen.add(name)
            names.append(name)
        self._names = tuple(names)
        self._name_set = frozenset(names)

    @property
    def names(self) -> tuple[str, ...]:
        return self._names

    def contains(self, operation_type: str) -> bool:
        return operation_type in self._name_set

    def require(self, operation_type: str, path: tuple[str | int, ...] = ()) -> str:
        if operation_type not in self._name_set:
            raise ConfigurationError(
                "unknown_operation",
                f"Unsupported operation '{operation_type}'.",
                path,
            )
        return operation_type


DEFAULT_OPERATION_REGISTRY = OperationRegistry(sorted(OPERATION_TYPES))

