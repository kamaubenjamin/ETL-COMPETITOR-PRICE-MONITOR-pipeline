from pathlib import Path

from tests.contracts.utils import validate_example


def test_reviewrequest_example_validates():
    schema = Path("docs/contracts/review_runtime/ReviewRequest.schema.json")
    example = Path("docs/contracts/examples/review_request_example.json")
    validate_example(schema, example)
