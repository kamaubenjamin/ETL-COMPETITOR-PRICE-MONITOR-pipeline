"""Bounded deterministic queries for privacy-safe export records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from .attempts import ExportAttempt
from .contracts import JsonContract, optional_id, stable_id
from .results import ExportResult
from .statuses import ExportOperationStatus


DEFAULT_EXPORT_QUERY_LIMIT = 50
MAX_EXPORT_QUERY_LIMIT = 100
MAX_EXPORT_QUERY_OFFSET = 10_000


@dataclass(frozen=True, slots=True)
class ExportPageRequest(JsonContract):
    limit: int = DEFAULT_EXPORT_QUERY_LIMIT
    offset: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.limit, bool) or not isinstance(self.limit, int) or not 1 <= self.limit <= MAX_EXPORT_QUERY_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_EXPORT_QUERY_LIMIT}")
        if isinstance(self.offset, bool) or not isinstance(self.offset, int) or not 0 <= self.offset <= MAX_EXPORT_QUERY_OFFSET:
            raise ValueError(f"offset must be between 0 and {MAX_EXPORT_QUERY_OFFSET}")


@dataclass(frozen=True, slots=True)
class ExportAttemptQuery(JsonContract):
    document_id: str | None = None
    tenant_id: str | None = None
    target_id: str | None = None
    status: ExportOperationStatus | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_id", optional_id(self.document_id, "document_id"))
        object.__setattr__(self, "tenant_id", optional_id(self.tenant_id, "tenant_id"))
        object.__setattr__(self, "target_id", optional_id(self.target_id, "target_id"))
        if self.status is not None:
            try:
                object.__setattr__(self, "status", ExportOperationStatus(self.status).value)
            except (TypeError, ValueError):
                raise ValueError("status is invalid") from None


T = TypeVar("T", ExportAttempt, ExportResult)


@dataclass(frozen=True, slots=True)
class ExportPage(JsonContract, Generic[T]):
    items: tuple[T, ...]
    total: int
    limit: int
    offset: int

    def __post_init__(self) -> None:
        items = tuple(self.items)
        page = ExportPageRequest(self.limit, self.offset)
        if isinstance(self.total, bool) or not isinstance(self.total, int) or self.total < 0:
            raise ValueError("total must be a non-negative integer")
        if len(items) > page.limit or len(items) > self.total:
            raise ValueError("items exceed pagination bounds")
        if any(not isinstance(item, (ExportAttempt, ExportResult)) for item in items):
            raise ValueError("items contain invalid export records")
        object.__setattr__(self, "items", items)


def validate_query_id(value: Any, field_name: str) -> str:
    try:
        return stable_id(value, field_name)
    except (TypeError, ValueError):
        from .repository_errors import ExportRepositoryError

        raise ExportRepositoryError("invalid_query", field=field_name) from None


def validate_page(value: Any) -> ExportPageRequest:
    if value is None:
        return ExportPageRequest()
    if not isinstance(value, ExportPageRequest):
        from .repository_errors import ExportRepositoryError

        raise ExportRepositoryError("invalid_query", field="page")
    return value
