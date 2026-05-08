import os
import tempfile
from datetime import datetime

from src.storage.workflow_history import WorkflowHistoryStore


def test_workflow_history_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        history_path = os.path.join(tmpdir, "workflow_history.json")
        store = WorkflowHistoryStore(filepath=history_path)

        entry = {
            "run_id": "test-run-001",
            "workflow_id": "electronics_monitoring",
            "workflow_name": "Electronics Price Monitoring",
            "status": "success",
            "error": None,
            "start_time": datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_duration": 1.23,
            "alerts_generated": 0,
            "report_paths": [],
            "steps": [],
        }

        saved = store.record_execution(entry)
        assert saved["run_id"] == "test-run-001"
        assert os.path.exists(history_path)

        history = store.get_history("electronics_monitoring")
        assert len(history) == 1
        assert history[0]["workflow_id"] == "electronics_monitoring"
        assert history[0]["status"] == "success"

        latest = store.get_latest_runs(limit=1)
        assert len(latest) == 1
        assert latest[0]["run_id"] == "test-run-001"


def test_workflow_history_filters_by_workflow_id():
    with tempfile.TemporaryDirectory() as tmpdir:
        history_path = os.path.join(tmpdir, "workflow_history.json")
        store = WorkflowHistoryStore(filepath=history_path)

        store.record_execution({
            "run_id": "run-1",
            "workflow_id": "electronics_monitoring",
            "workflow_name": "Electronics Price Monitoring",
            "status": "success",
            "error": None,
            "start_time": datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_duration": 2.0,
            "alerts_generated": 1,
            "report_paths": [],
            "steps": [],
        })
        store.record_execution({
            "run_id": "run-2",
            "workflow_id": "smartphones_monitoring",
            "workflow_name": "Smartphone Price Monitoring",
            "status": "failed",
            "error": "timeout",
            "start_time": datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_duration": 3.0,
            "alerts_generated": 0,
            "report_paths": [],
            "steps": [],
        })

        history = store.get_history("electronics_monitoring")
        assert len(history) == 1
        assert history[0]["workflow_id"] == "electronics_monitoring"

        all_history = store.get_history()
        assert len(all_history) == 2
