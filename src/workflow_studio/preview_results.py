"""Safe bounded preview result and adapter projection contracts."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any
from .contracts import StudioContract, bounded_text, optional_id, safe_code, stable_id
from .preview_errors import PREVIEW_MESSAGES, WorkflowPreviewErrorCode

class WorkflowPreviewStatus(str, Enum):
    ACCEPTED="accepted"; VALIDATION_BLOCKED="validation_blocked"; FIXTURE_INVALID="fixture_invalid"
    PREVIEW_UNAVAILABLE="preview_unavailable"; RUNNING="running"; COMPLETED="completed"
    COMPLETED_WITH_WARNINGS="completed_with_warnings"; FAILED="failed"; LIMIT_EXCEEDED="limit_exceeded"; CANCELLED="cancelled"

class WorkflowPreviewTraceEventType(str, Enum):
    PREVIEW_REQUESTED="preview_requested"; VALIDATION_STARTED="validation_started"; VALIDATION_BLOCKED="validation_blocked"
    FIXTURE_VALIDATED="fixture_validated"; EXECUTION_STARTED="execution_started"; STAGE_STARTED="stage_started"
    RULE_STARTED="rule_started"; RULE_COMPLETED="rule_completed"; RULE_FAILED="rule_failed"; STAGE_COMPLETED="stage_completed"
    PREVIEW_COMPLETED="preview_completed"; PREVIEW_FAILED="preview_failed"; PREVIEW_LIMIT_EXCEEDED="preview_limit_exceeded"; PREVIEW_UNAVAILABLE="preview_unavailable"

@dataclass(frozen=True, slots=True)
class WorkflowPreviewIssue(StudioContract):
    code: WorkflowPreviewErrorCode
    summary: str
    rule_id: str|None=None
    def __post_init__(self):
        code=self.code if isinstance(self.code,WorkflowPreviewErrorCode) else WorkflowPreviewErrorCode(self.code)
        if self.summary != PREVIEW_MESSAGES[code]: raise ValueError("preview issue must use fixed safe text")
        object.__setattr__(self,"code",code); object.__setattr__(self,"rule_id",optional_id(self.rule_id,"rule_id"))

def preview_issue(code: WorkflowPreviewErrorCode, rule_id: str|None=None)->WorkflowPreviewIssue:
    return WorkflowPreviewIssue(code,PREVIEW_MESSAGES[code],rule_id)

@dataclass(frozen=True, slots=True)
class WorkflowPreviewTraceEvent(StudioContract):
    order:int; event_type:WorkflowPreviewTraceEventType; status:str; reason_code:str; rule_id:str|None=None; stage_id:str|None=None
    def __post_init__(self):
        if not isinstance(self.order,int) or isinstance(self.order,bool) or self.order<0: raise ValueError("trace order invalid")
        object.__setattr__(self,"event_type",self.event_type if isinstance(self.event_type,WorkflowPreviewTraceEventType) else WorkflowPreviewTraceEventType(self.event_type))
        object.__setattr__(self,"status",safe_code(self.status,"status")); object.__setattr__(self,"reason_code",safe_code(self.reason_code,"reason_code"))
        object.__setattr__(self,"rule_id",optional_id(self.rule_id,"rule_id")); object.__setattr__(self,"stage_id",optional_id(self.stage_id,"stage_id"))

@dataclass(frozen=True, slots=True)
class WorkflowPreviewRuleResult(StudioContract):
    rule_id:str; label:str; status:str; order:int; input_item_count:int; output_item_count:int; duration_bucket:str; issue_codes:tuple[str,...]=(); output_fields:tuple[str,...]=()
    def __post_init__(self):
        object.__setattr__(self,"rule_id",stable_id(self.rule_id,"rule_id")); object.__setattr__(self,"label",bounded_text(self.label,"label")); object.__setattr__(self,"status",safe_code(self.status,"status")); object.__setattr__(self,"duration_bucket",safe_code(self.duration_bucket,"duration_bucket"))
        if min(self.order,self.input_item_count,self.output_item_count)<0: raise ValueError("rule counts invalid")
        object.__setattr__(self,"issue_codes",tuple(safe_code(x,"issue_code") for x in self.issue_codes)); object.__setattr__(self,"output_fields",tuple(stable_id(x,"output_field") for x in self.output_fields))

@dataclass(frozen=True, slots=True)
class WorkflowPreviewStageResult(StudioContract):
    stage_id:str; label:str; status:str; order:int; rule_ids:tuple[str,...]; input_item_count:int; output_item_count:int; duration_bucket:str; issue_codes:tuple[str,...]=()
    def __post_init__(self):
        object.__setattr__(self,"stage_id",stable_id(self.stage_id,"stage_id")); object.__setattr__(self,"label",bounded_text(self.label,"label")); object.__setattr__(self,"status",safe_code(self.status,"status")); object.__setattr__(self,"rule_ids",tuple(stable_id(x,"rule_id") for x in self.rule_ids)); object.__setattr__(self,"duration_bucket",safe_code(self.duration_bucket,"duration_bucket"))
        if min(self.order,self.input_item_count,self.output_item_count)<0: raise ValueError("stage counts invalid")
        object.__setattr__(self,"issue_codes",tuple(safe_code(x,"issue_code") for x in self.issue_codes))

@dataclass(frozen=True, slots=True)
class WorkflowPreviewOutput(StudioContract):
    item_count:int; fields:Mapping[str,Any]; changed_fields:tuple[str,...]=(); redacted_fields:tuple[str,...]=()
    def __post_init__(self):
        if not isinstance(self.item_count,int) or self.item_count<0: raise ValueError("item_count invalid")
        if not isinstance(self.fields,Mapping): raise ValueError("fields must be modeled")
        object.__setattr__(self,"fields",MappingProxyType(dict(sorted(self.fields.items())))); object.__setattr__(self,"changed_fields",tuple(stable_id(x,"changed_field") for x in self.changed_fields)); object.__setattr__(self,"redacted_fields",tuple(stable_id(x,"redacted_field") for x in self.redacted_fields))

@dataclass(frozen=True, slots=True)
class WorkflowPreviewRuntimeResult(StudioContract):
    status:WorkflowPreviewStatus; rules:tuple[WorkflowPreviewRuleResult,...]=(); stages:tuple[WorkflowPreviewStageResult,...]=(); trace:tuple[WorkflowPreviewTraceEvent,...]=(); output:WorkflowPreviewOutput|None=None; issues:tuple[WorkflowPreviewIssue,...]=()
    def __post_init__(self):
        object.__setattr__(self,"status",self.status if isinstance(self.status,WorkflowPreviewStatus) else WorkflowPreviewStatus(self.status))
        for name,expected,maximum in (("rules",WorkflowPreviewRuleResult,100),("stages",WorkflowPreviewStageResult,100),("trace",WorkflowPreviewTraceEvent,500),("issues",WorkflowPreviewIssue,500)):
            values=getattr(self,name)
            if not isinstance(values,(tuple,list)) or len(values)>maximum or not all(isinstance(x,expected) for x in values): raise ValueError(f"{name} must be bounded modeled values")
            object.__setattr__(self,name,tuple(values))
        if self.output is not None and not isinstance(self.output,WorkflowPreviewOutput): raise ValueError("output must be modeled")

@dataclass(frozen=True, slots=True)
class WorkflowPreviewResult(StudioContract):
    preview_id:str; workflow_id:str; version_id:str; status:WorkflowPreviewStatus; rules:tuple[WorkflowPreviewRuleResult,...]; stages:tuple[WorkflowPreviewStageResult,...]; trace:tuple[WorkflowPreviewTraceEvent,...]; output:WorkflowPreviewOutput|None; issues:tuple[WorkflowPreviewIssue,...]; audit_intents:tuple[Any,...]
    def __post_init__(self):
        object.__setattr__(self,"preview_id",stable_id(self.preview_id,"preview_id")); object.__setattr__(self,"workflow_id",stable_id(self.workflow_id,"workflow_id")); object.__setattr__(self,"version_id",stable_id(self.version_id,"version_id")); object.__setattr__(self,"status",self.status if isinstance(self.status,WorkflowPreviewStatus) else WorkflowPreviewStatus(self.status))
