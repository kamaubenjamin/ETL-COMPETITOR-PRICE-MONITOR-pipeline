"""Immutable JSON-safe upload processing read models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .contracts import UploadContract, optional_id, optional_text, optional_timestamp, safe_code, stable_id
from .progress import UploadProgressStage, UploadProgressStatus, stage_sequence


@dataclass(frozen=True, slots=True)
class UploadProcessingFailure(UploadContract):
    code: str
    summary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", safe_code(self.code, "failure code"))
        object.__setattr__(self, "summary", optional_text(self.summary, "failure summary", maximum=256))


@dataclass(frozen=True, slots=True)
class UploadDocumentLink(UploadContract):
    upload_id: str
    document_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "upload_id", stable_id(self.upload_id, "upload_id"))
        object.__setattr__(self, "document_id", stable_id(self.document_id, "document_id"))


@dataclass(frozen=True, slots=True)
class UploadProgressEvent(UploadContract):
    stage: UploadProgressStage
    status: UploadProgressStatus | str
    occurred_at: str
    summary: str

    def __post_init__(self) -> None:
        if not isinstance(self.stage, UploadProgressStage) or not self.stage.completed:
            raise ValueError("event stage must be completed")
        try:
            status = self.status if isinstance(self.status, UploadProgressStatus) else UploadProgressStatus(self.status)
        except (TypeError, ValueError):
            raise ValueError("processing status is invalid") from None
        object.__setattr__(self, "status", status.value)
        timestamp = optional_timestamp(self.occurred_at, "occurred_at")
        if timestamp is None:
            raise ValueError("occurred_at is required")
        object.__setattr__(self, "occurred_at", timestamp)
        object.__setattr__(self, "summary", optional_text(self.summary, "summary", maximum=256))


@dataclass(frozen=True, slots=True)
class UploadProgressSummary(UploadContract):
    upload_id: str
    status: UploadProgressStatus | str
    current_stage: str
    started_at: str
    updated_at: str
    document_id: str | None = None
    completed_at: str | None = None
    progress_percent: int | None = None
    progress_approximate: bool = False
    failure: UploadProcessingFailure | None = None
    actor_label: str | None = None
    source_label: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "upload_id", stable_id(self.upload_id, "upload_id"))
        object.__setattr__(self, "document_id", optional_id(self.document_id, "document_id"))
        try:
            status = self.status if isinstance(self.status, UploadProgressStatus) else UploadProgressStatus(self.status)
        except (TypeError, ValueError):
            raise ValueError("processing status is invalid") from None
        object.__setattr__(self, "status", status.value)
        stage_sequence(self.current_stage)
        for name in ("started_at", "updated_at"):
            value = optional_timestamp(getattr(self, name), name)
            if value is None:
                raise ValueError(f"{name} is required")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "completed_at", optional_timestamp(self.completed_at, "completed_at"))
        if status == UploadProgressStatus.COMPLETED and self.completed_at is None:
            raise ValueError("completed status requires completed_at")
        if self.progress_percent is not None and (
            isinstance(self.progress_percent, bool) or not isinstance(self.progress_percent, int)
            or not 0 <= self.progress_percent <= 100
        ):
            raise ValueError("progress_percent must be between 0 and 100")
        if not isinstance(self.progress_approximate, bool):
            raise ValueError("progress_approximate must be a boolean")
        if self.progress_percent is None and self.progress_approximate:
            raise ValueError("omitted progress cannot be approximate")
        if self.failure is not None and not isinstance(self.failure, UploadProcessingFailure):
            raise ValueError("failure is invalid")
        failure_statuses = {UploadProgressStatus.FAILED, UploadProgressStatus.VALIDATION_FAILED}
        if status in failure_statuses and self.failure is None:
            raise ValueError("failed status requires a safe failure")
        if status not in failure_statuses and self.failure is not None:
            raise ValueError("failure is only valid for failed status")
        for name in ("actor_label", "source_label"):
            object.__setattr__(self, name, optional_text(getattr(self, name), name, maximum=64))

    @property
    def stage_label(self) -> str:
        return UploadProgressStage(self.current_stage, False).label

    @property
    def stage_sequence(self) -> int:
        return stage_sequence(self.current_stage)

    def to_dict(self) -> dict[str, object]:
        result = UploadContract.to_dict(self)
        result["stage_label"] = self.stage_label
        result["stage_sequence"] = self.stage_sequence
        return result


@dataclass(frozen=True, slots=True)
class UploadProcessingTimeline(UploadContract):
    upload_id: str
    events: tuple[UploadProgressEvent, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "upload_id", stable_id(self.upload_id, "upload_id"))
        events = tuple(self.events)
        if any(not isinstance(event, UploadProgressEvent) for event in events):
            raise ValueError("events are invalid")
        ordered = tuple(sorted(events, key=lambda event: (
            datetime.fromisoformat(event.occurred_at.replace("Z", "+00:00")), event.stage.sequence, event.status
        )))
        object.__setattr__(self, "events", ordered)


@dataclass(frozen=True, slots=True)
class UploadProgressPage(UploadContract):
    items: tuple[UploadProgressSummary, ...]
    limit: int
    offset: int
    total: int

    def __post_init__(self) -> None:
        items = tuple(self.items)
        if any(not isinstance(item, UploadProgressSummary) for item in items):
            raise ValueError("items are invalid")
        if isinstance(self.limit, bool) or not isinstance(self.limit, int) or not 1 <= self.limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if isinstance(self.offset, bool) or not isinstance(self.offset, int) or not 0 <= self.offset <= 10_000:
            raise ValueError("offset must be between 0 and 10000")
        if isinstance(self.total, bool) or not isinstance(self.total, int) or self.total < len(items):
            raise ValueError("total is invalid")
        object.__setattr__(self, "items", items)
