"""MCP resources and utility tools.

Resources provide discoverability context for the LLM.
Utility tools for health checks and configuration.
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from typing import Any

from fastmcp.exceptions import ToolError

from .. import mcp, __version__
from ..config import config
from . import _helpers as h


# =========================================================================
# MCP Resources — teach the LLM how to use this server
# =========================================================================


@mcp.resource("serbian-data://guide")
def usage_guide() -> str:
    """Dynamic guide that teaches the LLM the recommended workflow."""
    return json.dumps(
        {
            "server": "serbian-data-mcp",
            "version": __version__,
            "purpose": "Access and visualize 3400+ datasets from the Serbian open data portal (data.gov.rs)",
            "workflow": [
                {"step": 1, "tool": "search_datasets", "purpose": "Find datasets. ALWAYS call first, never guess IDs."},
                {
                    "step": 2,
                    "tool": "get_dataset(detail_level='metadata')",
                    "purpose": "Get full details + resource list.",
                },
                {"step": 3, "tool": "get_resource_data(resource_id)", "purpose": "Download actual data."},
                {
                    "step": 4,
                    "tool": "data_profile(data)",
                    "purpose": "Learn column names and types BEFORE visualizing.",
                },
                {
                    "step": 5,
                    "tool": "transform_data(data, operation)",
                    "purpose": "Filter, group, sort, or select columns.",
                },
                {"step": 6, "tool": "create_chart(data, chart_type, x, y)", "purpose": "Create interactive chart."},
                {"step": 7, "tool": "export_visualization(figure, format)", "purpose": "Save chart to HTML/JSON."},
            ],
            "tips": [
                "Serbian and English queries both work in search_datasets()",
                "Use data_profile() before create_chart() to discover column names",
                "For large datasets, filter before visualizing",
                "Use get_dataset(detail_level='preview') for quick exploration",
                "Chart figure output from create_chart() feeds into apply_chart_theme() and export_visualization()",
            ],
            "return_shapes": {
                "search_datasets": "{datasets: [{id, title, organization, resources}], total, has_next}",
                "get_dataset": "{id, title, description, organization, resources: [{id, title, format, url}], tags}",
                "get_resource_data": "{data: [row_dicts], columns: [...], rows: N}",
                "data_profile": "{columns: [{name, dtype, min?, max?, mean?, sample_values}]}",
                "create_chart": "{figure: <plotly_spec>, chart_type, title}",
            },
        },
        indent=2,
    )


@mcp.resource("serbian-data://popular-datasets")
def popular_datasets() -> str:
    """Curated popular datasets with search terms and use cases."""
    return json.dumps(
        {
            "datasets": [
                {
                    "search_term": "stanovništvo",
                    "description": "Population census data from RZS",
                    "org": "РЗС",
                    "format": "xlsx",
                    "use_cases": ["Population trends", "Age demographics", "Migration"],
                },
                {
                    "search_term": "budžet",
                    "description": "Government budget execution",
                    "org": "Министарство финансија",
                    "format": "xlsx",
                    "use_cases": ["Budget analysis", "Spending trends", "Revenue vs expenditure"],
                },
                {
                    "search_term": "kvalitet vazduha",
                    "description": "Air quality monitoring stations",
                    "org": "Завод за јавно здравље",
                    "format": "xlsx",
                    "use_cases": ["Pollution levels", "PM2.5/PM10 trends"],
                },
                {
                    "search_term": "cene",
                    "description": "Consumer price indices",
                    "org": "РЗС",
                    "format": "xlsx",
                    "use_cases": ["Inflation", "Price comparisons"],
                },
                {
                    "search_term": "nekretnine",
                    "description": "Real estate prices",
                    "org": "РЗС",
                    "format": "xlsx",
                    "use_cases": ["Price trends", "Regional comparisons"],
                },
                {
                    "search_term": "obrazovanje",
                    "description": "Education statistics",
                    "org": "РЗС",
                    "format": "xlsx",
                    "use_cases": ["Enrollment trends", "Graduation rates"],
                },
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.resource("serbian-data://topics")
def topics() -> str:
    """Available topic categories with search terms."""
    return json.dumps(
        {
            "topics": [
                {"category": "Population", "search_terms": ["stanovništvo", "population", "census"]},
                {"category": "Budget", "search_terms": ["budžet", "budget", "javne prihodi"]},
                {"category": "Education", "search_terms": ["obrazovanje", "education", "škole", "studenti"]},
                {"category": "Health", "search_terms": ["zdravlje", "health", "bolnice"]},
                {"category": "Environment", "search_terms": ["kvalitet vazduha", "vazduh", "PM10", "ekologija"]},
                {"category": "Transport", "search_terms": ["saobraćaj", "transport", "promet", "nezgode"]},
                {"category": "Real Estate", "search_terms": ["nekretnine", "cene stanova", "nepokretnosti"]},
                {"category": "Prices", "search_terms": ["cene", "prices", "inflacija", "indeks cena"]},
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.resource("serbian-data://formats/{format}")
def format_info(format: str) -> str:
    """Data format handling info."""
    details = {
        "json": {"name": "JSON", "parsing": "Direct — columns are dict keys.", "tip": "Best for structured API data."},
        "csv": {"name": "CSV", "parsing": "pandas — handles encodings.", "tip": "Headers often in Serbian Cyrillic."},
        "xlsx": {
            "name": "Excel XLSX",
            "parsing": "pandas openpyxl engine.",
            "tip": "Most common format on data.gov.rs.",
        },
        "xls": {"name": "Excel XLS", "parsing": "pandas xlrd engine.", "tip": "Older datasets."},
        "xml": {"name": "XML", "parsing": "xmltodict → dict/list.", "tip": "May be nested — use data_profile()."},
    }
    info = details.get(format.lower())
    if info is None:
        return json.dumps({"error": f"Unknown format '{format}'", "supported": list(details.keys())}, indent=2)
    return json.dumps(info, indent=2)


@mcp.resource("serbian-data://server-info")
def server_info() -> str:
    """Server metadata."""
    return json.dumps(
        {
            "name": "serbian-data",
            "version": __version__,
            "description": "MCP server for Serbian open data portal (data.gov.rs)",
            "api_base": config.api_base,
            "supported_formats": ["json", "csv", "xlsx", "xls", "xml"],
            "chart_types": [
                "line", "bar", "pie", "scatter", "histogram", "box",
                "heatmap", "treemap", "gauge", "funnel",
                "animated_line", "comparison_bar", "sparklines",
                "choropleth_map", "bubble_map", "multi_layer_map",
                "arrow", "dumbbell", "lollipop",
                "slope_chart", "waffle_chart", "population_pyramid",
                "sankey_diagram", "radar_chart",
                "animated_bars", "animated_timeline", "animated_comparison",
                "scrollytelling", "data_table",
            ],
            "export_formats": ["html", "json", "csv", "xlsx", "pdf", "embed"],
            "themes": ["dark", "light", "infographic"],
        },
        indent=2,
    )


# =========================================================================
# Utility tools
# =========================================================================


@mcp.tool()
async def health_check() -> dict[str, Any]:
    """Check server health and API connectivity."""
    api_reachable = False
    try:
        client = await h.get_client()
        await client.list_organizations(page_size=1)
        api_reachable = True
    except Exception:
        pass
    return {
        "status": "healthy",
        "api_reachable": api_reachable,
        "version": __version__,
        "timestamp": datetime.now(UTC).isoformat(),
    }
