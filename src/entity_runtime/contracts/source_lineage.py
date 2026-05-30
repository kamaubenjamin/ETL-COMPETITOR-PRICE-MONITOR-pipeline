"""Provenance tracking for every extracted entity."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True, slots=True)
class SourceLineage:
    """Provenance metadata linking an extracted entity back to its original source."""

    source_type: str
    source_path: str
    ingestion_id: str
    pipeline_run_id: str
    parsed_block_index: int = -1
    line_number: Optional[int] = None
    extraction_rule: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)


def empty_lineage() -> SourceLineage:
    """Create a default empty SourceLineage for testing or placeholder use."""
    return SourceLineage(source_type="", source_path="", ingestion_id="", pipeline_run_id="")