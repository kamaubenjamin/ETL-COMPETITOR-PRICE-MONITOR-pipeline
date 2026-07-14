"""Deterministic process-local Workflow Studio repository implementation."""

from __future__ import annotations

from threading import RLock

from .contracts import stable_id
from .definitions import WorkflowDefinition, WorkflowPublication, WorkflowVersion
from .repositories import (
    RepositoryPage,
    StoredWorkflowDefinition,
    StoredWorkflowPublication,
    StoredWorkflowVersion,
)
from .repository_errors import RepositoryErrorCode, WorkflowRepositoryError
from .statuses import WorkflowDefinitionStatus, WorkflowPublicationStatus, WorkflowVersionStatus


_CURRENT_DRAFT_STATUSES = {
    WorkflowVersionStatus.DRAFT,
    WorkflowVersionStatus.VALIDATED,
    WorkflowVersionStatus.TEST_PASSED,
    WorkflowVersionStatus.APPROVED,
}
_VERSION_TRANSITIONS = {
    WorkflowVersionStatus.DRAFT: {WorkflowVersionStatus.VALIDATED, WorkflowVersionStatus.ARCHIVED},
    WorkflowVersionStatus.VALIDATED: {WorkflowVersionStatus.DRAFT, WorkflowVersionStatus.TEST_PASSED, WorkflowVersionStatus.ARCHIVED},
    WorkflowVersionStatus.TEST_PASSED: {WorkflowVersionStatus.DRAFT, WorkflowVersionStatus.APPROVED, WorkflowVersionStatus.ARCHIVED},
    WorkflowVersionStatus.APPROVED: {WorkflowVersionStatus.PUBLISHED},
    WorkflowVersionStatus.PUBLISHED: {WorkflowVersionStatus.SUPERSEDED, WorkflowVersionStatus.INACTIVE},
    WorkflowVersionStatus.SUPERSEDED: {WorkflowVersionStatus.ARCHIVED},
    WorkflowVersionStatus.INACTIVE: {WorkflowVersionStatus.ARCHIVED},
    WorkflowVersionStatus.ARCHIVED: set(),
}
_PUBLICATION_TRANSITIONS = {
    WorkflowPublicationStatus.NOT_PUBLISHED: {WorkflowPublicationStatus.PENDING_APPROVAL},
    WorkflowPublicationStatus.PENDING_APPROVAL: {WorkflowPublicationStatus.APPROVED},
    WorkflowPublicationStatus.APPROVED: {WorkflowPublicationStatus.ACTIVE},
    WorkflowPublicationStatus.ACTIVE: {WorkflowPublicationStatus.INACTIVE, WorkflowPublicationStatus.SUPERSEDED},
    WorkflowPublicationStatus.INACTIVE: {WorkflowPublicationStatus.ARCHIVED},
    WorkflowPublicationStatus.SUPERSEDED: {WorkflowPublicationStatus.ARCHIVED},
    WorkflowPublicationStatus.ARCHIVED: set(),
}
class InMemoryWorkflowStudioStore:
    """Thread-safe local store. It performs no I/O and offers no durability."""

    def __init__(self) -> None:
        self._definitions: dict[tuple[str, str], StoredWorkflowDefinition] = {}
        self._versions: dict[tuple[str, str], StoredWorkflowVersion] = {}
        self._publications: dict[tuple[str, str], StoredWorkflowPublication] = {}
        self._lock = RLock()

    def create_definition(self, definition: WorkflowDefinition) -> StoredWorkflowDefinition:
        key = (definition.tenant_id, definition.workflow_id)
        with self._lock:
            if key in self._definitions:
                raise WorkflowRepositoryError(RepositoryErrorCode.DUPLICATE_WORKFLOW)
            stored = StoredWorkflowDefinition(definition, 1)
            self._definitions[key] = stored
            return stored

    def get_definition(self, tenant_id: str, workflow_id: str) -> StoredWorkflowDefinition | None:
        return self._definitions.get((_id(tenant_id, "tenant_id"), _id(workflow_id, "workflow_id")))

    def list_definitions(self, tenant_id: str, *, limit: int = 100, offset: int = 0) -> RepositoryPage[StoredWorkflowDefinition]:
        tenant = _id(tenant_id, "tenant_id")
        with self._lock:
            values = tuple(sorted((item for (scope, _), item in self._definitions.items() if scope == tenant), key=lambda item: item.value.workflow_id))
        return _page(values, limit, offset)

    def update_definition(self, definition: WorkflowDefinition, expected_revision: int) -> StoredWorkflowDefinition:
        key = (definition.tenant_id, definition.workflow_id)
        with self._lock:
            current = self._require_definition(key)
            _revision(current.revision, expected_revision)
            if current.value.status is WorkflowDefinitionStatus.ARCHIVED and definition != current.value:
                raise WorkflowRepositoryError(RepositoryErrorCode.INVALID_STATE)
            stored = StoredWorkflowDefinition(definition, current.revision + 1)
            self._definitions[key] = stored
            return stored

    def create_version(self, tenant_id: str, version: WorkflowVersion) -> StoredWorkflowVersion:
        tenant = _id(tenant_id, "tenant_id")
        key = (tenant, version.version_id)
        with self._lock:
            self._require_definition((tenant, version.workflow_id))
            if key in self._versions:
                raise WorkflowRepositoryError(RepositoryErrorCode.DUPLICATE_VERSION)
            workflow_versions = self._workflow_versions(tenant, version.workflow_id)
            if any(item.value.version == version.version for item in workflow_versions):
                raise WorkflowRepositoryError(RepositoryErrorCode.DUPLICATE_VERSION_LABEL)
            if version.status in _CURRENT_DRAFT_STATUSES and any(item.value.status in _CURRENT_DRAFT_STATUSES for item in workflow_versions):
                raise WorkflowRepositoryError(RepositoryErrorCode.CURRENT_DRAFT_EXISTS)
            stored = StoredWorkflowVersion(tenant, version, 1)
            self._versions[key] = stored
            return stored

    def get_version(self, tenant_id: str, version_id: str) -> StoredWorkflowVersion | None:
        return self._versions.get((_id(tenant_id, "tenant_id"), _id(version_id, "version_id")))

    def list_versions(self, tenant_id: str, workflow_id: str, *, limit: int = 100, offset: int = 0) -> RepositoryPage[StoredWorkflowVersion]:
        tenant = _id(tenant_id, "tenant_id")
        workflow = _id(workflow_id, "workflow_id")
        with self._lock:
            values = tuple(sorted(self._workflow_versions(tenant, workflow), key=lambda item: (_version_key(item.value.version), item.value.version_id)))
        return _page(values, limit, offset)

    def find_current_draft(self, tenant_id: str, workflow_id: str) -> StoredWorkflowVersion | None:
        versions = self.list_versions(tenant_id, workflow_id).items
        return next((item for item in reversed(versions) if item.value.status in _CURRENT_DRAFT_STATUSES), None)

    def update_draft(self, tenant_id: str, version: WorkflowVersion, expected_revision: int) -> StoredWorkflowVersion:
        tenant = _id(tenant_id, "tenant_id")
        key = (tenant, version.version_id)
        with self._lock:
            current = self._require_version(key)
            _revision(current.revision, expected_revision)
            if current.value.workflow_id != version.workflow_id:
                raise WorkflowRepositoryError(RepositoryErrorCode.WORKFLOW_MISMATCH)
            if current.value.status is not WorkflowVersionStatus.DRAFT or version.status is not WorkflowVersionStatus.DRAFT:
                raise WorkflowRepositoryError(RepositoryErrorCode.IMMUTABLE_VERSION)
            if current.value.version != version.version or current.value.derived_from_version_id != version.derived_from_version_id:
                raise WorkflowRepositoryError(RepositoryErrorCode.IMMUTABLE_VERSION)
            stored = StoredWorkflowVersion(tenant, version, current.revision + 1)
            self._versions[key] = stored
            return stored

    def transition_version(self, tenant_id: str, version: WorkflowVersion, expected_revision: int) -> StoredWorkflowVersion:
        tenant = _id(tenant_id, "tenant_id")
        key = (tenant, version.version_id)
        with self._lock:
            current = self._require_version(key)
            _revision(current.revision, expected_revision)
            if not _same_version_content(current.value, version):
                raise WorkflowRepositoryError(RepositoryErrorCode.IMMUTABLE_VERSION)
            if version.status not in _VERSION_TRANSITIONS[current.value.status]:
                raise WorkflowRepositoryError(RepositoryErrorCode.INVALID_STATE)
            stored = StoredWorkflowVersion(tenant, version, current.revision + 1)
            self._versions[key] = stored
            return stored

    def create_publication(self, tenant_id: str, publication: WorkflowPublication) -> StoredWorkflowPublication:
        tenant = _id(tenant_id, "tenant_id")
        key = (tenant, publication.publication_id)
        with self._lock:
            if key in self._publications:
                raise WorkflowRepositoryError(RepositoryErrorCode.DUPLICATE_PUBLICATION)
            version = self._require_version((tenant, publication.version_id))
            if version.value.workflow_id != publication.workflow_id:
                raise WorkflowRepositoryError(RepositoryErrorCode.WORKFLOW_MISMATCH)
            if publication.status is WorkflowPublicationStatus.ACTIVE and self._active_publication(tenant, publication.workflow_id) is not None:
                raise WorkflowRepositoryError(RepositoryErrorCode.ACTIVE_PUBLICATION_EXISTS)
            stored = StoredWorkflowPublication(tenant, publication, 1)
            self._publications[key] = stored
            return stored

    def get_publication(self, tenant_id: str, publication_id: str) -> StoredWorkflowPublication | None:
        return self._publications.get((_id(tenant_id, "tenant_id"), _id(publication_id, "publication_id")))

    def find_active_publication(self, tenant_id: str, workflow_id: str) -> StoredWorkflowPublication | None:
        return self._active_publication(_id(tenant_id, "tenant_id"), _id(workflow_id, "workflow_id"))

    def transition_publication(self, tenant_id: str, publication: WorkflowPublication, expected_revision: int) -> StoredWorkflowPublication:
        tenant = _id(tenant_id, "tenant_id")
        key = (tenant, publication.publication_id)
        with self._lock:
            current = self._require_publication(key)
            _revision(current.revision, expected_revision)
            if (
                current.value.workflow_id != publication.workflow_id
                or current.value.version_id != publication.version_id
                or current.value.environment != publication.environment
                or current.value.created_at != publication.created_at
            ):
                raise WorkflowRepositoryError(RepositoryErrorCode.IMMUTABLE_VERSION)
            if publication.status not in _PUBLICATION_TRANSITIONS[current.value.status]:
                raise WorkflowRepositoryError(RepositoryErrorCode.INVALID_STATE)
            stored = StoredWorkflowPublication(tenant, publication, current.revision + 1)
            self._publications[key] = stored
            return stored

    def commit_publication(
        self,
        tenant_id: str,
        version: WorkflowVersion,
        expected_version_revision: int,
        publication: WorkflowPublication,
        definition: WorkflowDefinition,
        expected_definition_revision: int,
        *,
        previous_publication: WorkflowPublication | None = None,
        previous_version: WorkflowVersion | None = None,
        expected_previous_publication_revision: int | None = None,
        expected_previous_version_revision: int | None = None,
    ) -> tuple[StoredWorkflowVersion, StoredWorkflowPublication, StoredWorkflowDefinition, StoredWorkflowPublication | None, StoredWorkflowVersion | None]:
        tenant = _id(tenant_id, "tenant_id")
        with self._lock:
            current_version = self._require_version((tenant, version.version_id))
            current_definition = self._require_definition((tenant, definition.workflow_id))
            _revision(current_version.revision, expected_version_revision)
            _revision(current_definition.revision, expected_definition_revision)
            if publication.publication_id in {key[1] for key in self._publications if key[0] == tenant}:
                raise WorkflowRepositoryError(RepositoryErrorCode.DUPLICATE_PUBLICATION)
            if version.workflow_id != definition.workflow_id or publication.workflow_id != definition.workflow_id or publication.version_id != version.version_id:
                raise WorkflowRepositoryError(RepositoryErrorCode.WORKFLOW_MISMATCH)
            active = self._active_publication(tenant, definition.workflow_id)
            if (active is None) != (previous_publication is None):
                raise WorkflowRepositoryError(RepositoryErrorCode.ACTIVE_PUBLICATION_EXISTS)
            prior_publication_stored = None
            prior_version_stored = None
            if active is not None:
                if previous_publication is None or previous_version is None or active.value.publication_id != previous_publication.publication_id:
                    raise WorkflowRepositoryError(RepositoryErrorCode.ACTIVE_PUBLICATION_EXISTS)
                current_prior_version = self._require_version((tenant, previous_version.version_id))
                _revision(active.revision, expected_previous_publication_revision)
                _revision(current_prior_version.revision, expected_previous_version_revision)
                prior_publication_stored = StoredWorkflowPublication(tenant, previous_publication, active.revision + 1)
                prior_version_stored = StoredWorkflowVersion(tenant, previous_version, current_prior_version.revision + 1)
            new_version = StoredWorkflowVersion(tenant, version, current_version.revision + 1)
            new_publication = StoredWorkflowPublication(tenant, publication, 1)
            new_definition = StoredWorkflowDefinition(definition, current_definition.revision + 1)
            if prior_publication_stored is not None and prior_version_stored is not None:
                self._publications[(tenant, prior_publication_stored.value.publication_id)] = prior_publication_stored
                self._versions[(tenant, prior_version_stored.value.version_id)] = prior_version_stored
            self._versions[(tenant, version.version_id)] = new_version
            self._publications[(tenant, publication.publication_id)] = new_publication
            self._definitions[(tenant, definition.workflow_id)] = new_definition
            return new_version, new_publication, new_definition, prior_publication_stored, prior_version_stored

    def commit_deactivation(
        self,
        tenant_id: str,
        publication: WorkflowPublication,
        expected_publication_revision: int,
        version: WorkflowVersion,
        expected_version_revision: int,
        definition: WorkflowDefinition,
        expected_definition_revision: int,
    ) -> tuple[StoredWorkflowPublication, StoredWorkflowVersion, StoredWorkflowDefinition]:
        tenant = _id(tenant_id, "tenant_id")
        with self._lock:
            current_publication = self._require_publication((tenant, publication.publication_id))
            current_version = self._require_version((tenant, version.version_id))
            current_definition = self._require_definition((tenant, definition.workflow_id))
            _revision(current_publication.revision, expected_publication_revision)
            _revision(current_version.revision, expected_version_revision)
            _revision(current_definition.revision, expected_definition_revision)
            if current_publication.value.status is not WorkflowPublicationStatus.ACTIVE:
                raise WorkflowRepositoryError(RepositoryErrorCode.INVALID_STATE)
            if publication.version_id != version.version_id or publication.workflow_id != definition.workflow_id:
                raise WorkflowRepositoryError(RepositoryErrorCode.WORKFLOW_MISMATCH)
            stored_publication = StoredWorkflowPublication(tenant, publication, current_publication.revision + 1)
            stored_version = StoredWorkflowVersion(tenant, version, current_version.revision + 1)
            stored_definition = StoredWorkflowDefinition(definition, current_definition.revision + 1)
            self._publications[(tenant, publication.publication_id)] = stored_publication
            self._versions[(tenant, version.version_id)] = stored_version
            self._definitions[(tenant, definition.workflow_id)] = stored_definition
            return stored_publication, stored_version, stored_definition

    def _workflow_versions(self, tenant_id: str, workflow_id: str) -> tuple[StoredWorkflowVersion, ...]:
        return tuple(item for (scope, _), item in self._versions.items() if scope == tenant_id and item.value.workflow_id == workflow_id)

    def _active_publication(self, tenant_id: str, workflow_id: str) -> StoredWorkflowPublication | None:
        matches = [item for (scope, _), item in self._publications.items() if scope == tenant_id and item.value.workflow_id == workflow_id and item.value.status is WorkflowPublicationStatus.ACTIVE]
        if len(matches) > 1:
            raise WorkflowRepositoryError(RepositoryErrorCode.ACTIVE_PUBLICATION_EXISTS)
        return matches[0] if matches else None

    def _require_definition(self, key: tuple[str, str]) -> StoredWorkflowDefinition:
        value = self._definitions.get(key)
        if value is None:
            raise WorkflowRepositoryError(RepositoryErrorCode.NOT_FOUND)
        return value

    def _require_version(self, key: tuple[str, str]) -> StoredWorkflowVersion:
        value = self._versions.get(key)
        if value is None:
            raise WorkflowRepositoryError(RepositoryErrorCode.NOT_FOUND)
        return value

    def _require_publication(self, key: tuple[str, str]) -> StoredWorkflowPublication:
        value = self._publications.get(key)
        if value is None:
            raise WorkflowRepositoryError(RepositoryErrorCode.NOT_FOUND)
        return value


def _page(values: tuple, limit: int, offset: int) -> RepositoryPage:
    page = RepositoryPage((), limit, offset, len(values))
    return RepositoryPage(values[page.offset:page.offset + page.limit], page.limit, page.offset, page.total)


def _id(value: str, field_name: str) -> str:
    return stable_id(value, field_name)


def _revision(actual: int, expected: int | None) -> None:
    if isinstance(expected, bool) or not isinstance(expected, int) or expected != actual:
        raise WorkflowRepositoryError(RepositoryErrorCode.VERSION_CONFLICT)


def _version_key(value: int | str) -> tuple[int, int | str]:
    return (0, value) if isinstance(value, int) else (1, value)


def _same_version_content(left: WorkflowVersion, right: WorkflowVersion) -> bool:
    fields = ("version_id", "workflow_id", "version", "rules", "derived_from_version_id", "change_summary", "authored_by", "created_at", "source_lineage", "metadata")
    return all(getattr(left, field) == getattr(right, field) for field in fields)
