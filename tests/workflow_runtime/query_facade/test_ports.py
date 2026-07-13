import ast
import inspect
from pathlib import Path
from typing import Protocol

from src.workflow_runtime.query_facade import ports


PORT_TYPES = (
    ports.DocumentReadPort,
    ports.ProcessingReadPort,
    ports.ValidationReadPort,
    ports.MatchingReadPort,
    ports.ReviewReadPort,
    ports.WorkflowRunReadPort,
    ports.AuditReadPort,
    ports.WorkflowQueryFacadePort,
)


def test_ports_are_structural_protocols():
    assert all(getattr(port, "_is_protocol", False) for port in PORT_TYPES)
    assert all(issubclass(port, Protocol) for port in PORT_TYPES)


def test_ports_expose_read_methods_only():
    method_names = {
        name
        for port in PORT_TYPES
        for name, value in inspect.getmembers(port, inspect.isfunction)
        if not name.startswith("_")
    }
    assert method_names
    assert all(name.startswith(("get_", "list_")) for name in method_names)
    assert not any(name.startswith(("create_", "update_", "delete_", "save_", "execute_", "submit_")) for name in method_names)


def test_query_facade_package_has_only_standard_library_and_local_imports():
    package = Path(ports.__file__).parent
    forbidden = {
        "api", "document_engine", "entity_runtime", "matching_runtime",
        "review_runtime", "storage", "streamlit", "telemetry", "transform",
        "transforms", "flowsync", "competitor",
    }
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0].lower() for alias in node.names}
                assert not roots & forbidden
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                assert node.module.split(".")[0].lower() not in forbidden


def test_ports_module_source_contains_no_forbidden_runtime_names():
    source = inspect.getsource(ports).lower()
    for forbidden in ("fastapi", "streamlit", "review_runtime", "entity_runtime", "matching_runtime", "document_engine", "storage", "telemetry", "flowsync", "competitor"):
        assert forbidden not in source
