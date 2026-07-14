"""Pure result contracts for runtime configuration validation."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import RuntimeValidationError


@dataclass(frozen=True, slots=True)
class RuntimeValidationResult:
    errors: tuple[RuntimeValidationError, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.errors, tuple) or any(
            not isinstance(error, RuntimeValidationError) for error in self.errors
        ):
            raise ValueError("errors must be runtime validation errors")

    @property
    def valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "errors": [error.to_dict() for error in self.errors],
        }

