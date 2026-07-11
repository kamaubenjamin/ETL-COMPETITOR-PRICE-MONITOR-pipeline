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

from src.ui.streamlit.components import data_table, metric_cards, section_header
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
        workspace = st.selectbox("Workspace", ["Operations", "Finance", "Procurement"])
        document_type = st.selectbox("Document Type", ["All", "Invoice", "Purchase Order", "Bank Statement", "Receipt"])
        workflow = st.selectbox("Workflow", ["All", "Invoice Standard", "Purchase Order Standard", "Statement Reconciliation", "Receipt Standard"])
        runtime_status = st.selectbox("Runtime Filter", ["All", *DOCUMENT_STATUSES])
        review_status = st.selectbox("Review Filter", ["All", *REVIEW_STATUSES])
        st.divider()
        st.caption("Local demonstration data | Read only")
    return {
        "workspace": workspace,
        "document_type": None if document_type == "All" else document_type,
        "workflow": None if workflow == "All" else workflow,
        "runtime_status": None if runtime_status == "All" else runtime_status,
        "review_status": None if review_status == "All" else review_status,
    }


def _render_overview(provider: LocalOperatorConsoleProvider, filters: dict[str, str | None]) -> None:
    documents = provider.documents(document_type=filters["document_type"], status=filters["runtime_status"])
    metric_cards(summary_metrics(provider.summary_metrics(documents=documents)))
    section_header("Current workload")
    status_counts = (
        pd.DataFrame(documents).groupby("status", as_index=False).size().rename(columns={"size": "documents"})
        if documents
        else pd.DataFrame({"status": [], "documents": []})
    )
    left, right = st.columns([3, 2])
    with left:
        data_table(inbox_rows(documents), height=300)
    with right:
        st.bar_chart(status_counts.set_index("status"), horizontal=True, height=300)
    st.caption(f"Workspace: {filters['workspace']} | Snapshot: {SNAPSHOT.strftime('%Y-%m-%d %H:%M UTC')}")


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
    provider = LocalOperatorConsoleProvider()
    filters = _sidebar_filters()
    documents = provider.documents(document_type=filters["document_type"], status=filters["runtime_status"])

    st.title(PAGE_TITLE)
    st.caption("Document operations, exceptions, and runtime activity")
    tabs = st.tabs(["Overview", "Inbox", "Upload", "Processing", "Validation", "Matching", "Review Queue", "Workflow Runs", "Audit Logs"])

    with tabs[0]:
        _render_overview(provider, filters)
    with tabs[1]:
        section_header("Document inbox")
        data_table(inbox_rows(documents))
    with tabs[2]:
        section_header("Upload documents")
        st.file_uploader("Choose local documents", type=["pdf", "png", "jpg", "jpeg", "csv", "xlsx"], accept_multiple_files=True, disabled=True)
        st.info("Upload is a placeholder in v1. Files are not read, stored, or sent to a backend.")
    with tabs[3]:
        section_header("Active processing")
        data_table(provider.processing_statuses(status=filters["runtime_status"]))
    with tabs[4]:
        section_header("Validation issues")
        data_table(validation_rows(provider.validation_issues()))
    with tabs[5]:
        section_header("Candidate matching")
        data_table(matching_rows(provider.matching_results()))
    with tabs[6]:
        section_header("Review queue")
        data_table(review_queue_rows(provider.review_cases(status=filters["review_status"])))
    with tabs[7]:
        section_header("Workflow runs")
        data_table(workflow_run_rows(provider.workflow_runs(workflow_name=filters["workflow"])))
    with tabs[8]:
        section_header("Audit logs")
        data_table(audit_log_rows(provider.audit_events()))


if __name__ == "__main__":
    main()
