import pandas as pd
import pandas.testing as pdt
import pytest

from src.transforms.errors import ConfigurationError
from src.transforms.sorting import sort_data


def _plan(keys):
    return {"contract_version": 1, "stable": True, "keys": keys}


def test_single_column_ascending_and_descending():
    frame = pd.DataFrame({"price": [3, 1, 2], "name": ["C", "A", "B"]})
    ascending = sort_data(frame, _plan([{"field": "price", "direction": "asc", "nulls": "last"}]))
    descending = sort_data(frame, _plan([{"field": "price", "direction": "desc", "nulls": "last"}]))
    assert ascending["price"].tolist() == [1, 2, 3]
    assert descending["price"].tolist() == [3, 2, 1]


def test_mixed_multi_column_sort_with_independent_null_placement():
    frame = pd.DataFrame(
        {
            "supplier": ["B", "A", "A", "B", None],
            "price": [2, None, 3, 1, 0],
            "row": [0, 1, 2, 3, 4],
        }
    )
    result = sort_data(
        frame,
        _plan(
            [
                {"field": "supplier", "direction": "asc", "nulls": "last"},
                {"field": "price", "direction": "desc", "nulls": "first"},
            ]
        ),
    )
    assert result["row"].tolist() == [1, 2, 0, 3, 4]


def test_sort_is_stable_for_equal_keys():
    frame = pd.DataFrame({"key": [1, 1, 1], "original_order": ["first", "second", "third"]})
    result = sort_data(frame, _plan([{"field": "key", "direction": "asc", "nulls": "last"}]))
    assert result["original_order"].tolist() == ["first", "second", "third"]


def test_null_placement_first_and_last():
    frame = pd.DataFrame({"value": [2, None, 1]})
    first = sort_data(frame, _plan([{"field": "value", "direction": "asc", "nulls": "first"}]))
    last = sort_data(frame, _plan([{"field": "value", "direction": "asc", "nulls": "last"}]))
    assert pd.isna(first["value"].iloc[0])
    assert pd.isna(last["value"].iloc[-1])


def test_missing_sort_field_fails_clearly():
    with pytest.raises(ConfigurationError) as caught:
        sort_data(
            pd.DataFrame({"present": [1]}),
            _plan([{"field": "missing", "direction": "asc", "nulls": "last"}]),
        )
    assert caught.value.code == "missing_column"
    assert caught.value.path == "$.keys[0].field"


@pytest.mark.parametrize(
    "key",
    [
        {"field": "value", "direction": "up", "nulls": "last"},
        {"field": "value", "direction": "asc", "nulls": "middle"},
        {"field": "value", "direction": "asc"},
    ],
)
def test_invalid_sort_options_fail_clearly(key):
    with pytest.raises(ConfigurationError):
        sort_data(pd.DataFrame({"value": [1]}), _plan([key]))


def test_empty_input_preserves_declared_columns():
    frame = pd.DataFrame({"price": pd.Series(dtype="float64"), "name": pd.Series(dtype="object")})
    result = sort_data(frame, _plan([{"field": "price", "direction": "asc", "nulls": "last"}]))
    assert result.empty
    assert result.columns.tolist() == ["price", "name"]


def test_sort_does_not_mutate_input_or_change_values_and_columns():
    source = pd.DataFrame({"price": [2, 1], "name": ["B", "A"]})
    original = source.copy(deep=True)
    result = sort_data(source, _plan([{"field": "price", "direction": "asc", "nulls": "last"}]))
    pdt.assert_frame_equal(source, original)
    assert result.columns.tolist() == source.columns.tolist()
    assert sorted(result["name"].tolist()) == sorted(source["name"].tolist())


def test_incompatible_sort_values_fail_without_exposing_values():
    secret = "private-value"
    frame = pd.DataFrame({"mixed": [1, secret]})
    with pytest.raises(ConfigurationError) as caught:
        sort_data(frame, _plan([{"field": "mixed", "direction": "asc", "nulls": "last"}]))
    assert caught.value.code == "incompatible_type"
    assert secret not in str(caught.value)

