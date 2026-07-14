import pytest

from src.workflow_studio.actions import ActionDefinition
from src.workflow_studio.contracts import safe_metadata
from src.workflow_studio.errors import WorkflowStudioError, WorkflowStudioErrorCode


@pytest.mark.parametrize("metadata", [
    {"access_token": "value"}, {"raw_claims": "value"}, {"stack_trace": "value"},
    {"file_path": "document.txt"}, {"raw_rows": "value"}, {"payload": "value"},
    {"safe": {"nested": "value"}}, {"safe": ["not", "scalar"]},
])
def test_metadata_rejects_sensitive_and_nested_values(metadata: object) -> None:
    with pytest.raises(ValueError):
        safe_metadata(metadata)


def test_metadata_is_bounded_and_immutable() -> None:
    with pytest.raises(ValueError):
        safe_metadata({f"key_{index}": index for index in range(21)})
    metadata = safe_metadata({"owner": "finance"})
    with pytest.raises(TypeError):
        metadata["owner"] = "changed"


def test_errors_have_fixed_messages_and_do_not_echo_sensitive_input() -> None:
    error = WorkflowStudioError(WorkflowStudioErrorCode.INVALID_ACTION, field="arguments")
    assert error.to_dict() == {
        "code": "invalid_action", "message": "Workflow action is invalid.", "field": "arguments",
    }
    fallback = WorkflowStudioError("secret-value")
    assert "secret-value" not in str(fallback)
    assert fallback.code == "internal_error"


def test_serialized_action_never_contains_callable_or_nested_configuration() -> None:
    with pytest.raises(ValueError):
        ActionDefinition("action-1", "runtime", "filter", "1", arguments={"callback": object()})
