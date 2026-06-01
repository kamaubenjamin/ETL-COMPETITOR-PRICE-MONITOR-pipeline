from pathlib import Path

from tests.contracts.utils import validate_example


def test_workflowartifact_example_validates():
    schema = Path("docs/contracts/workflow_runtime/WorkflowArtifact.schema.json")
    example = Path("docs/contracts/examples/workflowartifact_example.json")
    validate_example(schema, example)
