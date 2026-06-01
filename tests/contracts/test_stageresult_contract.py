from pathlib import Path

from tests.contracts.utils import validate_example


def test_stageresult_example_validates():
    schema = Path("docs/contracts/workflow_runtime/StageResult.schema.json")
    example = Path("docs/contracts/examples/stageresult_example.json")
    validate_example(schema, example)
