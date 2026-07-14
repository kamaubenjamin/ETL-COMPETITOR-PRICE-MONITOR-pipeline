"""Immutable commands, fixture references, and preview policy."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from .contracts import StudioContract, optional_id, safe_code, safe_metadata, stable_id, utc_timestamp
from .definitions import WorkflowVersion
from .preview_fixtures import normalize_preview_sample
from .preview_limits import WorkflowPreviewLimits
from .validation_results import WorkflowValidationResult

@dataclass(frozen=True, slots=True)
class WorkflowPreviewFixtureReference(StudioContract):
    fixture_id:str; label:str
    def __post_init__(self): object.__setattr__(self,"fixture_id",stable_id(self.fixture_id,"fixture_id")); object.__setattr__(self,"label",stable_id(self.label,"label"))

@dataclass(frozen=True, slots=True)
class WorkflowPreviewFixture(StudioContract):
    label:str; value:Any
    def __post_init__(self): object.__setattr__(self,"label",stable_id(self.label,"label"))

@dataclass(frozen=True, slots=True)
class WorkflowPreviewPolicy(StudioContract):
    permission_granted:bool; required_features_available:bool=True; unresolved_legacy_review:bool=False; allow_redacted_values:bool=False; protected_fields:tuple[str,...]=(); replacement_marker:str="[REDACTED]"
    def __post_init__(self):
        for n in ("permission_granted","required_features_available","unresolved_legacy_review","allow_redacted_values"):
            if not isinstance(getattr(self,n),bool): raise ValueError(f"{n} must be boolean")
        object.__setattr__(self,"protected_fields",tuple(stable_id(x,"protected_field") for x in self.protected_fields))
        if self.replacement_marker != "[REDACTED]": raise ValueError("replacement marker is fixed")

@dataclass(frozen=True, slots=True)
class WorkflowPreviewExecutionReference(StudioContract):
    preview_id:str; workflow_id:str; version_id:str; fixture_label:str
    def __post_init__(self):
        for n in self.__dataclass_fields__: object.__setattr__(self,n,stable_id(getattr(self,n),n))

@dataclass(frozen=True, slots=True)
class WorkflowPreviewCommand(StudioContract):
    preview_id:str; tenant_id:str; workflow_id:str; version_id:str; actor_id:str; version:WorkflowVersion; validation_result:WorkflowValidationResult; policy:WorkflowPreviewPolicy; limits:WorkflowPreviewLimits; occurred_at:str; fixture_reference:WorkflowPreviewFixtureReference|None=None; inline_sample:Any=None; correlation_id:str|None=None; metadata:Mapping[str,Any]|None=None
    def __post_init__(self):
        for n in ("preview_id","tenant_id","workflow_id","version_id","actor_id"): object.__setattr__(self,n,stable_id(getattr(self,n),n))
        if not isinstance(self.version,WorkflowVersion) or not isinstance(self.validation_result,WorkflowValidationResult) or not isinstance(self.policy,WorkflowPreviewPolicy) or not isinstance(self.limits,WorkflowPreviewLimits): raise ValueError("preview command contracts must be modeled")
        if (self.fixture_reference is None)==(self.inline_sample is None): raise ValueError("exactly one fixture source is required")
        if self.inline_sample is not None: object.__setattr__(self,"inline_sample",normalize_preview_sample(self.inline_sample,self.limits))
        object.__setattr__(self,"occurred_at",utc_timestamp(self.occurred_at,"occurred_at")); object.__setattr__(self,"correlation_id",optional_id(self.correlation_id,"correlation_id")); object.__setattr__(self,"metadata",safe_metadata(self.metadata))
