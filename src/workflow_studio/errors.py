"""Fixed privacy-safe Workflow Studio errors."""

from __future__ import annotations

from enum import Enum

from .contracts import optional_text


class WorkflowStudioErrorCode(str, Enum):
    INVALID_DEFINITION = "invalid_definition"
    INVALID_RULE = "invalid_rule"
    INVALID_CONDITION = "invalid_condition"
    INVALID_ACTION = "invalid_action"
    INVALID_METADATA = "invalid_metadata"
    OPERATION_NOT_FOUND = "operation_not_found"
    OPERATION_UNAVAILABLE = "operation_unavailable"
    PUBLICATION_NOT_ELIGIBLE = "publication_not_eligible"
    VERSION_CONFLICT = "version_conflict"
    NOT_FOUND = "not_found"
    INTERNAL_ERROR = "internal_error"


_MESSAGES = {
    WorkflowStudioErrorCode.INVALID_DEFINITION: "Workflow definition is invalid.",
    WorkflowStudioErrorCode.INVALID_RULE: "Workflow rule is invalid.",
    WorkflowStudioErrorCode.INVALID_CONDITION: "Workflow condition is invalid.",
    WorkflowStudioErrorCode.INVALID_ACTION: "Workflow action is invalid.",
    WorkflowStudioErrorCode.INVALID_METADATA: "Workflow metadata is invalid.",
    WorkflowStudioErrorCode.OPERATION_NOT_FOUND: "Workflow operation was not found.",
    WorkflowStudioErrorCode.OPERATION_UNAVAILABLE: "Workflow operation is unavailable.",
    WorkflowStudioErrorCode.PUBLICATION_NOT_ELIGIBLE: "Workflow operation is not eligible for publication.",
    WorkflowStudioErrorCode.VERSION_CONFLICT: "Workflow version could not be updated.",
    WorkflowStudioErrorCode.NOT_FOUND: "Workflow resource was not found.",
    WorkflowStudioErrorCode.INTERNAL_ERROR: "Workflow Studio could not complete the request.",
}


class WorkflowStudioError(Exception):
    def __init__(self, code: WorkflowStudioErrorCode | str, *, field: str | None = None) -> None:
        try:
            normalized = code if isinstance(code, WorkflowStudioErrorCode) else WorkflowStudioErrorCode(code)
        except (TypeError, ValueError):
            normalized = WorkflowStudioErrorCode.INTERNAL_ERROR
        self.code = normalized.value
        self.message = _MESSAGES[normalized]
        self.field = optional_text(field, "field", maximum=64)
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "field": self.field}

