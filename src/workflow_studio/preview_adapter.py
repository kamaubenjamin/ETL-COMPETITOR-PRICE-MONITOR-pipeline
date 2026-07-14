"""Structural preview runtime port and deterministic no-I/O test adapters."""
from typing import Protocol,runtime_checkable,Any
from .definitions import WorkflowVersion
from .preview_contracts import WorkflowPreviewPolicy
from .preview_limits import WorkflowPreviewLimits
from .preview_results import *

@runtime_checkable
class WorkflowPreviewRuntimePort(Protocol):
    def execute_preview(self,version:WorkflowVersion,fixture:Any,limits:WorkflowPreviewLimits,policy:WorkflowPreviewPolicy)->WorkflowPreviewRuntimeResult: ...

class SuccessfulWorkflowPreviewAdapter:
    def execute_preview(self,version,fixture,limits,policy):
        count=len(fixture) if isinstance(fixture,(tuple,list)) else 1
        rules=tuple(WorkflowPreviewRuleResult(r.rule_id,r.name,"completed",r.order,count,count,"bounded",(),r.output_contract_hints) for r in sorted(version.rules,key=lambda x:(x.order,x.rule_id)))
        stages=tuple(WorkflowPreviewStageResult(r.stage,r.stage,"completed",i,(r.rule_id,),count,count,"bounded") for i,r in enumerate(sorted(version.rules,key=lambda x:(x.order,x.rule_id))))
        trace=tuple(WorkflowPreviewTraceEvent(i,"rule_completed","completed","adapter_completed",r.rule_id,r.stage) for i,r in enumerate(sorted(version.rules,key=lambda x:(x.order,x.rule_id))))
        return WorkflowPreviewRuntimeResult(WorkflowPreviewStatus.COMPLETED,rules,stages,trace,WorkflowPreviewOutput(count,{}),())
class FailingWorkflowPreviewAdapter:
    def execute_preview(self,*args,**kwargs): raise RuntimeError("sensitive adapter failure")
class UnavailableWorkflowPreviewAdapter:
    def execute_preview(self,*args,**kwargs): return WorkflowPreviewRuntimeResult(WorkflowPreviewStatus.PREVIEW_UNAVAILABLE,issues=(preview_issue(WorkflowPreviewErrorCode.PREVIEW_UNAVAILABLE),))
class LimitExceededWorkflowPreviewAdapter:
    def execute_preview(self,*args,**kwargs): return WorkflowPreviewRuntimeResult(WorkflowPreviewStatus.LIMIT_EXCEEDED,issues=(preview_issue(WorkflowPreviewErrorCode.LIMIT_EXCEEDED),))
