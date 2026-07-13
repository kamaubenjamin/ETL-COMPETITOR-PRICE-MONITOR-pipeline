from src.api.document_intelligence.providers.local_provider import LocalDocumentIntelligenceProvider


def test_provider_results_are_deterministic_and_filtered():
    provider = LocalDocumentIntelligenceProvider()
    assert provider.list_documents() == provider.list_documents()
    assert [row["document_id"] for row in provider.list_documents(status="review_required")] == ["doc-002"]
    assert [row["review_case_id"] for row in provider.list_review_cases(priority="high")] == ["review-001"]
    assert [row["run_id"] for row in provider.list_workflow_runs(status="failed")] == ["run-003"]
    assert [row["event_id"] for row in provider.list_audit_events(event_type="review_case_created")] == ["audit-002"]


def test_provider_returns_defensive_deep_copies():
    provider = LocalDocumentIntelligenceProvider()
    documents = provider.list_documents()
    documents[0]["status"] = "failed"
    events = provider.list_audit_events()
    events[0]["metadata"]["document_type"] = "changed"
    assert provider.list_documents()[0]["status"] == "validated"
    assert provider.list_audit_events()[0]["metadata"]["document_type"] == "invoice"


def test_correction_and_reprocess_projections_exclude_controlled_values():
    provider = LocalDocumentIntelligenceProvider()
    text = str(provider.list_corrections("review-001") + provider.list_reprocess_plans()).lower()
    assert "new_value" not in text
    assert "old_value" not in text
    assert "raw" not in text
    assert "payload" not in text
