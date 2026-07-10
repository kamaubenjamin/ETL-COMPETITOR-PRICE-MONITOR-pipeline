import pandas as pd
import pandas.testing as pdt
import pytest

from src.transforms.aggregation import aggregate_data
from src.transforms.errors import ConfigurationError


def _plan(aggregations, *, group_by=None, drop_null_groups=False):
    return {
        "contract_version": 1,
        "group_by": group_by or [],
        "aggregations": aggregations,
        "drop_null_groups": drop_null_groups,
    }


def test_dataset_level_count_sum_avg_min_max():
    frame = pd.DataFrame({"price": [10.0, 20.0, None], "product": ["A", "B", "C"]})
    result = aggregate_data(
        frame,
        _plan(
            [
                {"function": "count", "output": "row_count"},
                {"field": "price", "function": "count", "output": "price_count"},
                {"field": "price", "function": "sum", "output": "price_sum"},
                {"field": "price", "function": "avg", "output": "price_avg"},
                {"field": "price", "function": "min", "output": "price_min"},
                {"field": "price", "function": "max", "output": "price_max"},
            ]
        ),
    )
    assert result.to_dict("records") == [
        {"row_count": 3, "price_count": 2, "price_sum": 30.0, "price_avg": 15.0, "price_min": 10.0, "price_max": 20.0}
    ]


def test_grouped_aggregation_has_explicit_schema_and_order():
    frame = pd.DataFrame({"supplier": ["B", "A", "B"], "price": [3, 2, 1]})
    result = aggregate_data(
        frame,
        _plan(
            [
                {"function": "count", "output": "rows"},
                {"field": "price", "function": "sum", "output": "total"},
            ],
            group_by=["supplier"],
        ),
    )
    assert result.columns.tolist() == ["supplier", "rows", "total"]
    assert result.to_dict("records") == [
        {"supplier": "A", "rows": 1, "total": 2},
        {"supplier": "B", "rows": 2, "total": 4},
    ]


def test_multiple_group_keys_have_deterministic_order():
    frame = pd.DataFrame(
        {"supplier": ["B", "A", "A", "B"], "currency": ["USD", "USD", "KES", "KES"], "price": [4, 3, 2, 1]}
    )
    plan = _plan([{"field": "price", "function": "sum", "output": "total"}], group_by=["supplier", "currency"])
    first = aggregate_data(frame, plan)
    second = aggregate_data(frame, plan)
    pdt.assert_frame_equal(first, second)
    assert list(zip(first["supplier"], first["currency"])) == [("A", "KES"), ("A", "USD"), ("B", "KES"), ("B", "USD")]


def test_numeric_group_keys_sort_numerically():
    frame = pd.DataFrame({"group": [10, 2, 1], "value": [1, 1, 1]})
    result = aggregate_data(
        frame,
        _plan([{"field": "value", "function": "sum", "output": "total"}], group_by=["group"]),
    )
    assert result["group"].tolist() == [1, 2, 10]


def test_null_group_handling_is_explicit():
    frame = pd.DataFrame({"supplier": ["A", None, "A"], "price": [1, 2, 3]})
    keep = aggregate_data(
        frame,
        _plan([{"field": "price", "function": "sum", "output": "total"}], group_by=["supplier"], drop_null_groups=False),
    )
    drop = aggregate_data(
        frame,
        _plan([{"field": "price", "function": "sum", "output": "total"}], group_by=["supplier"], drop_null_groups=True),
    )
    assert len(keep) == 2
    assert pd.isna(keep["supplier"].iloc[-1])
    assert drop.to_dict("records") == [{"supplier": "A", "total": 4}]


def test_empty_dataset_level_aggregation_returns_one_deterministic_row():
    frame = pd.DataFrame({"price": pd.Series(dtype="float64")})
    result = aggregate_data(
        frame,
        _plan(
            [
                {"function": "count", "output": "rows"},
                {"field": "price", "function": "sum", "output": "total"},
                {"field": "price", "function": "avg", "output": "average"},
            ]
        ),
    )
    assert result.columns.tolist() == ["rows", "total", "average"]
    assert result["rows"].iloc[0] == 0
    assert pd.isna(result["total"].iloc[0])
    assert pd.isna(result["average"].iloc[0])


def test_empty_grouped_aggregation_returns_zero_rows_with_schema():
    frame = pd.DataFrame({"supplier": pd.Series(dtype="object"), "price": pd.Series(dtype="float64")})
    result = aggregate_data(
        frame,
        _plan([{"field": "price", "function": "sum", "output": "total"}], group_by=["supplier"]),
    )
    assert result.empty
    assert result.columns.tolist() == ["supplier", "total"]


@pytest.mark.parametrize(
    "plan",
    [
        _plan([{"field": "missing", "function": "sum", "output": "total"}]),
        _plan([{"function": "count", "output": "rows"}], group_by=["missing"]),
    ],
)
def test_missing_source_or_group_fields_fail(plan):
    with pytest.raises(ConfigurationError) as caught:
        aggregate_data(pd.DataFrame({"present": [1]}), plan)
    assert caught.value.code == "missing_column"


def test_unsupported_function_is_rejected_by_contract():
    with pytest.raises(ConfigurationError) as caught:
        aggregate_data(
            pd.DataFrame({"price": [1]}),
            _plan([{"field": "price", "function": "median", "output": "median_price"}]),
        )
    assert caught.value.code == "invalid_value"


def test_incompatible_sum_and_comparison_types_fail_safely():
    secret = "private-value"
    with pytest.raises(ConfigurationError) as sum_error:
        aggregate_data(
            pd.DataFrame({"value": [secret]}),
            _plan([{"field": "value", "function": "sum", "output": "total"}]),
        )
    assert sum_error.value.code == "incompatible_type"
    assert secret not in str(sum_error.value)

    with pytest.raises(ConfigurationError) as min_error:
        aggregate_data(
            pd.DataFrame({"value": [1, secret]}),
            _plan([{"field": "value", "function": "min", "output": "minimum"}]),
        )
    assert min_error.value.code == "incompatible_type"
    assert secret not in str(min_error.value)


def test_boolean_numeric_aggregation_and_unhashable_groups_fail():
    with pytest.raises(ConfigurationError) as bool_error:
        aggregate_data(
            pd.DataFrame({"flag": [True, False]}),
            _plan([{"field": "flag", "function": "sum", "output": "total"}]),
        )
    assert bool_error.value.code == "incompatible_type"

    with pytest.raises(ConfigurationError) as group_error:
        aggregate_data(
            pd.DataFrame({"group": [["A"], ["B"]], "value": [1, 2]}),
            _plan([{"field": "value", "function": "sum", "output": "total"}], group_by=["group"]),
        )
    assert group_error.value.code == "incompatible_type"


def test_aggregation_does_not_mutate_input():
    source = pd.DataFrame({"supplier": ["A", "A"], "price": [1, 2]})
    original = source.copy(deep=True)
    aggregate_data(
        source,
        _plan([{"field": "price", "function": "sum", "output": "total"}], group_by=["supplier"]),
    )
    pdt.assert_frame_equal(source, original)
