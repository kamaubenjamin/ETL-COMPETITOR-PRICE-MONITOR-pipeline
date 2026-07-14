import pytest

from src.workflow_studio import safe_logical_path, validate_logical_path


@pytest.mark.parametrize("path", [
    "field", "customer.name", "line_items[].product_code", "document.references.purchase_order",
])
def test_controlled_logical_paths_are_allowed(path: str) -> None:
    assert safe_logical_path(path) == path
    assert validate_logical_path(path) == ()


@pytest.mark.parametrize("path", [
    "C:\\records\\item", "https://example.invalid/value", "select.value;drop", "../secret",
    "items[*].name", "items[0].name", "field()", "field..name", "powershell.command",
])
def test_physical_external_sql_shell_and_expression_paths_are_rejected(path: str) -> None:
    assert validate_logical_path(path)[0].code == "invalid_path"


@pytest.mark.parametrize("path", ["internal.state", "system.audit", "security.claims", "auth.subject"])
def test_protected_roots_are_blocked(path: str) -> None:
    assert validate_logical_path(path)[0].code == "protected_path"
