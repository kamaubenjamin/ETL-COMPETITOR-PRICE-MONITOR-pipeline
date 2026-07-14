import pytest
from src.workflow_studio import WorkflowPreviewLimits,normalize_preview_sample

def test_safe_fixture_normalized_immutably_without_mutating_caller():
    source={"invoice":{"total":10},"items":[{"sku":"A"}]}; normalized=normalize_preview_sample(source,WorkflowPreviewLimits()); assert normalized["items"][0]["sku"]=="A"; source["invoice"]["total"]=99; assert normalized["invoice"]["total"]==10
@pytest.mark.parametrize("value",[{"token":"secret"},{"file_path":"x"},{"payload":{"raw":1}},{"call":lambda:None},{"x":"a"*257}])
def test_unsafe_fixture_rejected(value):
    with pytest.raises(ValueError): normalize_preview_sample(value,WorkflowPreviewLimits())
def test_nested_and_oversized_collections_rejected():
    with pytest.raises(ValueError): normalize_preview_sample({"a":{"b":{"c":{"d":{"e":{"f":1}}}}}},WorkflowPreviewLimits())
    with pytest.raises(ValueError): normalize_preview_sample(list(range(101)),WorkflowPreviewLimits())
