from src.workflow_studio import WorkflowPreviewOutput,WorkflowPreviewRuleResult,WorkflowPreviewTraceEvent

def test_rule_trace_and_output_are_json_safe():
    rule=WorkflowPreviewRuleResult("rule-1","Rule","completed",0,1,1,"bounded",(),("total",)); trace=WorkflowPreviewTraceEvent(0,"rule_completed","completed","adapter_completed","rule-1","stage-1"); output=WorkflowPreviewOutput(1,{"total":10},("total",),())
    assert rule.to_dict()["output_fields"]==["total"]; assert trace.to_dict()["event_type"]=="rule_completed"; assert output.to_dict()["fields"]=={"total":10}
def test_output_mapping_is_immutable():
    output=WorkflowPreviewOutput(1,{"total":10})
    try: output.fields["total"]=20
    except TypeError: pass
    else: raise AssertionError("output fields must be immutable")
