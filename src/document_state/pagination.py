"""Bounded persistence-neutral pagination contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar


DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 200


class SerializableRecord(Protocol):
    def to_dict(self) -> dict[str, Any]: ...


T = TypeVar("T", bound=SerializableRecord)


@dataclass(frozen=True, slots=True)
class PageRequest:
    limit: int = DEFAULT_PAGE_LIMIT
    offset: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.limit, bool) or not isinstance(self.limit, int) or not 1 <= self.limit <= MAX_PAGE_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_PAGE_LIMIT}")
        if isinstance(self.offset, bool) or not isinstance(self.offset, int) or self.offset < 0:
            raise ValueError("offset must be a non-negative integer")

    def to_dict(self) -> dict[str, int]:
        return {"limit": self.limit, "offset": self.offset}


@dataclass(frozen=True, slots=True)
class PageResult(Generic[T]):
    items: tuple[T, ...]
    total: int
    limit: int
    offset: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))
        PageRequest(limit=self.limit, offset=self.offset)
        if isinstance(self.total, bool) or not isinstance(self.total, int) or self.total < 0:
            raise ValueError("total must be a non-negative integer")
        if len(self.items) > self.limit or len(self.items) > self.total:
            raise ValueError("items exceed pagination bounds")
        if any(not callable(getattr(item, "to_dict", None)) for item in self.items):
            raise ValueError("items must be serializable records")

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset,
        }
