import importlib
import json

import pandas as pd

from src.ui.streamlit.data_providers import LocalOperatorConsoleProvider
from src.ui.streamlit.view_models import (
    audit_log_rows,
    inbox_rows,
    matching_rows,
    review_queue_rows,
    summary_metrics,
    validation_rows,
    workflow_run_rows,
)


def test_summary_metric_view_model_has_stable_order():
    metrics = summary_metrics(LocalOperatorConsoleProvider().summary_metrics())
    assert [item["label"] for item in metrics] == [
        "Documents received", "Processed", "Review required", "Failed", "Export ready"
    ]
    assert [item["value"] for item in metrics] == [7, 5, 1, 1, 1]


def test_tabular_view_models_are_json_and_dataframe_friendly():
    provider = LocalOperatorConsoleProvider()
    shaped = [
        inbox_rows(provider.documents()),
        validation_rows(provider.validation_issues()),
        matching_rows(provider.matching_results()),
        review_queue_rows(provider.review_cases()),
        workflow_run_rows(provider.workflow_runs()),
        audit_log_rows(provider.audit_events()),
    ]
    for rows in shaped:
        json.dumps(rows)
        assert not pd.DataFrame(rows).empty


def test_view_models_do_not_mutate_provider_rows():
    provider = LocalOperatorConsoleProvider()
    records = provider.documents()
    original = [dict(row) for row in records]
    result = inbox_rows(records)
    result[0]["status"] = "display-only-change"
    assert records == original


def test_components_import_has_no_streamlit_render_side_effects():
    components = importlib.import_module("src.ui.streamlit.components")
    assert components.format_status("review_required") == "Review Required"

