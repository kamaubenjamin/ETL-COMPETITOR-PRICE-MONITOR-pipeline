import pandas as pd
import pytest

from src.transforms.contracts import RegexDefinition
from src.transforms.errors import ConfigurationError
from src.transforms.regex_registry import RegexRegistry


def _registry() -> RegexRegistry:
    return RegexRegistry(
        [RegexDefinition(id="sku", pattern=r"(?P<sku>[A-Z]{2}-\d{3})", flags=("IGNORECASE",))]
    )


def test_registry_compiles_flags_and_exposes_groups():
    registry = _registry()
    assert registry.names == ("sku",)
    assert registry.compiled("sku").search("ab-123").group("sku") == "ab-123"


def test_registry_rejects_duplicate_patterns():
    definition = RegexDefinition(id="sku", pattern=r"(?P<sku>[A-Z]+)")
    with pytest.raises(ConfigurationError) as caught:
        RegexRegistry([definition, definition])
    assert caught.value.code == "duplicate_registration"


def test_registry_rejects_unknown_pattern_and_group():
    registry = _registry()
    with pytest.raises(ConfigurationError, match="Unknown regex definition"):
        registry.resolve("missing")
    with pytest.raises(ConfigurationError, match="no named group"):
        registry.validate_group("sku", "price")


def test_regex_mapping_extracts_named_group():
    result = _registry().map_series(pd.Series(["SKU AB-123", "cd-456"]), pattern_id="sku", group="sku")
    assert result.tolist() == ["AB-123", "cd-456"]


def test_regex_mapping_no_match_policies():
    series = pd.Series(["AB-123", "none"])
    registry = _registry()
    null_result = registry.map_series(series, pattern_id="sku", group="sku", on_no_match="null")
    keep_result = registry.map_series(series, pattern_id="sku", group="sku", on_no_match="keep")
    default_result = registry.map_series(series, pattern_id="sku", group="sku", on_no_match="default", default="UNKNOWN")
    assert pd.isna(null_result.iloc[1])
    assert keep_result.iloc[1] == "none"
    assert default_result.iloc[1] == "UNKNOWN"


def test_regex_mapping_fail_policy_is_privacy_safe():
    with pytest.raises(ConfigurationError) as caught:
        _registry().map_series(
            pd.Series(["private-unmatched-value"]), pattern_id="sku", group="sku", on_no_match="fail"
        )
    assert caught.value.code == "regex_no_match"
    assert "private-unmatched-value" not in str(caught.value)

