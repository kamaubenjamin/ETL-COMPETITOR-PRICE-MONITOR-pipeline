import pandas as pd
import pandas.testing as pdt
import pytest

from src.transforms.contracts import FieldMapping
from src.transforms.errors import ConfigurationError
from src.transforms.field_mapping import apply_field_mappings, validate_field_mappings


def test_mapping_applies_scalar_transforms_and_float_coercion():
    source = pd.DataFrame({"raw_price": [" 10.50 ", "20"]})
    mappings = (
        FieldMapping(
            source="raw_price", target="price", coerce="float",
            transforms=("trim",), on_error="fail",
        ),
    )
    result = apply_field_mappings(source, mappings)
    assert result["price"].tolist() == [10.5, 20.0]
    pdt.assert_frame_equal(source, pd.DataFrame({"raw_price": [" 10.50 ", "20"]}))


def test_mapping_scalar_transform_order_is_deterministic():
    source = pd.DataFrame({"name": ["  Acme   LTD "]})
    mapping = FieldMapping(
        source="name", target="canonical", transforms=("collapse_whitespace", "lower")
    )
    assert apply_field_mappings(source, (mapping,))["canonical"].iloc[0] == "acme ltd"


def test_required_mapping_rejects_missing_source_in_preflight():
    mapping = FieldMapping(source="missing", target="target", required=True)
    with pytest.raises(ConfigurationError) as caught:
        validate_field_mappings((mapping,), ("present",))
    assert caught.value.code == "missing_column"


def test_apply_field_mappings_enforces_required_source():
    mapping = FieldMapping(source="missing", target="target", required=True)
    with pytest.raises(ConfigurationError) as caught:
        apply_field_mappings(pd.DataFrame({"present": [1]}), (mapping,))
    assert caught.value.code == "missing_column"


def test_optional_missing_source_uses_default():
    source = pd.DataFrame({"name": ["a", "b"]})
    mapping = FieldMapping(source="missing", target="country", default="KE")
    assert apply_field_mappings(source, (mapping,))["country"].tolist() == ["KE", "KE"]


def test_null_source_values_use_default():
    source = pd.DataFrame({"country": [None, "UG"]})
    mapping = FieldMapping(source="country", target="country_code", default="KE")
    assert apply_field_mappings(source, (mapping,))["country_code"].tolist() == ["KE", "UG"]


def test_coercion_on_error_null():
    source = pd.DataFrame({"raw": ["10", "bad"]})
    mapping = FieldMapping(source="raw", target="number", coerce="float", on_error="null")
    result = apply_field_mappings(source, (mapping,))
    assert result["number"].iloc[0] == 10.0
    assert pd.isna(result["number"].iloc[1])


def test_coercion_on_error_default():
    source = pd.DataFrame({"raw": ["10", "bad"]})
    mapping = FieldMapping(source="raw", target="number", coerce="float", on_error="default", default=0)
    assert apply_field_mappings(source, (mapping,))["number"].tolist() == [10.0, 0.0]


def test_coercion_on_error_fail_is_privacy_safe():
    source = pd.DataFrame({"raw": ["secret-value"]})
    mapping = FieldMapping(source="raw", target="number", coerce="float", on_error="fail")
    with pytest.raises(ConfigurationError) as caught:
        apply_field_mappings(source, (mapping,))
    assert caught.value.code == "coercion_failed"
    assert "secret-value" not in str(caught.value)


def test_duplicate_mapping_targets_are_rejected():
    mappings = (
        FieldMapping(source="a", target="same"),
        FieldMapping(source="b", target="same"),
    )
    with pytest.raises(ConfigurationError, match="Duplicate field mapping target"):
        validate_field_mappings(mappings, ("a", "b"))
