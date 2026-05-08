import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


class WorkflowHistoryStore:
    """Persistent store for workflow execution metadata."""

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or os.path.join(os.path.dirname(__file__), "workflow_history.json")
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

    def _load_history(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.filepath):
            return []

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def _save_history(self, history: List[Dict[str, Any]]) -> None:
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, default=str)

    def record_execution(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        history = self._load_history()
        history.append(entry)
        self._save_history(history)
        return entry

    def get_history(self, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        history = self._load_history()
        if workflow_id:
            return [entry for entry in history if entry.get("workflow_id") == workflow_id]
        return history

    def get_latest_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        history = self._load_history()
        return history[-limit:][::-1]

    def clear_history(self) -> None:
        self._save_history([])


workflow_history_store = WorkflowHistoryStore()
