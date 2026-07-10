"""Field-level Review Runtime correction contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from src.review_runtime.errors import INVALID_VALUE, ReviewRuntimeError
from src.review_runtime.privacy import metadata_to_dict, validate_safe_metadata

from ._validation import (
    CONTRACT_VERSION,
    check_keys,
    code,
    contract_version,
    controlled_scalar,
    enum_value,
    field_path,
    identifier,
    mapping,
    optional_identifier,
    stage_name,
    timestamp,
)
from .enums import ControlledValueType, CorrectionOperation, SourceRuntime


@dataclass(frozen=True, slots=True)
class ControlledValue:
    value_type: ControlledValueType | str
    value: str | bool | int | float | None

    def __post_init__(self) -> None:
        value_type = enum_value(self.value_type, ControlledValueType, ("value_type",))
        value = controlled_scalar(self.value, ("value",))
        expected_types: dict[ControlledValueType, tuple[type, ...]] = {
            ControlledValueType.NULL: (type(None),),
            ControlledValueType.STRING: (str,),
            ControlledValueType.INTEGER: (int,),
            ControlledValueType.NUMBER: (int, float),
            ControlledValueType.BOOLEAN: (bool,),
        }
        if value_type is ControlledValueType.INTEGER and isinstance(value, bool):
            valid = False
        elif value_type is ControlledValueType.NUMBER and isinstance(value, bool):
            valid = False
        else:
            valid = isinstance(value, expected_types[value_type])
        if not valid:
            raise ReviewRuntimeError(INVALID_VALUE, "Controlled value does not match value_type.", ("value",))
        object.__setattr__(self, "value_type", value_type)
        object.__setattr__(self, "value", value)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ControlledValue":
        data = mapping(payload, ("new_value",))
        check_keys(data, allowed={"value_type", "value"}, required={"value_type", "value"}, path=("new_value",))
        return cls(value_type=data["value_type"], value=data["value"])

    def to_dict(self) -> dict[str, Any]:
        return {"value_type": self.value_type.value, "value": self.value}


@dataclass(frozen=True, slots=True)
class FieldCorrection:
    correction_id: str
    review_case_id: str
    field_path: str
    new_value: ControlledValue
    reason_code: str
    corrected_by: str
    created_at: str
    source_runtime: SourceRuntime | str
    source_stage: str
    source_artifact_id: str
    operation: CorrectionOperation | str = CorrectionOperation.REPLACE
    old_value_reference: str | None = None
    source_artifact_version: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    contract_version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "correction_id", identifier(self.correction_id, ("correction_id",)))
        object.__setattr__(self, "review_case_id", identifier(self.review_case_id, ("review_case_id",)))
        object.__setattr__(self, "field_path", field_path(self.field_path, ("field_path",)))
        if not isinstance(self.new_value, ControlledValue):
            raise ReviewRuntimeError(INVALID_VALUE, "new_value must be a ControlledValue.", ("new_value",))
        object.__setattr__(self, "reason_code", code(self.reason_code, ("reason_code",)))
        object.__setattr__(self, "corrected_by", identifier(self.corrected_by, ("corrected_by",)))
        object.__setattr__(self, "created_at", timestamp(self.created_at, ("created_at",)))
        object.__setattr__(self, "source_runtime", enum_value(self.source_runtime, SourceRuntime, ("source_runtime",)))
        object.__setattr__(self, "source_stage", stage_name(self.source_stage, ("source_stage",)))
        object.__setattr__(self, "source_artifact_id", identifier(self.source_artifact_id, ("source_artifact_id",)))
        operation = enum_value(self.operation, CorrectionOperation, ("operation",))
        if operation is CorrectionOperation.SET_NULL and self.new_value.value_type is not ControlledValueType.NULL:
            raise ReviewRuntimeError(INVALID_VALUE, "set_null requires a null controlled value.", ("new_value",))
        object.__setattr__(self, "operation", operation)
        object.__setattr__(
            self,
            "old_value_reference",
            optional_identifier(self.old_value_reference, ("old_value_reference",)),
        )
        object.__setattr__(
            self,
            "source_artifact_version",
            optional_identifier(self.source_artifact_version, ("source_artifact_version",)),
        )
        object.__setattr__(self, "metadata", validate_safe_metadata(self.metadata))
        object.__setattr__(self, "contract_version", contract_version(self.contract_version, ("contract_version",)))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FieldCorrection":
        data = mapping(payload)
        required = {
            "correction_id", "review_case_id", "field_path", "new_value", "reason_code",
            "corrected_by", "created_at", "source_runtime", "source_stage", "source_artifact_id",
        }
        allowed = required | {
            "operation", "old_value_reference", "source_artifact_version", "metadata", "contract_version",
        }
        check_keys(data, allowed=allowed, required=required)
        return cls(
            correction_id=data["correction_id"],
            review_case_id=data["review_case_id"],
            field_path=data["field_path"],
            new_value=ControlledValue.from_dict(data["new_value"]),
            reason_code=data["reason_code"],
            corrected_by=data["corrected_by"],
            created_at=data["created_at"],
            source_runtime=data["source_runtime"],
            source_stage=data["source_stage"],
            source_artifact_id=data["source_artifact_id"],
            operation=data.get("operation", CorrectionOperation.REPLACE.value),
            old_value_reference=data.get("old_value_reference"),
            source_artifact_version=data.get("source_artifact_version"),
            metadata=data.get("metadata", {}),
            contract_version=data.get("contract_version", CONTRACT_VERSION),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "correction_id": self.correction_id,
            "review_case_id": self.review_case_id,
            "field_path": self.field_path,
            "operation": self.operation.value,
            "old_value_reference": self.old_value_reference,
            "new_value": self.new_value.to_dict(),
            "reason_code": self.reason_code,
            "corrected_by": self.corrected_by,
            "created_at": self.created_at,
            "source_runtime": self.source_runtime.value,
            "source_stage": self.source_stage,
            "source_artifact_id": self.source_artifact_id,
            "source_artifact_version": self.source_artifact_version,
            "metadata": metadata_to_dict(self.metadata),
        }

