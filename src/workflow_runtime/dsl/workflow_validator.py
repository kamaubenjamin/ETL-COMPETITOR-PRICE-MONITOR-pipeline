"""Schema validation for workflow definitions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.workflow_runtime.contracts.workflow_definition import WorkflowDefinition
from src.document_engine.structure.models.validation_result import (
    ValidationResult,
    ValidationRuleResult,
)
from src.workflow_runtime.operations.stage_catalog import WORKFLOW_STAGE_TYPES

REQUIRED_WORKFLOW_FIELDS = ["workflow_id", "stages"]
REQUIRED_STAGE_FIELDS = ["name", "type"]
# Backward-compatible export; authoritative values live in stage_catalog.
VALID_STAGE_TYPES = WORKFLOW_STAGE_TYPES


class WorkflowValidator:
    """Validates a parsed WorkflowDefinition for structural correctness.

    This is a pure function — no side effects, no I/O.
    """

    @staticmethod
    def validate(definition: WorkflowDefinition) -> ValidationResult:
        """Run all validation rules against a workflow definition.

        Returns a ``ValidationResult`` with individual rule outcomes.
        """
        rules: List[ValidationRuleResult] = []

        # 1. Workflow-level field presence
        rules.extend(WorkflowValidator._validate_required_fields(definition))

        # 2. Stage-level validation
        rules.extend(WorkflowValidator._validate_stages(definition))

        # 3. Dependency graph validation
        rules.extend(WorkflowValidator._validate_dependencies(definition))

        return ValidationResult.from_rules(rules)

    @staticmethod
    def validate_or_raise(definition: WorkflowDefinition) -> WorkflowDefinition:
        """Validate and return the definition, or raise ValueError."""
        result = WorkflowValidator.validate(definition)
        if not result.all_passed:
            failures = [r for r in result.rules if not r.passed]
            messages = "; ".join(f"[{r.severity}] {r.rule_name}: {r.message}" for r in failures)
            raise ValueError(f"Workflow validation failed: {messages}")
        return definition

    @staticmethod
    def _validate_required_fields(definition: WorkflowDefinition) -> List[ValidationRuleResult]:
        results: List[ValidationRuleResult] = []
        if not definition.workflow_id:
            results.append(
                ValidationRuleResult(
                    rule_name="workflow_id_required",
                    passed=False,
                    severity="error",
                    message="Workflow ID is required.",
                )
            )
        else:
            results.append(
                ValidationRuleResult(
                    rule_name="workflow_id_required",
                    passed=True,
                    severity="info",
                    message=f"Workflow ID: {definition.workflow_id}",
                )
            )

        if not definition.stages:
            results.append(
                ValidationRuleResult(
                    rule_name="stages_required",
                    passed=False,
                    severity="error",
                    message="Workflow must have at least one stage.",
                )
            )
        else:
            results.append(
                ValidationRuleResult(
                    rule_name="stages_required",
                    passed=True,
                    severity="info",
                    message=f"Workflow has {len(definition.stages)} stage(s).",
                )
            )

        return results

    @staticmethod
    def _validate_stages(definition: WorkflowDefinition) -> List[ValidationRuleResult]:
        results: List[ValidationRuleResult] = []
        stage_names: set = set()
        duplicate_names: set = set()

        for stage in definition.stages:
            # Name uniqueness
            if stage.name in stage_names:
                duplicate_names.add(stage.name)
            stage_names.add(stage.name)

            # Type validation
            if stage.type not in VALID_STAGE_TYPES:
                results.append(
                    ValidationRuleResult(
                        rule_name=f"stage_type_{stage.name}",
                        passed=False,
                        severity="error",
                        message=f"Stage '{stage.name}' has unsupported type '{stage.type}'. "
                        f"Valid types: {', '.join(sorted(VALID_STAGE_TYPES))}.",
                    )
                )

        for dup in duplicate_names:
            results.append(
                ValidationRuleResult(
                    rule_name=f"duplicate_stage_name_{dup}",
                    passed=False,
                    severity="error",
                    message=f"Duplicate stage name: '{dup}'. Stage names must be unique.",
                )
            )

        if not duplicate_names:
            results.append(
                ValidationRuleResult(
                    rule_name="stage_names_unique",
                    passed=True,
                    severity="info",
                    message="All stage names are unique.",
                )
            )

        return results

    @staticmethod
    def _validate_dependencies(definition: WorkflowDefinition) -> List[ValidationRuleResult]:
        results: List[ValidationRuleResult] = []
        stage_names = {s.name for s in definition.stages}

        for stage in definition.stages:
            for dep in stage.depends_on:
                if dep not in stage_names:
                    results.append(
                        ValidationRuleResult(
                            rule_name=f"dependency_{stage.name}->{dep}",
                            passed=False,
                            severity="error",
                            message=f"Stage '{stage.name}' depends on '{dep}' which does not exist.",
                        )
                    )

        if all(dep in stage_names for s in definition.stages for dep in s.depends_on):
            results.append(
                ValidationRuleResult(
                    rule_name="dependencies_resolve",
                    passed=True,
                    severity="info",
                    message="All stage dependencies resolve to existing stages.",
                )
            )

        return results
