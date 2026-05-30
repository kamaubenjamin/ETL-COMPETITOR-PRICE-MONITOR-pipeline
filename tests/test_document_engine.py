import json
from pathlib import Path

from src.document_engine import DocumentIngestionEngine
from src.document_engine.loaders.base import get_loader_for_path
from src.document_engine.loaders.txt_loader import TxtDocumentLoader


class DummyTelemetry:
    def __init__(self):
        self.events = []

    def log_ingestion(self, event):
        self.events.append(event)
        return event


def test_txt_document_loader_reads_text(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("Hello world\nLine two\n", encoding="utf-8")

    loader = TxtDocumentLoader()
    document = loader.load(str(path))

    assert document.source.source_type == "text"
    assert "Hello world" in document.content
    assert document.metadata["line_count"] == 3


def test_csv_document_loader_reads_csv(tmp_path):
    path = tmp_path / "sample.csv"
    path.write_text("id,name\n1,Alpha\n2,Beta\n", encoding="utf-8")

    loader = get_loader_for_path(str(path))
    document = loader.load(str(path))

    assert document.source.source_type == "csv"
    assert "id,name" in document.content
    assert document.metadata["field_count"] == 2
    assert document.metadata["row_count"] == 3


def test_email_document_loader_parses_message(tmp_path):
    path = tmp_path / "sample.eml"
    path.write_text(
        "Subject: Greetings\nFrom: sender@example.com\nTo: recipient@example.com\n\nHello world from email.\n",
        encoding="utf-8",
    )

    loader = get_loader_for_path(str(path))
    document = loader.load(str(path))

    assert document.source.source_type == "email"
    assert "Greetings" in document.content
    assert document.metadata["subject"] == "Greetings"
    assert document.metadata["from"] == "sender@example.com"


def test_document_ingestion_engine_persists_debug_artifact(tmp_path):
    source_path = tmp_path / "sample.txt"
    source_path.write_text("Debug artifact text.\n", encoding="utf-8")
    debug_dir = tmp_path / "debug"
    telemetry = DummyTelemetry()
    engine = DocumentIngestionEngine(debug_path=str(debug_dir), telemetry=telemetry)

    result = engine.ingest(
        file_path=str(source_path),
        source_name="test_source",
        source_type="document",
        batch_id="batch-1",
        pipeline_run_id="run-1",
    )

    artifact_files = list(debug_dir.glob("document_ingestion_*.json"))
    assert len(artifact_files) == 1

    artifact = json.loads(artifact_files[0].read_text(encoding="utf-8"))
    assert artifact["classification"]["document_type"] == "text"
    assert telemetry.events


def test_get_loader_for_path_unsupported_raises():
    try:
        get_loader_for_path("sample.docx")
    except ValueError as exc:
        assert "Unsupported document extension" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported extension")
