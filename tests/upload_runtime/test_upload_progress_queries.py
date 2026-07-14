from src.upload_runtime import (
    UploadProcessingTimeline,
    UploadProgressQueryService,
    UploadProgressRecord,
    project_progress_summary,
)


def _record(tenant, upload, document, timestamp):
    summary = project_progress_summary(
        upload_id=upload, document_id=document, status="received", started_at=timestamp,
    )
    return UploadProgressRecord(tenant, summary, UploadProcessingTimeline(upload, ()))


def test_queries_are_tenant_scoped_and_cross_tenant_is_concealed():
    service = UploadProgressQueryService((
        _record("tenant-a", "upload-a", "document-a", "2026-07-14T10:00:00Z"),
        _record("tenant-b", "upload-b", "document-b", "2026-07-14T11:00:00Z"),
    ))
    assert service.get_upload_progress("upload-a", tenant_id="tenant-a").document_id == "document-a"
    assert service.get_upload_progress("upload-a", tenant_id="tenant-b") is None
    assert service.get_document_status("document-a", tenant_id="tenant-b") is None


def test_recent_query_has_stable_order_and_bounded_pagination():
    service = UploadProgressQueryService((
        _record("tenant-a", "upload-a", "document-a", "2026-07-14T10:00:00Z"),
        _record("tenant-a", "upload-b", "document-b", "2026-07-14T11:00:00Z"),
    ))
    page = service.list_recent(tenant_id="tenant-a", limit=1, offset=0)
    assert [item.upload_id for item in page.items] == ["upload-b"]
    assert page.total == 2


def test_timeline_lookup_returns_only_owned_upload():
    service = UploadProgressQueryService((_record("tenant-a", "upload-a", "document-a", "2026-07-14T10:00:00Z"),))
    assert service.get_timeline("upload-a", tenant_id="tenant-a").upload_id == "upload-a"
    assert service.get_timeline("upload-a", tenant_id="tenant-b") is None

