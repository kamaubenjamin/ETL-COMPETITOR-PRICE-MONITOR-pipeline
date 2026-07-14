import pytest
from src.workflow_studio import WorkflowPreviewFixtureReference,WorkflowPreviewLimits,WorkflowPreviewPolicy,WorkflowPreviewStatus

def test_status_catalog_is_fixed():
    assert [x.value for x in WorkflowPreviewStatus]==["accepted","validation_blocked","fixture_invalid","preview_unavailable","running","completed","completed_with_warnings","failed","limit_exceeded","cancelled"]
def test_fixture_reference_and_policy_serialize():
    assert WorkflowPreviewFixtureReference("fixture-1","safe_fixture").to_dict()=={"fixture_id":"fixture-1","label":"safe_fixture"}
    assert WorkflowPreviewPolicy(True,protected_fields=("customer_name",)).to_dict()["replacement_marker"]=="[REDACTED]"
def test_redaction_marker_cannot_be_client_defined():
    with pytest.raises(ValueError): WorkflowPreviewPolicy(True,replacement_marker="secret")
