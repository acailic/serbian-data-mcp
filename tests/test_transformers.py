"""Tests for data transformation functionality."""

from __future__ import annotations

import pytest
import pandas as pd
from serbian_data_mcp.data.transformers import (
    filter_data,
    group_data,
    aggregate_data,
    sort_data,
    select_columns,
    pivot_table,
    rename_columns,
    drop_columns,
    head,
    tail,
    describe_data,
    count_unique,
)


def test_sort_data_ascending():
    """Test sorting data in ascending order."""
    data = pd.DataFrame({"value": [30, 10, 20, 40]})

    result = sort_data(data, "value", ascending=True)

    assert list(result["value"]) == [10, 20, 30, 40]


def test_sort_data_descending():
    """Test sorting data in descending order."""
    data = pd.DataFrame({"value": [30, 10, 20, 40]})

    result = sort_data(data, "value", ascending=False)

    assert list(result["value"]) == [40, 30, 20, 10]


def test_sort_data_multiple_columns():
    """Test sorting by multiple columns."""
    data = pd.DataFrame({"category": ["A", "B", "A", "B"], "value": [20, 10, 30, 40]})

    result = sort_data(data, ["category", "value"], ascending=True)

    assert result.iloc[0]["category"] == "A"
    assert result.iloc[0]["value"] == 20


def test_sort_data_with_list():
    """Test sorting with list input."""
    data = [{"name": "C", "value": 30}, {"name": "A", "value": 10}, {"name": "B", "value": 20}]

    result = sort_data(data, "value", ascending=True)

    assert result.iloc[0]["name"] == "A"
    assert result.iloc[0]["value"] == 10


def test_select_columns():
    """Test selecting specific columns."""
    data = pd.DataFrame({"name": ["A", "B"], "value": [10, 20], "category": ["X", "Y"]})

    result = select_columns(data, ["name", "value"])

    assert "name" in result.columns
    assert "value" in result.columns
    assert "category" not in result.columns
    assert len(result.columns) == 2


def test_select_columns_with_list():
    """Test selecting columns from list input."""
    data = [{"name": "A", "value": 10, "extra": "data"}, {"name": "B", "value": 20, "extra": "more"}]

    result = select_columns(data, ["name", "value"])

    assert "name" in result.columns
    assert "value" in result.columns
    assert "extra" not in result.columns


def test_select_columns_nonexistent():
    """Test selecting columns that don't exist."""
    data = pd.DataFrame({"name": ["A", "B"], "value": [10, 20]})

    result = select_columns(data, ["name", "nonexistent"])

    # Should only include existing columns
    assert "name" in result.columns
    assert "nonexistent" not in result.columns


def test_aggregate_median():
    """Test median aggregation."""
    data = pd.DataFrame({"value": [10, 20, 30, 40, 50]})

    result = aggregate_data(data, "value", "median")

    assert result == 30.0


def test_aggregate_min_max():
    """Test min/max aggregation."""
    data = pd.DataFrame({"value": [10, 20, 30, 40, 50]})

    min_result = aggregate_data(data, "value", "min")
    max_result = aggregate_data(data, "value", "max")

    assert min_result == 10
    assert max_result == 50


def test_aggregate_count():
    """Test count aggregation."""
    data = pd.DataFrame({"value": [10, 20, 30, None, 50]})

    result = aggregate_data(data, "value", "count")

    assert result == 4  # None values are excluded


def test_aggregate_std_var():
    """Test standard deviation and variance aggregation."""
    data = pd.DataFrame({"value": [10, 20, 30, 40, 50]})

    std_result = aggregate_data(data, "value", "std")
    var_result = aggregate_data(data, "value", "var")

    assert std_result > 0
    assert var_result > 0


def test_group_data_with_aggregations():
    """Test grouping with custom aggregations."""
    data = pd.DataFrame({"category": ["A", "B", "A", "B"], "value": [10, 20, 30, 40]})

    result = group_data(data, "category", {"value": "sum"})

    assert "category" in result.columns
    assert len(result) == 2


def test_filter_data_with_multiple_filters():
    """Test filtering with multiple criteria."""
    data = pd.DataFrame(
        {
            "category": ["A", "B", "A", "C"],
            "value": [10, 20, 30, 40],
            "status": ["active", "inactive", "active", "active"],
        }
    )

    result = filter_data(data, {"category": "A", "status": "active"})

    assert len(result) == 2
    assert all(result["category"] == "A")
    assert all(result["status"] == "active")


def test_aggregate_data_invalid_column():
    """Test aggregation with non-existent column."""
    data = pd.DataFrame({"value": [10, 20, 30]})

    result = aggregate_data(data, "nonexistent", "sum")

    assert result is None


def test_filter_data_with_not_in_operator():
    """Test filtering with not_in operator."""
    data = pd.DataFrame({"category": ["A", "B", "C", "D"], "value": [10, 20, 30, 40]})

    result = filter_data(data, {"category": {"not_in": ["A", "B"]}})

    assert len(result) == 2
    assert all(result["category"].isin(["C", "D"]))


# -- Additional filter operator tests -----------------------------------------


def test_filter_operator_greater_than() -> None:
    """Test filter with > operator."""
    data = pd.DataFrame({"value": [10, 20, 30, 40]})
    result = filter_data(data, {"value": {">": 25}})
    assert len(result) == 2
    assert all(result["value"] > 25)


def test_filter_operator_less_than() -> None:
    """Test filter with < operator."""
    data = pd.DataFrame({"value": [10, 20, 30, 40]})
    result = filter_data(data, {"value": {"<": 25}})
    assert len(result) == 2
    assert all(result["value"] < 25)


def test_filter_operator_greater_equal() -> None:
    """Test filter with >= operator."""
    data = pd.DataFrame({"value": [10, 20, 30, 40]})
    result = filter_data(data, {"value": {">=": 20}})
    assert len(result) == 3


def test_filter_operator_less_equal() -> None:
    """Test filter with <= operator."""
    data = pd.DataFrame({"value": [10, 20, 30, 40]})
    result = filter_data(data, {"value": {"<=": 20}})
    assert len(result) == 2


def test_filter_operator_equals() -> None:
    """Test filter with == operator."""
    data = pd.DataFrame({"value": [10, 20, 30, 40]})
    result = filter_data(data, {"value": {"==": 20}})
    assert len(result) == 1
    assert result.iloc[0]["value"] == 20


def test_filter_operator_not_equals() -> None:
    """Test filter with != operator."""
    data = pd.DataFrame({"value": [10, 20, 30, 40]})
    result = filter_data(data, {"value": {"!=": 20}})
    assert len(result) == 3


def test_filter_operator_in() -> None:
    """Test filter with in operator using dict syntax."""
    data = pd.DataFrame({"category": ["A", "B", "C", "D"]})
    result = filter_data(data, {"category": {"in": ["A", "D"]}})
    assert len(result) == 2
    assert set(result["category"].tolist()) == {"A", "D"}


def test_filter_list_values() -> None:
    """Test filtering by passing a list directly (isin behavior)."""
    data = pd.DataFrame({"category": ["A", "B", "C", "D"]})
    result = filter_data(data, {"category": ["B", "C"]})
    assert len(result) == 2
    assert set(result["category"].tolist()) == {"B", "C"}


def test_filter_tuple_values() -> None:
    """Test filtering by passing a tuple directly (isin behavior)."""
    data = pd.DataFrame({"category": ["A", "B", "C"]})
    result = filter_data(data, {"category": ("A", "C")})
    assert len(result) == 2


def test_filter_nonexistent_column_ignored() -> None:
    """Filtering on a column that does not exist should return all rows."""
    data = pd.DataFrame({"value": [1, 2, 3]})
    result = filter_data(data, {"missing": "val"})
    assert len(result) == 3


def test_filter_empty_filters_returns_all() -> None:
    """Empty filter dict should return all rows."""
    data = pd.DataFrame({"value": [1, 2, 3]})
    result = filter_data(data, {})
    assert len(result) == 3


# -- Group data tests --------------------------------------------------------


def test_group_data_without_aggregations() -> None:
    """Group without aggregations should count rows per group."""
    data = pd.DataFrame({"cat": ["A", "B", "A", "B", "A"]})
    result = group_data(data, "cat")
    assert "count" in result.columns
    assert len(result) == 2
    assert result[result["cat"] == "A"]["count"].iloc[0] == 3


def test_group_data_multiple_group_by() -> None:
    """Group by multiple columns."""
    data = pd.DataFrame(
        {
            "cat": ["A", "A", "B", "B"],
            "sub": ["x", "y", "x", "y"],
            "value": [10, 20, 30, 40],
        }
    )
    result = group_data(data, ["cat", "sub"], {"value": "sum"})
    assert "cat" in result.columns
    assert "sub" in result.columns


def test_group_data_aggregation_missing_column() -> None:
    """Aggregation for a non-existent column raises when ALL are missing."""
    data = pd.DataFrame({"cat": ["A", "B"], "val": [1, 2]})
    with pytest.raises(ValueError):
        group_data(data, "cat", {"missing_col": "sum"})


# -- All 8 aggregation functions ----------------------------------------------


def test_aggregate_all_functions() -> None:
    """Verify all 8 aggregation functions return correct types/values."""
    data = pd.DataFrame({"value": [10, 20, 30, 40, 50]})
    assert aggregate_data(data, "value", "sum") == 150
    assert aggregate_data(data, "value", "mean") == 30.0
    assert aggregate_data(data, "value", "median") == 30.0
    assert aggregate_data(data, "value", "min") == 10
    assert aggregate_data(data, "value", "max") == 50
    assert aggregate_data(data, "value", "count") == 5
    assert isinstance(aggregate_data(data, "value", "std"), float)
    assert isinstance(aggregate_data(data, "value", "var"), float)


def test_aggregate_unknown_function_defaults_to_sum() -> None:
    """Unknown aggregation function should default to sum."""
    data = pd.DataFrame({"value": [10, 20]})
    result = aggregate_data(data, "value", "unknown_func")
    assert result == 30


# -- pivot_table --------------------------------------------------------------


def test_pivot_table_basic() -> None:
    data = pd.DataFrame(
        {
            "region": ["Београд", "Београд", "Нови Сад", "Нови Сад"],
            "year": [2020, 2021, 2020, 2021],
            "population": [100, 110, 80, 85],
        }
    )
    result = pivot_table(data, index="region", columns="year", values="population", aggfunc="sum")
    assert "region" in result.columns


def test_pivot_table_list_input() -> None:
    data = [
        {"region": "Београд", "year": 2020, "population": 100},
        {"region": "Београд", "year": 2021, "population": 110},
        {"region": "Нови Сад", "year": 2020, "population": 80},
    ]
    result = pivot_table(data, index="region", columns="year", values="population", aggfunc="mean")
    assert "region" in result.columns


def test_pivot_table_unknown_aggfunc_defaults_to_mean() -> None:
    data = pd.DataFrame(
        {
            "cat": ["A", "A", "B", "B"],
            "sub": ["x", "y", "x", "y"],
            "val": [1, 2, 3, 4],
        }
    )
    result = pivot_table(data, index="cat", columns="sub", values="val", aggfunc="nonsense")
    assert "cat" in result.columns


# -- rename_columns -----------------------------------------------------------


def test_rename_columns_basic() -> None:
    data = pd.DataFrame({"old_name": [1, 2], "keep": [3, 4]})
    result = rename_columns(data, {"old_name": "new_name"})
    assert "new_name" in result.columns
    assert "old_name" not in result.columns
    assert "keep" in result.columns


def test_rename_columns_nonexistent_ignored() -> None:
    data = pd.DataFrame({"a": [1]})
    result = rename_columns(data, {"missing": "new"})
    assert "a" in result.columns
    assert "new" not in result.columns


def test_rename_columns_list_input() -> None:
    data = [{"old": 1}]
    result = rename_columns(data, {"old": "new"})
    assert "new" in result.columns


# -- drop_columns -------------------------------------------------------------


def test_drop_columns_basic() -> None:
    data = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
    result = drop_columns(data, ["b"])
    assert "a" in result.columns
    assert "b" not in result.columns
    assert "c" in result.columns


def test_drop_columns_nonexistent_ignored() -> None:
    data = pd.DataFrame({"a": [1]})
    result = drop_columns(data, ["missing"])
    assert "a" in result.columns


def test_drop_columns_list_input() -> None:
    data = [{"a": 1, "b": 2}]
    result = drop_columns(data, ["b"])
    assert "b" not in result.columns


# -- head / tail ---------------------------------------------------------------


def test_head_default() -> None:
    data = pd.DataFrame({"value": range(20)})
    result = head(data)
    assert len(result) == 5


def test_head_custom_n() -> None:
    data = pd.DataFrame({"value": range(20)})
    result = head(data, n=3)
    assert len(result) == 3


def test_head_list_input() -> None:
    data = [{"value": i} for i in range(10)]
    result = head(data, n=2)
    assert len(result) == 2
    assert result.iloc[0]["value"] == 0


def test_tail_default() -> None:
    data = pd.DataFrame({"value": range(20)})
    result = tail(data)
    assert len(result) == 5
    assert result.iloc[-1]["value"] == 19


def test_tail_custom_n() -> None:
    data = pd.DataFrame({"value": range(20)})
    result = tail(data, n=2)
    assert len(result) == 2
    assert result.iloc[0]["value"] == 18


def test_tail_list_input() -> None:
    data = [{"value": i} for i in range(10)]
    result = tail(data, n=3)
    assert len(result) == 3


# -- describe_data ------------------------------------------------------------


def test_describe_data_basic() -> None:
    data = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [10, 20, 30, 40, 50]})
    result = describe_data(data)
    assert "count" in result.index
    assert "mean" in result.index
    assert "std" in result.index
    assert "a" in result.columns


def test_describe_data_list_input() -> None:
    data = [{"val": i} for i in range(10)]
    result = describe_data(data)
    assert "val" in result.columns


# -- count_unique --------------------------------------------------------------


def test_count_unique_basic() -> None:
    data = pd.DataFrame({"city": ["Београд", "Нови Сад", "Београд", "Ниш"]})
    result = count_unique(data, "city")
    assert "city" in result.columns
    assert "count" in result.columns
    assert len(result) == 3
    # Beograd should have count 2 (sorted desc)
    assert result.iloc[0]["count"] == 2


def test_count_unique_nonexistent_column() -> None:
    data = pd.DataFrame({"a": [1, 2]})
    result = count_unique(data, "missing")
    assert len(result) == 0
    assert "missing" in result.columns


def test_count_unique_list_input() -> None:
    data = [{"cat": "A"}, {"cat": "B"}, {"cat": "A"}]
    result = count_unique(data, "cat")
    assert len(result) == 2
