"""Immutable Workflow Studio definition and version contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .actions import ActionDefinition, ActionErrorPolicy
from .conditions import ConditionDefinition, ConditionGroup
from .contracts import (
    MAX_DESCRIPTION_LENGTH,
    StudioContract,
    bounded_text,
    logical_path,
    optional_id,
    optional_text,
    optional_timestamp,
    positive_integer,
    safe_metadata,
    stable_id,
    utc_timestamp,
    version_label,
)
from .statuses import WorkflowDefinitionStatus, WorkflowPublicationStatus, WorkflowVersionStatus


def _enum(value: Any, enum_type: type, field_name: str) -> Any:
    try:
        return value if isinstance(value, enum_type) else enum_type(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} is unsupported") from error


def _actor(value: Any, field_name: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    return stable_id(value, field_name)


@dataclass(frozen=True, slots=True)
class WorkflowReference(StudioContract):
    workflow_id: str
    version_id: str
    version: int | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "workflow_id", stable_id(self.workflow_id, "workflow_id"))
        object.__setattr__(self, "version_id", stable_id(self.version_id, "version_id"))
        object.__setattr__(self, "version", _safe_version(self.version))


@dataclass(frozen=True, slots=True)
class WorkflowSourceLineage(StudioContract):
    source_system: str
    source_reference: str
    imported_at: str
    import_mode: str = "declared"
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_system", stable_id(self.source_system, "source_system"))
        object.__setattr__(self, "source_reference", stable_id(self.source_reference, "source_reference"))
        object.__setattr__(self, "imported_at", utc_timestamp(self.imported_at, "imported_at"))
        object.__setattr__(self, "import_mode", bounded_text(self.import_mode, "import_mode", maximum=32))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class WorkflowOwnership(StudioContract):
    created_by: str
    updated_by: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_by", stable_id(self.created_by, "created_by"))
        object.__setattr__(self, "updated_by", stable_id(self.updated_by, "updated_by"))


@dataclass(frozen=True, slots=True)
class WorkflowChangeSummary(StudioContract):
    summary: str
    changed_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", bounded_text(self.summary, "summary", maximum=MAX_DESCRIPTION_LENGTH))
        if not isinstance(self.changed_fields, (tuple, list)) or len(self.changed_fields) > 32:
            raise ValueError("changed_fields must be a bounded path sequence")
        changed = tuple(logical_path(item, "changed_field") for item in self.changed_fields)
        if len(set(changed)) != len(changed):
            raise ValueError("changed_fields must not contain duplicates")
        object.__setattr__(self, "changed_fields", changed)


@dataclass(frozen=True, slots=True)
class RuleDefinition(StudioContract):
    rule_id: str
    name: str
    stage: str
    description: str
    dependencies: tuple[str, ...]
    order: int
    enabled: bool
    skip: bool
    condition: ConditionDefinition | ConditionGroup | None
    actions: tuple[ActionDefinition, ...]
    input_contract_hints: tuple[str, ...] = ()
    output_contract_hints: tuple[str, ...] = ()
    error_policy: ActionErrorPolicy = ActionErrorPolicy.FAIL_RULE
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", stable_id(self.rule_id, "rule_id"))
        object.__setattr__(self, "name", bounded_text(self.name, "name"))
        object.__setattr__(self, "stage", stable_id(self.stage, "stage"))
        object.__setattr__(self, "description", bounded_text(self.description, "description", maximum=MAX_DESCRIPTION_LENGTH, allow_empty=True))
        if not isinstance(self.dependencies, (tuple, list)) or len(self.dependencies) > 32:
            raise ValueError("dependencies must be a bounded rule ID sequence")
        dependencies = tuple(stable_id(item, "dependency") for item in self.dependencies)
        if self.rule_id in dependencies or len(set(dependencies)) != len(dependencies):
            raise ValueError("dependencies must be unique and may not reference the rule itself")
        if not isinstance(self.order, int) or isinstance(self.order, bool) or self.order < 0:
            raise ValueError("order must be a non-negative integer")
        if not isinstance(self.enabled, bool) or not isinstance(self.skip, bool):
            raise ValueError("enabled and skip must be booleans")
        if self.condition is not None and not isinstance(self.condition, (ConditionDefinition, ConditionGroup)):
            raise ValueError("condition must be a modeled condition")
        if not isinstance(self.actions, (tuple, list)) or not self.actions or len(self.actions) > 32:
            raise ValueError("actions must contain between 1 and 32 modeled actions")
        actions = tuple(self.actions)
        if not all(isinstance(item, ActionDefinition) for item in actions):
            raise ValueError("actions may contain only ActionDefinition values")
        if len({item.action_id for item in actions}) != len(actions):
            raise ValueError("action IDs must be unique within a rule")
        try:
            policy = self.error_policy if isinstance(self.error_policy, ActionErrorPolicy) else ActionErrorPolicy(self.error_policy)
        except (TypeError, ValueError) as error:
            raise ValueError("error_policy is unsupported") from error
        object.__setattr__(self, "dependencies", dependencies)
        object.__setattr__(self, "actions", actions)
        object.__setattr__(self, "input_contract_hints", _paths(self.input_contract_hints, "input_contract_hints"))
        object.__setattr__(self, "output_contract_hints", _paths(self.output_contract_hints, "output_contract_hints"))
        object.__setattr__(self, "error_policy", policy)
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class WorkflowVersion(StudioContract):
    version_id: str
    workflow_id: str
    version: int | str
    status: WorkflowVersionStatus
    rules: tuple[RuleDefinition, ...]
    derived_from_version_id: str | None
    change_summary: WorkflowChangeSummary
    authored_by: str
    reviewed_by: str | None
    approved_by: str | None
    created_at: str
    updated_at: str
    published_at: str | None
    source_lineage: WorkflowSourceLineage | None
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "version_id", stable_id(self.version_id, "version_id"))
        object.__setattr__(self, "workflow_id", stable_id(self.workflow_id, "workflow_id"))
        object.__setattr__(self, "version", _safe_version(self.version))
        object.__setattr__(self, "status", _enum(self.status, WorkflowVersionStatus, "status"))
        if not isinstance(self.rules, (tuple, list)) or len(self.rules) > 100:
            raise ValueError("rules must be a bounded RuleDefinition sequence")
        rules = tuple(self.rules)
        if not all(isinstance(item, RuleDefinition) for item in rules):
            raise ValueError("rules may contain only RuleDefinition values")
        if len({item.rule_id for item in rules}) != len(rules):
            raise ValueError("rule IDs must be unique within a version")
        if not isinstance(self.change_summary, WorkflowChangeSummary):
            raise ValueError("change_summary must be modeled")
        if self.source_lineage is not None and not isinstance(self.source_lineage, WorkflowSourceLineage):
            raise ValueError("source_lineage must be modeled")
        object.__setattr__(self, "rules", rules)
        object.__setattr__(self, "derived_from_version_id", optional_id(self.derived_from_version_id, "derived_from_version_id"))
        object.__setattr__(self, "authored_by", _actor(self.authored_by, "authored_by"))
        object.__setattr__(self, "reviewed_by", _actor(self.reviewed_by, "reviewed_by", optional=True))
        object.__setattr__(self, "approved_by", _actor(self.approved_by, "approved_by", optional=True))
        object.__setattr__(self, "created_at", utc_timestamp(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", utc_timestamp(self.updated_at, "updated_at"))
        object.__setattr__(self, "published_at", optional_timestamp(self.published_at, "published_at"))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class WorkflowDefinition(StudioContract):
    workflow_id: str
    tenant_id: str
    name: str
    description: str
    business_domain: str
    document_type: str | None
    status: WorkflowDefinitionStatus
    current_draft_version: WorkflowReference | None
    active_published_version: WorkflowReference | None
    ownership: WorkflowOwnership
    created_at: str
    updated_at: str
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "workflow_id", stable_id(self.workflow_id, "workflow_id"))
        object.__setattr__(self, "tenant_id", stable_id(self.tenant_id, "tenant_id"))
        object.__setattr__(self, "name", bounded_text(self.name, "name"))
        object.__setattr__(self, "description", bounded_text(self.description, "description", maximum=MAX_DESCRIPTION_LENGTH, allow_empty=True))
        object.__setattr__(self, "business_domain", stable_id(self.business_domain, "business_domain"))
        object.__setattr__(self, "document_type", optional_text(self.document_type, "document_type", maximum=64))
        object.__setattr__(self, "status", _enum(self.status, WorkflowDefinitionStatus, "status"))
        for field_name in ("current_draft_version", "active_published_version"):
            reference = getattr(self, field_name)
            if reference is not None and not isinstance(reference, WorkflowReference):
                raise ValueError(f"{field_name} must be a WorkflowReference")
            if reference is not None and reference.workflow_id != self.workflow_id:
                raise ValueError(f"{field_name} must reference this workflow")
        if not isinstance(self.ownership, WorkflowOwnership):
            raise ValueError("ownership must be modeled")
        object.__setattr__(self, "created_at", utc_timestamp(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", utc_timestamp(self.updated_at, "updated_at"))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class WorkflowPublication(StudioContract):
    publication_id: str
    workflow_id: str
    version_id: str
    status: WorkflowPublicationStatus
    environment: str
    approved_by: str | None
    created_at: str
    activated_at: str | None = None
    deactivated_at: str | None = None
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "publication_id", stable_id(self.publication_id, "publication_id"))
        object.__setattr__(self, "workflow_id", stable_id(self.workflow_id, "workflow_id"))
        object.__setattr__(self, "version_id", stable_id(self.version_id, "version_id"))
        object.__setattr__(self, "status", _enum(self.status, WorkflowPublicationStatus, "status"))
        object.__setattr__(self, "environment", stable_id(self.environment, "environment"))
        object.__setattr__(self, "approved_by", _actor(self.approved_by, "approved_by", optional=True))
        object.__setattr__(self, "created_at", utc_timestamp(self.created_at, "created_at"))
        object.__setattr__(self, "activated_at", optional_timestamp(self.activated_at, "activated_at"))
        object.__setattr__(self, "deactivated_at", optional_timestamp(self.deactivated_at, "deactivated_at"))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))


def _safe_version(value: Any) -> int | str:
    if isinstance(value, int) and not isinstance(value, bool):
        return positive_integer(value, "version")
    return version_label(value, "version")


def _paths(values: Sequence[str], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or len(values) > 32:
        raise ValueError(f"{field_name} must be a bounded path sequence")
    result = tuple(logical_path(item, field_name) for item in values)
    if len(set(result)) != len(result):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result
