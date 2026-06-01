from pathlib import Path

from tests.contracts.utils import validate_example


def test_entityset_example_validates():
    schema = Path("docs/contracts/entity_runtime/EntitySet.schema.json")
    example = Path("docs/contracts/examples/entityset_example.json")
    validate_example(schema, example)
