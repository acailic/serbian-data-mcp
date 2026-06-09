"""Integration tests for MCP server functionality."""

import pytest
import asyncio
from serbian_data_mcp.api import UDataClient
from serbian_data_mcp.viz import ChartBuilder
from serbian_data_mcp.data import parse_json, parse_csv, filter_data
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
