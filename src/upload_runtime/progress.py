"""Ordered, capability-aligned upload processing progress vocabulary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import UploadContract, optional_timestamp, stable_id


STAGE_ORDER = (
    "received", "validated", "staged", "document_state_recorded",
    "ingestion_requested", "processing_started", "ingested", "parsed",
    "extracted", "transformed", "validated_output", "matched",
    "review_required", "completed", "failed",
)

_STAGE_LABELS = {stage: stage.replace("_", " ").title() for stage in STAGE_ORDER}


class UploadProgressStatus(str, Enum):
    RECEIVED = "received"
    VALIDATION_FAILED = "validation_failed"
    VALIDATED = "validated"
    STAGED = "staged"
    INGESTION_REQUESTED = "ingestion_requested"
    PROCESSING_STARTED = "processing_started"
    COMPLETED = "completed"
    FAILED = "failed"
    DUPLICATE_PREVENTED = "duplicate_prevented"
    DEFERRED_STAGING_REQUIRED = "deferred_staging_required"
    UNSUPPORTED_ACTIVATION = "unsupported_activation"
    DOCUMENT_STATE_RECORDED = "document_state_recorded"


def stage_sequence(stage: str) -> int:
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        raise ValueError("progress stage is invalid") from None


def approximate_progress(stage: str, *, sufficient: bool = True) -> int | None:
    """Return deterministic approximate progress, or None without sufficient facts."""
    if not sufficient or stage == "failed":
        return None
    sequence = stage_sequence(stage)
    completed = stage_sequence("completed")
    return round(sequence * 100 / completed)


@dataclass(frozen=True, slots=True)
class UploadProgressStage(UploadContract):
    code: str
    completed: bool
    occurred_at: str | None = None

    def __post_init__(self) -> None:
        sequence = stage_sequence(self.code)
        if not isinstance(self.completed, bool):
            raise ValueError("completed must be a boolean")
        if self.occurred_at is not None and not self.completed:
            raise ValueError("incomplete stage cannot have occurred_at")
        object.__setattr__(self, "occurred_at", optional_timestamp(self.occurred_at, "occurred_at"))
        # Validate through the public identifier policy as defense in depth.
        stable_id(self.code, "stage")

    @property
    def label(self) -> str:
        return _STAGE_LABELS[self.code]

    @property
    def sequence(self) -> int:
        return stage_sequence(self.code)

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "label": self.label,
            "sequence": self.sequence,
            "completed": self.completed,
            "occurred_at": self.occurred_at,
        }
