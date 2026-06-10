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


# -- Additional chart tests ----------------------------------------------------


def test_line_chart_with_color_column(sample_data) -> None:
    """Line chart with color_column should group by color."""
    builder = ChartBuilder(sample_data)
    fig = builder.line_chart(x_column="year", y_column="population", color_column="category")
    assert fig is not None
    assert len(fig.data) > 0


def test_bar_chart_horizontal(sample_data) -> None:
    """Bar chart with horizontal orientation."""
    builder = ChartBuilder(sample_data)
    fig = builder.bar_chart(x_column="year", y_column="population", orientation="h")
    assert fig is not None


def test_bar_chart_with_color_column(sample_data) -> None:
    """Bar chart with color grouping."""
    builder = ChartBuilder(sample_data)
    fig = builder.bar_chart(x_column="year", y_column="population", color_column="category")
    assert fig is not None


def test_scatter_plot_with_color_and_size(sample_data) -> None:
    """Scatter plot with both color and size columns."""
    builder = ChartBuilder(sample_data)
    fig = builder.scatter_plot(
        x_column="year",
        y_column="population",
        color_column="category",
        size_column="population",
    )
    assert fig is not None


def test_histogram_custom_bins(sample_data) -> None:
    """Histogram with custom bin count."""
    builder = ChartBuilder(sample_data)
    fig = builder.histogram(column="population", bins=5)
    assert fig is not None


def test_histogram_without_bins(sample_data) -> None:
    """Histogram without explicit bins."""
    builder = ChartBuilder(sample_data)
    fig = builder.histogram(column="population")
    assert fig is not None


def test_box_plot_without_x_column(sample_data) -> None:
    """Box plot without x_column grouping."""
    builder = ChartBuilder(sample_data)
    fig = builder.box_plot(y_column="population")
    assert fig is not None


def test_box_plot_with_x_column(sample_data) -> None:
    """Box plot with x_column grouping."""
    builder = ChartBuilder(sample_data)
    fig = builder.box_plot(y_column="population", x_column="category")
    assert fig is not None


def test_pie_chart_with_title() -> None:
    """Pie chart with title."""
    data = pd.DataFrame({"grad": ["A", "B", "C"], "count": [10, 20, 30]})
    builder = ChartBuilder(data)
    fig = builder.pie_chart(values_column="count", names_column="grad", title="Grades")
    assert fig is not None


# -- Empty / minimal data handling ---------------------------------------------


def test_chart_with_single_row() -> None:
    """Charts should work with a single data point."""
    data = pd.DataFrame({"x": [1], "y": [10]})
    builder = ChartBuilder(data)
    fig = builder.bar_chart(x_column="x", y_column="y")
    assert fig is not None


def test_chart_with_many_columns_unused() -> None:
    """Extra columns should not affect chart creation."""
    data = pd.DataFrame({"x": [1, 2], "y": [10, 20], "z": [100, 200], "w": ["a", "b"]})
    builder = ChartBuilder(data)
    fig = builder.line_chart(x_column="x", y_column="y")
    assert fig is not None
