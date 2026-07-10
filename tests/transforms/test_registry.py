import pytest

from src.transforms.contracts import OPERATION_TYPES
from src.transforms.errors import ConfigurationError
from src.transforms.registry import DEFAULT_OPERATION_REGISTRY, OperationRegistry


def test_default_registry_is_exact_fixed_allowlist():
    assert frozenset(DEFAULT_OPERATION_REGISTRY.names) == OPERATION_TYPES
    assert "filter" not in DEFAULT_OPERATION_REGISTRY.names
    assert "add_column" not in DEFAULT_OPERATION_REGISTRY.names


def test_registry_resolves_allowlisted_operation():
    assert DEFAULT_OPERATION_REGISTRY.require("field_map") == "field_map"


def test_registry_rejects_unknown_operation_with_path():
    with pytest.raises(ConfigurationError) as caught:
        DEFAULT_OPERATION_REGISTRY.require("execute_python", ("operations", 0, "type"))
    assert caught.value.code == "unknown_operation"
    assert caught.value.path == "$.operations[0].type"


def test_registry_rejects_duplicate_registration():
    with pytest.raises(ConfigurationError) as caught:
        OperationRegistry(["rename", "rename"])
    assert caught.value.code == "duplicate_registration"
    assert caught.value.path == "$.operations[1]"

