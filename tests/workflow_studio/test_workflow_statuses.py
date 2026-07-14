from src.workflow_studio.statuses import (
    OperationAvailabilityStatus,
    RuleStatus,
    WorkflowDefinitionStatus,
    WorkflowPublicationStatus,
    WorkflowVersionStatus,
)


def test_status_catalogs_are_fixed_and_ordered() -> None:
    assert [item.value for item in WorkflowDefinitionStatus] == [
        "draft", "validating", "invalid", "valid", "test_ready", "testing",
        "test_failed", "approved", "published", "inactive", "archived",
    ]
    assert [item.value for item in WorkflowVersionStatus] == [
        "draft", "validated", "test_passed", "approved", "published",
        "superseded", "inactive", "archived",
    ]
    assert [item.value for item in WorkflowPublicationStatus] == [
        "not_published", "pending_approval", "approved", "active", "inactive",
        "superseded", "archived",
    ]
    assert [item.value for item in RuleStatus] == ["enabled", "disabled", "skipped"]
    assert [item.value for item in OperationAvailabilityStatus] == ["available", "unavailable", "deprecated"]


def test_statuses_are_string_enums() -> None:
    assert WorkflowDefinitionStatus.DRAFT == "draft"
    assert WorkflowPublicationStatus.ACTIVE.value == "active"
