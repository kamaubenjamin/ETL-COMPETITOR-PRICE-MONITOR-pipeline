"""
Centralized structured logging for execution and connector scopes.

The logger emits JSON to stdout by default so FlowSync workers, local dev, and
future log shippers can parse the same events. Kafka streaming, websocket
telemetry, Supabase realtime fanout, and Celery task logs can reuse the same
payload shape without exposing pipeline internals.
"""

from __future__ import annotations

import json
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class StructuredLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload.update(context)
        if record.exc_info:
            payload["trace"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_execution_logger(name: str = "etl.execution") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredLogFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


@dataclass(slots=True)
class ExecutionLogger:
    run_id: Optional[str] = None
    workflow_id: Optional[str] = None
    connector_type: Optional[str] = None
    logger: logging.Logger = field(default_factory=get_execution_logger)

    def bind(self, **context: Any) -> "ExecutionLogger":
        return ExecutionLogger(
            run_id=context.get("run_id", self.run_id),
            workflow_id=context.get("workflow_id", self.workflow_id),
            connector_type=context.get("connector_type", self.connector_type),
            logger=self.logger,
        )

    def info(self, message: str, **context: Any) -> None:
        self._log(logging.INFO, message, **context)

    def warning(self, message: str, **context: Any) -> None:
        self._log(logging.WARNING, message, **context)

    def retry(self, message: str, attempt: int, max_retries: int, **context: Any) -> None:
        self.warning(message, attempt=attempt, max_retries=max_retries, event="retry", **context)

    def error(self, message: str, error: BaseException | str | None = None, **context: Any) -> None:
        if error is not None:
            context["error"] = str(error)
            if isinstance(error, BaseException):
                context["trace"] = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        self._log(logging.ERROR, message, **context)

    def _log(self, level: int, message: str, **context: Any) -> None:
        payload: Dict[str, Any] = {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "connector_type": self.connector_type,
            **context,
        }
        self.logger.log(level, message, extra={"context": {k: v for k, v in payload.items() if v is not None}})
