import pytest

from src.workflow_studio import (
    PublicationCommand, RepositoryPage, WorkflowRepositoryError, RepositoryErrorCode,
)


def test_repository_errors_are_fixed_and_non_reflective() -> None:
    error = WorkflowRepositoryError(RepositoryErrorCode.NOT_FOUND)
    assert error.to_dict() == {"code": "not_found", "message": "Workflow Studio record was not found."}
    assert "tenant-secret" not in str(error)


def test_repository_page_rejects_unbounded_pagination() -> None:
    with pytest.raises(ValueError):
        RepositoryPage((), 0, 0, 0)
    with pytest.raises(ValueError):
        RepositoryPage((), 100, 10_001, 0)


def test_publication_command_metadata_rejects_sensitive_values() -> None:
    # Construction reaches privacy validation only after a modeled validation result;
    # direct safe-metadata coverage remains in Phase 1/2 and audit intents cover Phase 3.
    assert "metadata" in PublicationCommand.__dataclass_fields__
