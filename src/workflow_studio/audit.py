"""Immutable audit intents; Phase 3 does not write an audit log."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .contracts import StudioContract, optional_id, safe_code, safe_metadata, stable_id, utc_timestamp


class WorkflowStudioAuditEventType(str, Enum):
    WORKFLOW_CREATED = "workflow_created"
    DRAFT_CREATED = "draft_created"
    DRAFT_UPDATED = "draft_updated"
    DRAFT_SUBMITTED = "draft_submitted"
    DRAFT_REJECTED = "draft_rejected"
    DRAFT_APPROVED = "draft_approved"
    PUBLICATION_REQUESTED = "publication_requested"
    WORKFLOW_PUBLISHED = "workflow_published"
    PUBLICATION_SUPERSEDED = "publication_superseded"
    WORKFLOW_DEACTIVATED = "workflow_deactivated"
    DRAFT_ARCHIVED = "draft_archived"
    WORKFLOW_ARCHIVED = "workflow_archived"
    ROLLBACK_DRAFT_CREATED = "rollback_draft_created"


@dataclass(frozen=True, slots=True)
class WorkflowStudioAuditIntent(StudioContract):
    event_type: WorkflowStudioAuditEventType
    tenant_id: str
    workflow_id: str
    version_id: str | None
    publication_id: str | None
    actor_id: str
    status: str
    reason_code: str
    occurred_at: str
    correlation_id: str | None = None
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        try:
            event_type = self.event_type if isinstance(self.event_type, WorkflowStudioAuditEventType) else WorkflowStudioAuditEventType(self.event_type)
        except (TypeError, ValueError) as error:
            raise ValueError("audit event type is unsupported") from error
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "tenant_id", stable_id(self.tenant_id, "tenant_id"))
        object.__setattr__(self, "workflow_id", stable_id(self.workflow_id, "workflow_id"))
        object.__setattr__(self, "version_id", optional_id(self.version_id, "version_id"))
        object.__setattr__(self, "publication_id", optional_id(self.publication_id, "publication_id"))
        object.__setattr__(self, "actor_id", stable_id(self.actor_id, "actor_id"))
        object.__setattr__(self, "status", safe_code(self.status, "status"))
        object.__setattr__(self, "reason_code", safe_code(self.reason_code, "reason_code"))
        object.__setattr__(self, "occurred_at", utc_timestamp(self.occurred_at, "occurred_at"))
        object.__setattr__(self, "correlation_id", optional_id(self.correlation_id, "correlation_id"))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))
