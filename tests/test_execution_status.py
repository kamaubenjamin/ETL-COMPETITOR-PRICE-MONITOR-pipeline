from src.core.execution.status import ExecutionStatus, normalize_status
from src.contracts.api import WorkflowRunRequest


def test_execution_status_normalizes_legacy_partial():
    assert normalize_status("partial") == ExecutionStatus.PARTIAL_SUCCESS.value


def test_workflow_run_request_supports_execution_safety_fields():
    request = WorkflowRunRequest.from_dict(
        {
            "workflow_id": "daily_prices",
            "timeout_seconds": 120,
            "max_retries": 2,
            "prevent_overlap": True,
        }
    )

    assert request.timeout_seconds == 120
    assert request.max_retries == 2
    assert request.prevent_overlap is True
