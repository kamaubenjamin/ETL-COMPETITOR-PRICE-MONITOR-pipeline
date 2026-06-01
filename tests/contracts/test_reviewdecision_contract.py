from pathlib import Path

from tests.contracts.utils import validate_example


def test_reviewdecision_example_validates():
    schema = Path("docs/contracts/review_runtime/ReviewDecision.schema.json")
    example = Path("docs/contracts/examples/review_decision_example.json")
    validate_example(schema, example)
