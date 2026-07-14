"""Deterministic tenant-scoped in-memory queries over safe progress projections."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import stable_id
from .read_models import UploadProgressPage, UploadProgressSummary, UploadProcessingTimeline


@dataclass(frozen=True, slots=True)
class UploadProgressRecord:
    tenant_id: str
    summary: UploadProgressSummary
    timeline: UploadProcessingTimeline

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenant_id", stable_id(self.tenant_id, "tenant_id"))
        if not isinstance(self.summary, UploadProgressSummary):
            raise ValueError("summary is invalid")
        if not isinstance(self.timeline, UploadProcessingTimeline):
            raise ValueError("timeline is invalid")
        if self.summary.upload_id != self.timeline.upload_id:
            raise ValueError("progress record upload identity is inconsistent")


class UploadProgressQueryService:
    def __init__(self, records: tuple[UploadProgressRecord, ...] = ()) -> None:
        safe = tuple(records)
        if any(not isinstance(record, UploadProgressRecord) for record in safe):
            raise ValueError("progress records are invalid")
        identities = {(record.tenant_id, record.summary.upload_id) for record in safe}
        if len(identities) != len(safe):
            raise ValueError("progress records must be unique per tenant")
        self._records = safe

    def get_upload_progress(self, upload_id: str, *, tenant_id: str) -> UploadProgressSummary | None:
        upload_id = stable_id(upload_id, "upload_id")
        tenant_id = stable_id(tenant_id, "tenant_id")
        return next((r.summary for r in self._records if r.tenant_id == tenant_id and r.summary.upload_id == upload_id), None)

    def get_document_status(self, document_id: str, *, tenant_id: str) -> UploadProgressSummary | None:
        document_id = stable_id(document_id, "document_id")
        tenant_id = stable_id(tenant_id, "tenant_id")
        matches = [r.summary for r in self._records if r.tenant_id == tenant_id and r.summary.document_id == document_id]
        return max(matches, key=lambda item: (item.updated_at, item.upload_id), default=None)

    def get_timeline(self, upload_id: str, *, tenant_id: str) -> UploadProcessingTimeline | None:
        upload_id = stable_id(upload_id, "upload_id")
        tenant_id = stable_id(tenant_id, "tenant_id")
        return next((r.timeline for r in self._records if r.tenant_id == tenant_id and r.summary.upload_id == upload_id), None)

    def list_recent(self, *, tenant_id: str, limit: int = 50, offset: int = 0) -> UploadProgressPage:
        tenant_id = stable_id(tenant_id, "tenant_id")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= 10_000:
            raise ValueError("offset must be between 0 and 10000")
        matches = sorted(
            (r.summary for r in self._records if r.tenant_id == tenant_id),
            key=lambda item: (item.updated_at, item.upload_id),
            reverse=True,
        )
        return UploadProgressPage(tuple(matches[offset:offset + limit]), limit, offset, len(matches))

