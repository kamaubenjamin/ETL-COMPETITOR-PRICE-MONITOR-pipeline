import ast
from pathlib import Path
import sys

from src.upload_runtime import UploadArtifactReference, UploadArtifactStagingPort, UploadCommand, validate_upload


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "upload_runtime"
FORBIDDEN_ROOTS = {
    "api", "document_engine", "document_state", "export_runtime", "platform_runtime", "security",
    "storage", "telemetry", "ui", "workflow_runtime",
}


class NoIOStagingAdapter:
    def stage(self, command, validation):
        assert validation.valid
        return UploadArtifactReference("artifact-test", "test_placeholder", command.file_type, command.file_size_bytes, "2026-07-14T10:00:00Z")


def command():
    return UploadCommand("upload-001", "tenant-001", "actor-001", "invoice.pdf", 10, "pdf", "local_demo")


def test_staging_port_is_structural_and_test_adapter_performs_no_io():
    adapter = NoIOStagingAdapter()
    assert isinstance(adapter, UploadArtifactStagingPort)
    result = adapter.stage(command(), validate_upload(command()))
    assert result.provider_code == "test_placeholder"


def imports_for(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield 0, alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.level, node.module or ""


def test_upload_runtime_uses_only_standard_library_and_package_local_imports():
    violations = []
    for path in PACKAGE.glob("*.py"):
        for level, module in imports_for(path):
            root = module.split(".", 1)[0]
            if level:
                continue
            if root not in sys.stdlib_module_names or root in FORBIDDEN_ROOTS or module.startswith("src."):
                violations.append((path.name, module))
    assert violations == []


def test_upload_runtime_has_no_io_database_network_vendor_or_ai_code():
    source = "\n".join(path.read_text(encoding="utf-8-sig").lower() for path in PACKAGE.glob("*.py"))
    for forbidden in (
        "requests", "httpx", "urllib", "socket", "sqlite", "subprocess", "boto", "open(",
        "write_text", "read_bytes", "pandas", "sap", "oracle", "openai", "ocr",
    ):
        assert forbidden not in source


def test_existing_source_modules_do_not_import_upload_runtime():
    violations = []
    for path in (ROOT / "src").rglob("*.py"):
        if PACKAGE in path.parents:
            continue
        for _level, module in imports_for(path):
            if module == "upload_runtime" or module.startswith("upload_runtime.") or module.startswith("src.upload_runtime"):
                violations.append(str(path.relative_to(ROOT)))
    assert violations == []

