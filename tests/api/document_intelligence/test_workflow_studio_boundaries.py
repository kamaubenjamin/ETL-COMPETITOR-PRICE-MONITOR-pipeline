from pathlib import Path


def test_api_import_direction_is_narrow_and_provider_has_no_forbidden_integrations():
    provider = Path("src/api/document_intelligence/providers/workflow_studio_provider.py").read_text(encoding="utf-8")
    studio = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/workflow_studio").glob("*.py"))
    assert "from src.workflow_studio import" in provider
    for forbidden in ("workflow_runtime", "export_runtime", "erp", "ocr", "llm", "competitor", "dashboard", "filesystem", "requests"):
        assert forbidden not in provider.lower()
    assert "src.api" not in studio and "document_intelligence" not in studio
