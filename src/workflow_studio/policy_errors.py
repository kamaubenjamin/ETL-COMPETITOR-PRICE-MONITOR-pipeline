"""Fixed publication and lifecycle policy results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import StudioContract


class PolicyErrorCode(str, Enum):
    INVALID_TRANSITION = "invalid_transition"
    VERSION_NOT_APPROVED = "version_not_approved"
    VALIDATION_REQUIRED = "validation_required"
    TEST_EVIDENCE_REQUIRED = "test_evidence_required"
    APPROVAL_EVIDENCE_REQUIRED = "approval_evidence_required"
    PUBLICATION_PERMISSION_REQUIRED = "publication_permission_required"
    PUBLICATION_INELIGIBLE = "publication_ineligible"
    DEPENDENCY_INVALID = "dependency_invalid"
    REQUIRED_FEATURE_UNAVAILABLE = "required_feature_unavailable"
    LEGACY_REVIEW_UNRESOLVED = "legacy_review_unresolved"
    VERSION_CONFLICT = "version_conflict"
    TENANT_WORKFLOW_MISMATCH = "tenant_workflow_mismatch"
    PUBLICATION_ALREADY_EXISTS = "publication_already_exists"
    ACTIVE_PUBLICATION_CONFLICT = "active_publication_conflict"
    ACTIVE_PUBLICATION_REQUIRED = "active_publication_required"
    ARCHIVE_BLOCKED = "archive_blocked"


_MESSAGES = {
    PolicyErrorCode.INVALID_TRANSITION: "Workflow version transition is not allowed.",
    PolicyErrorCode.VERSION_NOT_APPROVED: "Workflow version is not approved for publication.",
    PolicyErrorCode.VALIDATION_REQUIRED: "Workflow validation evidence is not structurally valid.",
    PolicyErrorCode.TEST_EVIDENCE_REQUIRED: "Passing workflow test evidence is required.",
    PolicyErrorCode.APPROVAL_EVIDENCE_REQUIRED: "Workflow approval evidence is required.",
    PolicyErrorCode.PUBLICATION_PERMISSION_REQUIRED: "Publication authority is required.",
    PolicyErrorCode.PUBLICATION_INELIGIBLE: "Workflow validation does not permit publication.",
    PolicyErrorCode.DEPENDENCY_INVALID: "Workflow dependencies are invalid.",
    PolicyErrorCode.REQUIRED_FEATURE_UNAVAILABLE: "A required workflow feature is unavailable.",
    PolicyErrorCode.LEGACY_REVIEW_UNRESOLVED: "Legacy compatibility review remains unresolved.",
    PolicyErrorCode.VERSION_CONFLICT: "Workflow version changed before publication.",
    PolicyErrorCode.TENANT_WORKFLOW_MISMATCH: "Publication scope does not match the workflow version.",
    PolicyErrorCode.PUBLICATION_ALREADY_EXISTS: "Publication identity already exists.",
    PolicyErrorCode.ACTIVE_PUBLICATION_CONFLICT: "An active publication conflicts with this request.",
    PolicyErrorCode.ACTIVE_PUBLICATION_REQUIRED: "No active publication exists for this workflow.",
    PolicyErrorCode.ARCHIVE_BLOCKED: "Workflow cannot be archived while a publication is active.",
}


@dataclass(frozen=True, slots=True)
class PolicyIssue(StudioContract):
    code: PolicyErrorCode
    message: str

    def __post_init__(self) -> None:
        try:
            code = self.code if isinstance(self.code, PolicyErrorCode) else PolicyErrorCode(self.code)
        except (TypeError, ValueError) as error:
            raise ValueError("policy error code is unsupported") from error
        if self.message != _MESSAGES[code]:
            raise ValueError("policy messages must use fixed safe text")
        object.__setattr__(self, "code", code)


def policy_issue(code: PolicyErrorCode) -> PolicyIssue:
    return PolicyIssue(code, _MESSAGES[code])
