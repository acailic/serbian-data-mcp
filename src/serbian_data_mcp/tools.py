"""MCP tool, resource, and prompt definitions for Serbian Data MCP Server.

This module registers all MCP capabilities on the FastMCP server instance.

The Serbian open data portal (data.gov.rs) hosts 3400+ datasets from 180+
organizations covering demographics, public budgets, education, health,
air quality monitoring, transport, real estate, and government registries.
Data is available in JSON, CSV, XLSX, XLS, and XML formats.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Any, Optional, Union

import pandas as pd

from . import mcp
from .api.client import UDataClient
from .api.models import Dataset, Organization, SearchResult
from .catalog import DatasetCatalog, SearchEngine, AlternativeSuggestions, DatasetPreview
from .catalog.exceptions import DatasetNotFound
from .config import config
from .data.transformers import aggregate_data, filter_data, group_data, select_columns, sort_data
from .exceptions import VisualizationError
from .viz.charts import ChartBuilder
from .viz.exporters import export_html, export_json, fig_to_dict
from .viz.themes import apply_theme, add_annotation, add_highlight_zone
from .viz.advanced_charts import AdvancedChartBuilder
from .viz.insights import extract_insights, generate_narrative, compute_derived_metrics
from .viz.infographics import create_infographic, create_dashboard
from .viz.maps import SerbiaMapBuilder
from .viz.special_charts import arrow_chart, dumbbell_chart, lollipop_chart
from .viz.tooltips import add_rich_tooltips, add_annotation_callouts, add_comparison_markers
from .viz.datawrapper_export import DatawrapperExporter
from .viz.animations import animated_timeline, animated_bars_evolution, animated_comparison
from .viz.scrollytelling import scrollytelling
from .viz.novel_charts import slope_chart, waffle_chart, population_pyramid, sankey_diagram, radar_chart
from .viz.map_advanced import AdvancedMapBuilder
from .viz.data_tables import data_table_html, data_table_css
from .viz.forecast import forecast_linear, benchmark_comparison, cross_dataset_insights
from .viz.exporters import export_pdf, generate_embed_code

logger = logging.getLogger(__name__)

_client: Optional[UDataClient] = None


def _reset_client():
    """Reset the shared client (needed when event loops change)."""
    global _client
    _client = None


async def _get_client() -> UDataClient:
    """Get or create a shared API client."""
    global _client
    # Always create a fresh client to avoid event loop reuse issues
    _client = UDataClient()
    return _client


def _dataset_to_dict(ds: Dataset) -> dict[str, Any]:
    """Convert a Dataset to a JSON-serialisable dict with all available fields."""
    org = None
    if ds.organization:
        org = _org_to_dict(ds.organization)
    resources = []
    for r in ds.resources:
        resources.append(
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "format": r.format,
                "url": r.url,
                "size": r.size,
                "mime_type": r.mime_type,
                "checksum": r.checksum,
            }
        )
    return {
        "id": ds.id,
        "title": ds.title,
        "description": ds.description,
        "organization": org,
        "resources": resources,
        "tags": ds.tags,
        "created_at": ds.created_at.isoformat() if ds.created_at else None,
        "modified_at": ds.modified_at.isoformat() if ds.modified_at else None,
        "frequency": ds.frequency,
        "temporal_coverage": ds.temporal_coverage,
        "spatial_coverage": ds.spatial_coverage,
        "license": ds.license,
        # Extended fields (from raw API data when available via getattr)
        "slug": getattr(ds, "slug", None),
        "page": getattr(ds, "page", None),
        "uri": getattr(ds, "uri", None),
        "quality": getattr(ds, "quality", None),
        "metrics": getattr(ds, "metrics", None),
        "acronym": getattr(ds, "acronym", None),
        "badges": getattr(ds, "badges", []),
    }


def _result_to_dict(result: SearchResult) -> dict[str, Any]:
    """Convert a SearchResult to a JSON-serialisable dict."""
    return {
        "datasets": [_dataset_to_dict(ds) for ds in result.datasets],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
        "has_next": result.has_next,
        "has_previous": result.has_previous,
    }


def _org_to_dict(org: Organization) -> dict[str, Any]:
    """Convert an Organization to a JSON-serialisable dict."""
    return {"id": org.id, "name": org.name, "description": org.description, "url": org.url, "logo": org.logo}


def _dataframe_to_dict(df: Union[pd.DataFrame, Any]) -> dict[str, Any]:
    """Convert a DataFrame or list-of-dicts to JSON-serialisable structure."""
    if isinstance(df, pd.DataFrame):
        return {"data": df.to_dict(orient="records"), "columns": list(df.columns), "rows": len(df)}
    if isinstance(df, list):
        return {"data": df, "rows": len(df)}
    return {"data": df}


# =========================================================================
# Search tools
# =========================================================================


@mcp.tool()
async def search_datasets(
    query: str = "",
    format: Optional[str] = None,
    organization: Optional[str] = None,
    page_size: int = 10,
    page: int = 1,
) -> dict[str, Any]:
    """Search for datasets on the Serbian open data portal (data.gov.rs).

    The portal contains 3400+ datasets from 180+ organizations covering topics like:
    population demographics, public budgets, education, health, air quality monitoring,
    transport statistics, real estate prices, and government registries.

    Use this tool FIRST to discover datasets. Results include dataset IDs needed for get_dataset().

    Common search queries (Serbian and English both work):
    - "stanovništvo" or "population" — demographic and census data
    - "budžet" or "budget" — government budgets and financial reports
    - "vazduh" or "air quality" — air pollution monitoring data
    - "saobraćaj" or "transport" — traffic, roads, public transit statistics
    - "obrazovanje" or "education" — school and university data
    - "cene" or "prices" — consumer prices, inflation data
    - "nekretnine" or "real estate" — property prices
    - "Zavod za statistiku" or "RZS" — statistical bureau datasets
    - "registar" — public registries (companies, vehicles, etc.)

    After finding datasets, use get_dataset(dataset_id) for full details and
    get_resource_data(resource_id) to download actual data. Use get_dataset_resources()
    to list available files before downloading.

    To search by tags specifically, use the search_by_tag() tool which joins tag names
    as a search query for broader topic-level discovery.

    To discover recently added/updated datasets, use browse_recent_datasets().

    Args:
        query: Search terms (Serbian or English). Empty string returns newest datasets.
        format: Filter by data format: json, csv, xlsx, xls, xml
        organization: Filter by organization ID (obtain via list_organizations)
        page_size: Results per page (1-100, default 10)
        page: Page number (1-indexed)

    Returns: Dict with 'datasets' (list), 'total', 'page', 'page_size', 'total_pages', 'has_next'
    """
    client = await _get_client()
    result = await client.search_datasets(
        query=query,
        format=format,
        organization=organization,
        page_size=min(max(page_size, 1), 100),
        page=max(page, 1),
    )
    return _result_to_dict(result)


@mcp.tool()
async def suggest_datasets(query: str, format: Optional[str] = None, size: int = 10) -> dict[str, Any]:
    """Get autocomplete suggestions for dataset search queries on data.gov.rs.

    Use this when you're unsure about the exact Serbian terms to search for.
    Returns up to 20 matching dataset titles. Useful for discovering dataset names
    before running a full search_datasets() query.

    Example: suggest_datasets("stanov") → ["Stanovništvo Republike Srbije", ...]

    Args:
        query: Partial search text (at least 2 characters recommended)
        format: Optionally filter by data format: json, csv, xlsx, xls, xml
        size: Number of suggestions to return (1-20, default 10)
    """
    client = await _get_client()
    suggestions = await client.suggest_datasets(query, format=format, size=min(max(size, 1), 20))
    return {"suggestions": suggestions, "count": len(suggestions)}


@mcp.tool()
async def list_organizations(page_size: int = 50, page: int = 1) -> dict[str, Any]:
    """List all organizations that publish datasets on the Serbian data portal.

    The portal has 180+ organizations including government ministries, statistical
    offices, public health institutes, municipal governments, and agencies.

    Key organizations to look for:
    - РЗС (Републички завод за статистику) — Statistical Office of the Republic of Serbia
    - Министарство финансија — Ministry of Finance
    - Завод за јавно здравље — Public Health Institute (air quality data)
    - Various city and municipal governments

    Use the returned organization IDs as the 'organization' parameter in search_datasets()
    to filter results by a specific publisher.

    Args:
        page_size: Results per page (1-100, default 50)
        page: Page number (1-indexed)

    Returns: Dict with 'organizations' (list of org dicts with id, name, description, url, logo),
             'count', 'page', 'page_size'
    """
    client = await _get_client()
    orgs = await client.list_organizations(page_size=min(max(page_size, 1), 100), page=max(page, 1))
    return {
        "organizations": [_org_to_dict(org) for org in orgs],
        "count": len(orgs),
        "page": page,
        "page_size": page_size,
    }


# =========================================================================
# Data retrieval tools
# =========================================================================


@mcp.tool()
async def get_dataset(dataset_id: str) -> dict[str, Any]:
    """Get complete details for a specific dataset by its ID.

    Use after search_datasets() to get full metadata including:
    - Description, tags, license, update frequency
    - Organization info (publisher name, URL)
    - List of resources (data files) with formats and URLs
    - Temporal and spatial coverage

    The returned 'resources' list contains resource IDs needed for get_resource_data().
    For a cleaner resource listing with just IDs, titles, and formats, use get_dataset_resources().

    Args:
        dataset_id: Dataset identifier (from search_datasets results)

    Returns: Full dataset dict with id, title, description, organization, resources, tags,
             created_at, modified_at, frequency, temporal_coverage, spatial_coverage, license
    """
    client = await _get_client()
    dataset = await client.get_dataset(dataset_id)
    if dataset is None:
        return {"error": True, "message": f"Dataset '{dataset_id}' not found"}
    return _dataset_to_dict(dataset)


@mcp.tool()
async def get_resource_data(resource_id: str) -> dict[str, Any]:
    """Download and parse the data file for a specific resource from data.gov.rs.

    This is the main tool for getting actual data (not just metadata). It downloads
    the file and parses it based on format:
    - JSON → parsed as list of dicts
    - CSV/XLSX/XLS → parsed as DataFrame, converted to list of records
    - XML → parsed and returned as dict/list

    Resource IDs come from get_dataset() or get_dataset_resources() results.
    After getting data, use data_profile() to understand columns and types,
    then filter_data_tool() / group_data_tool() for transformations,
    and create_visualization() for charts.

    Args:
        resource_id: Resource identifier (from dataset's resources list)

    Returns: Dict with 'data' (list of row dicts), plus 'columns' and 'rows' for tabular data.
             On error: {'error': True, 'message': '...'}
    """
    client = await _get_client()
    try:
        data = await client.get_resource_data(resource_id)
        if isinstance(data, pd.DataFrame):
            return _dataframe_to_dict(data)
        if isinstance(data, (dict, list)):
            return {"data": data}
        return {"data": str(data)}
    except Exception as e:
        return {"error": True, "message": str(e)}


# =========================================================================
# Visualization tools
# =========================================================================


@mcp.tool()
async def create_visualization(
    data: list[dict[str, Any]],
    chart_type: str = "line",
    x_column: Optional[str] = None,
    y_column: Optional[str] = None,
    values_column: Optional[str] = None,
    names_column: Optional[str] = None,
    color_column: Optional[str] = None,
    size_column: Optional[str] = None,
    title: str = "",
    orientation: str = "v",
    bins: Optional[int] = None,
) -> dict[str, Any]:
    """Create an interactive chart from data using Plotly.

    Generates publication-quality interactive charts that can be exported to HTML.
    Use AFTER get_resource_data() and ideally after data_profile() to know column names.

    Supported chart types and their required parameters:
    - "line": needs x_column + y_column → time series, trends
    - "bar": needs x_column + y_column → comparisons, rankings
    - "pie": needs values_column + names_column → proportions, distributions
    - "scatter": needs x_column + y_column → correlations
    - "histogram": needs x_column OR y_column → frequency distributions
    - "box": needs y_column (+ optional x_column) → statistical distributions

    Tip: Use data_profile() first to see available columns and their types.
    This helps you choose the right x_column and y_column.

    Args:
        data: List of row dicts (from get_resource_data)
        chart_type: One of: line, bar, pie, scatter, histogram, box
        x_column: Column name for x-axis (line, bar, scatter, histogram)
        y_column: Column name for y-axis (line, bar, scatter, box)
        values_column: Column with numeric values (pie charts)
        names_column: Column with category labels (pie charts)
        color_column: Optional column for color grouping
        size_column: Optional column for bubble sizes (scatter only)
        title: Chart title (defaults to chart_type name)
        orientation: Bar orientation: "v" (vertical) or "h" (horizontal)
        bins: Number of bins for histograms (default auto)

    Returns: Dict with 'figure' (Plotly spec), 'type', 'interactive', 'chart_type', 'title'
    """
    valid_types = {"line", "bar", "pie", "scatter", "histogram", "box"}
    if chart_type not in valid_types:
        raise VisualizationError(
            chart_type, f"Unsupported chart type '{chart_type}'. Use: {', '.join(sorted(valid_types))}"
        )
    builder = ChartBuilder(data)
    fig = None
    if chart_type == "line":
        if not x_column or not y_column:
            raise VisualizationError(chart_type, "line chart requires x_column and y_column")
        fig = builder.line_chart(x_column, y_column, title=title, color_column=color_column)
    elif chart_type == "bar":
        if not x_column or not y_column:
            raise VisualizationError(chart_type, "bar chart requires x_column and y_column")
        fig = builder.bar_chart(x_column, y_column, title=title, color_column=color_column, orientation=orientation)
    elif chart_type == "pie":
        if not values_column or not names_column:
            raise VisualizationError(chart_type, "pie chart requires values_column and names_column")
        fig = builder.pie_chart(values_column, names_column, title=title)
    elif chart_type == "scatter":
        if not x_column or not y_column:
            raise VisualizationError(chart_type, "scatter plot requires x_column and y_column")
        fig = builder.scatter_plot(x_column, y_column, title=title, color_column=color_column, size_column=size_column)
    elif chart_type == "histogram":
        col = x_column or y_column
        if not col:
            raise VisualizationError(chart_type, "histogram requires x_column or y_column")
        fig = builder.histogram(col, title=title, bins=bins)
    elif chart_type == "box":
        if not y_column:
            raise VisualizationError(chart_type, "box plot requires y_column")
        fig = builder.box_plot(y_column, x_column=x_column, title=title)
    if fig is None:
        raise VisualizationError(chart_type, "Failed to create chart")
    return {"figure": fig_to_dict(fig), "type": "plotly", "interactive": True, "chart_type": chart_type, "title": title}


# =========================================================================
# Advanced visualization tools
# =========================================================================


@mcp.tool()
async def create_advanced_visualization(
    data: list[dict[str, Any]],
    chart_type: str = "heatmap",
    x_column: str = "",
    y_column: str = "",
    z_column: str = "",
    names_column: str = "",
    values_column: str = "",
    color_column: Optional[str] = None,
    hierarchy_column: Optional[str] = None,
    title: str = "",
    theme: str = "dark",
    value: Optional[float] = None,
    min_val: float = 0,
    max_val: float = 100,
    label: str = "",
    frame_column: str = "",
    category_column: Optional[str] = None,
    comparison_columns: Optional[list[str]] = None,
    trend_column: str = "",
    top_n: int = 10,
) -> dict[str, Any]:
    """Create advanced visualizations: heatmap, treemap, gauge, funnel, animated line, comparison, sparklines.

    Beyond the basic 6 chart types, these advanced visualizations are designed for
    data journalism impact and storytelling. Each supports custom theming.

    Supported chart types and their parameters:
    - "heatmap": needs x_column + y_column + z_column → air quality grid, correlation matrix
    - "treemap": needs names_column + values_column → budget breakdown, nested categories
    - "gauge": needs value (float) → target vs actual, scores (0-100 scale)
    - "funnel": needs labels_column (use names_column) + values_column → budget flow, cascading values
    - "animated_line": needs x_column + y_column + frame_column → animated time-series playback
    - "comparison_bar": needs x_column + comparison_columns (list of 2) → side-by-side comparison
    - "sparklines": needs x_column + y_column + trend_column → faceted mini-charts per entity

    Args:
        data: List of row dicts
        chart_type: One of: heatmap, treemap, gauge, funnel, animated_line, comparison_bar, sparklines
        theme: 'dark', 'light', or 'infographic'
        value: Single numeric value for gauge charts
        min_val / max_val: Gauge range
        label: Label for gauge value
        frame_column: Column defining animation frames
        comparison_columns: Two column names for comparison_bar
        trend_column: Time column for sparklines/animated
        top_n: Number of entities for sparklines

    Returns: Dict with 'figure' (Plotly spec), 'type', 'interactive', 'chart_type', 'title'
    """
    valid_types = {"heatmap", "treemap", "gauge", "funnel", "animated_line", "comparison_bar", "sparklines"}
    if chart_type not in valid_types:
        raise VisualizationError(
            chart_type, f"Unsupported advanced chart type '{chart_type}'. Use: {', '.join(sorted(valid_types))}"
        )

    builder = AdvancedChartBuilder(data)
    fig = None

    try:
        if chart_type == "heatmap":
            fig = builder.heatmap(x_column, y_column, z_column, title=title, theme=theme)
        elif chart_type == "treemap":
            fig = builder.treemap(
                names_column,
                values_column,
                title=title,
                theme=theme,
                color_column=color_column,
                hierarchy_column=hierarchy_column,
            )
        elif chart_type == "gauge":
            if value is None:
                raise VisualizationError(chart_type, "gauge chart requires 'value' parameter")
            fig = builder.gauge(value, title=title, theme=theme, min_val=min_val, max_val=max_val, label=label)
        elif chart_type == "funnel":
            fig = builder.funnel(names_column, values_column, title=title, theme=theme)
        elif chart_type == "animated_line":
            fig = builder.animated_line(
                x_column, y_column, frame_column, title=title, theme=theme, category_column=category_column
            )
        elif chart_type == "comparison_bar":
            if not comparison_columns or len(comparison_columns) != 2:
                raise VisualizationError(
                    chart_type, "comparison_bar requires comparison_columns (list of 2 column names)"
                )
            fig = builder.comparison_bar(x_column, comparison_columns, title=title, theme=theme)
        elif chart_type == "sparklines":
            fig = builder.sparkline_container(
                y_column, x_column, trend_column, title=title, theme=theme, sort_by=x_column, top_n=top_n
            )
    except Exception as e:
        raise VisualizationError(chart_type, f"Failed to create {chart_type}: {e}") from e

    if fig is None:
        raise VisualizationError(chart_type, "Failed to create chart")

    return {"figure": fig_to_dict(fig), "type": "plotly", "interactive": True, "chart_type": chart_type, "title": title}


@mcp.tool()
async def apply_chart_theme(
    figure: dict[str, Any],
    theme: str = "dark",
    annotations: Optional[list[dict[str, Any]]] = None,
    highlight_zones: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Apply a visual theme to an existing chart figure.

    Transforms a basic chart into a visually striking, data-journalism style
    visualization with custom colors, dark backgrounds, and annotations.

    Themes:
    - 'dark': Dramatic data-journalism style with deep navy background
    - 'light': Clean professional white background
    - 'infographic': Large typography, minimal chrome, centered titles

    Annotations add callout arrows to specific data points for storytelling.
    Each annotation: {"text": "string", "x": value, "y": value}

    Highlight zones add shaded vertical regions (e.g., pandemic years, crisis period).
    Each zone: {"x_start": value, "x_end": value, "label": "optional text", "color": "rgba(...)"}

    Args:
        figure: Plotly figure dict (from create_visualization or create_advanced_visualization)
        theme: 'dark', 'light', or 'infographic'
        annotations: List of annotation dicts to add callouts
        highlight_zones: List of highlight zone dicts

    Returns: Themed figure dict
    """
    from plotly.graph_objects import Figure

    fig = Figure(figure.get("data", []), figure.get("layout", {}))
    fig = apply_theme(fig, theme)

    if annotations:
        for ann in annotations:
            fig = add_annotation(fig, ann.get("text", ""), ann.get("x", 0), ann.get("y", 0))

    if highlight_zones:
        for zone in highlight_zones:
            fig = add_highlight_zone(
                fig,
                zone.get("x_start", 0),
                zone.get("x_end", 0),
                fill_color=zone.get("color", "rgba(198, 40, 40, 0.1)"),
                annotation_text=zone.get("label", ""),
            )

    return fig_to_dict(fig)


@mcp.tool()
async def extract_data_insights(
    data: list[dict[str, Any]],
    time_column: Optional[str] = None,
    entity_column: Optional[str] = None,
    max_insights: int = 10,
) -> dict[str, Any]:
    """Extract the most interesting and shocking insights from a dataset.

    Automatically scans data for statistically significant patterns,
    extreme values, dramatic changes, outliers, and inequality.
    Each insight includes a severity rating and human-readable narrative.

    Insight types detected:
    - Extreme values: Max/min with context ("Highest pollution: Niš at 245 μg/m³")
    - Temporal changes: Biggest % changes over time ("Population dropped 12.3%")
    - Rankings: Top/bottom entities ("Beograd leads with 50% of GDP")
    - Inequality: High variance between entities ("10× gap between richest and poorest")
    - Outliers: Statistical anomalies ("3 stations exceeded 3σ threshold")

    Use AFTER get_resource_data() and data_profile() to understand columns.
    Results sorted by severity (critical > high > medium > low).

    Args:
        data: List of row dicts (from get_resource_data)
        time_column: Column with years/dates for temporal analysis
        entity_column: Column with entity names (cities, ministries, etc.)
        max_insights: Maximum insights to return (default 10)

    Returns: Dict with 'insights' (list), 'total_found', 'headline'
    """
    insights = extract_insights(
        data,
        time_column=time_column,
        entity_column=entity_column,
    )
    top = insights[:max_insights]

    headline = ""
    if top:
        headline = top[0].get("headline", "")

    return {
        "insights": top,
        "total_found": len(insights),
        "headline": headline,
        "severity_summary": {
            sev: sum(1 for i in top if i.get("severity") == sev) for sev in ("critical", "high", "medium", "low")
        },
    }


@mcp.tool()
async def generate_data_narrative(
    data: list[dict[str, Any]],
    title: str = "",
    time_column: Optional[str] = None,
    entity_column: Optional[str] = None,
    max_insights: int = 5,
) -> dict[str, Any]:
    """Generate a complete data story with headline, big number, and narrative.

    Combines insight extraction with narrative generation to create
    a compelling data story suitable for infographics, articles, or
    social media. Returns a headline, summary text, key insights,
    and a "big number" — the most dramatic single finding.

    Workflow:
        1. get_resource_data(resource_id) → download data
        2. data_profile(data) → understand columns
        3. generate_data_narrative(data, title="...", time_column="year") → full story
        4. create_infographic(data, ...) → visual infographic HTML

    Args:
        data: List of row dicts (from get_resource_data)
        title: Story title / topic
        time_column: Column with temporal data for trend analysis
        entity_column: Column with entity names
        max_insights: Maximum insights to include in narrative

    Returns: Dict with 'title', 'headline', 'big_number', 'big_label',
             'insights', 'summary', 'total_insights_found'
    """
    narrative = generate_narrative(
        data, title=title, time_column=time_column, entity_column=entity_column, max_insights=max_insights
    )
    return narrative


@mcp.tool()
async def compute_metrics(
    data: list[dict[str, Any]],
    time_column: Optional[str] = None,
    entity_column: Optional[str] = None,
    population_column: Optional[str] = None,
) -> dict[str, Any]:
    """Compute derived metrics: year-over-year changes, per-capita, growth rates, index values.

    Goes beyond raw data to calculate meaningful derived metrics:
    - YoY changes: Percentage change between consecutive periods
    - Per-capita: Divide metrics by population for fairer comparisons
    - Growth rates: Compound annual and linear growth rates
    - Index values: Normalize to base period = 100 for easy comparison

    Use AFTER get_resource_data() to enrich raw data with analytical depth.

    Example: Population data with time_column="godina" yields:
      yoy_changes: {"stanovnistvo": {"2010→2011": -0.5, "2011→2012": -0.4, ...}}
      growth_rates: {"stanovnistvo": {"compound_annual": -0.45, "total_change_pct": -4.2}}
      index_values: {"stanovnistvo": {"2010": 100.0, "2011": 99.5, ...}}

    Args:
        data: List of row dicts
        time_column: Column with temporal ordering (years, dates)
        entity_column: Column with entity names (for per-entity breakdown)
        population_column: Column with population counts (for per-capita)

    Returns: Dict with 'yoy_changes', 'per_capita', 'growth_rates', 'index_values', 'derived_data'
    """
    return compute_derived_metrics(
        data,
        time_column=time_column,
        entity_column=entity_column,
        population_column=population_column,
    )


@mcp.tool()
async def build_infographic(
    data: list[dict[str, Any]],
    title: str = "Serbian Data Story",
    subtitle: str = "",
    chart_type: str = "bar",
    x_column: str = "",
    y_column: str = "",
    theme: str = "infographic",
    time_column: Optional[str] = None,
    entity_column: Optional[str] = None,
    filename: str = "infographic",
) -> dict[str, Any]:
    """Create a complete infographic HTML page: big number + chart + insights.

    Generates a visually striking, self-contained HTML page with:
    - A large headline with gradient styling
    - A "big number" card showing the most dramatic finding
    - An auto-generated chart with the chosen theme
    - Color-coded insight cards (critical/high/medium/low severity)
    - A narrative summary paragraph
    - Responsive design for mobile/desktop

    This is the RECOMMENDED tool for creating shareable data stories.
    The output HTML can be opened in any browser or shared as a file.

    Workflow:
        1. search_datasets(query="...") → find dataset
        2. get_resource_data(resource_id) → download data
        3. data_profile(data) → identify columns
        4. build_infographic(data, title="...", x_column="...", y_column="...") → HTML
        5. Export saved to exports/ directory

    Args:
        data: List of row dicts
        title: Infographic title (e.g., "Air Quality Crisis in Niš")
        subtitle: Optional subtitle text
        chart_type: Main chart type (line, bar, pie, scatter, histogram, box)
        x_column: X axis column name
        y_column: Y axis column name
        theme: 'dark', 'light', or 'infographic' (default: infographic)
        time_column: Optional time column for insight extraction
        entity_column: Optional entity column for insight extraction
        filename: Output filename (without .html)

    Returns: Dict with 'filepath', 'metadata' (title, insights count, big number),
             'insights', 'headline'
    """
    result = create_infographic(
        data,
        title=title,
        subtitle=subtitle,
        chart_type=chart_type,
        x_column=x_column,
        y_column=y_column,
        theme=theme,
        time_column=time_column,
        entity_column=entity_column,
    )

    if result.get("html"):
        output_dir = config.export_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / f"{filename}.html"
        filepath.write_text(result["html"], encoding="utf-8")
        return {
            "filepath": str(filepath),
            "metadata": result.get("metadata", {}),
            "insights": result.get("insights", []),
            "headline": result.get("metadata", {}).get("headline", ""),
            "total_rows": len(data),
        }
    return {"error": True, "message": "Failed to generate infographic"}


@mcp.tool()
async def build_dashboard(
    panels: list[dict[str, Any]],
    title: str = "Serbia Data Dashboard",
    subtitle: str = "",
    filename: str = "dashboard",
) -> dict[str, Any]:
    """Create a multi-panel dashboard HTML page combining charts and text.

    Build a comprehensive dashboard with multiple visualization panels.
    Each panel can be a chart, HTML content block, or a big number card.

    Panel types:
    - Chart: {"type": "chart", "title": "...", "figure": <plotly_dict>, "span": 1}
    - HTML:  {"type": "html", "title": "...", "content": "<p>...</p>", "span": 1}
    - Big number: {"type": "big_number", "number": "7M", "label": "Population", "color": "red"}

    The 'span' field (1 or 2) controls width: span=2 takes full row, span=1 is half.

    Example panels:
        [
            {"type": "big_number", "number": "-12%", "label": "Population Change", "color": "red"},
            {"type": "chart", "title": "Population Trend", "figure": <from create_visualization>},
            {"type": "html", "title": "Key Findings", "content": "<p>Serbia's population...</p>"},
        ]

    Args:
        panels: List of panel dicts (see above for types)
        title: Dashboard title
        subtitle: Dashboard subtitle
        filename: Output filename (without .html)

    Returns: Dict with 'filepath', 'panel_count', 'filename'
    """
    html = create_dashboard(panels, title=title, subtitle=subtitle)

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(html, encoding="utf-8")

    return {
        "filepath": str(filepath),
        "panel_count": len(panels),
        "filename": f"{filename}.html",
    }


@mcp.tool()
async def export_visualization(
    figure: dict[str, Any],
    format: str = "html",
    filename: str = "chart",
    output_dir: Optional[str] = None,
    scale: float = 1.0,  # noqa: ARG001
) -> dict[str, Any]:
    """Export a visualization figure to a file (html or json format)."""
    from plotly.graph_objects import Figure

    fig = Figure(figure.get("data", []), figure.get("layout", {}))
    out_dir = Path(output_dir) if output_dir else config.export_dir
    valid_formats = {"html", "json"}
    if format not in valid_formats:
        return {"error": True, "message": f"Unsupported format '{format}'. Use: {', '.join(sorted(valid_formats))}"}
    filepath = ""
    if format == "html":
        filepath = await export_html(fig, filename, output_dir=out_dir)
    elif format == "json":
        filepath = await export_json(fig, filename, output_dir=out_dir)
    return {"filepath": filepath, "format": format, "filename": filename}


# =========================================================================
# Data transformation tools
# =========================================================================


@mcp.tool()
async def filter_data_tool(data: list[dict[str, Any]], filters: dict[str, Any]) -> dict[str, Any]:
    """Filter rows in a dataset based on criteria.

    Use AFTER get_resource_data() to narrow down data before visualization or analysis.

    Supported filter patterns:
    - Direct match: {"column": "value"} — exact match
    - Comparison: {"column": {"$gt": 100}} — greater than
    - Supported operators: $gt, $gte, $lt, $lte, $eq, $ne, $in, $not_in
    - List match: {"column": ["val1", "val2"]} — match any in list

    Example: Filter population data for specific year:
    {"godina": "2023"} or {"stanovnistvo": {"$gte": 50000}}

    Args:
        data: List of row dicts (from get_resource_data)
        filters: Dict of column → value or column → {operator: value}

    Returns: Filtered data with 'data', 'columns', 'rows'
    """
    result = filter_data(data, filters)
    return _dataframe_to_dict(result)


@mcp.tool()
async def group_data_tool(
    data: list[dict[str, Any]],
    group_by: str | list[str],
    aggregations: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Group data by one or more columns with optional aggregations.

    Aggregation functions: sum, mean, median, min, max, count, std, var.
    """
    result = group_data(data, group_by, aggregations)
    return _dataframe_to_dict(result)


@mcp.tool()
async def aggregate_data_tool(data: list[dict[str, Any]], column: str, function: str = "sum") -> dict[str, Any]:
    """Aggregate a single column using a function (sum, mean, median, min, max, count, std, var)."""
    result = aggregate_data(data, column, function)
    value = result
    if value is not None:
        # Ensure JSON-serialisable types
        import numpy as np

        if isinstance(value, (np.integer,)):
            value = int(value)
        elif isinstance(value, (np.floating,)):
            value = float(value)
    return {"value": value, "column": column, "function": function}


@mcp.tool()
async def sort_data_tool(data: list[dict[str, Any]], by: str | list[str], ascending: bool = True) -> dict[str, Any]:
    """Sort data by one or more columns."""
    result = sort_data(data, by, ascending)
    return _dataframe_to_dict(result)


@mcp.tool()
async def select_columns_tool(data: list[dict[str, Any]], columns: list[str]) -> dict[str, Any]:
    """Select specific columns from data."""
    result = select_columns(data, columns)
    return _dataframe_to_dict(result)


# =========================================================================
# Utility tools
# =========================================================================


@mcp.tool()
async def get_config_tool() -> dict[str, Any]:
    """Get the current MCP server configuration settings."""
    return {
        "api_base": config.api_base,
        "rate_limit": config.rate_limit,
        "timeout": config.timeout,
        "cache_dir": str(config.cache_dir),
        "export_dir": str(config.export_dir),
    }


@mcp.tool()
async def health_check() -> dict[str, Any]:
    """Check MCP server health and API connectivity."""
    api_reachable = False
    try:
        client = await _get_client()
        await client.list_organizations(page_size=1)
        api_reachable = True
    except Exception:
        api_reachable = False
    return {
        "status": "healthy",
        "api_reachable": api_reachable,
        "version": __import__("serbian_data_mcp").__version__,
        "timestamp": datetime.now(UTC).isoformat(),
    }


# =========================================================================
# Discovery & Analysis tools
# =========================================================================


@mcp.tool()
async def search_by_tag(tags: list[str], page_size: int = 10, page: int = 1) -> dict[str, Any]:
    """Search datasets by tags on the Serbian data portal.

    Tags classify datasets by topic. Common tags include:
    - "statistika" (statistics), "budžet" (budget), "obrazovanje" (education)
    - "zdravlje" (health), "saobraćaj" (transport), "cene" (prices)
    - "izveštaj" (report), "registar" (registry), "plan" (plan)
    - "ekologija" (ecology), "stanovništvo" (population)

    Useful when you want to find all datasets about a broad topic
    regardless of which organization published them.

    Args:
        tags: List of tag strings to search for (joined as search query)
        page_size: Results per page (1-100, default 10)
        page: Page number (1-indexed)
    """
    client = await _get_client()
    tag_query = " ".join(tags)
    result = await client.search_datasets(query=tag_query, page_size=min(max(page_size, 1), 100), page=max(page, 1))
    return _result_to_dict(result)


@mcp.tool()
async def get_dataset_resources(dataset_id: str) -> dict[str, Any]:
    """List all resources (data files) available for a specific dataset.

    Before downloading data with get_resource_data(), use this tool to see:
    - Available resource IDs (needed for get_resource_data)
    - Data formats (json, csv, xlsx, xls, xml)
    - File descriptions and sizes
    - Direct download URLs

    Args:
        dataset_id: Dataset identifier (from search_datasets or browse)
    """
    client = await _get_client()
    dataset = await client.get_dataset(dataset_id)
    if dataset is None:
        return {"error": True, "message": f"Dataset '{dataset_id}' not found"}
    resources = []
    for r in dataset.resources:
        resources.append(
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "format": r.format,
                "url": r.url,
                "size": r.size,
                "mime_type": r.mime_type,
            }
        )
    return {"dataset_id": dataset_id, "dataset_title": dataset.title, "resources": resources, "count": len(resources)}


@mcp.tool()
async def get_portal_statistics() -> dict[str, Any]:
    """Get overview statistics of the Serbian open data portal (data.gov.rs).

    Returns current counts of datasets and organizations.
    """
    client = await _get_client()
    try:
        data = await client._request("GET", "/api/1/datasets/", params={"rows": 1})
        total = data.get("total", 0)
    except Exception:
        total = 0
    try:
        org_data = await client._request("GET", "/api/1/organizations/", params={"rows": 1})
        total_orgs = org_data.get("total", 0)
    except Exception:
        total_orgs = 0
    return {
        "total_datasets": total,
        "total_organizations": total_orgs,
        "api_base": client.base_url,
        "portal_url": "https://data.gov.rs",
    }


@mcp.tool()
async def data_profile(data: list[dict[str, Any]], sample_size: int = 5) -> dict[str, Any]:
    """Analyze the structure and statistics of a dataset.

    Use AFTER get_resource_data() to understand columns, types, and basic statistics
    BEFORE creating visualizations. Essential for choosing correct x_column/y_column
    for create_visualization().

    Returns column names, types, unique counts, null counts, and sample values.
    For numeric columns, also includes min, max, mean, and median.

    Args:
        data: Dataset rows (list of dicts, from get_resource_data)
        sample_size: Number of sample values to show per column (default 5)
    """
    if not data:
        return {"error": True, "message": "Empty dataset — pass data from get_resource_data()"}
    import numpy as np

    df = pd.DataFrame(data)
    columns = []
    for col in df.columns:
        col_info: dict[str, Any] = {
            "name": col,
            "dtype": str(df[col].dtype),
            "non_null": int(df[col].count()),
            "null_count": int(df[col].isna().sum()),
            "unique": int(df[col].nunique()),
            "sample_values": df[col].dropna().head(sample_size).tolist(),
        }
        if df[col].dtype in ("int64", "float64"):
            col_info["min"] = float(df[col].min()) if pd.notna(df[col].min()) else None
            col_info["max"] = float(df[col].max()) if pd.notna(df[col].max()) else None
            col_info["mean"] = float(df[col].mean()) if pd.notna(df[col].mean()) else None
            col_info["median"] = float(df[col].median()) if pd.notna(df[col].median()) else None
        columns.append(col_info)
    return {
        "columns": columns,
        "total_rows": len(data),
        "total_columns": len(df.columns),
        "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB",
    }


# =========================================================================
# Comparison & Discovery tools (Wave 2)
# =========================================================================


@mcp.tool()
async def compare_datasets(dataset_id_1: str, dataset_id_2: str) -> dict[str, Any]:
    """Compare two datasets side by side on the Serbian open data portal.

    Shows differences in organization, tags, resource count, formats available,
    quality scores, and temporal coverage between two datasets. Useful when
    choosing the best dataset for a specific analysis task (e.g., multiple
    population datasets from different years or publishers).

    Workflow: search_datasets() → compare_datasets(id1, id2) → pick best → download.

    Args:
        dataset_id_1: First dataset identifier
        dataset_id_2: Second dataset identifier

    Returns: Dict with 'dataset_1', 'dataset_2' summaries and 'comparison' dict.
    """
    client = await _get_client()
    ds1 = await client.get_dataset(dataset_id_1)
    ds2 = await client.get_dataset(dataset_id_2)
    if ds1 is None:
        return {"error": True, "message": f"Dataset '{dataset_id_1}' not found"}
    if ds2 is None:
        return {"error": True, "message": f"Dataset '{dataset_id_2}' not found"}

    def _summary(ds: Dataset) -> dict[str, Any]:
        org_name = ds.organization.name if ds.organization else "N/A"
        formats = sorted({r.format for r in ds.resources if r.format})
        quality = getattr(ds, "quality", None) or {}
        return {
            "id": ds.id,
            "title": ds.title,
            "organization": org_name,
            "resource_count": len(ds.resources),
            "formats": formats,
            "tags": ds.tags[:10],
            "temporal_coverage": ds.temporal_coverage,
            "frequency": ds.frequency,
            "modified_at": ds.modified_at.isoformat() if ds.modified_at else None,
            "quality_score": quality.get("score") if isinstance(quality, dict) else None,
        }

    s1, s2 = _summary(ds1), _summary(ds2)
    comparison: dict[str, Any] = {
        "same_organization": s1["organization"] == s2["organization"],
        "resource_count_diff": s1["resource_count"] - s2["resource_count"],
        "shared_formats": list(set(s1["formats"]) & set(s2["formats"])),
        "unique_formats_1": list(set(s1["formats"]) - set(s2["formats"])),
        "unique_formats_2": list(set(s2["formats"]) - set(s1["formats"])),
        "shared_tags": list(set(s1["tags"]) & set(s2["tags"])),
    }
    return {"dataset_1": s1, "dataset_2": s2, "comparison": comparison}


@mcp.tool()
async def browse_recent_datasets(days: int = 7, page_size: int = 20) -> dict[str, Any]:
    """Browse recently added or updated datasets on data.gov.rs.

    Discover new data as it's published. Great for staying up to date with
    the latest Serbian open data releases. Returns datasets sorted by most
    recently modified.

    Use this to find fresh datasets, monitor new publications, or track
    data updates (e.g., new budget execution reports).

    Args:
        days: Number of days to look back (default 7, max 365)
        page_size: Number of results (1-100, default 20)

    Returns: Dict with 'datasets', 'total_returned', 'days_back', 'queried_at'
    """
    client = await _get_client()
    days = min(max(days, 1), 365)
    page_size = min(max(page_size, 1), 100)
    result = await client.search_datasets(query="", page_size=page_size, page=1)
    now = datetime.now(UTC)
    cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)

    recent = []
    for ds in result.datasets:
        if (ds.modified_at and ds.modified_at >= cutoff) or (ds.created_at and ds.created_at >= cutoff):
            recent.append(ds)

    return {
        "datasets": [_dataset_to_dict(ds) for ds in recent],
        "total_returned": len(recent),
        "days_back": days,
        "queried_at": now.isoformat(),
    }


# =========================================================================
# Quick Analysis & Export tools (Wave 2)
# =========================================================================


@mcp.tool()
async def get_data_summary(resource_id: str) -> dict[str, Any]:
    """Get a quick summary of a resource's data without downloading the full file.

    Returns column names, data types, row count, and sample values for the
    first few rows. Use this BEFORE get_resource_data() to understand what
    the data looks like and plan your analysis.

    Much faster than downloading the full dataset — ideal for large XLSX/CSV
    files where you just need to know the schema.

    Workflow:
        1. get_dataset_resources(dataset_id) → find resource_id
        2. get_data_summary(resource_id) → understand structure
        3. get_resource_data(resource_id) → download full data if useful
        4. data_profile(data) → detailed stats after download

    Args:
        resource_id: Resource identifier (from dataset's resources list)

    Returns: Dict with 'columns' (list of {name, dtype, sample_values}),
             'estimated_rows', 'format', 'resource_id'.
    """
    client = await _get_client()
    try:
        data = await client.get_resource_data(resource_id)
        if isinstance(data, pd.DataFrame):
            df = data.head(20)
            columns = []
            for col in df.columns:
                columns.append(
                    {
                        "name": col,
                        "dtype": str(df[col].dtype),
                        "sample_values": df[col].dropna().head(5).tolist(),
                    }
                )
            return {
                "columns": columns,
                "estimated_rows": len(data),
                "format": "tabular",
                "resource_id": resource_id,
            }
        if isinstance(data, dict):
            top_keys = list(data.keys())[:20]
            sample: dict[str, Any] = {}
            for k in top_keys:
                val = data[k]
                if isinstance(val, list):
                    sample[k] = {"type": "list", "length": len(val), "first_items": val[:3]}
                elif isinstance(val, dict):
                    sample[k] = {"type": "dict", "keys": list(val.keys())[:10]}
                else:
                    sample[k] = val
            return {
                "columns": [{"name": k, "dtype": "key", "sample_values": None} for k in top_keys],
                "estimated_rows": "N/A (dict structure)",
                "format": "json-dict",
                "sample": sample,
                "resource_id": resource_id,
            }
        if isinstance(data, list) and data:
            sample_items = data[:5]
            if isinstance(sample_items[0], dict):
                columns = []
                for col in sample_items[0]:
                    columns.append(
                        {
                            "name": col,
                            "dtype": type(sample_items[0][col]).__name__,
                            "sample_values": [item.get(col) for item in sample_items if col in item][:5],
                        }
                    )
                return {
                    "columns": columns,
                    "estimated_rows": len(data),
                    "format": "json-list",
                    "resource_id": resource_id,
                }
            return {
                "columns": [],
                "estimated_rows": len(data),
                "format": "json-list-scalar",
                "sample": sample_items[:3],
                "resource_id": resource_id,
            }
        return {"error": True, "message": f"Unexpected data type: {type(data).__name__}"}
    except Exception as e:
        return {"error": True, "message": str(e)}


@mcp.tool()
async def export_data(
    data: list[dict[str, Any]],
    filename: str = "data",
    format: str = "csv",
    output_dir: Optional[str] = None,
) -> dict[str, Any]:
    """Export data to a file in various formats for offline analysis or sharing.

    Save downloaded/transformed data from get_resource_data() or after
    filter_data_tool()/group_data_tool() transformations.

    Supported formats:
    - "csv": Comma-separated values (universal, works in Excel/LibreOffice)
    - "json": JSON array of objects (great for APIs and JavaScript)
    - "xlsx": Excel workbook (requires openpyxl; may not be installed)

    Files are saved to the configured export directory (default: ./exports).

    Args:
        data: Data rows to export (list of dicts from get_resource_data)
        filename: Output filename without extension (default: "data")
        format: Export format — "csv", "json", or "xlsx" (default: "csv")
        output_dir: Output directory path (defaults to server export_dir)

    Returns: Dict with 'filepath', 'format', 'rows', 'columns', 'filename'.
    """
    if not data:
        return {"error": True, "message": "No data to export — pass data from get_resource_data()"}
    out_dir = Path(output_dir) if output_dir else config.export_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    valid_formats = {"csv", "json", "xlsx"}
    if format not in valid_formats:
        return {"error": True, "message": f"Unsupported format '{format}'. Use: {', '.join(sorted(valid_formats))}"}

    df = pd.DataFrame(data)
    filepath: Path
    try:
        if format == "csv":
            filepath = out_dir / f"{filename}.csv"
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
        elif format == "json":
            filepath = out_dir / f"{filename}.json"
            filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        elif format == "xlsx":
            try:
                filepath = out_dir / f"{filename}.xlsx"
                df.to_excel(filepath, index=False, engine="openpyxl")
            except ImportError:
                return {
                    "error": True,
                    "message": "openpyxl is required for XLSX export. Install with: pip install openpyxl",
                }
    except Exception as e:
        return {"error": True, "message": f"Export failed: {str(e)}"}

    return {
        "filepath": str(filepath),
        "format": format,
        "rows": len(data),
        "columns": list(df.columns),
        "filename": f"{filename}.{format}",
    }


# =========================================================================
# Map & Special Chart tools
# =========================================================================


_map_builder: Optional[SerbiaMapBuilder] = None


def _get_map_builder() -> SerbiaMapBuilder:
    """Get or create cached map builder."""
    global _map_builder
    if _map_builder is None:
        _map_builder = SerbiaMapBuilder()
    return _map_builder


@mcp.tool()
async def create_serbia_map(
    data: list[dict[str, Any]],
    name_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    colorscale: Optional[str] = None,
    highlight_top: int = 3,
    filename: str = "serbia_map",
) -> dict[str, Any]:
    """Create a choropleth map of Serbia by administrative district (25 okruga).

    Renders real district boundaries from Natural Earth geographic data.
    Color-coded by the provided metric. Use for population density, pollution
    levels, budget allocation, or any district-level comparison.

    District names should match Natural Earth format (English transliteration).
    Common names: 'Grad Beograd', 'Nišavski', 'Sremski', 'Zapadno-Backi',
    'Šumadijski', 'Južno-Banatski', 'Severno-Backi', 'Zlatiborski', etc.
    Cyrillic names and city shorthand are also supported (e.g., 'Niš', 'Novi Sad').

    Use list_serbia_districts() to see all 25 available district names.

    Workflow:
        1. get_resource_data(resource_id) → download district-level data
        2. create_serbia_map(data, name_column='okrug', value_column='populacija')

    Args:
        data: List of row dicts with district names and values
        name_column: Column containing district names
        value_column: Column containing numeric values to color by
        title: Map title
        theme: 'dark', 'light', or 'infographic'
        colorscale: Color scheme: 'red', 'blue', 'diverging', or 'heat' (default: blue)
        highlight_top: Number of top districts to highlight with thick border
        filename: Output filename (without .html)

    Returns: Dict with 'filepath', 'districts_matched', 'total_districts', 'title'
    """
    builder = _get_map_builder()

    color_map = {
        "red": [(0.0, "#fff9c4"), (0.25, "#ffcc80"), (0.5, "#ff8a65"), (0.75, "#e53935"), (1.0, "#b71c1c")],
        "blue": None,  # default sequential blue
        "diverging": [(0.0, "#1565c0"), (0.25, "#42a5f5"), (0.5, "#f5f5f5"), (0.75, "#ef5350"), (1.0, "#c62828")],
        "heat": [(0.0, "#fff9c4"), (0.25, "#ffcc80"), (0.5, "#ff8a65"), (0.75, "#e53935"), (1.0, "#b71c1c")],
    }
    cs = color_map.get(colorscale or "blue") if colorscale else None

    fig = builder.choropleth(
        data,
        name_column=name_column,
        value_column=value_column,
        title=title or f"{value_column} po okruzima",
        theme=theme,
        colorscale=cs,
        highlight_top=highlight_top,
    )

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")

    df = pd.DataFrame(data)
    matched = df[name_column].apply(builder.resolve_name).notna().sum()

    return {
        "filepath": str(filepath),
        "districts_matched": int(matched),
        "total_districts": len(data),
        "available_districts": 25,
        "title": title,
    }


@mcp.tool()
async def list_serbia_districts() -> dict[str, Any]:
    """List all 25 administrative districts of Serbia available for mapping.

    Returns district names and codes used by create_serbia_map().
    Use this to understand what district names are recognized.
    """
    builder = _get_map_builder()
    return {"districts": builder.list_districts(), "total": 25}


@mcp.tool()
async def create_arrow_chart(
    data: list[dict[str, Any]],
    label_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    reference_value: Optional[float] = None,
    filename: str = "arrow_chart",
) -> dict[str, Any]:
    """Create an arrow-style chart showing directional changes.

    Horizontal bars colored green (positive) or red (negative) relative to
    a reference value (default: 0). Ideal for rankings change, budget surplus/
    deficit, growth/decline visualization.

    Args:
        data: List of row dicts
        label_column: Category labels (district names, cities, etc.)
        value_column: Numeric values (change, growth rate, etc.)
        title: Chart title
        theme: Visual theme
        reference_value: Zero/baseline line (default: 0)
        filename: Output filename

    Returns: Dict with 'filepath', 'title'
    """
    fig = arrow_chart(
        data,
        label_column=label_column,
        value_column=value_column,
        title=title,
        theme=theme,
        reference_value=reference_value,
    )
    fig = apply_theme(fig, theme)

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")

    return {"filepath": str(filepath), "title": title, "rows": len(data)}


@mcp.tool()
async def create_dumbbell_chart(
    data: list[dict[str, Any]],
    label_column: str,
    start_column: str,
    end_column: str,
    title: str = "",
    theme: str = "dark",
    filename: str = "dumbbell_chart",
) -> dict[str, Any]:
    """Create a dumbbell chart showing before/after comparison.

    Two dots per category connected by a line, colored by direction (green for
    increase, red for decrease). Shows the magnitude and direction of change.

    Ideal for: population 2010 vs 2022, budget planned vs executed, start vs end.

    Args:
        data: List of row dicts with start and end values
        label_column: Category names
        start_column: Starting/baseline values
        end_column: Final/current values
        title: Chart title
        theme: Visual theme
        filename: Output filename

    Returns: Dict with 'filepath', 'title', 'rows'
    """
    fig = dumbbell_chart(
        data,
        label_column=label_column,
        start_column=start_column,
        end_column=end_column,
        title=title,
        theme=theme,
    )
    fig = apply_theme(fig, theme)

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")

    return {"filepath": str(filepath), "title": title, "rows": len(data)}


@mcp.tool()
async def create_lollipop_chart(
    data: list[dict[str, Any]],
    label_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    highlight_column: Optional[str] = None,
    highlight_value: Optional[str] = None,
    filename: str = "lollipop_chart",
) -> dict[str, Any]:
    """Create a lollipop chart — dots on stems for clean ranking visualization.

    Like a bar chart but with dots instead of bars, giving a cleaner visual.
    Can highlight a specific category with a contrasting color.

    Ideal for: district population ranking, budget allocation by ministry,
    top-N lists where you want to spotlight one entity.

    Args:
        data: List of row dicts
        label_column: Category labels (districts, cities, etc.)
        value_column: Numeric values to rank by
        title: Chart title
        theme: Visual theme
        highlight_column: Column to match for highlighting
        highlight_value: Value to highlight (e.g., 'Grad Beograd')
        filename: Output filename

    Returns: Dict with 'filepath', 'title', 'rows'
    """
    fig = lollipop_chart(
        data,
        label_column=label_column,
        value_column=value_column,
        title=title,
        theme=theme,
        highlight_column=highlight_column,
        highlight_value=highlight_value,
    )

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")

    return {"filepath": str(filepath), "title": title, "rows": len(data)}


# =========================================================================
# Datawrapper Cloud Export
# =========================================================================


@mcp.tool()
async def export_to_datawrapper(
    data: list[dict[str, Any]],
    title: str,
    chart_type: str = "d3-bars-vertical",
    labels: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Export data to Datawrapper for professional cloud-hosted charts.

    Creates a chart on Datawrapper (datawrapper.de) with your data, publishes it,
    and returns embed URLs and codes. Requires DATAWRAPPER_ACCESS_TOKEN env var.

    Get a free API token at: https://app.datawrapper.de/account/api-tokens

    Supported chart types:
    - 'd3-bars-vertical' — vertical bar chart
    - 'd3-bars-horizontal' — horizontal bar chart
    - 'd3-lines' — line chart
    - 'd3-area' — area chart
    - 'd3-pies' — pie chart
    - 'd3-pie-donut' — donut chart
    - 'd3-scatter' — scatter plot
    - 'd3-table' — data table

    Args:
        data: List of row dicts
        title: Chart title
        chart_type: Datawrapper chart type (default: d3-bars-vertical)
        labels: Column name → display label mapping

    Returns: Dict with 'id', 'url', 'embed_url', 'embed_code' or 'error' if no token
    """
    exporter = DatawrapperExporter()
    result = exporter.create_and_publish(data, title, chart_type, labels)
    return result


# =========================================================================
# Animated Charts
# =========================================================================


@mcp.tool()
async def create_animated_chart(
    animation_type: str = "bars_evolution",
    data: Optional[list[dict[str, Any]]] = None,
    datasets: Optional[dict[str, list[dict[str, Any]]]] = None,
    time_column: str = "",
    category_column: str = "",
    value_column: str = "",
    title: str = "",
    theme: str = "dark",
    filename: str = "animated",
) -> dict[str, Any]:
    """Create an animated chart with smooth transitions between states.

    Three animation types available:

    1. 'bars_evolution' — Animated bar chart showing time evolution.
       Bars grow/shrink smoothly as you advance through time periods.
       Auto-sorts by value in each frame. Needs: time_column, category_column, value_column.

    2. 'timeline' — Morphs from bar chart to line chart over time.
       First half shows bars, second half transitions to multi-line trend.
       Needs: time_column, category_column, value_column.

    3. 'comparison' — Toggle between different datasets with smooth transitions.
       Pass datasets as a dict of label→data. Needs: datasets, category_column, value_column.

    All animations include play/pause buttons and a slider scrubber.

    Args:
        animation_type: 'bars_evolution', 'timeline', or 'comparison'
        data: Single dataset (for bars_evolution and timeline)
        datasets: Dict of label→data (for comparison type)
        time_column: Column with time periods
        category_column: Column with entity names
        value_column: Column with numeric values
        title: Chart title
        theme: Visual theme
        filename: Output filename

    Returns: Dict with 'filepath', 'animation_type', 'title'
    """
    valid_types = {"bars_evolution", "timeline", "comparison"}
    if animation_type not in valid_types:
        return {"error": True, "message": f"Invalid type. Use: {', '.join(sorted(valid_types))}"}

    fig = None
    if animation_type == "bars_evolution" and data:
        fig = animated_bars_evolution(
            data,
            time_column=time_column,
            category_column=category_column,
            value_column=value_column,
            title=title,
            theme=theme,
        )
    elif animation_type == "timeline" and data:
        fig = animated_timeline(
            data,
            time_column=time_column,
            category_column=category_column,
            value_column=value_column,
            title=title,
            theme=theme,
        )
    elif animation_type == "comparison" and datasets:
        fig = animated_comparison(
            datasets,
            category_column=category_column,
            value_column=value_column,
            title=title,
            theme=theme,
        )

    if fig is None:
        return {"error": True, "message": "Failed to create animated chart. Check parameters."}

    fig = apply_theme(fig, theme)

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")

    return {"filepath": str(filepath), "animation_type": animation_type, "title": title}


# =========================================================================
# Scrollytelling
# =========================================================================


@mcp.tool()
async def create_scrollytelling_story(
    steps: list[dict[str, Any]],
    title: str = "Serbian Data Story",
    subtitle: str = "",
    byline: str = "",
    theme: str = "dark",
    filename: str = "story",
) -> dict[str, Any]:
    """Create a scroll-driven HTML data story (scrollytelling).

    Generates a visually stunning multi-section page where narrative text scrolls
    on the left and interactive charts update on the right — the visualise.admin.ch
    pattern used by Swiss government data portal.

    Each step has a headline, narrative text, and optional chart. As the user
    scrolls, charts transition in and out with smooth animations.

    Step format:
    - 'headline' (str): Section headline text
    - 'text' (str): Narrative paragraph (supports HTML: <br>, <b>, <em>)
    - 'chart' (dict, optional): Plotly figure dict from create_visualization()
    - 'big_number' (str, optional): Large statistic to display (e.g., '-12%')
    - 'big_number_label' (str, optional): Label for big number
    - 'highlight_color' (str, optional): Step accent color (default: #0C4076)

    Example:
        steps = [
            {"headline": "Srbija gubi ljude", "text": "Od 2002...", "big_number": "-12%", "big_number_label": "pad populacije"},
            {"headline": "Vazduh u Nišu", "text": "Niš je...", "chart": <from create_visualization>},
        ]

    The output HTML includes: hero header, progress bar, sticky chart area,
    scroll-triggered animations, and responsive layout.

    Args:
        steps: List of step dicts (see format above)
        title: Story title
        subtitle: Story subtitle
        byline: Author credit
        theme: 'dark' or 'light'
        filename: Output filename (without .html)

    Returns: Dict with 'filepath', 'step_count', 'title'
    """
    # Convert figure dicts back to Plotly figures
    processed_steps = []
    for step in steps:
        proc = dict(step)
        if "chart" in step and step["chart"] and isinstance(step["chart"], dict):
            from plotly.graph_objects import Figure

            proc["chart"] = Figure(step["chart"].get("data", []), step["chart"].get("layout", {}))
        processed_steps.append(proc)

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"

    html_path = scrollytelling(
        processed_steps,
        title=title,
        subtitle=subtitle,
        byline=byline,
        theme=theme,
        output_path=filepath,
    )

    return {
        "filepath": html_path,
        "step_count": len(steps),
        "title": title,
    }


# =========================================================================
# Chart Enhancement Tools
# =========================================================================


@mcp.tool()
async def enhance_chart_tooltips(
    figure: dict[str, Any],
    value_column: str = "value",
    unit: str = "",
    show_mean: bool = True,
    show_rank: bool = True,
) -> dict[str, Any]:
    """Add rich contextual tooltips to any Plotly figure.

    Enriches hover tooltips with: formatted values, deviation from mean,
    and rank among peers. Works with any chart from create_visualization().

    Without enhancement: "Value: 7150000"
    With enhancement: "Value: 7.15M\nProsečno: 4.2M\nRank: #1 of 25\nPromena: +2.3%"

    Args:
        figure: Plotly figure dict (from create_visualization)
        value_column: Name of the value axis
        unit: Unit suffix (e.g., ' stanovnika', ' RSD')
        show_mean: Show average and deviation
        show_rank: Show rank position

    Returns: Enhanced figure dict with rich tooltips
    """
    from plotly.graph_objects import Figure

    fig = Figure(figure.get("data", []), figure.get("layout", {}))
    fig = add_rich_tooltips(
        fig,
        value_column=value_column,
        unit=unit,
        show_mean=show_mean,
        show_rank=show_rank,
    )
    return fig_to_dict(fig)


@mcp.tool()
async def add_chart_annotation(
    figure: dict[str, Any],
    text: str,
    x: float | str = 0,
    y: float | str = 0,
    arrow_color: str = "#ffab00",
    font_size: int = 14,
    show_arrow: bool = True,
) -> dict[str, Any]:
    """Add a callout annotation to a chart for data storytelling.

    Places a text box with optional arrow pointing to a specific data point.
    Use for highlighting key insights like "Peak year" or "COVID impact".

    Workflow:
        1. create_visualization() → get figure dict
        2. add_chart_annotation(figure, text='Peak: 7.2M', x=2022, y=7200000)
        3. export_visualization(figure) → save

    Args:
        figure: Plotly figure dict (from create_visualization)
        text: Annotation text (the insight/callout)
        x: X position (data coordinate, e.g., year 2020)
        y: Y position (data coordinate, e.g., value 5000000)
        arrow_color: Color of annotation arrow (default: gold)
        font_size: Text size
        show_arrow: Whether to show arrow pointing to data

    Returns: Enhanced figure dict
    """
    from plotly.graph_objects import Figure

    fig = Figure(figure.get("data", []), figure.get("layout", {}))
    fig = add_annotation(fig, text=text, x=x, y=y, arrow_color=arrow_color, font_size=font_size, show_arrow=show_arrow)
    return fig_to_dict(fig)


@mcp.tool()
async def add_chart_highlight_zone(
    figure: dict[str, Any],
    x_start: float | str,
    x_end: float | str,
    fill_color: str = "rgba(198, 40, 40, 0.1)",
    annotation_text: str = "",
) -> dict[str, Any]:
    """Add a shaded vertical highlight zone to a chart.

    Highlights a time period or range on the x-axis with a colored band.
    Ideal for marking crisis periods, pandemic years, policy changes.

    Example:
        add_chart_highlight_zone(figure, x_start=2020, x_end=2022, annotation_text='COVID period')

    Args:
        figure: Plotly figure dict (from create_visualization)
        x_start: Start of zone (e.g., year 2020)
        x_end: End of zone (e.g., year 2022)
        fill_color: RGBA fill color (default: light red)
        annotation_text: Optional label above the zone

    Returns: Enhanced figure dict
    """
    from plotly.graph_objects import Figure

    fig = Figure(figure.get("data", []), figure.get("layout", {}))
    fig = add_highlight_zone(fig, x_start=x_start, x_end=x_end, fill_color=fill_color, annotation_text=annotation_text)
    return fig_to_dict(fig)


@mcp.tool()
async def add_chart_callouts(
    figure: dict[str, Any],
    points: list[dict[str, Any]],
    prefix: str = "",
    suffix: str = "",
) -> dict[str, Any]:
    """Add annotation callout boxes to highlight specific data points on a chart.

    Unlike add_chart_annotation (single point), this adds multiple callout boxes
    from a list of positions. Each box has an arrow pointing to the data.

    Example:
        points = [
            {"x": 2020, "y": 7200000, "text": "7.2M", "color": "#4caf50"},
            {"x": 2015, "y": 7100000, "text": "Previous peak", "ax": 0, "ay": -40},
        ]
        add_chart_callouts(figure, points)

    Args:
        figure: Plotly figure dict (from create_visualization)
        points: List of dicts with keys: x, y, text, color (optional), ax (optional), ay (optional)
        prefix: Text before each callout
        suffix: Text after each callout

    Returns: Enhanced figure dict
    """
    from plotly.graph_objects import Figure

    fig = Figure(figure.get("data", []), figure.get("layout", {}))
    fig = add_annotation_callouts(fig, points=points, prefix=prefix, suffix=suffix)
    return fig_to_dict(fig)


@mcp.tool()
async def add_chart_threshold_line(
    figure: dict[str, Any],
    threshold: float,
    label: str = "",
    direction: str = "above",
    color: str = "#ffab00",
) -> dict[str, Any]:
    """Add a horizontal threshold/reference line with label to a chart.

    Draws a dashed horizontal line at a given Y value. Use for:
    - EU average benchmark line
    - Target/goal line
    - Critical threshold (e.g., PM10 > 50 µg/m³)

    Example:
        add_chart_threshold_line(figure, threshold=50000, label='EU prosečno', color='#4caf50')

    Args:
        figure: Plotly figure dict (from create_visualization)
        threshold: Y-value of the threshold line
        label: Label text (empty for no label)
        direction: 'above' or 'below' — label position relative to line
        color: Line and label color (default: gold)

    Returns: Enhanced figure dict
    """
    from plotly.graph_objects import Figure

    fig = Figure(figure.get("data", []), figure.get("layout", {}))
    fig = add_comparison_markers(fig, threshold=threshold, label=label, direction=direction, color=color)
    return fig_to_dict(fig)


# =========================================================================
# Novel Chart Types
# =========================================================================


@mcp.tool()
async def create_slope_chart(
    data: list[dict[str, Any]],
    entity_column: str,
    start_column: str,
    end_column: str,
    title: str = "",
    theme: str = "dark",
    top_n: int = 15,
    filename: str = "slope_chart",
) -> dict[str, Any]:
    """Create a slope chart showing ranking changes between two periods.

    Connects entities across two time periods with lines showing how rankings
    shifted. Color-coded by direction (green=gained, red=lost).

    Ideal for: census ranking changes (2002 vs 2022), budget share shifts,
    district population reorderings.

    Args:
        data: List of row dicts with entity names and two period values
        entity_column: Entity/district names
        start_column: First period values (e.g., 'pop_2002')
        end_column: Second period values (e.g., 'pop_2022')
        title: Chart title
        theme: Visual theme
        top_n: Number of entities to show
        filename: Output filename

    Returns: Dict with 'filepath', 'title', 'rows'
    """
    fig = slope_chart(data, entity_column, start_column, end_column, title=title, theme=theme, top_n=top_n)

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")

    return {"filepath": str(filepath), "title": title, "rows": len(data)}


@mcp.tool()
async def create_waffle_chart(
    data: list[dict[str, Any]],
    names_column: str,
    values_column: str,
    title: str = "",
    theme: str = "dark",
    total_icons: int = 100,
    filename: str = "waffle_chart",
) -> dict[str, Any]:
    """Create a waffle chart (icon grid) for proportional data.

    Each category gets a block of small squares in a grid.
    More intuitive than pie charts for showing "X out of 100".

    Ideal for: "1 in 4 Serbs live in Belgrade", budget share, sector breakdown.

    Args:
        data: List of row dicts
        names_column: Category labels
        values_column: Numeric values (normalized to fill grid)
        title: Chart title
        theme: Visual theme
        total_icons: Total icons in grid (100 = 10x10)
        filename: Output filename

    Returns: Dict with 'filepath', 'title', 'categories'
    """
    fig = waffle_chart(data, names_column, values_column, title=title, theme=theme, total_icons=total_icons)

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")

    return {"filepath": str(filepath), "title": title, "categories": len(data)}


@mcp.tool()
async def create_population_pyramid(
    data: list[dict[str, Any]],
    age_column: str,
    male_column: str,
    female_column: str,
    title: str = "",
    theme: str = "dark",
    filename: str = "population_pyramid",
) -> dict[str, Any]:
    """Create a population pyramid (age × sex distribution).

    Classic demographic chart with males on the left and females on the right.
    Essential for census data from RZS.

    Args:
        data: List of row dicts with age groups and male/female counts
        age_column: Age group labels (e.g., '0-4', '5-9', '65+')
        male_column: Male population counts
        female_column: Female population counts
        title: Chart title
        theme: Visual theme
        filename: Output filename

    Returns: Dict with 'filepath', 'title', 'age_groups'
    """
    fig = population_pyramid(data, age_column, male_column, female_column, title=title, theme=theme)

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")

    return {"filepath": str(filepath), "title": title, "age_groups": len(data)}


@mcp.tool()
async def create_sankey_diagram(
    data: list[dict[str, Any]],
    source_column: str,
    target_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    filename: str = "sankey",
) -> dict[str, Any]:
    """Create a Sankey (alluvial) diagram showing flow between categories.

    Ideal for: budget flow (revenue → ministry → spending), migration flows,
    energy distribution, supply chains.

    Args:
        data: List of row dicts with source, target, and flow value
        source_column: Source/origin category
        target_column: Target/destination category
        value_column: Flow magnitude
        title: Chart title
        theme: Visual theme
        filename: Output filename

    Returns: Dict with 'filepath', 'title', 'flows'
    """
    fig = sankey_diagram(data, source_column, target_column, value_column, title=title, theme=theme)

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")

    return {"filepath": str(filepath), "title": title, "flows": len(data)}


@mcp.tool()
async def create_radar_chart(
    data: list[dict[str, Any]],
    category_column: str,
    value_columns: list[str],
    title: str = "",
    theme: str = "dark",
    filename: str = "radar",
) -> dict[str, Any]:
    """Create a radar/spider chart for multi-metric comparison.

    Compare entities across multiple indicators (population, budget, schools,
    hospitals, air quality) on a single radar plot.

    Args:
        data: List of row dicts
        category_column: Entity names (cities, districts)
        value_columns: List of numeric columns to compare
        title: Chart title
        theme: Visual theme
        filename: Output filename

    Returns: Dict with 'filepath', 'title', 'entities', 'metrics'
    """
    fig = radar_chart(data, category_column, value_columns, title=title, theme=theme)

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")

    return {"filepath": str(filepath), "title": title, "entities": len(data), "metrics": len(value_columns)}


# =========================================================================
# Advanced Map Tools
# =========================================================================


_advanced_map_builder: Optional[AdvancedMapBuilder] = None


def _get_advanced_map_builder() -> AdvancedMapBuilder:
    global _advanced_map_builder
    if _advanced_map_builder is None:
        _advanced_map_builder = AdvancedMapBuilder()
    return _advanced_map_builder


@mcp.tool()
async def create_bubble_map(
    data: list[dict[str, Any]],
    name_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    second_value_column: Optional[str] = None,
    filename: str = "bubble_map",
) -> dict[str, Any]:
    """Create a bubble map of Serbia — bubble size represents absolute values.

    Unlike choropleth (which colors by density), bubble maps represent magnitude
    with circle size, avoiding the "large district bias" problem.

    Ideal for: population by district, budget allocation, number of schools.

    Args:
        data: List of row dicts with district names and values
        name_column: District names column
        value_column: Primary numeric value (determines bubble size)
        title: Map title
        theme: Visual theme
        second_value_column: Optional second metric for overlay bubbles
        filename: Output filename

    Returns: Dict with 'filepath', 'districts_matched', 'title'
    """
    builder = _get_advanced_map_builder()
    fig = builder.bubble_map(
        data,
        name_column=name_column,
        value_column=value_column,
        title=title,
        theme=theme,
        second_value_column=second_value_column,
    )

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")

    df = pd.DataFrame(data)
    matched = df[name_column].apply(builder.resolve_name).notna().sum()

    return {"filepath": str(filepath), "districts_matched": int(matched), "title": title}


@mcp.tool()
async def create_multi_layer_map(
    layers: list[dict[str, Any]],
    title: str = "",
    theme: str = "dark",
    filename: str = "multi_layer_map",
) -> dict[str, Any]:
    """Create a multi-layer choropleth map with toggle buttons between layers.

    Each layer is a separate dataset rendered as a choropleth. Toggle buttons
    let users switch between indicators on the same map.

    Args:
        layers: List of layer dicts, each with:
            - 'data': List of row dicts
            - 'name_column': District names column
            - 'value_column': Value column
            - 'label': Display name for this layer
            - 'colorscale': 'blue', 'red', 'heat', or 'diverging'
        title: Map title
        theme: Visual theme
        filename: Output filename

    Returns: Dict with 'filepath', 'layer_count', 'title'
    """
    builder = _get_advanced_map_builder()
    fig = builder.multi_layer_map(layers, title=title, theme=theme)

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")

    return {"filepath": str(filepath), "layer_count": len(layers), "title": title}


# =========================================================================
# Forecasting & Benchmarking Tools
# =========================================================================


@mcp.tool()
async def forecast_data(
    data: list[dict[str, Any]],
    time_column: str,
    value_column: str,
    periods_ahead: int = 5,
    method: str = "linear",
) -> dict[str, Any]:
    """Forecast future values using linear or exponential regression.

    Projects a metric forward by N periods. Useful for "at this rate,
    Serbia will have X by 2030" type insights.

    Args:
        data: List of row dicts with time series data
        time_column: Column with temporal ordering (years, dates)
        value_column: Column with numeric values to forecast
        periods_ahead: Number of future periods to predict
        method: 'linear' or 'exponential'

    Returns: Dict with 'forecast_data', 'growth_rate', 'projection_note',
             'r_squared', 'historical_data', 'trend_line'
    """
    return forecast_linear(
        data,
        time_column=time_column,
        value_column=value_column,
        periods_ahead=periods_ahead,
        method=method,
    )


@mcp.tool()
async def benchmark_data(
    data: list[dict[str, Any]],
    value_column: str,
    entity_column: str,
    benchmarks: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    """Compare data against benchmark values (EU average, regional, custom).

    Computes how each entity compares to reference values, identifying
    above/below performers and generating comparison insights.

    Args:
        data: List of row dicts
        value_column: Numeric column to benchmark
        entity_column: Entity names (districts, cities)
        benchmarks: Dict of benchmark_name → value (e.g., {'EU average': 50000})

    Returns: Dict with 'statistical_benchmarks', 'best_performer', 'worst_performer',
             'comparisons', 'insights'
    """
    return benchmark_comparison(
        data,
        value_column=value_column,
        entity_column=entity_column,
        benchmarks=benchmarks,
    )


@mcp.tool()
async def compare_cross_dataset(
    data_a: list[dict[str, Any]],
    data_b: list[dict[str, Any]],
    value_column_a: str,
    value_column_b: str,
    entity_column_a: Optional[str] = None,
    entity_column_b: Optional[str] = None,
    label_a: str = "Dataset A",
    label_b: str = "Dataset B",
) -> dict[str, Any]:
    """Extract insights by comparing two related datasets.

    Finds correlations, divergences, and rank disagreements between
    two datasets. Useful for "population vs air quality" analyses.

    Args:
        data_a: First dataset
        data_b: Second dataset
        value_column_a: Numeric column in first dataset
        value_column_b: Numeric column in second dataset
        entity_column_a: Entity column in first dataset
        entity_column_b: Entity column in second dataset
        label_a: Label for first dataset
        label_b: Label for second dataset

    Returns: Dict with 'summary_a', 'summary_b', 'correlation', 'insights'
    """
    return cross_dataset_insights(
        data_a,
        data_b,
        value_column_a=value_column_a,
        value_column_b=value_column_b,
        entity_column_a=entity_column_a,
        entity_column_b=entity_column_b,
        label_a=label_a,
        label_b=label_b,
    )


# =========================================================================
# Data Table Tool
# =========================================================================


@mcp.tool()
async def create_data_table(
    data: list[dict[str, Any]],
    columns: Optional[list[str]] = None,
    title: str = "",
    caption: str = "",
    highlight_column: Optional[str] = None,
    highlight_max: bool = True,
    max_rows: int = 50,
    format_columns: Optional[dict[str, str]] = None,
    filename: str = "data_table",
) -> dict[str, Any]:
    """Create a styled, responsive HTML data table.

    Generates a professional data table with conditional formatting,
    ranking indicators, and value formatting. Supports highlighting
    the maximum or minimum value row.

    Ideal for: district statistics tables, budget breakdowns, top-N listings,
    data summaries alongside charts.

    Args:
        data: List of row dicts
        columns: Columns to include (auto-detected if None)
        title: Table title
        caption: Table caption text
        highlight_column: Column to highlight max/min row
        highlight_max: True to highlight max, False for min
        max_rows: Maximum rows to display
        format_columns: Dict of column→format ('number', 'pct', 'currency')
        filename: Output filename

    Returns: Dict with 'filepath', 'title', 'rows', 'columns'
    """
    if not data:
        return {"error": True, "message": "No data to create table"}

    table_html = data_table_html(
        data,
        columns=columns,
        highlight_column=highlight_column,
        highlight_max=highlight_max,
        max_rows=max_rows,
        format_columns=format_columns,
        title=title,
        caption=caption,
    )
    table_css = data_table_css()

    full_html = f"""<!DOCTYPE html>
<html lang="sr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title or 'Data Table'}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #0d1117;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: #e0e0e0;
            padding: 40px 20px;
        }}
        .container {{ max-width: 960px; margin: 0 auto; }}
        {table_css}
    </style>
</head>
<body>
    <div class="container">
        {table_html}
    </div>
</body>
</html>"""

    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(full_html, encoding="utf-8")

    cols = columns or list(data[0].keys())
    return {
        "filepath": str(filepath),
        "title": title,
        "rows": min(len(data), max_rows),
        "total_rows": len(data),
        "columns": cols,
    }


# =========================================================================
# Embed & Share Tools
# =========================================================================


@mcp.tool()
async def generate_embed(
    figure: dict[str, Any],
    width: int = 700,
    height: int = 450,
    title: str = "Chart",
) -> dict[str, Any]:
    """Generate iframe embed code for sharing a chart in websites/blogs.

    Creates a self-contained embed snippet that can be pasted into any
    website, CMS, or HTML document. The chart renders via Plotly.js CDN.

    Args:
        figure: Plotly figure dict (from create_visualization)
        width: Embed width in pixels
        height: Embed height in pixels
        title: Accessible title for the iframe

    Returns: Dict with 'iframe_code', 'html_snippet', 'width', 'height'
    """
    from plotly.graph_objects import Figure

    fig = Figure(figure.get("data", []), figure.get("layout", {}))
    result = generate_embed_code(fig, width=width, height=height, title=title)
    # Don't return the full html_snippet (too large), just the embed code
    return {
        "iframe_code": result["iframe_code"],
        "width": result["width"],
        "height": result["height"],
        "note": "Paste the iframe_code into your HTML to embed the chart.",
    }


@mcp.tool()
async def export_chart_pdf(
    figure: dict[str, Any],
    filename: str = "chart",
    width: int = 1200,
    height: int = 700,
) -> dict[str, Any]:
    """Export a chart figure to PDF file.

    Renders a Plotly figure to a high-quality PDF. Requires kaleido package.
    Install with: pip install kaleido

    Workflow:
        1. create_visualization() → get figure dict
        2. export_chart_pdf(figure, filename='populacija')

    Args:
        figure: Plotly figure dict (from create_visualization)
        filename: Output filename (without .pdf extension)
        width: Page width in pixels (default: 1200)
        height: Page height in pixels (default: 700)

    Returns: Dict with 'filepath' or 'error' if kaleido not installed
    """
    from plotly.graph_objects import Figure

    fig = Figure(figure.get("data", []), figure.get("layout", {}))

    try:
        filepath = await export_pdf(fig, filename=filename, width=width, height=height)
        return {"filepath": filepath, "format": "pdf", "width": width, "height": height}
    except RuntimeError as e:
        return {
            "error": True,
            "message": str(e),
            "note": "Install kaleido with: pip install kaleido",
        }


# =========================================================================
# MCP Resources
# =========================================================================


@mcp.resource("serbian-data://server-info")
def server_info() -> str:
    """Server metadata: version, capabilities, supported formats."""
    return json.dumps(
        {
            "name": "serbian-data",
            "version": __import__("serbian_data_mcp").__version__,
            "description": "MCP server for Serbian open data portal (data.gov.rs)",
            "api_base": config.api_base,
            "supported_formats": ["json", "csv", "xlsx", "xml"],
            "chart_types": [
                "line",
                "bar",
                "pie",
                "scatter",
                "histogram",
                "box",
                "heatmap",
                "treemap",
                "gauge",
                "funnel",
                "animated_line",
                "comparison_bar",
                "sparklines",
                "choropleth_map",
                "bubble_map",
                "multi_layer_map",
                "arrow",
                "dumbbell",
                "lollipop",
                "slope_chart",
                "waffle_chart",
                "population_pyramid",
                "sankey_diagram",
                "radar_chart",
                "animated_bars",
                "animated_timeline",
                "animated_comparison",
                "data_table",
            ],
            "export_formats": ["html", "json", "png", "pdf", "embed"],
            "export_targets": ["local_html", "datawrapper_cloud"],
            "aggregation_functions": ["sum", "mean", "median", "min", "max", "count", "std", "var"],
            "themes": ["dark", "light", "infographic"],
            "special_features": [
                "Serbia choropleth map (25 districts, Natural Earth boundaries)",
                "Arrow chart (directional change with green/red bars)",
                "Dumbbell chart (before/after connected dot comparison)",
                "Lollipop chart (ranking with highlighted dot)",
                "Rich tooltips (mean, rank, % change in hover)",
                "Datawrapper cloud export (professional charts)",
                "Animated bar evolution (smooth time playback)",
                "Animated timeline (bar→line morphing)",
                "Animated dataset comparison (toggle between datasets)",
                "Scrollytelling HTML (scroll-driven data stories)",
                "Auto-insight extraction (shocking facts, outliers, trends)",
                "Data narrative generation (headline + big number + summary)",
                "Derived metrics (YoY%, per-capita, growth rates, index values)",
                "Infographic builder (single-page data story)",
                "Multi-panel dashboard builder",
                "Chart theming (dark/light/infographic)",
                "Annotations and highlight zones for storytelling",
                "Threshold/reference lines for benchmarking",
                "Multiple callout annotations for key data points",
                "Styled data tables with conditional formatting",
                "PDF export for reports and printing",
            ],
        },
        indent=2,
    )


@mcp.resource("serbian-data://portal-stats")
def portal_stats_resource() -> str:
    """Portal statistics and quick-start guide for Serbian open data."""
    return json.dumps(
        {
            "name": "Serbian Open Data Portal",
            "url": "https://data.gov.rs",
            "description": "National open data portal of Republic of Serbia with 3400+ datasets",
            "api_docs": "https://data.gov.rs/api/1/",
            "total_datasets": "3400+",
            "total_organizations": "180+",
            "supported_formats": ["json", "csv", "xlsx", "xls", "xml"],
            "chart_types": ["line", "bar", "pie", "scatter", "histogram", "box"],
            "aggregation_functions": ["sum", "mean", "median", "min", "max", "count", "std", "var"],
            "popular_topics": [
                "Stanovništvo (population)",
                "Budžet (budget)",
                "Obrazovanje (education)",
                "Zdravlje (health)",
                "Životna sredina (environment)",
                "Saobraćaj (transport)",
                "Nekretnine (real estate)",
                "Cene (prices)",
                "Registri (registries)",
            ],
            "key_organizations": [
                "Републички завод за статистику (RZS) — primary statistics publisher",
                "Министарство финансија — budget and public finance",
                "Завод за јавно здравље — air quality monitoring",
            ],
            "workflow": (
                "1. search_datasets → 2. get_dataset → 3. get_dataset_resources → "
                "4. get_resource_data → 5. data_profile → 6. filter/transform → "
                "7. create_visualization → 8. export_visualization"
            ),
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.resource("serbian-data://popular-datasets")
def popular_datasets() -> str:
    """Curated list of popular and interesting datasets from data.gov.rs."""
    return json.dumps(
        {
            "description": "Popular and frequently accessed datasets on the Serbian open data portal",
            "datasets": [
                {
                    "search_term": "stanovništvo",
                    "description": "Population census and demographic data from RZS",
                    "expected_org": "РЗС",
                    "typical_format": "xlsx",
                    "use_cases": ["Population trends", "Age demographics", "Migration data"],
                },
                {
                    "search_term": "budžet",
                    "description": "Government budget execution and planning data",
                    "expected_org": "Министарство финансија",
                    "typical_format": "xlsx",
                    "use_cases": ["Budget analysis", "Spending trends", "Revenue vs expenditure"],
                },
                {
                    "search_term": "kvalitet vazduha",
                    "description": "Air quality monitoring from measuring stations",
                    "expected_org": "Завод за јавно здравље",
                    "typical_format": "xlsx",
                    "use_cases": ["Pollution levels", "PM2.5/PM10 trends", "Station comparisons"],
                },
                {
                    "search_term": "cene",
                    "description": "Consumer price indices and product price monitoring",
                    "expected_org": "РЗС",
                    "typical_format": "xlsx",
                    "use_cases": ["Inflation analysis", "Price comparisons", "Cost of living"],
                },
                {
                    "search_term": "saobraćaj",
                    "description": "Traffic statistics, road data, transport infrastructure",
                    "expected_org": "Various",
                    "typical_format": "csv",
                    "use_cases": ["Traffic accidents", "Road usage", "Infrastructure analysis"],
                },
                {
                    "search_term": "nekretnine",
                    "description": "Real estate prices and property transaction data",
                    "expected_org": "РЗС",
                    "typical_format": "xlsx",
                    "use_cases": ["Price trends", "Regional comparisons", "Market analysis"],
                },
                {
                    "search_term": "obrazovanje",
                    "description": "Education statistics — enrollment, schools, graduates",
                    "expected_org": "РЗС",
                    "typical_format": "xlsx",
                    "use_cases": ["Enrollment trends", "Regional education access", "Graduation rates"],
                },
                {
                    "search_term": "registar",
                    "description": "Public registries — companies, vehicles, permits",
                    "expected_org": "Various",
                    "typical_format": "json",
                    "use_cases": ["Registry analysis", "Permit tracking", "Compliance data"],
                },
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.resource("serbian-data://topics")
def topics() -> str:
    """Available topics and categories from the Serbian data portal."""
    return json.dumps(
        {
            "description": "Main topic categories with suggested search terms",
            "topics": [
                {
                    "category": "Stanovništvo (Population)",
                    "search_terms": ["stanovništvo", "population", "populacija", "census", "popis"],
                    "description": "Census data, demographics, migration, birth/death rates",
                    "key_org": "РЗС",
                },
                {
                    "category": "Javne finansije (Public Finance)",
                    "search_terms": ["budžet", "budget", "finansije", "javne prihodi", "javne rashodi"],
                    "description": "Government budgets, revenue, expenditure",
                    "key_org": "Министарство финансија",
                },
                {
                    "category": "Obrazovanje (Education)",
                    "search_terms": ["obrazovanje", "education", "škole", "učenici", "studenti"],
                    "description": "Schools, enrollment, graduates, literacy rates",
                    "key_org": "РЗС / Министарство просвете",
                },
                {
                    "category": "Zdravlje (Health)",
                    "search_terms": ["zdravlje", "health", "bolnice", "lekovi", "zdravstvena zaštita"],
                    "description": "Healthcare facilities, disease statistics",
                    "key_org": "Министарство здравља",
                },
                {
                    "category": "Životna sredina (Environment)",
                    "search_terms": ["kvalitet vazduha", "vazduh", "zagađenje", "PM10", "PM2.5", "ekologija"],
                    "description": "Air quality, pollution, environmental monitoring",
                    "key_org": "Завод за јавно здравље / Министарство животне средине",
                },
                {
                    "category": "Saobraćaj (Transport)",
                    "search_terms": ["saobraćaj", "transport", "promet", "putevi", "saobraćajne nezgode"],
                    "description": "Traffic data, road infrastructure, accidents",
                    "key_org": "Министарство саobraћaja / АМСС",
                },
                {
                    "category": "Nekretnine (Real Estate)",
                    "search_terms": ["nekretnine", "cene stanova", "nepokretnosti", "zemljište"],
                    "description": "Property prices, real estate transactions",
                    "key_org": "РЗС / Министарство грађевинарства",
                },
                {
                    "category": "Cene (Prices)",
                    "search_terms": ["cene", "prices", "inflacija", "potrošačke cene", "indeks cena"],
                    "description": "Consumer prices, inflation, price indices",
                    "key_org": "РЗС",
                },
                {
                    "category": "Statistika (Statistics)",
                    "search_terms": ["statistika", "statistics", "indikatori", "godišnjak"],
                    "description": "Statistical yearbooks, indicators, economic statistics",
                    "key_org": "РЗС",
                },
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.resource("serbian-data://formats/{format}")
def format_info(format: str) -> str:
    """Information about a specific data format and how it's handled."""
    format_details = {
        "json": {
            "name": "JSON",
            "mime": "application/json",
            "description": "Structured data. Returns list of dicts.",
            "parsing": "Parsed directly — columns are dict keys.",
            "tips": "Best for structured API data.",
        },
        "csv": {
            "name": "CSV",
            "mime": "text/csv",
            "description": "Comma-separated values. Returns list of dicts.",
            "parsing": "Parsed with pandas — handles encodings, separators.",
            "tips": "Column names from first row. May need data_profile().",
        },
        "xlsx": {
            "name": "Excel XLSX",
            "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "description": "Microsoft Excel. First sheet parsed as list of dicts.",
            "parsing": "Parsed with pandas openpyxl engine.",
            "tips": "Most common format on data.gov.rs. Headers often in Serbian Cyrillic.",
        },
        "xls": {
            "name": "Excel XLS",
            "mime": "application/vnd.ms-excel",
            "description": "Legacy Excel format. First sheet parsed.",
            "parsing": "Parsed with pandas xlrd engine.",
            "tips": "Older datasets may use this format.",
        },
        "xml": {
            "name": "XML",
            "mime": "application/xml",
            "description": "Markup language. Parsed into nested dict/list.",
            "parsing": "Parsed with xmltodict — converts to Python dict.",
            "tips": "May have nested structure. Use data_profile() to explore.",
        },
    }
    info = format_details.get(format.lower())
    if info is None:
        return json.dumps({"error": f"Unknown format '{format}'", "supported": list(format_details.keys())}, indent=2)
    return json.dumps(info, indent=2)


@mcp.resource("serbian-data://datasets/{dataset_id}")
async def dataset_resource(dataset_id: str) -> str:
    """Read full metadata for a specific dataset."""
    client = await _get_client()
    dataset = await client.get_dataset(dataset_id)
    if dataset is None:
        return json.dumps({"error": "Dataset not found", "id": dataset_id})
    return json.dumps(_dataset_to_dict(dataset), indent=2)


# =========================================================================
# Intelligent Search & Catalog Tools
# =========================================================================


_catalog_instance: Optional[DatasetCatalog] = None


async def _get_catalog() -> DatasetCatalog:
    """Get or create shared catalog instance."""
    global _catalog_instance
    if _catalog_instance is None:
        _catalog_instance = DatasetCatalog()
        await _catalog_instance.initialize()
    if _catalog_instance is None:  # Type guard for pyright
        _catalog_instance = DatasetCatalog()
        await _catalog_instance.initialize()
    return _catalog_instance


@mcp.tool()
async def intelligent_search(
    query: str, suggest_alternatives: bool = True, max_results: int = 10, min_score: float = 0.3
) -> dict[str, Any]:
    """Search datasets with semantic understanding and fallback suggestions.

    Uses cached catalog for fast results without API rate limits.
    Automatically expands queries with synonyms and translations (Serbian↔English).
    Provides alternative suggestions when no exact match found.

    This is the RECOMMENDED way to search for datasets. Use search_datasets()
    only if you need live API results or specific filters (organization, format).

    Example:
        intelligent_search("population by age")
        intelligent_search("stanovništvo")
        intelligent_search("budžet", suggest_alternatives=True)

    Args:
        query: Search query (Serbian or English both work)
        suggest_alternatives: If True, provide suggestions when no exact match
        max_results: Maximum number of results (1-50, default 10)
        min_score: Minimum relevance score (0.0-1.0, default 0.3)

    Returns:
        Dict with 'results' (list of datasets with relevance scores),
              'total_found', 'query_used', 'expanded_terms',
              and 'suggestions' (if no exact match and suggest_alternatives=True)
    """
    catalog = await _get_catalog()
    search_engine = SearchEngine(catalog)

    # Search with semantic understanding
    results = await search_engine.search(query, max_results=max_results, min_score=min_score)

    response: dict[str, Any] = {
        "results": [r.to_dict() for r in results],
        "total_found": len(results),
        "query": query,
        "expanded_terms": await search_engine.query_expander.expand(query),
    }

    # Provide alternatives if no results
    if not results and suggest_alternatives:
        suggestions = AlternativeSuggestions(catalog, search_engine)
        suggestion_result = await suggestions.suggest(query, max_alternatives=max_results)
        response["suggestions"] = suggestion_result.to_dict()
        response["note"] = "No exact match found. See 'suggestions' for related datasets."

    return response


@mcp.tool()
async def preview_dataset(dataset_id: str, nrows: int = 10) -> dict[str, Any]:
    """Show dataset info with data preview (first N rows).

    Displays dataset metadata and sample data from the first downloadable resource.
    Use this BEFORE downloading full data to understand the structure.

    Workflow:
        1. intelligent_search() → find dataset_id
        2. preview_dataset(dataset_id) → understand structure
        3. get_resource_data(resource_id) → download full data if useful

    Args:
        dataset_id: Dataset identifier (from intelligent_search or search_datasets)
        nrows: Number of rows to preview (1-100, default 10)

    Returns:
        Dict with 'metadata' (dataset info), 'sample_data' (first N rows),
              'columns' (field names), and 'preview_reason'

    Example:
        >>> preview = await preview_dataset("abc123")
        >>> preview["metadata"]["title"]
        "Population by Age"
        >>> preview["sample_data"][0]
        {"age": "0-18", "count": 12345}
        >>> preview["preview_reason"]
        "Showing first 10 rows from CSV resource"
    """
    catalog = await _get_catalog()
    preview = DatasetPreview(catalog)

    try:
        result = await preview.preview_dataset(dataset_id, nrows=nrows)
        return result
    except DatasetNotFound as e:
        return {
            "error": True,
            "message": str(e),
            "dataset_id": dataset_id,
            "note": "Dataset not found in catalog. Try intelligent_search() to find it.",
        }
    except Exception as e:
        return {"error": True, "message": f"Preview failed: {str(e)[:200]}", "dataset_id": dataset_id}


@mcp.tool()
async def refresh_catalog(force: bool = False) -> dict[str, Any]:
    """Refresh dataset catalog cache from data.gov.rs API.

    Fetches all datasets from the API and updates the local cache.
    Use this to get the latest datasets or if the cache is stale.

    Automatic refresh: Cache auto-refreshes every 24 hours on server start.
    Manual refresh: Use this tool when you need fresh data immediately.

    Args:
        force: If True, rebuild catalog even if cache is recent (default False)

    Returns:
        Dict with 'total_datasets', 'cache_path', 'built_at', and 'duration_seconds'

    Example:
        >>> result = await refresh_catalog()
        >>> result["total_datasets"]
        3430
        >>> result["duration_seconds"]
        45.2
    """
    import time

    catalog = await _get_catalog()
    start = time.time()

    try:
        result = await catalog.refresh() if force else await catalog.refresh()
        duration = time.time() - start

        return {**result, "duration_seconds": round(duration, 2), "timestamp": datetime.now(UTC).isoformat()}
    except Exception as e:
        duration = time.time() - start
        return {
            "error": True,
            "message": f"Catalog refresh failed: {str(e)[:200]}",
            "duration_seconds": round(duration, 2),
            "note": "The API may be rate-limited or unavailable. Try again later.",
        }


@mcp.tool()
async def get_catalog_stats() -> dict[str, Any]:
    """Get statistics about the cached dataset catalog.

    Returns information about the catalog including total datasets,
    organizations, formats, and cache age without triggering a refresh.

    Example:
        >>> stats = await get_catalog_stats()
        >>> stats["total_datasets"]
        3430
        >>> stats["total_organizations"]
        182
        >>> stats["cache_age_hours"]
        2.5
    """
    catalog = await _get_catalog()

    # Get organization and format stats
    organizations: set[str] = set()
    formats: set[str] = set()
    downloadable = 0

    for dataset in catalog.get_all():
        if dataset.organization:
            organizations.add(dataset.organization)
        formats.update(dataset.formats)
        if dataset.has_downloadable:
            downloadable += 1

    # Calculate cache age
    cache_age_hours = None
    if catalog.cache_path.exists():
        import os

        cache_mtime = catalog.cache_path.stat().st_mtime
        cache_age = time.time() - cache_mtime
        cache_age_hours = round(cache_age / 3600, 2)

    return {
        "total_datasets": len(catalog),
        "total_organizations": len(organizations),
        "total_formats": len(formats),
        "downloadable_datasets": downloadable,
        "formats": sorted(formats),
        "organizations": sorted(organizations)[:20],  # Show first 20
        "cache_path": str(catalog.cache_path),
        "cache_age_hours": cache_age_hours,
        "cache_exists": catalog.cache_path.exists(),
    }


# =========================================================================
# MCP Prompts
# =========================================================================


@mcp.prompt()
def search_prompt(query: str = "population") -> str:
    """Prompt for searching datasets related to a topic."""
    return (
        f"Search the Serbian data portal (data.gov.rs) for datasets about '{query}'.\n"
        f"Steps:\n"
        f"1. Use suggest_datasets('{query}') to find matching dataset names\n"
        f"2. Use search_datasets(query='{query}') to get the top results\n"
        f"3. For each interesting result, use get_dataset(dataset_id) for full details\n"
        f"4. Use get_dataset_resources(dataset_id) to list available data files\n"
        f"5. Report the top 5 results with descriptions, formats, and available resources"
    )


@mcp.prompt()
def explore_dataset_prompt(dataset_id: str = "") -> str:
    """Prompt for exploring a specific dataset in depth."""
    hint = f" (ID: {dataset_id})" if dataset_id else ""
    return (
        f"Explore a dataset{hint} from the Serbian data portal.\n"
        f"Steps:\n"
        f"1. get_dataset() or search_datasets() to find the dataset\n"
        f"2. get_dataset_resources(dataset_id) to list all data files\n"
        f"3. get_resource_data(resource_id) to download the most relevant file\n"
        f"4. data_profile(data) to understand column structure\n"
        f"5. Suggest what insights could be derived from the data"
    )


@mcp.prompt()
def visualize_prompt(description: str = "Create a chart") -> str:
    """Prompt for creating a visualization from data."""
    return (
        f"{description}\n"
        f"Workflow:\n"
        f"1. search_datasets() → 2. get_dataset_resources() → 3. get_resource_data()\n"
        f"4. data_profile() → 5. filter/transform → 6. create_visualization()\n"
        f"7. export_visualization(format='html') to save"
    )


@mcp.prompt()
def analyze_air_quality_prompt(city: str = "Београд", period: str = "2024") -> str:
    """Prompt for analyzing air quality monitoring data from Serbian cities."""
    return (
        f"Analyze air quality data for {city} in {period}.\n"
        f"1. search_datasets(query='kvalitet vazduha') for air quality datasets\n"
        f"2. Look for datasets from 'Zavod za javno zdravlje'\n"
        f"3. get_resource_data() to download (usually XLS format)\n"
        f"4. data_profile() to understand columns\n"
        f"5. Create line charts of pollutant concentrations over time"
    )


@mcp.prompt()
def population_demographics_prompt(region: str = "Srbija") -> str:
    """Prompt for population demographics analysis."""
    return (
        f"Analyze population demographics for {region}.\n"
        f"1. search_datasets(query='stanovništvo') for population datasets\n"
        f"2. Focus on datasets from РЗС (Републички завод за статистику)\n"
        f"3. get_resource_data() to download (usually XLSX)\n"
        f"4. Create bar charts for age groups, line charts for trends"
    )


@mcp.prompt()
def public_budget_prompt(year: str = "2024", level: str = "republic") -> str:
    """Prompt for public budget analysis."""
    return (
        f"Analyze {level} budget for {year}.\n"
        f"1. search_datasets(query='budžet') for budget datasets\n"
        f"2. Look for execution reports and planned budgets\n"
        f"3. Create pie charts for allocation, grouped bars for planned vs executed"
    )


@mcp.prompt()
def real_estate_prompt(city: str = "Београд") -> str:
    """Prompt for analyzing real estate prices in Serbian cities."""
    return (
        f"Analyze real estate prices for {city}.\n"
        f"1. search_datasets(query='nekretnine' or 'cene stanova')\n"
        f"2. get_resource_data() to download\n"
        f"3. Create line charts for price trends, bar charts by municipality"
    )


@mcp.prompt()
def data_journalism_prompt(topic: str = "Serbian economy") -> str:
    """Prompt for general data journalism exploration workflow."""
    return (
        f"Data journalism: {topic}\n"
        f"Workflow: search_datasets → get_dataset → get_resource_data → data_profile → "
        f"filter/transform → create_visualization → export_visualization → narrate findings"
    )
