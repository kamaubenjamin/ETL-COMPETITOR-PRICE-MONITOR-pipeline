import pytest
from src.workflow_studio import WorkflowPreviewLimits

def test_limits_are_fixed_bounded_and_serializable():
    limits=WorkflowPreviewLimits(); assert limits.max_rules==100; assert limits.to_dict()["max_duration_ms"]==30000
@pytest.mark.parametrize("kwargs",[{"max_rules":0},{"max_rules":101},{"max_duration_ms":120001},{"max_nested_depth":11}])
def test_invalid_limits_rejected(kwargs):
    with pytest.raises(ValueError): WorkflowPreviewLimits(**kwargs)
