"""Safe read-only export projections for the Phase 5 API placeholder."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Any


_ALLOWED_FIELDS = frozenset(
    {
        "attempt_id",
        "tenant_id",
        "document_id",
        "target_id",
        "target_type",
        "status",
        "result_status",
        "result_code",
        "created_at",
        "updated_at",
    }
)


class ReadOnlyExportProvider:
    """App-scoped, tenant-filtered provider containing summaries only."""

    def __init__(self, attempts: Iterable[Mapping[str, Any]] = ()) -> None:
        safe: list[Mapping[str, str | None]] = []
        for attempt in attempts:
            if not isinstance(attempt, Mapping) or not set(attempt).issubset(_ALLOWED_FIELDS):
                raise ValueError("export attempt summary is invalid")
            projected: dict[str, str | None] = {}
            for key, value in attempt.items():
                if value is not None and (not isinstance(value, str) or not value or len(value) > 256):
                    raise ValueError("export attempt summary is invalid")
                projected[key] = value
            safe.append(MappingProxyType(projected))
        self._attempts = tuple(safe)

    def list_attempts(
        self, *, tenant_id: str | None = None, document_id: str | None = None
    ) -> list[dict[str, str | None]]:
        return [
            {key: value for key, value in item.items() if key != "tenant_id"}
            for item in self._attempts
            if (tenant_id is None or item.get("tenant_id") == tenant_id)
            and (document_id is None or item.get("document_id") == document_id)
        ]

    def get_attempt(self, attempt_id: str, *, tenant_id: str | None = None) -> dict[str, str | None] | None:
        return next(
            (
                {key: value for key, value in item.items() if key != "tenant_id"}
                for item in self._attempts
                if item.get("attempt_id") == attempt_id
                and (tenant_id is None or item.get("tenant_id") == tenant_id)
            ),
            None,
        )


empty_export_provider = ReadOnlyExportProvider()
