import json

from src.ui.streamlit.data_providers import LocalOperatorConsoleProvider


def test_provider_data_is_deterministic_and_ordered():
    provider = LocalOperatorConsoleProvider()
    assert provider.documents() == provider.documents()
    assert [row["document_id"] for row in provider.documents()] == sorted(
        row["document_id"] for row in provider.documents()
    )
    assert [row["review_case_id"] for row in provider.review_cases()] == sorted(
        row["review_case_id"] for row in provider.review_cases()
    )


def test_provider_returns_defensive_copies_without_mutation_leaks():
    provider = LocalOperatorConsoleProvider()
    documents = provider.documents()
    documents[0]["status"] = "changed"
    documents.append({"document_id": "private"})
    assert provider.documents()[0]["status"] == "export_ready"
    assert len(provider.documents()) == 7


def test_summary_metrics_are_correct_and_do_not_mutate_input():
    provider = LocalOperatorConsoleProvider()
    documents = provider.documents()
    original = [dict(row) for row in documents]
    assert provider.summary_metrics(documents=documents) == {
        "documents_received": 7,
        "processed": 5,
        "review_required": 1,
        "failed": 1,
        "export_ready": 1,
    }
    assert documents == original


def test_document_status_and_type_filters_work():
    provider = LocalOperatorConsoleProvider()
    assert [row["document_id"] for row in provider.documents(status="failed")] == ["DOC-1045"]
    assert [row["document_id"] for row in provider.documents(document_type="Invoice")] == [
        "DOC-1042", "DOC-1046", "DOC-1048"
    ]


def test_review_status_filter_works():
    rows = LocalOperatorConsoleProvider().review_cases(status="review_required")
    assert [row["review_case_id"] for row in rows] == ["REV-2202"]


def test_all_provider_outputs_are_json_friendly():
    provider = LocalOperatorConsoleProvider()
    payload = {
        "documents": provider.documents(),
        "processing": provider.processing_statuses(),
        "validation": provider.validation_issues(),
        "matching": provider.matching_results(),
        "reviews": provider.review_cases(),
        "runs": provider.workflow_runs(),
        "audit": provider.audit_events(),
        "metrics": provider.summary_metrics(),
    }
    json.dumps(payload)

