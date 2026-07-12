"""Reusable Streamlit display components with no import-time rendering."""

from __future__ import annotations

from typing import Any, Iterable

import pandas as pd
import streamlit as st


_ATTENTION_STATUSES = {"failed", "rejected", "error"}
_REVIEW_STATUSES = {"review_required", "in_review", "reprocess_requested", "warning", "ambiguous"}
_READY_STATUSES = {
    "approved", "completed", "corrected", "export_ready", "exported", "matched",
    "resolved", "validated",
}
_PRIORITY_CODES = {"critical": "P1", "high": "P2", "normal": "P3", "low": "P4"}


def format_status(status: str) -> str:
    label = status.replace("_", " ").title()
    if status in _ATTENTION_STATUSES:
        return f"Issue - {label}"
    if status in _REVIEW_STATUSES:
        return f"Review - {label}"
    if status in _READY_STATUSES:
        return f"Ready - {label}"
    return f"Active - {label}"


def format_priority(priority: str) -> str:
    return f"{_PRIORITY_CODES.get(priority, 'P-')} - {priority.title()}"


def page_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.markdown(f"<p class='ops-subtitle'>{subtitle}</p>", unsafe_allow_html=True)


def run_mode_banner() -> None:
    st.info(
        "Run mode: Local deterministic preview | No API | No database | No mutation",
        icon=":material/lock:",
    )


def section_header(title: str, caption: str | None = None) -> None:
    st.subheader(title)
    if caption:
        st.caption(caption)


def metric_cards(metrics: Iterable[dict[str, Any]]) -> None:
    values = list(metrics)
    columns = st.columns(len(values))
    for column, metric in zip(columns, values):
        column.metric(metric["label"], metric["value"])


def _display_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    display_rows = [dict(row) for row in rows]
    for row in display_rows:
        for key in ("status", "match_status", "severity", "reprocess_state", "decision"):
            value = row.get(key)
            if isinstance(value, str):
                row[key] = format_status(value)
        priority = row.get("priority")
        if isinstance(priority, str):
            row["priority"] = format_priority(priority)
    return display_rows


def data_table(
    rows: Iterable[dict[str, Any]],
    *,
    height: int = 360,
    empty_message: str = "No records match the selected filters.",
) -> None:
    display_rows = _display_rows(rows)
    if not display_rows:
        st.info(empty_message, icon=":material/filter_alt_off:")
        return
    st.dataframe(pd.DataFrame(display_rows), width="stretch", hide_index=True, height=height)
