import ast
import inspect
from pathlib import Path

import pytest

from src.document_state import persistence
from src.document_state.persistence import PersistenceError, PersistenceErrorCode


ROOT = Path(persistence.__file__).parent


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(f"{'.' * node.level}{node.module}")
    return tuple(modules), tree


def test_persistence_modules_have_only_standard_or_package_local_imports():
    standard = {"__future__", "dataclasses", "enum", "types", "typing"}
    for path in ROOT.rglob("*.py"):
        modules, _ = _imports(path)
        for module in modules:
            assert module.startswith(".") or module.split(".")[0] in standard


def test_phase_one_has_no_database_file_or_network_access():
    forbidden_imports = {"sqlite3", "sqlalchemy", "requests", "httpx", "socket", "urllib"}
    forbidden_calls = {"connect", "open", "urlopen"}
    for path in ROOT.rglob("*.py"):
        modules, tree = _imports(path)
        assert not {module.lstrip(".").split(".")[0] for module in modules} & forbidden_imports
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert not calls & forbidden_calls
    assert not hasattr(persistence, "create_repository")


@pytest.mark.parametrize("code", list(PersistenceErrorCode))
def test_persistence_errors_are_fixed_and_privacy_safe(code):
    error = PersistenceError(code, field="backend")
    assert error.to_dict() == {"code": code.value, "message": error.message, "field": "backend"}
    source = inspect.getsource(type(error)).lower()
    for forbidden in ("connection_string", "database_path", "payload", "sql", "traceback"):
        assert forbidden not in str(error).lower()
        assert forbidden not in error.message.lower()
    assert "raise" in source


def test_persistence_errors_reject_arbitrary_codes():
    with pytest.raises(ValueError):
        PersistenceError("driver_exception")
