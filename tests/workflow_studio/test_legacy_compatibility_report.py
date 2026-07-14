import pytest

from src.workflow_studio import (
    LegacyActionDescriptor,
    LegacyRuleDescriptor,
    LegacyWorkflowDescriptor,
    generate_legacy_compatibility_report,
)


def descriptor(*labels: str) -> LegacyWorkflowDescriptor:
    actions = tuple(LegacyActionDescriptor(f"action-{index}", label) for index, label in enumerate(labels))
    rule = LegacyRuleDescriptor("rule-1", "legacy", "", (), False, None, actions)
    return LegacyWorkflowDescriptor("sanifu", "template-1", "invoice_flow", (rule,), {"owner": "migration"})


def test_exact_proven_legacy_mappings_are_supported() -> None:
    report = generate_legacy_compatibility_report(descriptor("filter", "fuzzy_match"))
    assert [item.status.value for item in report.operations] == ["supported", "supported"]
    assert [item.candidate_operation for item in report.operations] == ["filter", "fuzzy_match"]
    assert not report.manual_review_required


def test_partial_mappings_identify_candidate_and_missing_proof() -> None:
    report = generate_legacy_compatibility_report(descriptor("strtoupper", "convert_units_v2"))
    assert [item.candidate_operation for item in report.operations] == ["uppercase", "convert_units"]
    assert all(item.status.value == "partially_supported" for item in report.operations)
    assert all(item.missing_runtime_or_compiler_proof for item in report.operations)


def test_generic_wrappers_require_manual_review() -> None:
    report = generate_legacy_compatibility_report(descriptor("function", "transform"))
    assert report.overall_status.value == "manual_review_required"
    assert {item.reason_code for item in report.operations} == {"generic_wrapper_requires_review"}


def test_semantic_and_external_operations_are_unsupported_with_safe_features() -> None:
    report = generate_legacy_compatibility_report(descriptor("semantic_search", "get_master_data"))
    assert report.overall_status.value == "unsupported"
    assert report.operations[0].required_features == ("semantic_search_port",)
    assert report.operations[1].required_features == ("master_data_port",)


def test_report_preserves_safe_lineage_and_never_produces_executable_conversion() -> None:
    report = generate_legacy_compatibility_report(descriptor("filter"))
    payload = report.to_dict()
    assert payload["source_system"] == "sanifu"
    assert payload["source_reference"] == "template-1"
    assert payload["executable_conversion_produced"] is False
    assert "workflow_version" not in payload


def test_legacy_descriptor_rejects_raw_code_configuration() -> None:
    with pytest.raises(ValueError):
        LegacyActionDescriptor("action-1", "function", {"source_code": "return secret"})
