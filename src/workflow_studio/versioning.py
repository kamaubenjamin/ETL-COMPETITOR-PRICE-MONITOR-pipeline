"""Pure workflow version sequencing and immutable-history cloning policies."""

from __future__ import annotations

from dataclasses import replace

from .definitions import WorkflowChangeSummary, WorkflowVersion
from .repository_errors import RepositoryErrorCode, WorkflowRepositoryError
from .statuses import WorkflowVersionStatus
from .store import InMemoryWorkflowStudioStore


def next_integer_version(store: InMemoryWorkflowStudioStore, tenant_id: str, workflow_id: str) -> int:
    versions = store.list_versions(tenant_id, workflow_id).items
    integers = [item.value.version for item in versions if isinstance(item.value.version, int)]
    return max(integers, default=0) + 1


def clone_version_to_draft(
    store: InMemoryWorkflowStudioStore,
    tenant_id: str,
    source_version_id: str,
    *,
    new_version_id: str,
    authored_by: str,
    change_summary: WorkflowChangeSummary,
    timestamp: str,
    version: int | str | None = None,
) -> WorkflowVersion:
    source = store.get_version(tenant_id, source_version_id)
    if source is None:
        raise WorkflowRepositoryError(RepositoryErrorCode.NOT_FOUND)
    if source.value.status not in {
        WorkflowVersionStatus.PUBLISHED,
        WorkflowVersionStatus.SUPERSEDED,
        WorkflowVersionStatus.INACTIVE,
        WorkflowVersionStatus.ARCHIVED,
    }:
        raise WorkflowRepositoryError(RepositoryErrorCode.INVALID_STATE)
    label = version if version is not None else next_integer_version(store, tenant_id, source.value.workflow_id)
    return replace(
        source.value,
        version_id=new_version_id,
        version=label,
        status=WorkflowVersionStatus.DRAFT,
        derived_from_version_id=source.value.version_id,
        change_summary=change_summary,
        authored_by=authored_by,
        reviewed_by=None,
        approved_by=None,
        created_at=timestamp,
        updated_at=timestamp,
        published_at=None,
    )
