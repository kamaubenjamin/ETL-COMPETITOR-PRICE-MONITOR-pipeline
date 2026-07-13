from typing import Protocol

from src.document_state.writers.ports import (
    AuditDocumentStateWriterPort,
    DocumentStateWriterPort,
    IngestionDocumentStateWriterPort,
    ProcessingDocumentStateWriterPort,
    ReviewDocumentStateWriterPort,
    WorkflowDocumentStateWriterPort,
)


class CompleteWriter:
    def create_document(self, command): ...
    def append_lifecycle_event(self, command): ...
    def write_processing_snapshot(self, command): ...
    def write_validation_issues(self, command): ...
    def write_matching_summaries(self, command): ...
    def write_review_summary(self, command): ...
    def write_correction_summary(self, command): ...
    def write_reprocess_plan(self, command): ...
    def write_workflow_run(self, command): ...
    def write_audit_event(self, command): ...


def test_writer_ports_are_structural_protocols():
    writer = CompleteWriter()
    for port in (
        IngestionDocumentStateWriterPort,
        ProcessingDocumentStateWriterPort,
        ReviewDocumentStateWriterPort,
        WorkflowDocumentStateWriterPort,
        AuditDocumentStateWriterPort,
        DocumentStateWriterPort,
    ):
        assert issubclass(port, Protocol)
        assert isinstance(writer, port)


def test_ports_expose_intent_only_and_no_public_transport_methods():
    methods = {name for name in dir(DocumentStateWriterPort) if not name.startswith("_")}
    assert {"post", "put", "patch", "delete", "execute", "commit"}.isdisjoint(methods)
