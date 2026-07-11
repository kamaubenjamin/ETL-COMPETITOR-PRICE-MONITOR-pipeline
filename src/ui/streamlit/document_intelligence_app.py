"""Display-only Streamlit operator console backed by deterministic mock data."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st


PAGE_TITLE = "Intelligent Document Processing Platform"

DOCUMENT_STATUSES = (
    "received",
    "ingested",
    "classified",
    "parsed",
    "extracted",
    "transformed",
    "validated",
    "matched",
    "review_required",
    "approved",
    "export_ready",
    "exported",
    "failed",
)

REVIEW_STATUSES = (
    "review_required",
    "in_review",
    "corrected",
    "approved",
    "rejected",
    "skipped",
    "reprocess_requested",
    "resolved",
)


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _mock_data() -> dict[str, pd.DataFrame]:
    documents = _frame(
        [
            {"document_id": "DOC-1042", "filename": "acme_invoice_1042.pdf", "document_type": "Invoice", "status": "export_ready", "confidence": 0.98, "current_stage": "export"},
            {"document_id": "DOC-1043", "filename": "northwind_po_771.pdf", "document_type": "Purchase Order", "status": "review_required", "confidence": 0.71, "current_stage": "matching"},
            {"document_id": "DOC-1044", "filename": "contoso_statement_jun.pdf", "document_type": "Bank Statement", "status": "validated", "confidence": 0.94, "current_stage": "validation"},
            {"document_id": "DOC-1045", "filename": "fabrikam_receipt_88.png", "document_type": "Receipt", "status": "failed", "confidence": 0.42, "current_stage": "parsing"},
            {"document_id": "DOC-1046", "filename": "tailspin_invoice_309.pdf", "document_type": "Invoice", "status": "matched", "confidence": 0.91, "current_stage": "matching"},
            {"document_id": "DOC-1047", "filename": "wideworld_po_551.pdf", "document_type": "Purchase Order", "status": "received", "confidence": 0.00, "current_stage": "intake"},
            {"document_id": "DOC-1048", "filename": "adatum_invoice_204.pdf", "document_type": "Invoice", "status": "exported", "confidence": 0.97, "current_stage": "complete"},
        ]
    )
    processing = _frame(
        [
            {"document_id": "DOC-1043", "stage": "matching", "status": "review_required", "started_at": "2026-07-11 09:18 UTC", "elapsed": "00:01:42"},
            {"document_id": "DOC-1044", "stage": "validation", "status": "validated", "started_at": "2026-07-11 09:21 UTC", "elapsed": "00:00:36"},
            {"document_id": "DOC-1045", "stage": "parsing", "status": "failed", "started_at": "2026-07-11 09:24 UTC", "elapsed": "00:00:08"},
            {"document_id": "DOC-1046", "stage": "matching", "status": "matched", "started_at": "2026-07-11 09:26 UTC", "elapsed": "00:00:51"},
            {"document_id": "DOC-1047", "stage": "intake", "status": "received", "started_at": "2026-07-11 09:30 UTC", "elapsed": "00:00:02"},
        ]
    )
    validation = _frame(
        [
            {"document_id": "DOC-1043", "severity": "error", "field": "supplier.tax_id", "rule": "required", "message": "Required field is missing."},
            {"document_id": "DOC-1043", "severity": "warning", "field": "invoice.total", "rule": "max", "message": "Value exceeds the configured review threshold."},
            {"document_id": "DOC-1044", "severity": "warning", "field": "account.currency", "rule": "allowed_values", "message": "Currency requires operator confirmation."},
            {"document_id": "DOC-1045", "severity": "error", "field": "document.structure", "rule": "required", "message": "Expected tabular structure was not found."},
        ]
    )
    matching = _frame(
        [
            {"document_id": "DOC-1043", "entity": "Northwind Traders", "candidate_match": "Northwind Trading Ltd", "confidence": 0.74, "match_status": "ambiguous"},
            {"document_id": "DOC-1043", "entity": "Northwind Traders", "candidate_match": "Northwind Wholesale", "confidence": 0.68, "match_status": "candidate"},
            {"document_id": "DOC-1046", "entity": "Tailspin Toys", "candidate_match": "Tailspin Toys Ltd", "confidence": 0.96, "match_status": "matched"},
            {"document_id": "DOC-1044", "entity": "Contoso Bank", "candidate_match": "Contoso Bank PLC", "confidence": 0.93, "match_status": "matched"},
        ]
    )
    reviews = _frame(
        [
            {"review_case_id": "REV-2201", "document_id": "DOC-1043", "reason": "matching_ambiguity", "priority": "high", "status": "in_review", "assigned_reviewer": "M. Otieno"},
            {"review_case_id": "REV-2202", "document_id": "DOC-1045", "reason": "invalid_data", "priority": "urgent", "status": "review_required", "assigned_reviewer": "Unassigned"},
            {"review_case_id": "REV-2198", "document_id": "DOC-1042", "reason": "validation_failure", "priority": "normal", "status": "resolved", "assigned_reviewer": "A. Kamau"},
            {"review_case_id": "REV-2199", "document_id": "DOC-1046", "reason": "duplicate_detection", "priority": "normal", "status": "corrected", "assigned_reviewer": "J. Njeri"},
        ]
    )
    runs = _frame(
        [
            {"run_id": "RUN-8807", "workflow_name": "Invoice Standard", "status": "completed", "started_at": "2026-07-11 09:15 UTC", "duration": "00:02:14"},
            {"run_id": "RUN-8808", "workflow_name": "Purchase Order Standard", "status": "review_required", "started_at": "2026-07-11 09:18 UTC", "duration": "00:01:42"},
            {"run_id": "RUN-8809", "workflow_name": "Statement Reconciliation", "status": "completed", "started_at": "2026-07-11 09:21 UTC", "duration": "00:00:36"},
            {"run_id": "RUN-8810", "workflow_name": "Receipt Standard", "status": "failed", "started_at": "2026-07-11 09:24 UTC", "duration": "00:00:08"},
        ]
    )
    audit = _frame(
        [
            {"timestamp": "2026-07-11 09:31:12 UTC", "event_type": "review_assigned", "actor": "M. Otieno", "safe_metadata": "case=REV-2201; priority=high"},
            {"timestamp": "2026-07-11 09:29:48 UTC", "event_type": "validation_completed", "actor": "transform_runtime", "safe_metadata": "document=DOC-1044; issues=1"},
            {"timestamp": "2026-07-11 09:27:03 UTC", "event_type": "matching_completed", "actor": "matching_runtime", "safe_metadata": "document=DOC-1046; candidates=1"},
            {"timestamp": "2026-07-11 09:24:19 UTC", "event_type": "stage_failed", "actor": "workflow_runtime", "safe_metadata": "document=DOC-1045; stage=parsing"},
            {"timestamp": "2026-07-11 09:20:06 UTC", "event_type": "review_created", "actor": "workflow_runtime", "safe_metadata": "case=REV-2201; reason=matching_ambiguity"},
        ]
    )
    return {"documents": documents, "processing": processing, "validation": validation, "matching": matching, "reviews": reviews, "runs": runs, "audit": audit}


def _table(frame: pd.DataFrame, *, height: int = 360) -> None:
    st.dataframe(frame, width="stretch", hide_index=True, height=height)


def _apply_filters(data: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    with st.sidebar:
        st.header("Operator Console")
        workspace = st.selectbox("Workspace", ["Operations", "Finance", "Procurement"])
        document_type = st.selectbox("Document Type", ["All", "Invoice", "Purchase Order", "Bank Statement", "Receipt"])
        workflow = st.selectbox("Workflow", ["All", "Invoice Standard", "Purchase Order Standard", "Statement Reconciliation", "Receipt Standard"])
        runtime_filter = st.selectbox("Runtime Filter", ["All", *DOCUMENT_STATUSES])
        review_filter = st.selectbox("Review Filter", ["All", *REVIEW_STATUSES])
        st.divider()
        st.caption("Local demonstration data | Read only")

    filtered = {name: frame.copy() for name, frame in data.items()}
    if document_type != "All":
        filtered["documents"] = filtered["documents"].loc[filtered["documents"]["document_type"] == document_type]
    if runtime_filter != "All":
        filtered["documents"] = filtered["documents"].loc[filtered["documents"]["status"] == runtime_filter]
        if runtime_filter in set(filtered["processing"]["status"]):
            filtered["processing"] = filtered["processing"].loc[filtered["processing"]["status"] == runtime_filter]
    if workflow != "All":
        filtered["runs"] = filtered["runs"].loc[filtered["runs"]["workflow_name"] == workflow]
    if review_filter != "All":
        filtered["reviews"] = filtered["reviews"].loc[filtered["reviews"]["status"] == review_filter]
    return filtered, {"workspace": workspace, "document_type": document_type, "workflow": workflow}


def _render_overview(data: dict[str, pd.DataFrame], context: dict[str, str]) -> None:
    documents = data["documents"]
    processed_statuses = {"validated", "matched", "review_required", "approved", "export_ready", "exported"}
    counts = {
        "Documents received": len(documents),
        "Processed": int(documents["status"].isin(processed_statuses).sum()),
        "Review required": int((documents["status"] == "review_required").sum()),
        "Failed": int((documents["status"] == "failed").sum()),
        "Export ready": int((documents["status"] == "export_ready").sum()),
    }
    columns = st.columns(5)
    for column, (label, value) in zip(columns, counts.items()):
        column.metric(label, value)
    st.subheader("Current workload")
    status_counts = documents.groupby("status", as_index=False).size().rename(columns={"size": "documents"})
    left, right = st.columns([3, 2])
    with left:
        _table(documents[["document_id", "filename", "document_type", "status", "current_stage"]], height=300)
    with right:
        st.bar_chart(status_counts.set_index("status"), horizontal=True, height=300)
    st.caption(f"Workspace: {context['workspace']} | Snapshot: {datetime(2026, 7, 11, 9, 35, tzinfo=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, page_icon=":material/description:", layout="wide")
    st.markdown(
        """
        <style>
        :root { --ops-ink: #17202a; --ops-teal: #157a6e; --ops-red: #b42318; }
        .stApp { background: #f7f9fa; color: var(--ops-ink); }
        [data-testid="stMetric"] { background: #ffffff; border: 1px solid #d8dee4; border-radius: 6px; padding: 14px; }
        [data-testid="stSidebar"] { border-right: 1px solid #d8dee4; }
        h1, h2, h3 { letter-spacing: 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    data, context = _apply_filters(_mock_data())

    st.title(PAGE_TITLE)
    st.caption("Document operations, exceptions, and runtime activity")
    tabs = st.tabs(["Overview", "Inbox", "Upload", "Processing", "Validation", "Matching", "Review Queue", "Workflow Runs", "Audit Logs"])

    with tabs[0]:
        _render_overview(data, context)
    with tabs[1]:
        st.subheader("Document inbox")
        _table(data["documents"][["document_id", "filename", "document_type", "status", "confidence", "current_stage"]])
    with tabs[2]:
        st.subheader("Upload documents")
        st.file_uploader("Choose local documents", type=["pdf", "png", "jpg", "jpeg", "csv", "xlsx"], accept_multiple_files=True, disabled=True)
        st.info("Upload is a placeholder in v1. Files are not read, stored, or sent to a backend.")
    with tabs[3]:
        st.subheader("Active processing")
        _table(data["processing"])
    with tabs[4]:
        st.subheader("Validation issues")
        _table(data["validation"][["document_id", "severity", "field", "rule", "message"]])
    with tabs[5]:
        st.subheader("Candidate matching")
        _table(data["matching"][["document_id", "entity", "candidate_match", "confidence", "match_status"]])
    with tabs[6]:
        st.subheader("Review queue")
        _table(data["reviews"][["review_case_id", "reason", "priority", "status", "assigned_reviewer"]])
    with tabs[7]:
        st.subheader("Workflow runs")
        _table(data["runs"][["run_id", "workflow_name", "status", "started_at", "duration"]])
    with tabs[8]:
        st.subheader("Audit logs")
        _table(data["audit"][["timestamp", "event_type", "actor", "safe_metadata"]])


if __name__ == "__main__":
    main()
