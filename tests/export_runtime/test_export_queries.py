import pytest

from src.export_runtime import (
    MAX_EXPORT_QUERY_LIMIT,
    MAX_EXPORT_QUERY_OFFSET,
    ExportAttempt,
    ExportAttemptQuery,
    ExportPageRequest,
    ExportRepositoryError,
    ExportTarget,
    InMemoryExportStore,
    generate_export_idempotency_key,
)


def attempt(attempt_id, tenant_id, document_id, target_id, created_at, fingerprint):
    target = ExportTarget(target_id, "erp", target_id)
    key = generate_export_idempotency_key(
        tenant_id=tenant_id, document_id=document_id, export_target=target, payload_fingerprint=fingerprint
    )
    return ExportAttempt(
        attempt_id, tenant_id, document_id, target, key, fingerprint, "preparing", "export", "actor-001", created_at, created_at
    )


def populated_store():
    store = InMemoryExportStore()
    records = (
        attempt("attempt-003", "tenant-002", "doc-002", "erp-secondary", "2026-07-14T10:02:00Z", "c" * 64),
        attempt("attempt-001", "tenant-001", "doc-001", "erp-main", "2026-07-14T10:00:00Z", "a" * 64),
        attempt("attempt-002", "tenant-001", "doc-001", "erp-main", "2026-07-14T10:01:00Z", "b" * 64),
    )
    for record in records:
        store.writer.save_attempt(record)
    return store


def test_document_tenant_and_target_queries_are_deterministically_ordered():
    store = populated_store()

    assert [item.attempt_id for item in store.reader.list_attempts_by_document("doc-001").items] == ["attempt-001", "attempt-002"]
    assert [item.attempt_id for item in store.reader.list_attempts_by_tenant("tenant-001").items] == ["attempt-001", "attempt-002"]
    assert [item.attempt_id for item in store.reader.list_attempts_by_target("erp-main").items] == ["attempt-001", "attempt-002"]


def test_combined_query_and_pagination_are_stable():
    store = populated_store()
    query = ExportAttemptQuery(tenant_id="tenant-001", target_id="erp-main", status="preparing")

    first = store.reader.list_attempts(query, ExportPageRequest(limit=1, offset=0))
    second = store.reader.list_attempts(query, ExportPageRequest(limit=1, offset=1))

    assert first.total == second.total == 2
    assert first.items[0].attempt_id == "attempt-001"
    assert second.items[0].attempt_id == "attempt-002"
    assert first.to_dict()["items"][0]["payload_fingerprint"] == "a" * 64


@pytest.mark.parametrize(
    "values",
    [
        {"limit": 0, "offset": 0},
        {"limit": MAX_EXPORT_QUERY_LIMIT + 1, "offset": 0},
        {"limit": 1, "offset": -1},
        {"limit": 1, "offset": MAX_EXPORT_QUERY_OFFSET + 1},
    ],
)
def test_page_bounds_are_enforced(values):
    with pytest.raises(ValueError):
        ExportPageRequest(**values)


def test_invalid_query_objects_are_rejected_with_repository_safe_error():
    with pytest.raises(ExportRepositoryError) as captured:
        populated_store().reader.list_attempts(query={"raw": "query"})
    assert captured.value.code == "invalid_query"

