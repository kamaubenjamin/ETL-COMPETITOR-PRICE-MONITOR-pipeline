import ast
from pathlib import Path
import sys

from src.export_runtime import ExportAdapterPort, ExportAdapterResult, ExportPayload


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "export_runtime"
FORBIDDEN_ROOTS = {
    "api",
    "document_state",
    "entity_runtime",
    "matching_runtime",
    "observability",
    "platform_runtime",
    "review_runtime",
    "security",
    "storage",
    "telemetry",
    "transforms",
    "ui",
    "workflow_runtime",
}


class AdapterFixture:
    def export(self, payload: ExportPayload) -> ExportAdapterResult:
        raise AssertionError("Phase 1 contract test must not perform adapter I/O")


def imports_for(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield 0, alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.level, node.module or ""


def test_adapter_port_is_structural_and_narrow():
    assert isinstance(AdapterFixture(), ExportAdapterPort)
    assert set(ExportAdapterPort.__dict__) & {"readiness", "authorize", "audit", "advance_lifecycle"} == set()


def test_export_runtime_imports_only_standard_library_and_package_local_modules():
    stdlib = set(sys.stdlib_module_names)
    violations = []
    for path in PACKAGE.rglob("*.py"):
        for level, module in imports_for(path):
            root = module.split(".", 1)[0]
            if level:
                continue
            if root not in stdlib and root != "src":
                violations.append((path.name, module))
            if root in FORBIDDEN_ROOTS or module.startswith("src."):
                violations.append((path.name, module))
    assert violations == []


def test_existing_source_modules_do_not_import_export_runtime():
    violations = []
    for path in (ROOT / "src").rglob("*.py"):
        if PACKAGE in path.parents:
            continue
        for _level, module in imports_for(path):
            if module == "export_runtime" or module.startswith("export_runtime.") or module.startswith("src.export_runtime"):
                violations.append(str(path.relative_to(ROOT)))
    assert violations == []


def test_export_runtime_has_no_durable_repository_or_real_adapter_implementation():
    module_names = {path.name for path in PACKAGE.glob("*.py")}
    assert "repositories_sqlite.py" not in module_names
    adapter_files = {path.name for path in (PACKAGE / "adapters").glob("*.py")}
    assert adapter_files == {"__init__.py", "placeholder.py"}
