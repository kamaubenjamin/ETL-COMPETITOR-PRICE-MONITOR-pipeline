from pathlib import Path

from tests.contracts.utils import validate_example


def test_matchset_example_validates():
    schema = Path("docs/contracts/matching_runtime/MatchSet.schema.json")
    example = Path("docs/contracts/examples/matchset_example.json")
    validate_example(schema, example)
