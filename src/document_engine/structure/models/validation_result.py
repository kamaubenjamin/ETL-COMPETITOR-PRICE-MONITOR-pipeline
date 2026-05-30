"""Validation result models for deterministic structural checks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True, slots=True)
class ValidationRuleResult:
    """Outcome of a single structural validation rule."""

    rule_name: str
    passed: bool
    severity: str = "warning"
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Aggregate outcome of all structural validation rules.

    ``all_passed`` is True only when every rule passed.
    Quality scoring is handled separately in ``quality_scorer``.
    """

    rules: List[ValidationRuleResult] = field(default_factory=list)
    all_passed: bool = False
    total_rules: int = 0
    passed_count: int = 0

    def __post_init__(self) -> None:
        if self.total_rules == 0 and not self.rules:
            object.__setattr__(self, "total_rules", 0)
            object.__setattr__(self, "passed_count", 0)
            object.__setattr__(self, "all_passed", True)

    @classmethod
    def from_rules(cls, rules: List[ValidationRuleResult]) -> ValidationResult:
        """Build a ValidationResult from a list of rule results.

        This is the primary construction path. Avoids exposing mutable lists
        in frozen dataclass __post_init__.
        """
        total = len(rules)
        passed_count = sum(1 for r in rules if r.passed)
        return cls(
            rules=list(rules),
            all_passed=passed_count == total,
            total_rules=total,
            passed_count=passed_count,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "all_passed": self.all_passed,
            "total_rules": self.total_rules,
            "passed_count": self.passed_count,
            "failed_count": self.total_rules - self.passed_count,
            "rules": [r.to_dict() for r in self.rules],
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)