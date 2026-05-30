from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List

from src.core.execution.status import ExecutionStatus
from src.entity_runtime.contracts.entity_set import EntitySet
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_result import StageResult
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY
from src.matching_runtime.contracts.match_request import MatchRequest
from src.matching_runtime.services.matching_service import MatchingService


class MatchingStage(BaseStage):
    """Matching stage — reconciles entities against master data sources."""

    def _flatten_entity_artifact(self, artifact: Dict[str, Any]) -> List[Dict[str, Any]]:
        if "entities" in artifact:
            return artifact["entities"]

        entities: List[Dict[str, Any]] = []
        for raw in artifact.get("customers", []):
            entities.append({
                "entity_id": raw.get("entity_id", raw.get("customer_id", "")),
                "entity_type": raw.get("entity_type", "customer"),
                "entity_data": raw,
            })
        for raw in artifact.get("suppliers", []):
            entities.append({
                "entity_id": raw.get("entity_id", raw.get("vendor_code", "")),
                "entity_type": raw.get("entity_type", "supplier"),
                "entity_data": raw,
            })
        for raw in artifact.get("line_items", []):
            entities.append({
                "entity_id": raw.get("entity_id", raw.get("id", "")),
                "entity_type": raw.get("entity_type", "line_item"),
                "entity_data": raw,
            })
        return entities

    def _extract_entities(self, input_artifact: Any) -> List[Dict[str, Any]]:
        if isinstance(input_artifact, dict):
            return self._flatten_entity_artifact(input_artifact)
        if isinstance(input_artifact, EntitySet):
            return self._flatten_entity_artifact(input_artifact.to_dict())
        if hasattr(input_artifact, "to_dict"):
            artifact = input_artifact.to_dict()
            if isinstance(artifact, dict):
                return self._flatten_entity_artifact(artifact)
        if isinstance(input_artifact, list):
            return input_artifact
        return []

    def run(self, input_artifact: Any, context: ExecutionContext) -> StageResult:
        match_strategy = self._config.get("match_strategy", "default")
        confidence_threshold = float(self._config.get("confidence_threshold", 0.7))
        allow_multiple_matches = bool(self._config.get("allow_multiple_matches", False))
        master_data_type = self._config.get("master_data_type")
        source_document_id = self._config.get("source_document_id", "unknown")

        start = time.monotonic()
        try:
            entities = self._extract_entities(input_artifact)

            requests: List[MatchRequest] = []
            for entity in entities:
                entity_type = entity.get("entity_type", "unknown")
                request = MatchRequest(
                    request_id=str(uuid.uuid4()),
                    entity_id=entity.get("entity_id", entity.get("id", "")),
                    entity_type=entity_type,
                    entity_data=entity.get("entity_data", entity),
                    master_data_type=master_data_type or entity.get("master_data_type", entity_type),
                    match_strategy=match_strategy,
                    confidence_threshold=confidence_threshold,
                    allow_multiple_matches=allow_multiple_matches,
                    source_lineage=entity.get("source_lineage"),
                    metadata=entity.get("metadata", {}),
                )
                requests.append(request)

            service = MatchingService()
            match_set = service.match_batch(source_document_id=source_document_id, requests=requests)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="matching",
                status=ExecutionStatus.SUCCESS.value,
                output_artifact=match_set,
                duration_ms=elapsed_ms,
                metadata={
                    "match_strategy": match_strategy,
                    "confidence_threshold": confidence_threshold,
                    "allow_multiple_matches": allow_multiple_matches,
                    "master_data_type": master_data_type,
                    "entity_count": len(requests),
                },
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="matching",
                status=ExecutionStatus.FAILED.value,
                error=str(exc),
                duration_ms=elapsed_ms,
            )


STAGE_REGISTRY["matching"] = MatchingStage