"""Immutable backend configuration contracts for Document State persistence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import PersistenceError


class PersistenceBackend(str, Enum):
    IN_MEMORY = "in_memory"
    SQLITE = "sqlite"
    FUTURE_POSTGRES = "future_postgres"


ACTIVE_BACKENDS = frozenset({PersistenceBackend.IN_MEMORY.value, PersistenceBackend.SQLITE.value})
DEFERRED_BACKENDS = frozenset({PersistenceBackend.FUTURE_POSTGRES.value})


def _backend(value: PersistenceBackend | str) -> str:
    try:
        return value.value if isinstance(value, PersistenceBackend) else PersistenceBackend(value).value
    except (TypeError, ValueError):
        raise PersistenceError("invalid_backend", field="backend") from None


def _sqlite_path(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise PersistenceError("invalid_backend", field="sqlite_path")
    if value.strip() != value or value == ":memory:" or any(ord(character) < 32 for character in value):
        raise PersistenceError("invalid_backend", field="sqlite_path")
    return value


@dataclass(frozen=True, slots=True)
class PersistenceConfig:
    backend: PersistenceBackend | str
    sqlite_path: str | None = None
    sqlite_busy_timeout_ms: int = 5000

    def __post_init__(self) -> None:
        safe_backend = _backend(self.backend)
        object.__setattr__(self, "backend", safe_backend)
        if isinstance(self.sqlite_busy_timeout_ms, bool) or not isinstance(self.sqlite_busy_timeout_ms, int):
            raise PersistenceError("invalid_backend", field="sqlite_busy_timeout_ms")
        if not 1 <= self.sqlite_busy_timeout_ms <= 60_000:
            raise PersistenceError("invalid_backend", field="sqlite_busy_timeout_ms")
        if safe_backend == PersistenceBackend.SQLITE.value:
            object.__setattr__(self, "sqlite_path", _sqlite_path(self.sqlite_path))
        elif self.sqlite_path is not None:
            raise PersistenceError("invalid_backend", field="sqlite_path")

    @property
    def is_active(self) -> bool:
        return self.backend in ACTIVE_BACKENDS

    @property
    def is_deferred(self) -> bool:
        return self.backend in DEFERRED_BACKENDS

    def to_dict(self) -> dict[str, str | int | bool | None]:
        return {
            "backend": self.backend,
            "sqlite_path": self.sqlite_path,
            "sqlite_busy_timeout_ms": self.sqlite_busy_timeout_ms,
            "is_active": self.is_active,
            "is_deferred": self.is_deferred,
        }


def require_active_backend(config: object) -> PersistenceConfig:
    if not isinstance(config, PersistenceConfig) or not config.is_active:
        raise PersistenceError("invalid_backend", field="backend")
    return config
