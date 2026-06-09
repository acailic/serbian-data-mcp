"""Tests for data transformation functionality."""

import pytest
import pandas as pd
from serbian_data_mcp.data.transformers import filter_data, group_data, aggregate_data, sort_data, select_columns


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
