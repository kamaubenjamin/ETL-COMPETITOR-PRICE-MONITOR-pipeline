"""Read-only Streamlit operator console backed by a local provider boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ui.streamlit.components import (
    data_table,
    metric_cards,
    page_header,
    run_mode_banner,
    section_header,
)
from src.ui.streamlit.data_providers import DOCUMENT_STATUSES, REVIEW_STATUSES, LocalOperatorConsoleProvider
from src.ui.streamlit.view_models import (
    audit_log_rows,
    inbox_rows,
    matching_rows,
    review_queue_rows,
    summary_metrics,
    validation_rows,
    workflow_run_rows,
)


PAGE_TITLE = "Intelligent Document Processing Platform"
SNAPSHOT = datetime(2026, 7, 11, 9, 35, tzinfo=timezone.utc)


def _sidebar_filters() -> dict[str, str | None]:
    with st.sidebar:
        st.header("Operator Console")
        st.caption("Document Intelligence workspace")
        st.subheader("Scope")
        workspace = st.selectbox("Workspace", ["Operations", "Finance", "Procurement"])
        document_type = st.selectbox("Document Type", ["All", "Invoice", "Purchase Order", "Bank Statement", "Receipt"])
        workflow = st.selectbox("Workflow", ["All", "Invoice Standard", "Purchase Order Standard", "Statement Reconciliation", "Receipt Standard"])
        st.subheader("Runtime filters")
        runtime_status = st.selectbox("Runtime Filter", ["All", *DOCUMENT_STATUSES])
        review_status = st.selectbox("Review Filter", ["All", *REVIEW_STATUSES])
        st.divider()
        st.markdown("**Run mode**")
        st.caption("Local deterministic preview")
        st.caption("No API | No database | No mutation")
    return {
        "workspace": workspace,
        "document_type": None if document_type == "All" else document_type,
        "workflow": None if workflow == "All" else workflow,
        "runtime_status": None if runtime_status == "All" else runtime_status,
        "review_status": None if review_status == "All" else review_status,
    }


def _render_overview(provider: LocalOperatorConsoleProvider, filters: dict[str, str | None]) -> None:
    documents = provider.documents(document_type=filters["document_type"], status=filters["runtime_status"])
    reviews = provider.review_cases(status=filters["review_status"])
    runs = provider.workflow_runs(workflow_name=filters["workflow"])
    section_header("Operational overview", "Current deterministic snapshot for the selected workspace and filters.")
    metric_cards(summary_metrics(provider.summary_metrics(documents=documents)))
    st.divider()
    status_counts = (
        pd.DataFrame(documents).groupby("status", as_index=False).size().rename(columns={"size": "documents"})
        if documents
        else pd.DataFrame({"status": [], "documents": []})
    )
    left, right = st.columns([3, 2], gap="large")
    with left:
        section_header("Document workload", "Documents currently visible in the operator scope.")
        data_table(inbox_rows(documents), height=300, empty_message="No documents match the selected scope.")
    with right:
        section_header("Lifecycle distribution", "Document count by current lifecycle status.")
        if documents:
            st.bar_chart(status_counts.set_index("status"), horizontal=True, height=300)
        else:
            st.info("No lifecycle data is available for this filter.", icon=":material/filter_alt_off:")
    st.divider()
    review_column, workflow_column = st.columns(2, gap="large")
    with review_column:
        section_header("Review workload", "Read-only cases requiring or recording operator attention.")
        data_table(review_queue_rows(reviews), height=250, empty_message="No review cases match the selected status.")
    with workflow_column:
        section_header("Workflow activity", "Recent deterministic runs in the selected workflow scope.")
        data_table(workflow_run_rows(runs), height=250, empty_message="No workflow runs match the selected workflow.")
    st.caption(f"Workspace: {filters['workspace']} | Snapshot: {SNAPSHOT.strftime('%Y-%m-%d %H:%M UTC')}")


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, page_icon=":material/description:", layout="wide")
    st.markdown(
        """
        <style>
        :root { --ops-ink: #17202a; --ops-teal: #157a6e; --ops-red: #b42318; }
        .stApp { background: #f7f9fa; color: var(--ops-ink); }
        .block-container { padding-top: 1.8rem; }
        .ops-subtitle { color: #52606d; font-size: 1rem; margin-top: -0.8rem; margin-bottom: 1.1rem; }
        [data-testid="stMetric"] { background: #ffffff; border: 1px solid #d8dee4; border-top: 3px solid #157a6e; border-radius: 6px; padding: 14px; min-height: 104px; }
        [data-testid="stSidebar"] { border-right: 1px solid #d8dee4; }
        [data-testid="stTabs"] button { padding-left: 0.75rem; padding-right: 0.75rem; }
        [data-testid="stTabs"] [aria-selected="true"] { border-bottom-color: #157a6e; }
        h1, h2, h3 { letter-spacing: 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    provider = LocalOperatorConsoleProvider()
    filters = _sidebar_filters()
    documents = provider.documents(document_type=filters["document_type"], status=filters["runtime_status"])

    page_header(PAGE_TITLE, "Document operations, exception review, workflow activity, and audit visibility")
    run_mode_banner()
    tabs = st.tabs(["01 Overview", "02 Inbox", "03 Upload", "04 Processing", "05 Validation", "06 Matching", "07 Reviews", "08 Workflows", "09 Audit"])

    with tabs[0]:
        _render_overview(provider, filters)
    with tabs[1]:
        section_header("Document inbox", "Scan document identity, confidence, lifecycle status, and current processing stage.")
        data_table(inbox_rows(documents), empty_message="No documents match the selected scope.")
    with tabs[2]:
        section_header("Upload documents", "Preview only. Ingestion is not connected in v0.8.")
        with st.container(border=True):
            st.file_uploader("Choose local documents", type=["pdf", "png", "jpg", "jpeg", "csv", "xlsx"], accept_multiple_files=True, disabled=True)
            st.warning("Upload is disabled. Files are not read, persisted, or sent to a backend.", icon=":material/block:")
    with tabs[3]:
        section_header("Active processing", "Current stage progress for deterministic preview documents.")
        data_table(provider.processing_statuses(status=filters["runtime_status"]), empty_message="No processing records match the runtime filter.")
    with tabs[4]:
        section_header("Validation issues", "Bounded rule findings without raw source values.")
        data_table(validation_rows(provider.validation_issues()))
    with tabs[5]:
        section_header("Candidate matching", "Candidate confidence and deterministic match outcomes.")
        data_table(matching_rows(provider.matching_results()))
    with tabs[6]:
        section_header("Review queue", "Read-only Review Runtime cases, decisions, corrections, and reprocess state.")
        data_table(review_queue_rows(provider.review_cases(status=filters["review_status"])), empty_message="No review cases match the selected status.")
    with tabs[7]:
        section_header("Workflow runs", "Recent workflow outcomes for the selected workflow scope.")
        data_table(workflow_run_rows(provider.workflow_runs(workflow_name=filters["workflow"])), empty_message="No workflow runs match the selected workflow.")
    with tabs[8]:
        section_header("Audit activity", "Safe, bounded operational and Review Runtime events.")
        data_table(audit_log_rows(provider.audit_events()))


if __name__ == "__main__":
    main()
