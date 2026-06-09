"""Tests for visualization functionality."""

import pytest
import pandas as pd
from serbian_data_mcp.viz import ChartBuilder


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    return pd.DataFrame(
        {"year": [2020, 2021, 2022, 2023], "population": [1000, 1100, 1200, 1300], "category": ["A", "B", "A", "B"]}
    )


def test_chart_builder_initialization(sample_data):
    """Test ChartBuilder initialization."""
    builder = ChartBuilder(sample_data)
    assert builder.data is not None
    assert len(builder.data) == 4


def test_chart_builder_with_list():
    """Test ChartBuilder with list of dictionaries."""
    data = [{"x": 1, "y": 10}, {"x": 2, "y": 20}]
    builder = ChartBuilder(data)
    assert len(builder.data) == 2


def test_line_chart(sample_data):
    """Test line chart creation."""
    builder = ChartBuilder(sample_data)
    fig = builder.line_chart(x_column="year", y_column="population", title="Population Over Time")

    assert fig is not None
    assert fig.layout.title.text == "Population Over Time"


def test_bar_chart(sample_data):
    """Test bar chart creation."""
    builder = ChartBuilder(sample_data)
    fig = builder.bar_chart(x_column="year", y_column="population", title="Population by Year")

    assert fig is not None
    assert len(fig.data) > 0


def test_pie_chart():
    """Test pie chart creation."""
    data = pd.DataFrame({"category": ["A", "B", "C"], "value": [10, 20, 30]})

    builder = ChartBuilder(data)
    fig = builder.pie_chart(values_column="value", names_column="category", title="Distribution")

    assert fig is not None


def test_scatter_plot(sample_data):
    """Test scatter plot creation."""
    builder = ChartBuilder(sample_data)
    fig = builder.scatter_plot(x_column="year", y_column="population", title="Population Scatter")

    assert fig is not None


def test_histogram(sample_data):
    """Test histogram creation."""
    builder = ChartBuilder(sample_data)
    fig = builder.histogram(column="population", title="Population Distribution", bins=10)

    assert fig is not None


def test_box_plot(sample_data):
    """Test box plot creation."""
    builder = ChartBuilder(sample_data)
    fig = builder.box_plot(y_column="population", x_column="category", title="Population by Category")

    assert fig is not None
