"""Persistence-neutral repository records and structural protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar, Generic, runtime_checkable

from .contracts import StudioContract, non_negative_integer, positive_integer, stable_id
from .definitions import WorkflowDefinition, WorkflowPublication, WorkflowVersion


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RepositoryPage(StudioContract, Generic[T]):
    items: tuple[T, ...]
    limit: int
    offset: int
    total: int

    def __post_init__(self) -> None:
        if not isinstance(self.items, (tuple, list)):
            raise ValueError("items must be a sequence")
        object.__setattr__(self, "items", tuple(self.items))
        limit = positive_integer(self.limit, "limit")
        if limit > 100:
            raise ValueError("limit must not exceed 100")
        offset = non_negative_integer(self.offset, "offset")
        if offset > 10_000:
            raise ValueError("offset must not exceed 10000")
        object.__setattr__(self, "limit", limit)
        object.__setattr__(self, "offset", offset)
        object.__setattr__(self, "total", non_negative_integer(self.total, "total"))


@dataclass(frozen=True, slots=True)
class StoredWorkflowDefinition(StudioContract):
    value: WorkflowDefinition
    revision: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, WorkflowDefinition):
            raise ValueError("value must be a WorkflowDefinition")
        object.__setattr__(self, "revision", positive_integer(self.revision, "revision"))


@dataclass(frozen=True, slots=True)
class StoredWorkflowVersion(StudioContract):
    tenant_id: str
    value: WorkflowVersion
    revision: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenant_id", stable_id(self.tenant_id, "tenant_id"))
        if not isinstance(self.value, WorkflowVersion):
            raise ValueError("value must be a WorkflowVersion")
        object.__setattr__(self, "revision", positive_integer(self.revision, "revision"))


@dataclass(frozen=True, slots=True)
class StoredWorkflowPublication(StudioContract):
    tenant_id: str
    value: WorkflowPublication
    revision: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "tenant_id", stable_id(self.tenant_id, "tenant_id"))
        if not isinstance(self.value, WorkflowPublication):
            raise ValueError("value must be a WorkflowPublication")
        object.__setattr__(self, "revision", positive_integer(self.revision, "revision"))


@runtime_checkable
class WorkflowDefinitionRepositoryPort(Protocol):
    def create_definition(self, definition: WorkflowDefinition) -> StoredWorkflowDefinition: ...
    def get_definition(self, tenant_id: str, workflow_id: str) -> StoredWorkflowDefinition | None: ...
    def list_definitions(self, tenant_id: str, *, limit: int = 100, offset: int = 0) -> RepositoryPage[StoredWorkflowDefinition]: ...
    def update_definition(self, definition: WorkflowDefinition, expected_revision: int) -> StoredWorkflowDefinition: ...


@runtime_checkable
class WorkflowVersionRepositoryPort(Protocol):
    def create_version(self, tenant_id: str, version: WorkflowVersion) -> StoredWorkflowVersion: ...
    def get_version(self, tenant_id: str, version_id: str) -> StoredWorkflowVersion | None: ...
    def list_versions(self, tenant_id: str, workflow_id: str, *, limit: int = 100, offset: int = 0) -> RepositoryPage[StoredWorkflowVersion]: ...
    def find_current_draft(self, tenant_id: str, workflow_id: str) -> StoredWorkflowVersion | None: ...
    def update_draft(self, tenant_id: str, version: WorkflowVersion, expected_revision: int) -> StoredWorkflowVersion: ...


@runtime_checkable
class WorkflowPublicationRepositoryPort(Protocol):
    def create_publication(self, tenant_id: str, publication: WorkflowPublication) -> StoredWorkflowPublication: ...
    def get_publication(self, tenant_id: str, publication_id: str) -> StoredWorkflowPublication | None: ...
    def find_active_publication(self, tenant_id: str, workflow_id: str) -> StoredWorkflowPublication | None: ...
