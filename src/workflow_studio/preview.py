"""Deterministic bounded Workflow Studio preview orchestration."""
from __future__ import annotations
from collections.abc import Mapping
from .preview_adapter import WorkflowPreviewRuntimePort
from .preview_audit import WorkflowPreviewAuditEventType,WorkflowPreviewAuditIntent
from .preview_contracts import WorkflowPreviewCommand,WorkflowPreviewFixture
from .preview_errors import WorkflowPreviewErrorCode
from .preview_fixtures import InMemoryWorkflowPreviewFixtureProvider,normalize_preview_sample
from .preview_results import *

class WorkflowPreviewService:
    def __init__(self,adapter:WorkflowPreviewRuntimePort,fixtures:InMemoryWorkflowPreviewFixtureProvider|None=None): self._adapter=adapter; self._fixtures=fixtures or InMemoryWorkflowPreviewFixtureProvider()
    def preview(self,command:WorkflowPreviewCommand)->WorkflowPreviewResult:
        label=command.fixture_reference.label if command.fixture_reference else "inline_sample"
        trace=[_trace(0,"preview_requested","accepted","preview_requested")]
        audits=[_audit(command,label,"preview_requested","accepted","preview_requested")]
        if command.workflow_id!=command.version.workflow_id or command.version_id!=command.version.version_id or command.validation_result.workflow_id!=command.workflow_id or command.validation_result.version_id!=command.version_id:
            return _blocked(command,label,WorkflowPreviewStatus.VALIDATION_BLOCKED,WorkflowPreviewErrorCode.IDENTITY_MISMATCH,trace,audits)
        trace.append(_trace(1,"validation_started","running","validation_started"))
        validation=command.validation_result
        if not validation.structurally_valid or not validation.dependency_result.valid:
            return _blocked(command,label,WorkflowPreviewStatus.VALIDATION_BLOCKED,WorkflowPreviewErrorCode.VALIDATION_BLOCKED,trace,audits)
        if not validation.preview_eligible:
            code=WorkflowPreviewErrorCode.REQUIRED_FEATURE_UNAVAILABLE if any(i.code=="required_feature_unavailable" for i in validation.issues) else WorkflowPreviewErrorCode.PREVIEW_INELIGIBLE
            return _blocked(command,label,WorkflowPreviewStatus.VALIDATION_BLOCKED,code,trace,audits)
        if command.policy.unresolved_legacy_review or any(i.code=="legacy_manual_review" for i in validation.issues):
            return _blocked(command,label,WorkflowPreviewStatus.VALIDATION_BLOCKED,WorkflowPreviewErrorCode.LEGACY_REVIEW_UNRESOLVED,trace,audits)
        if not command.policy.permission_granted or not command.policy.required_features_available:
            return _blocked(command,label,WorkflowPreviewStatus.VALIDATION_BLOCKED,WorkflowPreviewErrorCode.REQUIRED_FEATURE_UNAVAILABLE,trace,audits)
        if len(command.version.rules)>command.limits.max_rules or any(len(r.actions)>command.limits.max_actions_per_rule for r in command.version.rules) or sum(len(r.actions) for r in command.version.rules)>command.limits.max_execution_steps or _dependency_depth(command.version)>command.limits.max_dependency_depth:
            return _blocked(command,label,WorkflowPreviewStatus.LIMIT_EXCEEDED,WorkflowPreviewErrorCode.LIMIT_EXCEEDED,trace,audits)
        try:
            raw=command.inline_sample if command.fixture_reference is None else self._fixtures.get_fixture(command.tenant_id,command.fixture_reference.fixture_id)
            if raw is None: return _blocked(command,label,WorkflowPreviewStatus.FIXTURE_INVALID,WorkflowPreviewErrorCode.FIXTURE_NOT_FOUND,trace,audits)
            fixture=normalize_preview_sample(raw,command.limits)
        except (TypeError,ValueError): return _blocked(command,label,WorkflowPreviewStatus.FIXTURE_INVALID,WorkflowPreviewErrorCode.FIXTURE_INVALID,trace,audits)
        trace.append(_trace(len(trace),"fixture_validated","accepted","fixture_validated")); trace.append(_trace(len(trace),"execution_started","running","execution_started")); audits.append(_audit(command,label,"preview_started","running","execution_started"))
        try: runtime=self._adapter.execute_preview(command.version,fixture,command.limits,command.policy)
        except Exception:
            return _blocked(command,label,WorkflowPreviewStatus.FAILED,WorkflowPreviewErrorCode.ADAPTER_FAILED,trace,audits)
        if not isinstance(runtime,WorkflowPreviewRuntimeResult): return _blocked(command,label,WorkflowPreviewStatus.FAILED,WorkflowPreviewErrorCode.ADAPTER_FAILED,trace,audits)
        if runtime.status in (WorkflowPreviewStatus.PREVIEW_UNAVAILABLE,WorkflowPreviewStatus.LIMIT_EXCEEDED,WorkflowPreviewStatus.CANCELLED,WorkflowPreviewStatus.FAILED):
            code={WorkflowPreviewStatus.PREVIEW_UNAVAILABLE:WorkflowPreviewErrorCode.PREVIEW_UNAVAILABLE,WorkflowPreviewStatus.LIMIT_EXCEEDED:WorkflowPreviewErrorCode.LIMIT_EXCEEDED,WorkflowPreviewStatus.CANCELLED:WorkflowPreviewErrorCode.CANCELLED,WorkflowPreviewStatus.FAILED:WorkflowPreviewErrorCode.ADAPTER_FAILED}[runtime.status]
            return _blocked(command,label,runtime.status,code,trace,audits)
        rules=tuple(x for x in runtime.rules[:command.limits.max_rules] if isinstance(x,WorkflowPreviewRuleResult))
        stages=tuple(x for x in runtime.stages[:command.limits.max_rules] if isinstance(x,WorkflowPreviewStageResult))
        trace.extend(x for x in runtime.trace if isinstance(x,WorkflowPreviewTraceEvent))
        trace=trace[:command.limits.max_trace_events-1]; trace.append(_trace(len(trace),"preview_completed",runtime.status.value,"preview_completed"))
        issues=tuple(x for x in runtime.issues[:command.limits.max_issue_count] if isinstance(x,WorkflowPreviewIssue))
        output=_sanitize_output(runtime.output,command)
        audits.append(_audit(command,label,"preview_completed",runtime.status.value,"preview_completed"))
        return WorkflowPreviewResult(command.preview_id,command.workflow_id,command.version_id,runtime.status,rules,stages,tuple(trace),output,issues,tuple(audits))

def _sanitize_output(output,command):
    if not isinstance(output,WorkflowPreviewOutput): return None
    fields={}
    redacted=[]
    if command.policy.allow_redacted_values:
        for key in sorted(output.fields)[:command.limits.max_output_fields]:
            if key in command.policy.protected_fields: fields[key]=command.policy.replacement_marker; redacted.append(key)
            else:
                try: fields[key]=normalize_preview_sample({key:output.fields[key]},command.limits)[key]
                except ValueError: continue
    return WorkflowPreviewOutput(min(output.item_count,command.limits.max_output_collection_size),fields,output.changed_fields[:command.limits.max_output_fields],tuple(redacted))
def _trace(order,event,status,reason): return WorkflowPreviewTraceEvent(order,event,status,reason)
def _audit(c,label,event,status,reason): return WorkflowPreviewAuditIntent(event,c.tenant_id,c.workflow_id,c.version_id,c.actor_id,label,status,reason,c.occurred_at,c.correlation_id)
def _blocked(c,label,status,code,trace,audits):
    event={WorkflowPreviewStatus.VALIDATION_BLOCKED:"validation_blocked",WorkflowPreviewStatus.FIXTURE_INVALID:"preview_failed",WorkflowPreviewStatus.PREVIEW_UNAVAILABLE:"preview_unavailable",WorkflowPreviewStatus.LIMIT_EXCEEDED:"preview_limit_exceeded",WorkflowPreviewStatus.FAILED:"preview_failed",WorkflowPreviewStatus.CANCELLED:"preview_failed"}.get(status,"preview_failed")
    trace.append(_trace(len(trace),event,status.value,code.value)); audit_event={WorkflowPreviewStatus.VALIDATION_BLOCKED:"preview_validation_blocked",WorkflowPreviewStatus.PREVIEW_UNAVAILABLE:"preview_unavailable",WorkflowPreviewStatus.LIMIT_EXCEEDED:"preview_limit_exceeded"}.get(status,"preview_failed"); audits.append(_audit(c,label,audit_event,status.value,code.value))
    return WorkflowPreviewResult(c.preview_id,c.workflow_id,c.version_id,status,(),(),tuple(trace),None,(preview_issue(code),),tuple(audits))
def _dependency_depth(version):
    graph={r.rule_id:r.dependencies for r in version.rules}; memo={}
    def depth(rule_id):
        if rule_id in memo:return memo[rule_id]
        memo[rule_id]=1+max((depth(x) for x in graph.get(rule_id,()) if x in graph),default=0); return memo[rule_id]
    return max((depth(x) for x in graph),default=0)
