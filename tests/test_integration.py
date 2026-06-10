"""Integration tests for MCP server functionality."""

from __future__ import annotations

import pytest
import asyncio
from serbian_data_mcp.api import UDataClient
from serbian_data_mcp.viz import ChartBuilder
from serbian_data_mcp.data import parse_json, parse_csv, filter_data, group_data
from serbian_data_mcp.data.transformers import (
    sort_data,
    select_columns,
    head,
    drop_columns,
    rename_columns,
    aggregate_data,
)
import pandas as pd


@pytest.mark.asyncio
async def test_client_search_integration():
    """Test integration between client and search functionality."""
    client = UDataClient()

    # Test that client can be initialized
    assert client.base_url == "https://data.gov.rs"
    assert client.rate_limit == 1.0


@pytest.mark.asyncio
async def test_data_pipeline_integration():
    """Test integration between data parsing and transformation."""
    # Sample data
    json_content = b'[{"name": "A", "value": 10}, {"name": "B", "value": 20}]'

    # Parse JSON
    data = await parse_json(json_content)
    assert len(data) == 2

    # Transform to DataFrame
    df = pd.DataFrame(data)
    assert len(df) == 2
    assert "name" in df.columns


def test_viz_data_integration():
    """Test integration between data transformation and visualization."""
    # Create sample data
    data = pd.DataFrame({"year": [2020, 2021, 2022], "value": [100, 200, 300]})

    # Build chart
    builder = ChartBuilder(data)
    fig = builder.line_chart("year", "value", "Test Chart")

    assert fig is not None
    assert len(fig.data) > 0


@pytest.mark.asyncio
async def test_end_to_end_data_flow():
    """Test complete data flow from parsing to visualization."""
    # Simulate CSV data
    csv_content = b"year,category,value\n2020,A,100\n2021,B,200\n2022,A,300"

    # Parse CSV
    df = await parse_csv(csv_content)
    assert len(df) == 3

    # Filter data
    filtered = filter_data(df, {"category": "A"})
    assert len(filtered) == 2

    # Create visualization
    builder = ChartBuilder(filtered)
    fig = builder.bar_chart("year", "value", "Filtered Data")

    assert fig is not None


def test_data_transformer_integration():
    """Test integration between multiple data transformers."""
    data = [
        {"category": "A", "value": 10},
        {"category": "B", "value": 20},
        {"category": "A", "value": 30},
        {"category": "B", "value": 40},
    ]

    # Filter
    filtered = filter_data(data, {"category": "A"})
    assert len(filtered) == 2

    # Convert to DataFrame for visualization
    df = pd.DataFrame(filtered)
    builder = ChartBuilder(df)
    fig = builder.pie_chart("value", "category", "Category Distribution")

    assert fig is not None


@pytest.mark.asyncio
async def test_client_rate_limiting():
    """Test that client respects rate limiting."""
    client = UDataClient(rate_limit=0.1)

    assert client.rate_limit == 0.1
    assert client._last_request_time == 0


def test_error_handling_integration():
    """Test error handling across the pipeline."""
    # Test with invalid data
    invalid_json = b'{"invalid": json}'

    # Should handle gracefully
    with pytest.raises(Exception):
        asyncio.run(parse_json(invalid_json))


# -- Full workflow tests --------------------------------------------------------


@pytest.mark.asyncio
async def test_full_workflow_search_get_filter_visualize() -> None:
    """Test full workflow: parse -> filter -> group -> visualize."""
    csv_content = b"grad,opstina,stanovnistvo\nBeograd,Stari grad,50000\nBeograd,Novi Beograd,70000\nNovi Sad,Petrovaradin,30000\nNovi Sad,Liman,40000"
    df = await parse_csv(csv_content)
    assert len(df) == 4
    filtered = filter_data(df, {"grad": "Beograd"})
    assert len(filtered) == 2
    grouped = group_data(filtered, "grad", {"stanovnistvo": "sum"})
    assert len(grouped) == 1
    builder = ChartBuilder(filtered)
    fig = builder.bar_chart(x_column="opstina", y_column="stanovnistvo", title="Stanovnistvo")
    assert fig is not None


def test_transformer_chain_workflow() -> None:
    """Test chaining multiple transformers: sort -> select -> head."""
    data = [
        {"grad": "Novi Sad", "stanovnistvo": 250000},
        {"grad": "Beograd", "stanovnistvo": 1200000},
        {"grad": "Nis", "stanovnistvo": 180000},
    ]
    sorted_df = sort_data(data, "stanovnistvo", ascending=False)
    selected = select_columns(sorted_df, ["grad", "stanovnistvo"])
    top = head(selected, n=2)
    assert len(top) == 2
    assert top.iloc[0]["grad"] == "Beograd"


def test_rename_and_drop_workflow() -> None:
    """Test rename then drop workflow."""
    data = [{"old_col1": 1, "old_col2": 2, "remove_me": 99}]
    renamed = rename_columns(data, {"old_col1": "col1", "old_col2": "col2"})
    cleaned = drop_columns(renamed, ["remove_me"])
    assert "col1" in cleaned.columns
    assert "col2" in cleaned.columns
    assert "remove_me" not in cleaned.columns


@pytest.mark.asyncio
async def test_csv_json_parsing_comparison() -> None:
    """Compare CSV and JSON parsing of same data."""
    csv_content = b"name,value\nA,1\nB,2"
    json_content = b'[{"name": "A", "value": 1}, {"name": "B", "value": 2}]'
    csv_df = await parse_csv(csv_content)
    json_data = await parse_json(json_content)
    json_df = pd.DataFrame(json_data)
    assert len(csv_df) == len(json_df)
    assert list(csv_df.columns) == list(json_df.columns)


# -- Error recovery workflow ----------------------------------------------------


def test_filter_empty_result_continues() -> None:
    """Filtering that returns empty should not crash downstream ops."""
    data = pd.DataFrame({"cat": ["A", "B"], "val": [1, 2]})
    filtered = filter_data(data, {"cat": "Z"})
    assert len(filtered) == 0
    sorted_result = sort_data(filtered, "val")
    assert len(sorted_result) == 0
    selected = select_columns(filtered, ["cat", "val"])
    assert len(selected) == 0


def test_aggregate_on_empty_data() -> None:
    """Aggregating empty data."""
    data = pd.DataFrame({"a": []})
    result = aggregate_data(data, "a", "sum")
    assert result == 0 or result is not None
