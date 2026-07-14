from dataclasses import FrozenInstanceError

import pytest

from src.workflow_studio.actions import ActionDefinition


def make_action(**changes: object) -> ActionDefinition:
    values = dict(
        action_id="action-1", action_type="transform", operation_name="trim",
        operation_version="1", source_path="invoice.reference", target_path="invoice.reference",
        arguments={"mode": "strict", "allowed": ["A", "B"]}, metadata={"owner": "finance"},
    )
    values.update(changes)
    return ActionDefinition(**values)


def test_action_is_immutable_and_serializes_safe_arguments() -> None:
    action = make_action()
    assert action.to_dict()["arguments"] == {"allowed": ["A", "B"], "mode": "strict"}
    with pytest.raises(FrozenInstanceError):
        action.enabled = False
    with pytest.raises(TypeError):
        action.arguments["mode"] = "unsafe"


@pytest.mark.parametrize("arguments", [
    {"script": "__import__('os')"}, {"query": "select * from users"},
    {"endpoint": "https://example.invalid"}, {"path": "C:\\private\\record.txt"},
    {"handler": lambda: None}, {"nested": {"key": "value"}},
])
def test_action_rejects_code_external_configuration_and_nested_values(arguments: object) -> None:
    with pytest.raises(ValueError):
        make_action(arguments=arguments)


def test_action_rejects_sensitive_argument_keys_and_physical_paths() -> None:
    with pytest.raises(ValueError):
        make_action(arguments={"api_token": "value"})
    with pytest.raises(ValueError):
        make_action(source_path="credentials.token")
