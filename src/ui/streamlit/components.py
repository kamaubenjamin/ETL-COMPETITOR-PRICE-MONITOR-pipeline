"""Reusable Streamlit display components with no import-time rendering."""

from __future__ import annotations

from typing import Any, Iterable

import pandas as pd
import streamlit as st


def format_status(status: str) -> str:
    return status.replace("_", " ").title()


def section_header(title: str, caption: str | None = None) -> None:
    st.subheader(title)
    if caption:
        st.caption(caption)


def metric_cards(metrics: Iterable[dict[str, Any]]) -> None:
    values = list(metrics)
    columns = st.columns(len(values))
    for column, metric in zip(columns, values):
        column.metric(metric["label"], metric["value"])


def data_table(rows: Iterable[dict[str, Any]], *, height: int = 360) -> None:
    st.dataframe(pd.DataFrame(list(rows)), width="stretch", hide_index=True, height=height)

