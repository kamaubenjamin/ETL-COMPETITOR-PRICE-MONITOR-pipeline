"""Canonical lifecycle states and deterministic transition catalog."""

from __future__ import annotations

from types import MappingProxyType

from ..contracts import DocumentStatus


STRUCTURED_EQUIVALENT = DocumentStatus.PARSED.value

LIFECYCLE_STATES = tuple(status.value for status in DocumentStatus)
TERMINAL_STATES = frozenset({DocumentStatus.EXPORTED.value, DocumentStatus.FAILED.value})
NON_TERMINAL_STATES = frozenset(set(LIFECYCLE_STATES) - TERMINAL_STATES)

_NORMAL_TRANSITIONS = {
    DocumentStatus.RECEIVED.value: (
        DocumentStatus.INGESTED.value,
        DocumentStatus.CLASSIFIED.value,
    ),
    DocumentStatus.INGESTED.value: (
        DocumentStatus.CLASSIFIED.value,
        DocumentStatus.PARSED.value,
    ),
    DocumentStatus.CLASSIFIED.value: (
        DocumentStatus.PARSED.value,
        DocumentStatus.EXTRACTED.value,
    ),
    DocumentStatus.PARSED.value: (
        DocumentStatus.EXTRACTED.value,
        DocumentStatus.TRANSFORMED.value,
        DocumentStatus.VALIDATED.value,
        DocumentStatus.REVIEW_REQUIRED.value,
    ),
    DocumentStatus.EXTRACTED.value: (
        DocumentStatus.TRANSFORMED.value,
        DocumentStatus.VALIDATED.value,
        DocumentStatus.REVIEW_REQUIRED.value,
    ),
    DocumentStatus.TRANSFORMED.value: (
        DocumentStatus.VALIDATED.value,
        DocumentStatus.REVIEW_REQUIRED.value,
    ),
    DocumentStatus.VALIDATED.value: (
        DocumentStatus.MATCHED.value,
        DocumentStatus.REVIEW_REQUIRED.value,
        DocumentStatus.APPROVED.value,
        DocumentStatus.EXPORT_READY.value,
    ),
    DocumentStatus.MATCHED.value: (
        DocumentStatus.REVIEW_REQUIRED.value,
        DocumentStatus.APPROVED.value,
        DocumentStatus.EXPORT_READY.value,
    ),
    DocumentStatus.REVIEW_REQUIRED.value: (DocumentStatus.APPROVED.value,),
    DocumentStatus.APPROVED.value: (
        DocumentStatus.EXPORT_READY.value,
        DocumentStatus.EXPORTED.value,
    ),
    DocumentStatus.EXPORT_READY.value: (DocumentStatus.EXPORTED.value,),
    DocumentStatus.EXPORTED.value: (),
    DocumentStatus.FAILED.value: (),
}

ALLOWED_TRANSITIONS = MappingProxyType(
    {
        source: tuple(targets) + ((DocumentStatus.FAILED.value,) if source in NON_TERMINAL_STATES else ())
        for source, targets in _NORMAL_TRANSITIONS.items()
    }
)

RECOVERY_TARGETS = frozenset(
    {
        DocumentStatus.CLASSIFIED.value,
        DocumentStatus.PARSED.value,
        DocumentStatus.EXTRACTED.value,
        DocumentStatus.TRANSFORMED.value,
        DocumentStatus.VALIDATED.value,
        DocumentStatus.MATCHED.value,
        DocumentStatus.APPROVED.value,
    }
)

_STATE_PRIORITY = {
    status: index
    for index, status in enumerate(
        (
            DocumentStatus.RECEIVED.value,
            DocumentStatus.INGESTED.value,
            DocumentStatus.CLASSIFIED.value,
            DocumentStatus.PARSED.value,
            DocumentStatus.EXTRACTED.value,
            DocumentStatus.TRANSFORMED.value,
            DocumentStatus.VALIDATED.value,
            DocumentStatus.MATCHED.value,
            DocumentStatus.REVIEW_REQUIRED.value,
            DocumentStatus.APPROVED.value,
            DocumentStatus.EXPORT_READY.value,
            DocumentStatus.EXPORTED.value,
            DocumentStatus.FAILED.value,
        )
    )
}
STATE_PRIORITY = MappingProxyType(_STATE_PRIORITY)


def lifecycle_priority(status: DocumentStatus | str) -> int:
    """Return the stable tie-break priority for a known lifecycle state."""

    value = status.value if isinstance(status, DocumentStatus) else status
    try:
        return STATE_PRIORITY[value]
    except (KeyError, TypeError) as exc:
        raise ValueError("status is invalid") from exc
