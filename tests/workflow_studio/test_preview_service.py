from dataclasses import replace
from src.workflow_studio import *

NOW="2026-07-14T10:00:00+00:00"
def make_version(operation="filter"):
    action=ActionDefinition("action-1","runtime",operation,"1"); rule=RuleDefinition("rule-1","Rule","stage-1","",(),0,True,False,None,(action,),output_contract_hints=("total",)); return WorkflowVersion("version-1","workflow-1",1,"draft",(rule,),None,WorkflowChangeSummary("Preview"),"actor-1",None,None,NOW,NOW,None,None)
def make_command(operation="filter",**changes):
    version=make_version(operation); validation=WorkflowValidationService(InMemoryWorkflowOperationCatalog()).validate(version)
    values=dict(preview_id="preview-1",tenant_id="tenant-1",workflow_id="workflow-1",version_id="version-1",actor_id="actor-1",version=version,validation_result=validation,policy=WorkflowPreviewPolicy(True,allow_redacted_values=True,protected_fields=("secret_field",)),limits=WorkflowPreviewLimits(),occurred_at=NOW,inline_sample={"total":10})
    values.update(changes); return WorkflowPreviewCommand(**values)
class CountingAdapter(SuccessfulWorkflowPreviewAdapter):
    def __init__(self): self.calls=0
    def execute_preview(self,*args): self.calls+=1; return super().execute_preview(*args)
class OutputAdapter:
    def execute_preview(self,*args): return WorkflowPreviewRuntimeResult("completed",output=WorkflowPreviewOutput(1,{"total":10,"secret_field":"hidden"},("total",)))

def test_successful_preview_returns_stable_rule_stage_trace():
    service=WorkflowPreviewService(SuccessfulWorkflowPreviewAdapter()); first=service.preview(make_command()); second=service.preview(make_command()); assert first.status.value=="completed"; assert first.to_dict()==second.to_dict(); assert first.rules[0].rule_id=="rule-1"; assert first.stages[0].stage_id=="stage-1"
def test_invalid_workflow_blocked_before_adapter_invocation():
    adapter=CountingAdapter(); command=make_command(); command=replace(command,workflow_id="workflow-other"); result=WorkflowPreviewService(adapter).preview(command); assert result.status.value=="validation_blocked"; assert adapter.calls==0
def test_preview_ineligible_operation_blocked():
    adapter=CountingAdapter(); result=WorkflowPreviewService(adapter).preview(make_command("trim")); assert result.status.value=="validation_blocked"; assert adapter.calls==0
def test_missing_feature_and_legacy_review_blocked():
    adapter=CountingAdapter(); a=WorkflowPreviewService(adapter).preview(make_command(policy=WorkflowPreviewPolicy(True,required_features_available=False))); b=WorkflowPreviewService(adapter).preview(make_command(policy=WorkflowPreviewPolicy(True,unresolved_legacy_review=True))); assert a.status.value==b.status.value=="validation_blocked"; assert adapter.calls==0
def test_failing_and_unavailable_adapters_are_safe():
    failed=WorkflowPreviewService(FailingWorkflowPreviewAdapter()).preview(make_command()); unavailable=WorkflowPreviewService(UnavailableWorkflowPreviewAdapter()).preview(make_command()); assert failed.status.value=="failed"; assert "sensitive" not in str(failed.to_dict()); assert unavailable.status.value=="preview_unavailable"
def test_limit_exceeded_before_and_after_adapter_is_safe():
    version=make_version(); validation=WorkflowValidationService(InMemoryWorkflowOperationCatalog()).validate(version); command=make_command(version=version,validation_result=validation,limits=WorkflowPreviewLimits(max_execution_steps=1)); assert WorkflowPreviewService(LimitExceededWorkflowPreviewAdapter()).preview(command).status.value=="limit_exceeded"
def test_dependency_depth_limit_is_enforced_before_adapter():
    first=RuleDefinition("rule-a","A","stage","",(),0,True,False,None,(ActionDefinition("action-a","runtime","filter","1"),)); second=RuleDefinition("rule-b","B","stage","",("rule-a",),1,True,False,None,(ActionDefinition("action-b","runtime","filter","1"),)); version=replace(make_version(),rules=(first,second)); validation=WorkflowValidationService(InMemoryWorkflowOperationCatalog()).validate(version); adapter=CountingAdapter(); result=WorkflowPreviewService(adapter).preview(make_command(version=version,validation_result=validation,limits=WorkflowPreviewLimits(max_dependency_depth=1))); assert result.status.value=="limit_exceeded" and adapter.calls==0
def test_output_redaction_and_omission_policy():
    result=WorkflowPreviewService(OutputAdapter()).preview(make_command()); assert result.output.fields=={"secret_field":"[REDACTED]","total":10}; omitted=WorkflowPreviewService(OutputAdapter()).preview(make_command(policy=WorkflowPreviewPolicy(True,allow_redacted_values=False))); assert omitted.output.fields=={}
def test_approved_fixture_reference_is_resolved_without_body_in_audit():
    provider=InMemoryWorkflowPreviewFixtureProvider({"tenant-1:fixture-1":{"total":10}}); command=make_command(inline_sample=None,fixture_reference=WorkflowPreviewFixtureReference("fixture-1","safe_fixture")); result=WorkflowPreviewService(SuccessfulWorkflowPreviewAdapter(),provider).preview(command); assert result.status.value=="completed"; assert result.audit_intents[0].fixture_label=="safe_fixture"
