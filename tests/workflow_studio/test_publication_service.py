from dataclasses import replace

from src.workflow_studio import (
    ActionDefinition, InMemoryWorkflowOperationCatalog, InMemoryWorkflowStudioStore,
    PublicationCommand, RuleDefinition, WorkflowChangeSummary, WorkflowDefinition,
    WorkflowOwnership, WorkflowPublicationService, WorkflowValidationService, WorkflowVersion,
)


NOW = "2026-07-14T10:00:00+00:00"
LATER = "2026-07-15T10:00:00+00:00"


def version(version_id: str, label: int) -> WorkflowVersion:
    action = ActionDefinition(f"action-{label}", "runtime", "filter", "1")
    rule = RuleDefinition(f"rule-{label}", "Rule", "process", "", (), 0, True, False, None, (action,))
    return WorkflowVersion(version_id, "workflow-1", label, "approved", (rule,), None, WorkflowChangeSummary("Approved"), "author-1", "reviewer-1", "approver-1", NOW, NOW, None, None)


def setup() -> tuple[InMemoryWorkflowStudioStore, WorkflowPublicationService, WorkflowVersion]:
    store = InMemoryWorkflowStudioStore()
    store.create_definition(WorkflowDefinition("workflow-1", "tenant-1", "Flow", "", "finance", None, "draft", None, None, WorkflowOwnership("actor-1", "actor-1"), NOW, NOW))
    approved = version("version-1", 1)
    store.create_version("tenant-1", approved)
    return store, WorkflowPublicationService(store), approved


def command(value: WorkflowVersion, publication_id: str, *, definition_revision: int, supersede: bool = False, timestamp: str = NOW) -> PublicationCommand:
    validation = WorkflowValidationService(InMemoryWorkflowOperationCatalog()).validate(value)
    return PublicationCommand(
        "tenant-1", "workflow-1", value.version_id, publication_id, "production", "publisher-1",
        1, definition_revision, validation, True, True, True, True, False, supersede, timestamp,
    )


def test_publication_service_creates_immutable_record_and_updates_definition() -> None:
    store, service, approved = setup()
    result = service.publish(command(approved, "publication-1", definition_revision=1))
    assert result.published
    assert result.version.value.status.value == "published"
    assert result.publication.value.status.value == "active"
    assert result.definition.value.active_published_version.version_id == "version-1"
    assert [item.event_type.value for item in result.audit_intents] == ["publication_requested", "workflow_published"]


def test_previous_active_publication_is_superseded_safely() -> None:
    store, service, approved = setup()
    first = service.publish(command(approved, "publication-1", definition_revision=1))
    second_version = version("version-2", 2)
    store.create_version("tenant-1", second_version)
    second = service.publish(command(second_version, "publication-2", definition_revision=first.definition.revision, supersede=True, timestamp=LATER))
    assert second.published
    assert second.superseded_publication.value.status.value == "superseded"
    assert store.get_version("tenant-1", "version-1").value.status.value == "superseded"
    assert store.find_active_publication("tenant-1", "workflow-1").value.publication_id == "publication-2"


def test_active_publication_is_not_replaced_without_explicit_policy() -> None:
    store, service, approved = setup()
    first = service.publish(command(approved, "publication-1", definition_revision=1))
    second_version = version("version-2", 2)
    store.create_version("tenant-1", second_version)
    denied = service.publish(command(second_version, "publication-2", definition_revision=first.definition.revision))
    assert not denied.published
    assert "active_publication_conflict" in {item.code.value for item in denied.issues}


def test_deactivation_does_not_activate_another_version() -> None:
    store, service, approved = setup()
    published = service.publish(command(approved, "publication-1", definition_revision=1))
    result = service.deactivate(
        "tenant-1", "workflow-1", actor_id="publisher-1", occurred_at=LATER,
        expected_publication_revision=published.publication.revision,
        expected_definition_revision=published.definition.revision,
    )
    assert result.publication.value.status.value == "inactive"
    assert store.find_active_publication("tenant-1", "workflow-1") is None
    assert result.definition.value.active_published_version is None


def test_archive_requires_no_active_publication_and_retains_history() -> None:
    store, service, approved = setup()
    published = service.publish(command(approved, "publication-1", definition_revision=1))
    blocked = service.archive_definition("tenant-1", "workflow-1", actor_id="actor-1", occurred_at=LATER, expected_definition_revision=published.definition.revision)
    assert not blocked.published and blocked.issues[0].code.value == "archive_blocked"
    inactive = service.deactivate("tenant-1", "workflow-1", actor_id="actor-1", occurred_at=LATER, expected_publication_revision=1, expected_definition_revision=published.definition.revision)
    archived = service.archive_definition("tenant-1", "workflow-1", actor_id="actor-1", occurred_at=LATER, expected_definition_revision=inactive.definition.revision)
    assert archived.definition.value.status.value == "archived"
    assert store.get_version("tenant-1", "version-1") is not None
    assert store.get_publication("tenant-1", "publication-1") is not None
