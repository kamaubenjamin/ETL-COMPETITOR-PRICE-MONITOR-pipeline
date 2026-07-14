import pytest

from src.workflow_studio import (
    InMemoryWorkflowOperationCatalog,
    OperationAvailabilityStatus,
    OperationCategory,
    OperationDeterminism,
    OperationExecutionMode,
    StudioOperationDefinition,
)


EXPECTED = {
    "set", "remove_path", "append", "trim", "normalize", "uppercase", "lowercase",
    "concat", "split", "date_format", "regex_extract", "regex_mapper", "filter",
    "conditional_filter", "duplicate_remove", "required", "type_check", "regex_validate",
    "min_value", "max_value", "allowed_values", "unique", "fuzzy_match", "compare",
    "count", "sum", "average", "minimum", "maximum", "convert_units",
}


def test_catalog_contains_required_entries_in_stable_order() -> None:
    catalog = InMemoryWorkflowOperationCatalog()
    names = [item.name for item in catalog.list_operations()]
    assert set(names) == EXPECTED
    assert names == sorted(names)


def test_catalog_lookup_by_name_and_version_is_deterministic() -> None:
    catalog = InMemoryWorkflowOperationCatalog()
    assert catalog.get_operation("filter").version == "1"
    assert catalog.get_operation("filter", "1").runtime_operation == "filter"
    assert catalog.get_operation("filter", "2") is None
    assert catalog.get_operation("not_registered") is None


def test_unproven_operations_are_visibly_unavailable_and_unpublishable() -> None:
    catalog = InMemoryWorkflowOperationCatalog()
    unavailable = catalog.list_operations(availability=OperationAvailabilityStatus.UNAVAILABLE)
    assert len(unavailable) == 27
    assert all(not item.preview_eligible and not item.publication_eligible for item in unavailable)
    assert catalog.get_operation("trim").required_features == ("workflow_operation_compiler",)


def test_only_exact_proven_runtime_mappings_are_publication_eligible() -> None:
    eligible = [item.name for item in InMemoryWorkflowOperationCatalog().list_operations() if item.publication_eligible]
    assert eligible == ["compare", "filter", "fuzzy_match"]


def test_catalog_can_filter_by_category() -> None:
    names = {item.name for item in InMemoryWorkflowOperationCatalog().list_operations(category=OperationCategory.MATCHING)}
    assert names == {"compare", "fuzzy_match"}


def test_publication_eligibility_cannot_be_claimed_without_proven_mapping() -> None:
    with pytest.raises(ValueError):
        StudioOperationDefinition(
            "unsafe", "1", OperationCategory.TRANSFORMATION, "Unsafe claim",
            OperationAvailabilityStatus.AVAILABLE, OperationDeterminism.DETERMINISTIC,
            OperationExecutionMode.COMPILER, "transform", False, True, True,
        )
