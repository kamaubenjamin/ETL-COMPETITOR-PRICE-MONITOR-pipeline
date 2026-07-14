"""Structured, non-executable Workflow Studio conditions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

from .contracts import SafeArgumentValue, StudioContract, logical_path, safe_condition_value


class ConditionOperator(str, Enum):
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    MATCHES_REGEX = "matches_regex"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class BooleanOperator(str, Enum):
    ALL = "all"
    ANY = "any"
    NOT = "not"


class NullPolicy(str, Enum):
    REJECT = "reject"
    MATCH = "match"
    IGNORE = "ignore"


_VALUELESS = {
    ConditionOperator.EXISTS,
    ConditionOperator.NOT_EXISTS,
    ConditionOperator.IS_NULL,
    ConditionOperator.IS_NOT_NULL,
}
_LIST_OPERATORS = {ConditionOperator.IN, ConditionOperator.NOT_IN}


@dataclass(frozen=True, slots=True)
class ConditionDefinition(StudioContract):
    field_path: str
    operator: ConditionOperator
    value: SafeArgumentValue = None
    null_policy: NullPolicy = NullPolicy.REJECT

    def __post_init__(self) -> None:
        object.__setattr__(self, "field_path", logical_path(self.field_path, "field_path"))
        try:
            operator = self.operator if isinstance(self.operator, ConditionOperator) else ConditionOperator(self.operator)
            null_policy = self.null_policy if isinstance(self.null_policy, NullPolicy) else NullPolicy(self.null_policy)
        except (TypeError, ValueError) as error:
            raise ValueError("condition uses an unsupported policy or operator") from error
        object.__setattr__(self, "operator", operator)
        object.__setattr__(self, "null_policy", null_policy)
        if operator in _VALUELESS:
            if self.value is not None:
                raise ValueError("this condition operator does not accept a value")
            return
        value = safe_condition_value(self.value)
        if operator in _LIST_OPERATORS and (not isinstance(value, tuple) or not value):
            raise ValueError("membership conditions require a non-empty scalar list")
        if operator not in _LIST_OPERATORS and isinstance(value, tuple):
            raise ValueError("this condition operator requires a scalar value")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class ConditionGroup(StudioContract):
    operator: BooleanOperator
    conditions: tuple[ConditionDefinition | "ConditionGroup", ...]

    def __post_init__(self) -> None:
        try:
            operator = self.operator if isinstance(self.operator, BooleanOperator) else BooleanOperator(self.operator)
        except (TypeError, ValueError) as error:
            raise ValueError("condition group uses an unsupported boolean operator") from error
        if not isinstance(self.conditions, (tuple, list)):
            raise ValueError("conditions must be a bounded condition sequence")
        conditions = tuple(self.conditions)
        if not conditions or len(conditions) > 32:
            raise ValueError("condition group must contain between 1 and 32 conditions")
        if operator is BooleanOperator.NOT and len(conditions) != 1:
            raise ValueError("not condition groups require exactly one condition")
        if not all(isinstance(item, (ConditionDefinition, ConditionGroup)) for item in conditions):
            raise ValueError("condition groups may contain only modeled conditions")
        object.__setattr__(self, "operator", operator)
        object.__setattr__(self, "conditions", conditions)
        if _condition_depth(self) > 5:
            raise ValueError("condition nesting exceeds the supported depth")


def _condition_depth(group: ConditionGroup) -> int:
    nested = [item for item in group.conditions if isinstance(item, ConditionGroup)]
    return 1 + max((_condition_depth(item) for item in nested), default=0)


Condition: TypeAlias = ConditionDefinition | ConditionGroup
