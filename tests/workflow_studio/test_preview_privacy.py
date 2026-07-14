from src.workflow_studio import *
NOW="2026-07-14T10:00:00+00:00"
class LeakyAdapter:
    def execute_preview(self,*args): raise RuntimeError("token=secret C:\\backend\\path stack trace")
def test_raw_adapter_exception_not_exposed():
    action=ActionDefinition("action-1","runtime","filter","1"); rule=RuleDefinition("rule-1","Rule","stage-1","",(),0,True,False,None,(action,)); version=WorkflowVersion("version-1","workflow-1",1,"draft",(rule,),None,WorkflowChangeSummary("Preview"),"actor-1",None,None,NOW,NOW,None,None); validation=WorkflowValidationService(InMemoryWorkflowOperationCatalog()).validate(version); command=WorkflowPreviewCommand("preview-1","tenant-1","workflow-1","version-1","actor-1",version,validation,WorkflowPreviewPolicy(True),WorkflowPreviewLimits(),NOW,inline_sample={"safe":1}); payload=WorkflowPreviewService(LeakyAdapter()).preview(command).to_dict(); text=str(payload).lower(); assert "secret" not in text and "backend" not in text and "stack" not in text
def test_preview_modules_do_not_expose_workflow_or_fixture_bodies_in_audit():
    fields=set(WorkflowPreviewAuditIntent.__dataclass_fields__); assert "fixture" not in fields and "workflow" not in fields and "output" not in fields and "trace" not in fields
