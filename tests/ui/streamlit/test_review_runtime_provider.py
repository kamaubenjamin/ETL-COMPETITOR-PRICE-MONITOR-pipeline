import inspect
import json

import pandas as pd

from src.review_runtime.contracts import ReviewStatus
from src.ui.streamlit.data_providers import LocalOperatorConsoleProvider
from src.ui.streamlit.view_models import audit_log_rows, review_queue_rows


def test_review_preview_is_deterministic_and_contract_compatible():
    provider = LocalOperatorConsoleProvider()
    first = provider.review_cases()
    second = provider.review_cases()
    assert first == second
    assert [row["review_case_id"] for row in first] == sorted(row["review_case_id"] for row in first)
    assert {row["status"] for row in first} <= {status.value for status in ReviewStatus}


def test_review_preview_exposes_safe_operational_fields():
    rows = LocalOperatorConsoleProvider().review_cases()
    reprocess = next(row for row in rows if row["review_case_id"] == "REV-2204")
    corrected = next(row for row in rows if row["review_case_id"] == "REV-2199")
    assert reprocess["decision"] == "request_reprocess"
    assert reprocess["reprocess_state"] == "planned"
    assert corrected["correction_count"] == 1
    assert "new_value" not in json.dumps(rows)
    assert "corrected-reference" not in json.dumps(rows)


def test_review_audit_rows_include_review_runtime_events():
    rows = LocalOperatorConsoleProvider().audit_events()
    review_rows = [row for row in rows if row.get("source_runtime") == "review"]
    assert {row["event_type"] for row in review_rows} == {
        "review_assigned", "correction_recorded", "reprocess_plan_created"
    }
    assert all("case=" in row["safe_metadata"] for row in review_rows)


def test_review_provider_outputs_are_defensive_copies():
    provider = LocalOperatorConsoleProvider()
    cases = provider.review_cases()
    events = provider.audit_events()
    cases[0]["status"] = "changed"
    events[0]["safe_metadata"] = "changed"
    assert provider.review_cases()[0]["status"] == "resolved"
    assert provider.audit_events()[0]["safe_metadata"] != "changed"


def test_review_view_models_are_json_and_dataframe_friendly():
    provider = LocalOperatorConsoleProvider()
    queue = review_queue_rows(provider.review_cases())
    audit = audit_log_rows(provider.audit_events())
    json.dumps({"queue": queue, "audit": audit})
    assert not pd.DataFrame(queue).empty
    assert not pd.DataFrame(audit).empty


def test_operator_console_provider_has_no_competitor_price_imports():
    source = inspect.getsource(__import__("src.ui.streamlit.data_providers", fromlist=["*"]))
    assert "competitor" not in source.lower()
    assert "connectors" not in source.lower()
