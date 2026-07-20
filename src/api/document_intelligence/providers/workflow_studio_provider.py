"""App-scoped, in-memory composition for the guarded Workflow Studio API.

This provider deliberately composes only ``workflow_studio`` contracts.  It is
governance storage and safe preview orchestration, not a production executor.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.workflow_studio import (
    ActionDefinition,
    ActionErrorPolicy,
    ActionOutputPolicy,
    BooleanOperator,
    ConditionDefinition,
    ConditionGroup,
    DraftLifecycleService,
    InMemoryWorkflowOperationCatalog,
    InMemoryWorkflowStudioStore,
    PublicationCommand,
    RuleDefinition,
    UnavailableWorkflowPreviewAdapter,
    ValidationPolicyFacts,
    WorkflowChangeSummary,
    WorkflowDefinition,
    WorkflowDefinitionStatus,
    WorkflowOwnership,
    WorkflowPreviewCommand,
    WorkflowPreviewFixtureReference,
    WorkflowPreviewLimits,
    WorkflowPreviewPolicy,
    WorkflowPreviewService,
    WorkflowPublicationService,
    WorkflowReference,
    WorkflowRepositoryError,
    WorkflowStudioAuditEventType,
    WorkflowStudioAuditIntent,
    WorkflowValidationService,
    WorkflowVersion,
    WorkflowVersionStatus,
    next_integer_version,
)


GOVERNANCE_ONLY_NOTICE = (
    "Published definition governance only; production execution activation is not enabled."
)


class WorkflowStudioProviderError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class WorkflowStudioAPIProvider:
    """Process-local Studio composition with tenant filtering and safe projections."""

    def __init__(self, *, preview_adapter: Any | None = None) -> None:
        self.store = InMemoryWorkflowStudioStore()
        self.operation_catalog = InMemoryWorkflowOperationCatalog()
        self.validator = WorkflowValidationService(self.operation_catalog)
        self.lifecycle = DraftLifecycleService(self.store)
        self.publication = WorkflowPublicationService(self.store)
        self.preview = WorkflowPreviewService(preview_adapter or UnavailableWorkflowPreviewAdapter())
        self._audits: list[WorkflowStudioAuditIntent | Mapping[str, Any]] = []
        self._validation: dict[tuple[str, str], Any] = {}
        self._preview_status: dict[tuple[str, str], str] = {}

    def list_definitions(self, tenant_id: str, *, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
        page = self.store.list_definitions(tenant_id, limit=limit, offset=offset)
        return [self._definition(item) for item in page.items], page.total

    def get_definition(self, tenant_id: str, workflow_id: str) -> dict[str, Any] | None:
        stored = self.store.get_definition(tenant_id, workflow_id)
        return None if stored is None else self._definition(stored, detail=True)

    def list_versions(self, tenant_id: str, workflow_id: str, *, limit: int, offset: int) -> tuple[list[dict[str, Any]], int] | None:
        if self.store.get_definition(tenant_id, workflow_id) is None:
            return None
        page = self.store.list_versions(tenant_id, workflow_id, limit=limit, offset=offset)
        return [self._version(item, detail=False) for item in page.items], page.total

    def get_version(self, tenant_id: str, workflow_id: str, version_id: str) -> dict[str, Any] | None:
        stored = self.store.get_version(tenant_id, version_id)
        if stored is None or stored.value.workflow_id != workflow_id:
            return None
        return self._version(stored, detail=True)

    def operations(self) -> list[dict[str, Any]]:
        result = []
        for operation in self.operation_catalog.list_operations():
            result.append({
                "name": operation.name,
                "version": operation.version,
                "category": operation.category.value,
                "description": operation.description,
                "availability": operation.availability.value,
                "preview_eligible": operation.preview_eligible,
                "publication_eligible": operation.publication_eligible,
                "required_features": list(operation.required_features),
                "arguments": [argument.to_dict() for argument in operation.arguments],
            })
        return result

    def audit(self, tenant_id: str, workflow_id: str, *, limit: int, offset: int) -> tuple[list[dict[str, Any]], int] | None:
        if self.store.get_definition(tenant_id, workflow_id) is None:
            return None
        matching = [item for item in self._audits if _audit_value(item, "tenant_id") == tenant_id and _audit_value(item, "workflow_id") == workflow_id]
        rows = [self._audit_projection(item) for item in matching]
        return rows[offset : offset + limit], len(rows)

    def create_workflow(self, tenant_id: str, actor_id: str, payload: Mapping[str, Any], correlation_id: str | None) -> dict[str, Any]:
        _fields(payload, {"workflow_id", "name", "description", "business_domain", "document_type", "version_id", "version", "change_summary", "rules"})
        now = _now()
        workflow_id = payload.get("workflow_id") or f"workflow-{uuid4().hex}"
        version_id = payload.get("version_id") or f"version-{uuid4().hex}"
        rules = _rules(payload.get("rules", ()))
        version_label = payload.get("version", 1)
        change = WorkflowChangeSummary(str(payload.get("change_summary", "Initial workflow draft.")))
        version = WorkflowVersion(version_id, workflow_id, version_label, WorkflowVersionStatus.DRAFT, rules, None, change, actor_id, None, None, now, now, None, None)
        definition = WorkflowDefinition(
            workflow_id, tenant_id, payload.get("name"), payload.get("description", ""),
            payload.get("business_domain"), payload.get("document_type"), WorkflowDefinitionStatus.DRAFT,
            WorkflowReference(workflow_id, version_id, version_label), None,
            WorkflowOwnership(actor_id, actor_id), now, now,
        )
        try:
            stored = self.store.create_definition(definition)
            created = self.lifecycle.create_initial_draft(tenant_id, version, actor_id=actor_id, correlation_id=correlation_id)
        except (ValueError, WorkflowRepositoryError):
            raise WorkflowStudioProviderError("invalid_workflow_definition", "Workflow definition is invalid or already exists.", status_code=409) from None
        self._audits.append(WorkflowStudioAuditIntent(WorkflowStudioAuditEventType.WORKFLOW_CREATED, tenant_id, workflow_id, version_id, None, actor_id, "draft", "workflow_created", now, correlation_id))
        self._audits.extend(created.audit_intents)
        return {"definition": self._definition(stored, detail=True), "version": self._version(created.version, detail=True), "audit": self._audit_projection(self._audits[-2])}

    def create_version(self, tenant_id: str, workflow_id: str, actor_id: str, payload: Mapping[str, Any], correlation_id: str | None) -> dict[str, Any]:
        _fields(payload, {"version_id", "version", "source_version_id", "change_summary", "rules"})
        definition = self.store.get_definition(tenant_id, workflow_id)
        if definition is None:
            raise _not_found()
        if self.store.find_current_draft(tenant_id, workflow_id) is not None:
            raise WorkflowStudioProviderError("current_draft_exists", "Workflow already has a current draft.", status_code=409)
        now = _now()
        version_id = payload.get("version_id") or f"version-{uuid4().hex}"
        source_id = payload.get("source_version_id")
        if source_id is None and definition.value.active_published_version is not None:
            source_id = definition.value.active_published_version.version_id
        change = WorkflowChangeSummary(payload.get("change_summary"))
        try:
            if source_id:
                result = self.lifecycle.derive_draft(tenant_id, source_id, new_version_id=version_id, authored_by=actor_id, change_summary=change, timestamp=now, version=payload.get("version"), correlation_id=correlation_id)
                if "rules" in payload:
                    replacement = replace(result.version.value, rules=_rules(payload["rules"]))
                    result = self.lifecycle.update_draft(tenant_id, replacement, result.version.revision, actor_id=actor_id, timestamp=now, correlation_id=correlation_id)
            else:
                version = WorkflowVersion(version_id, workflow_id, payload.get("version", next_integer_version(self.store, tenant_id, workflow_id)), WorkflowVersionStatus.DRAFT, _rules(payload.get("rules", ())), None, change, actor_id, None, None, now, now, None, None)
                result = self.lifecycle.create_initial_draft(tenant_id, version, actor_id=actor_id, correlation_id=correlation_id)
            updated_definition = replace(definition.value, current_draft_version=WorkflowReference(workflow_id, version_id, result.version.value.version), updated_at=now, ownership=replace(definition.value.ownership, updated_by=actor_id))
            self.store.update_definition(updated_definition, definition.revision)
        except (ValueError, WorkflowRepositoryError):
            raise WorkflowStudioProviderError("version_creation_rejected", "Workflow version could not be created in its current state.", status_code=409) from None
        self._audits.extend(result.audit_intents)
        return self._version(result.version, detail=True)

    def replace_draft(self, tenant_id: str, workflow_id: str, version_id: str, actor_id: str, payload: Mapping[str, Any], correlation_id: str | None) -> dict[str, Any]:
        _fields(payload, {"expected_revision", "rules", "change_summary"}, required={"expected_revision", "rules", "change_summary"})
        current = self._require_version(tenant_id, workflow_id, version_id)
        if current.value.status is not WorkflowVersionStatus.DRAFT:
            raise WorkflowStudioProviderError("immutable_version", "Workflow version is immutable in its current state.", status_code=409)
        try:
            replacement = replace(current.value, rules=_rules(payload["rules"]), change_summary=WorkflowChangeSummary(payload["change_summary"]))
            result = self.lifecycle.update_draft(tenant_id, replacement, payload["expected_revision"], actor_id=actor_id, timestamp=_now(), correlation_id=correlation_id)
        except WorkflowRepositoryError:
            raise WorkflowStudioProviderError("revision_conflict", "Workflow version changed before the update.", status_code=409) from None
        except ValueError:
            raise WorkflowStudioProviderError("invalid_draft", "Workflow draft replacement is invalid.") from None
        self._validation.pop((tenant_id, version_id), None)
        self._preview_status.pop((tenant_id, version_id), None)
        self._audits.extend(result.audit_intents)
        return self._version(result.version, detail=True)

    def validate(self, tenant_id: str, workflow_id: str, version_id: str, actor_id: str) -> dict[str, Any]:
        current = self._require_version(tenant_id, workflow_id, version_id)
        definition = self.store.get_definition(tenant_id, workflow_id)
        result = self.validator.validate(current.value, definition=definition.value)
        self._validation[(tenant_id, version_id)] = result
        stored = current
        if current.value.status is WorkflowVersionStatus.DRAFT and result.structurally_valid:
            transition = self.lifecycle.mark_validated(tenant_id, version_id, current.revision, validation_passed=True, actor_id=actor_id, timestamp=_now())
            stored = transition.version
            self._audits.extend(transition.audit_intents)
        return {**_validation_projection(result), "version_status": stored.value.status.value, "revision": stored.revision}

    def test(self, tenant_id: str, workflow_id: str, version_id: str, actor_id: str, payload: Mapping[str, Any], correlation_id: str | None) -> dict[str, Any]:
        _fields(payload, {"fixture_reference", "inline_sample", "options"})
        if (payload.get("fixture_reference") is None) == (payload.get("inline_sample") is None):
            raise WorkflowStudioProviderError("invalid_preview_request", "Exactly one approved fixture reference or inline sample is required.")
        current = self._require_version(tenant_id, workflow_id, version_id)
        validation = self._validation.get((tenant_id, version_id)) or self.validator.validate(current.value, definition=self.store.get_definition(tenant_id, workflow_id).value)
        fixture = payload.get("fixture_reference")
        reference = None
        if fixture is not None:
            if not isinstance(fixture, Mapping):
                raise WorkflowStudioProviderError("invalid_preview_request", "Preview request is invalid.")
            _fields(fixture, {"fixture_id", "label"}, required={"fixture_id", "label"})
            reference = WorkflowPreviewFixtureReference(fixture["fixture_id"], fixture["label"])
        options = payload.get("options") or {}
        if not isinstance(options, Mapping):
            raise WorkflowStudioProviderError("invalid_preview_request", "Preview request is invalid.")
        _fields(options, {"allow_redacted_values"})
        try:
            command = WorkflowPreviewCommand(
                f"preview-{uuid4().hex}", tenant_id, workflow_id, version_id, actor_id,
                current.value, validation,
                WorkflowPreviewPolicy(True, allow_redacted_values=bool(options.get("allow_redacted_values", False))),
                WorkflowPreviewLimits(), _now(), reference, payload.get("inline_sample"), correlation_id,
            )
            result = self.preview.preview(command)
        except ValueError:
            raise WorkflowStudioProviderError("invalid_preview_request", "Preview sample or options are invalid.") from None
        self._audits.extend(result.audit_intents)
        self._preview_status[(tenant_id, version_id)] = result.status.value
        if result.status.value == "completed" and current.value.status is WorkflowVersionStatus.VALIDATED:
            transition = self.lifecycle.mark_test_passed(tenant_id, version_id, current.revision, test_passed=True, actor_id=actor_id, timestamp=_now())
            self._audits.extend(transition.audit_intents)
        # Audit intents are retained server-side; their tenant-scoped internals are
        # never serialized in the public preview response.
        projected = result.to_dict()
        projected.pop("audit_intents", None)
        return projected

    def submit(self, tenant_id: str, workflow_id: str, version_id: str, actor_id: str, correlation_id: str | None) -> dict[str, Any]:
        self._require_version(tenant_id, workflow_id, version_id)
        result = self.lifecycle.submit_for_approval(tenant_id, version_id, actor_id=actor_id, timestamp=_now(), correlation_id=correlation_id)
        if not result.succeeded:
            raise WorkflowStudioProviderError("invalid_transition", "Workflow version is not ready for submission.", status_code=409)
        self._audits.extend(result.audit_intents)
        return {"submitted": True, "version": self._version(result.version, detail=False)}

    def approve(self, tenant_id: str, workflow_id: str, version_id: str, actor_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        _fields(payload, {"expected_revision"}, required={"expected_revision"})
        current = self._require_version(tenant_id, workflow_id, version_id)
        if current.value.authored_by == actor_id:
            raise WorkflowStudioProviderError("reviewer_separation_required", "A workflow author cannot approve the same version.", status_code=409)
        if self._preview_status.get((tenant_id, version_id)) != "completed":
            raise WorkflowStudioProviderError("test_evidence_required", "Passing preview evidence is required.", status_code=409)
        try:
            result = self.lifecycle.approve_draft(tenant_id, version_id, payload["expected_revision"], approver_id=actor_id, timestamp=_now())
        except WorkflowRepositoryError:
            raise WorkflowStudioProviderError("revision_conflict", "Workflow version changed before approval.", status_code=409) from None
        if not result.succeeded:
            raise WorkflowStudioProviderError("invalid_transition", "Workflow version is not ready for approval.", status_code=409)
        self._audits.extend(result.audit_intents)
        return self._version(result.version, detail=False)

    def publish(self, tenant_id: str, workflow_id: str, version_id: str, actor_id: str, payload: Mapping[str, Any], correlation_id: str | None) -> dict[str, Any]:
        _fields(payload, {"publication_id", "expected_version_revision", "expected_definition_revision", "environment", "supersede_previous"}, required={"expected_version_revision", "expected_definition_revision"})
        current = self._require_version(tenant_id, workflow_id, version_id)
        definition = self.store.get_definition(tenant_id, workflow_id)
        validation = self.validator.validate(current.value, definition=definition.value, policy=ValidationPolicyFacts(test_evidence_passed=True, approval_evidence_present=True))
        command = PublicationCommand(
            tenant_id, workflow_id, version_id, payload.get("publication_id") or f"publication-{uuid4().hex}",
            payload.get("environment", "governance"), actor_id, payload["expected_version_revision"],
            payload["expected_definition_revision"], validation,
            self._preview_status.get((tenant_id, version_id)) == "completed",
            current.value.status is WorkflowVersionStatus.APPROVED and current.value.approved_by is not None,
            True, True, False, bool(payload.get("supersede_previous", True)), _now(), correlation_id,
        )
        result = self.publication.publish(command)
        self._audits.extend(result.audit_intents)
        if not result.published:
            raise WorkflowStudioProviderError("publication_rejected", "Workflow publication policy rejected the request.", status_code=409)
        return {"publication": _publication_projection(result.publication), "definition": self._definition(result.definition), "notice": GOVERNANCE_ONLY_NOTICE}

    def deactivate(self, tenant_id: str, workflow_id: str, actor_id: str, payload: Mapping[str, Any], correlation_id: str | None) -> dict[str, Any]:
        _fields(payload, {"expected_publication_revision", "expected_definition_revision"}, required={"expected_publication_revision", "expected_definition_revision"})
        result = self.publication.deactivate(tenant_id, workflow_id, actor_id=actor_id, occurred_at=_now(), expected_publication_revision=payload["expected_publication_revision"], expected_definition_revision=payload["expected_definition_revision"], correlation_id=correlation_id)
        self._audits.extend(result.audit_intents)
        if result.publication is None:
            raise WorkflowStudioProviderError("deactivation_rejected", "Active publication could not be deactivated.", status_code=409)
        return {"deactivated": True, "publication": _publication_projection(result.publication), "notice": GOVERNANCE_ONLY_NOTICE}

    def archive(self, tenant_id: str, workflow_id: str, actor_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        _fields(payload, {"expected_definition_revision"}, required={"expected_definition_revision"})
        result = self.publication.archive_definition(tenant_id, workflow_id, actor_id=actor_id, occurred_at=_now(), expected_definition_revision=payload["expected_definition_revision"])
        self._audits.extend(result.audit_intents)
        if result.definition is None or result.definition.value.status is not WorkflowDefinitionStatus.ARCHIVED:
            raise WorkflowStudioProviderError("archive_rejected", "Workflow cannot be archived in its current state.", status_code=409)
        return {"archived": True, "definition": self._definition(result.definition)}

    def _require_version(self, tenant_id: str, workflow_id: str, version_id: str):
        stored = self.store.get_version(tenant_id, version_id)
        if stored is None or stored.value.workflow_id != workflow_id:
            raise _not_found()
        return stored

    def _definition(self, stored, detail: bool = False) -> dict[str, Any]:
        value = stored.value
        row = {
            "workflow_id": value.workflow_id, "name": value.name, "description": value.description,
            "business_domain": value.business_domain, "document_type": value.document_type,
            "status": value.status.value, "current_draft_reference": _reference(value.current_draft_version),
            "active_published_reference": _reference(value.active_published_version),
            "created_at": value.created_at, "updated_at": value.updated_at,
            "ownership": {"created_by": value.ownership.created_by, "updated_by": value.ownership.updated_by},
            "revision": stored.revision,
        }
        return row

    def _version(self, stored, detail: bool) -> dict[str, Any]:
        value = stored.value
        row = {
            "version_id": value.version_id, "workflow_id": value.workflow_id, "version": value.version,
            "status": value.status.value, "derived_from_version_id": value.derived_from_version_id,
            "change_summary": value.change_summary.to_dict(), "authored_by": value.authored_by,
            "reviewed_by": value.reviewed_by, "approved_by": value.approved_by,
            "created_at": value.created_at, "updated_at": value.updated_at, "published_at": value.published_at,
            "revision": stored.revision,
            "validation_state": _validation_projection(self._validation[(stored.tenant_id, value.version_id)]) if (stored.tenant_id, value.version_id) in self._validation else None,
            "preview_state": self._preview_status.get((stored.tenant_id, value.version_id), "not_tested"),
        }
        if detail:
            row["rules"] = [rule.to_dict() for rule in value.rules]
            row["source_lineage"] = None if value.source_lineage is None else value.source_lineage.to_dict()
        return row

    @staticmethod
    def _audit_projection(item: Any) -> dict[str, Any]:
        return {
            "event_type": _audit_value(item, "event_type").value if hasattr(_audit_value(item, "event_type"), "value") else _audit_value(item, "event_type"),
            "workflow_id": _audit_value(item, "workflow_id"), "version_id": _audit_value(item, "version_id"),
            "publication_id": _audit_value(item, "publication_id"), "actor_label": _audit_value(item, "actor_id"),
            "status": _audit_value(item, "status"), "reason_code": _audit_value(item, "reason_code"),
            "timestamp": _audit_value(item, "occurred_at"), "correlation_id": _audit_value(item, "correlation_id"),
        }


def _rules(value: Any) -> tuple[RuleDefinition, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) > 100:
        raise ValueError("rules are invalid")
    return tuple(_rule(item) for item in value)


def _rule(value: Any) -> RuleDefinition:
    if not isinstance(value, Mapping):
        raise ValueError("rule is invalid")
    allowed = {"rule_id", "name", "stage", "description", "dependencies", "order", "enabled", "skip", "condition", "actions", "input_contract_hints", "output_contract_hints", "error_policy"}
    _fields(value, allowed, required={"rule_id", "name", "stage", "order", "actions"})
    return RuleDefinition(
        value["rule_id"], value["name"], value["stage"], value.get("description", ""), tuple(value.get("dependencies", ())),
        value["order"], value.get("enabled", True), value.get("skip", False), _condition(value.get("condition")),
        tuple(_action(item) for item in value["actions"]), tuple(value.get("input_contract_hints", ())), tuple(value.get("output_contract_hints", ())), value.get("error_policy", ActionErrorPolicy.FAIL_RULE),
    )


def _action(value: Any) -> ActionDefinition:
    if not isinstance(value, Mapping):
        raise ValueError("action is invalid")
    _fields(value, {"action_id", "action_type", "operation_name", "operation_version", "source_path", "target_path", "arguments", "error_policy", "output_policy", "enabled"}, required={"action_id", "action_type", "operation_name", "operation_version"})
    return ActionDefinition(value["action_id"], value["action_type"], value["operation_name"], value["operation_version"], value.get("source_path"), value.get("target_path"), value.get("arguments"), value.get("error_policy", ActionErrorPolicy.FAIL_RULE), value.get("output_policy", ActionOutputPolicy.REPLACE), value.get("enabled", True))


def _condition(value: Any):
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("condition is invalid")
    if "conditions" in value:
        _fields(value, {"operator", "conditions"}, required={"operator", "conditions"})
        return ConditionGroup(BooleanOperator(value["operator"]), tuple(_condition(item) for item in value["conditions"]))
    _fields(value, {"field_path", "operator", "value", "null_policy"}, required={"field_path", "operator"})
    return ConditionDefinition(value["field_path"], value["operator"], value.get("value"), value.get("null_policy", "reject"))


def _fields(value: Any, allowed: set[str], *, required: set[str] = frozenset()) -> None:
    if not isinstance(value, Mapping) or not set(value).issubset(allowed) or not required.issubset(value):
        raise WorkflowStudioProviderError("invalid_request", "Request body is invalid.")


def _validation_projection(result: Any) -> dict[str, Any]:
    return {
        "structurally_valid": result.structurally_valid,
        "dependency_valid": result.dependency_result.valid,
        "issues": [issue.to_dict() for issue in result.issues],
        "ordered_rule_ids": list(result.ordered_rule_ids),
        "preview_eligible": result.preview_eligible,
        "publication_eligible": result.publication_eligible,
        "blocked_reason_codes": [issue.code for issue in result.issues if issue.severity.value in {"error", "blocking"}],
    }


def _publication_projection(stored: Any) -> dict[str, Any]:
    value = stored.value
    return {"publication_id": value.publication_id, "workflow_id": value.workflow_id, "version_id": value.version_id, "status": value.status.value, "environment": value.environment, "created_at": value.created_at, "deactivated_at": value.deactivated_at, "revision": stored.revision}


def _reference(value: Any) -> dict[str, Any] | None:
    return None if value is None else value.to_dict()


def _audit_value(item: Any, name: str) -> Any:
    return item.get(name) if isinstance(item, Mapping) else getattr(item, name, None)


def _not_found() -> WorkflowStudioProviderError:
    return WorkflowStudioProviderError("workflow_not_found", "Workflow resource was not found.", status_code=404)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


empty_workflow_studio_provider = WorkflowStudioAPIProvider()
