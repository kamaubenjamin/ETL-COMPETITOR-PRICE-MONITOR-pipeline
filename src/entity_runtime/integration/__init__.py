"""Entity Runtime integration package — hooks concurrency hardening into Workflow Runtime.

Provides the EntityWorkflowAdapter that wraps workflow stage functions with
concurrency guard protection for entity write operations.
"""

from src.entity_runtime.integration.workflow_adapter import EntityWorkflowAdapter

__all__ = ["EntityWorkflowAdapter"]