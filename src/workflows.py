"""
Workflow definitions for configurable ETL pipelines.
Supports source-specific thresholds, filters, and monitoring configurations.
"""
from typing import List, Dict, Optional
import json
import glob
import os
from dataclasses import dataclass, asdict


@dataclass
class SourceConfig:
    """Configuration for a single data source."""
    name: str
    source_type: str  # "playwright", "selenium", "csv", "api"
    url: Optional[str] = None
    selector: Optional[str] = None
    mode: str = "Auto Detect"
    keyword: Optional[str] = None
    match_threshold: int = 70  # Source-specific match threshold


@dataclass
class WorkflowConfig:
    """Configuration for a complete ETL workflow."""
    workflow_id: str
    name: str
    description: str
    sources: List[SourceConfig]
    transformation_rules: List[Dict] = None
    alert_rules: List[Dict] = None
    global_match_threshold: int = 70
    enabled: bool = True

    def __post_init__(self):
        if self.transformation_rules is None:
            self.transformation_rules = []
        if self.alert_rules is None:
            self.alert_rules = []

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "sources": [asdict(s) for s in self.sources],
            "transformation_rules": self.transformation_rules,
            "alert_rules": self.alert_rules,
            "global_match_threshold": self.global_match_threshold,
            "enabled": self.enabled,
        }

    @staticmethod
    def from_dict(data: dict) -> "WorkflowConfig":
        """Create from dictionary."""
        sources = [
            SourceConfig(**s) for s in data.get("sources", [])
        ]
        return WorkflowConfig(
            workflow_id=data["workflow_id"],
            name=data["name"],
            description=data["description"],
            sources=sources,
            transformation_rules=data.get("transformation_rules", []),
            alert_rules=data.get("alert_rules", []),
            global_match_threshold=data.get("global_match_threshold", 70),
            enabled=data.get("enabled", True),
        )


# Predefined workflows for common use cases
ELECTRONICS_MONITORING = WorkflowConfig(
    workflow_id="electronics_monitoring",
    name="Electronics Price Monitoring",
    description="Monitor competitor pricing on electronics across Jumia and Kilimall",
    sources=[
        SourceConfig(
            name="jumia_electronics",
            source_type="playwright",
            url="https://www.jumia.co.ke/electronics/",
            selector="article.prd",
            match_threshold=72,
        ),
        SourceConfig(
            name="kilimall_electronics",
            source_type="playwright",
            url="https://www.kilimall.co.ke/search",
            selector=".product-item",
            match_threshold=72,
        ),
    ],
    transformation_rules=[
        {"type": "drop_nulls", "subset": ["price"]},
    ],
    alert_rules=[
        {"type": "price_drop", "threshold": 5},
        {"type": "undercut", "threshold": 2000},
    ],
    global_match_threshold=70,
)

SMARTPHONES_MONITORING = WorkflowConfig(
    workflow_id="smartphones_monitoring",
    name="Smartphone Price Monitoring",
    description="Track smartphone pricing across multiple channels",
    sources=[
        SourceConfig(
            name="jumia_phones",
            source_type="playwright",
            url="https://www.jumia.co.ke/mobile-phones/",
            selector="article.prd",
            keyword="smartphone",
            match_threshold=75,
        ),
    ],
    transformation_rules=[
        {"type": "drop_nulls", "subset": ["price"]},
        {"type": "filter", "condition": "price > 5000"},
    ],
    global_match_threshold=75,
)


class WorkflowRegistry:
    """Registry for managing workflow configurations."""

    def __init__(self):
        self.workflows: Dict[str, WorkflowConfig] = {
            ELECTRONICS_MONITORING.workflow_id: ELECTRONICS_MONITORING,
            SMARTPHONES_MONITORING.workflow_id: SMARTPHONES_MONITORING,
        }

    def register(self, workflow: WorkflowConfig):
        """Register a new workflow."""
        self.workflows[workflow.workflow_id] = workflow

    def get(self, workflow_id: str) -> Optional[WorkflowConfig]:
        """Retrieve a workflow by ID."""
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> List[str]:
        """List all available workflow IDs."""
        return list(self.workflows.keys())

    def list_enabled(self) -> List[WorkflowConfig]:
        """List all enabled workflows."""
        return [w for w in self.workflows.values() if w.enabled]

    def save_to_file(self, workflow_id: str, filepath: str):
        """Save a workflow to JSON file."""
        workflow = self.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(workflow.to_dict(), f, indent=2)

    def load_all_workflows(self, directory: str):
        """Load all workflow JSON files from a directory."""
        if not os.path.isdir(directory):
            return
        for path in glob.glob(os.path.join(directory, "*.json")):
            try:
                self.load_from_file(path)
            except Exception:
                continue

    def load_from_file(self, filepath: str) -> WorkflowConfig:
        """Load a workflow from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        workflow = WorkflowConfig.from_dict(data)
        self.register(workflow)
        return workflow


# Global registry instance
registry = WorkflowRegistry()
workflow_store_dir = os.path.join(os.path.dirname(__file__), "workflows")
registry.load_all_workflows(workflow_store_dir)
