"""Safe declarative Workflow Studio actions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .contracts import (
    SafeArgumentValue,
    StudioContract,
    logical_path,
    safe_arguments,
    safe_code,
    safe_metadata,
    stable_id,
    version_label,
)


class ActionErrorPolicy(str, Enum):
    FAIL_RULE = "fail_rule"
    SKIP_RULE = "skip_rule"
    RECORD_ISSUE = "record_issue"


class ActionOutputPolicy(str, Enum):
    REPLACE = "replace"
    APPEND = "append"
    EMIT_PREVIEW = "emit_preview"


@dataclass(frozen=True, slots=True)
class ActionDefinition(StudioContract):
    action_id: str
    action_type: str
    operation_name: str
    operation_version: str
    source_path: str | None = None
    target_path: str | None = None
    arguments: Mapping[str, SafeArgumentValue] | None = None
    error_policy: ActionErrorPolicy = ActionErrorPolicy.FAIL_RULE
    output_policy: ActionOutputPolicy = ActionOutputPolicy.REPLACE
    enabled: bool = True
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_id", stable_id(self.action_id, "action_id"))
        object.__setattr__(self, "action_type", safe_code(self.action_type, "action_type"))
        object.__setattr__(self, "operation_name", safe_code(self.operation_name, "operation_name"))
        object.__setattr__(self, "operation_version", version_label(self.operation_version, "operation_version"))
        if self.source_path is not None:
            object.__setattr__(self, "source_path", logical_path(self.source_path, "source_path"))
        if self.target_path is not None:
            object.__setattr__(self, "target_path", logical_path(self.target_path, "target_path"))
        try:
            error_policy = self.error_policy if isinstance(self.error_policy, ActionErrorPolicy) else ActionErrorPolicy(self.error_policy)
            output_policy = self.output_policy if isinstance(self.output_policy, ActionOutputPolicy) else ActionOutputPolicy(self.output_policy)
        except (TypeError, ValueError) as error:
            raise ValueError("action uses an unsupported policy") from error
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        object.__setattr__(self, "error_policy", error_policy)
        object.__setattr__(self, "output_policy", output_policy)
        object.__setattr__(self, "arguments", safe_arguments(self.arguments))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))
