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
            "chart_types": ["line", "bar", "pie", "scatter", "histogram", "box"],
            "export_formats": ["html", "json"],
            "aggregation_functions": ["sum", "mean", "median", "min", "max", "count", "std", "var"],
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
    query: str,
    suggest_alternatives: bool = True,
    max_results: int = 10,
    min_score: float = 0.3
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
    results = await search_engine.search(
        query,
        max_results=max_results,
        min_score=min_score
    )

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
            "note": "Dataset not found in catalog. Try intelligent_search() to find it."
        }
    except Exception as e:
        return {
            "error": True,
            "message": f"Preview failed: {str(e)[:200]}",
            "dataset_id": dataset_id
        }


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

        return {
            **result,
            "duration_seconds": round(duration, 2),
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        duration = time.time() - start
        return {
            "error": True,
            "message": f"Catalog refresh failed: {str(e)[:200]}",
            "duration_seconds": round(duration, 2),
            "note": "The API may be rate-limited or unavailable. Try again later."
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
        "cache_exists": catalog.cache_path.exists()
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
