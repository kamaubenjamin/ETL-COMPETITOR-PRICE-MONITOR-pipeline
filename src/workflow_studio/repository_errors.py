"""Fixed privacy-safe Workflow Studio repository errors."""

from __future__ import annotations

from enum import Enum


class RepositoryErrorCode(str, Enum):
    NOT_FOUND = "not_found"
    DUPLICATE_WORKFLOW = "duplicate_workflow"
    DUPLICATE_VERSION = "duplicate_version"
    DUPLICATE_VERSION_LABEL = "duplicate_version_label"
    DUPLICATE_PUBLICATION = "duplicate_publication"
    CURRENT_DRAFT_EXISTS = "current_draft_exists"
    ACTIVE_PUBLICATION_EXISTS = "active_publication_exists"
    TENANT_MISMATCH = "tenant_mismatch"
    WORKFLOW_MISMATCH = "workflow_mismatch"
    VERSION_CONFLICT = "version_conflict"
    IMMUTABLE_VERSION = "immutable_version"
    INVALID_STATE = "invalid_state"


_MESSAGES = {
    RepositoryErrorCode.NOT_FOUND: "Workflow Studio record was not found.",
    RepositoryErrorCode.DUPLICATE_WORKFLOW: "Workflow identity already exists in this tenant.",
    RepositoryErrorCode.DUPLICATE_VERSION: "Workflow version identity already exists in this tenant.",
    RepositoryErrorCode.DUPLICATE_VERSION_LABEL: "Workflow version label already exists for this workflow.",
    RepositoryErrorCode.DUPLICATE_PUBLICATION: "Workflow publication identity already exists.",
    RepositoryErrorCode.CURRENT_DRAFT_EXISTS: "Workflow already has a current draft.",
    RepositoryErrorCode.ACTIVE_PUBLICATION_EXISTS: "Workflow already has an active publication.",
    RepositoryErrorCode.TENANT_MISMATCH: "Workflow record does not belong to the requested tenant.",
    RepositoryErrorCode.WORKFLOW_MISMATCH: "Workflow version or publication reference is inconsistent.",
    RepositoryErrorCode.VERSION_CONFLICT: "Workflow record changed before the requested update.",
    RepositoryErrorCode.IMMUTABLE_VERSION: "Workflow version content is immutable in its current state.",
    RepositoryErrorCode.INVALID_STATE: "Workflow record state does not allow this operation.",
}


class WorkflowRepositoryError(Exception):
    def __init__(self, code: RepositoryErrorCode) -> None:
        self.code = code.value
        self.message = _MESSAGES[code]
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}
