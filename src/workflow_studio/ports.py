"""Structural ports for later Workflow Studio adapters."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .definitions import WorkflowDefinition, WorkflowVersion
from .operation_catalog import OperationCategory, StudioOperationDefinition
from .statuses import OperationAvailabilityStatus


@runtime_checkable
class WorkflowOperationCatalogPort(Protocol):
    def get_operation(self, name: str, version: str | None = None) -> StudioOperationDefinition | None: ...

    def list_operations(
        self,
        *,
        category: OperationCategory | None = None,
        availability: OperationAvailabilityStatus | None = None,
    ) -> tuple[StudioOperationDefinition, ...]: ...


@runtime_checkable
class WorkflowDefinitionReadPort(Protocol):
    def get_definition(self, tenant_id: str, workflow_id: str) -> WorkflowDefinition | None: ...

    def list_definitions(self, tenant_id: str) -> tuple[WorkflowDefinition, ...]: ...


@runtime_checkable
class WorkflowDefinitionWritePort(Protocol):
    def create_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition: ...

    def update_definition(self, definition: WorkflowDefinition, expected_updated_at: str) -> WorkflowDefinition: ...


@runtime_checkable
class WorkflowVersionReadPort(Protocol):
    def get_version(self, tenant_id: str, workflow_id: str, version_id: str) -> WorkflowVersion | None: ...

    def list_versions(self, tenant_id: str, workflow_id: str) -> tuple[WorkflowVersion, ...]: ...


@runtime_checkable
class WorkflowVersionWritePort(Protocol):
    def create_version(self, tenant_id: str, version: WorkflowVersion) -> WorkflowVersion: ...

    def update_draft(self, tenant_id: str, version: WorkflowVersion, expected_updated_at: str) -> WorkflowVersion: ...
