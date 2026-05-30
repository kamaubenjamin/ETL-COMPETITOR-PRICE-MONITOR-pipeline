"""Orchestration helpers for Entity Runtime v1."""

from __future__ import annotations

from typing import Any


class EntityRuntimeOrchestrator:
    """Orchestrates Entity Runtime execution with a pluggable extraction engine."""

    def __init__(self, extraction_engine: Any):
        self.extraction_engine = extraction_engine

    def run(self, pipeline_result: Any) -> Any:
        return self.extraction_engine.extract(pipeline_result)
