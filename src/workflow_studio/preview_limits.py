"""Fixed bounded Workflow Studio preview limits."""
from dataclasses import dataclass
from .contracts import StudioContract, positive_integer

@dataclass(frozen=True, slots=True)
class WorkflowPreviewLimits(StudioContract):
    max_rules: int = 100
    max_actions_per_rule: int = 32
    max_dependency_depth: int = 32
    max_execution_steps: int = 500
    max_input_collection_size: int = 100
    max_output_collection_size: int = 100
    max_trace_events: int = 200
    max_issue_count: int = 100
    max_output_fields: int = 50
    max_string_length: int = 256
    max_duration_ms: int = 30_000
    max_nested_depth: int = 5

    def __post_init__(self) -> None:
        ceilings = (100, 32, 32, 1000, 1000, 1000, 500, 500, 100, 1024, 120_000, 10)
        for (name, ceiling) in zip(self.__dataclass_fields__, ceilings):
            value = positive_integer(getattr(self, name), name)
            if value > ceiling:
                raise ValueError(f"{name} exceeds the fixed preview ceiling")
