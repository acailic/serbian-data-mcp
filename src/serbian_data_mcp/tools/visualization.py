"""Visualization tools.

Contracts:
  - create_chart(data, chart_type, ...) → Plotly figure dict
  - apply_theme(figure, ...) → themed figure dict
  - build_infographic(data, ...) → HTML file
  - build_dashboard(panels, ...) → HTML file
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from fastmcp.exceptions import ToolError

from .. import mcp
from ..config import config
from ..exceptions import VisualizationError
from ..viz.charts import ChartBuilder
from ..viz.exporters import export_html, export_json, fig_to_dict
from ..viz.themes import apply_theme, add_annotation, add_highlight_zone
from ..viz.advanced_charts import AdvancedChartBuilder
from ..viz.insights import extract_insights, generate_narrative, compute_derived_metrics
from ..viz.infographics import create_infographic, create_dashboard
from . import _helpers as h


@mcp.tool()
async def create_chart(
    data: list[dict[str, Any]],
    chart_type: str = "line",
    x_column: str = "",
    y_column: str = "",
    values_column: str = "",
    names_column: str = "",
    color_column: Optional[str] = None,
    size_column: Optional[str] = None,
    title: str = "",
    orientation: str = "v",
    bins: Optional[int] = None,
    # Advanced chart params
    z_column: str = "",
    hierarchy_column: Optional[str] = None,
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
    """Create interactive charts from data. Supports 20+ chart types.

    BASIC CHARTS (most common):
      - "line": x_column + y_column → time series, trends
      - "bar": x_column + y_column → comparisons, rankings
      - "pie": values_column + names_column → proportions
      - "scatter": x_column + y_column → correlations
      - "histogram": x_column or y_column → frequency distributions
      - "box": y_column (+ optional x_column) → statistical distributions

    ADVANCED CHARTS:
      - "heatmap": x_column + y_column + z_column → correlation/heat grids
      - "treemap": names_column + values_column → nested breakdowns
      - "gauge": value (float, 0-100) → single metric display
      - "funnel": names_column + values_column → cascading flow
      - "animated_line": x_column + y_column + frame_column → time playback
      - "comparison_bar": x_column + comparison_columns (2 cols) → side-by-side
      - "sparklines": y_column + x_column + trend_column → faceted mini-charts

    TIP: Use data_profile() first to discover column names.

    Returns: {figure: <plotly_spec>, type: "plotly", interactive: true, chart_type, title}

    Args:
        data: Row dicts from get_resource_data()
        chart_type: Chart type (see above)
        x_column: X-axis column (line, bar, scatter, histogram)
        y_column: Y-axis column (line, bar, scatter, box)
        values_column: Numeric values column (pie, treemap, funnel)
        names_column: Category labels (pie, treemap, funnel)
        color_column: Optional color grouping
        size_column: Optional bubble sizes (scatter)
        title: Chart title
        orientation: Bar direction: "v" (vertical) or "h" (horizontal)
        bins: Histogram bins (default auto)
        z_column: Heat values (heatmap)
        hierarchy_column: Treemap parent column
        theme: 'dark', 'light', or 'infographic'
        value: Single numeric value for gauge (0-100)
        min_val / max_val: Gauge range
        label: Gauge label
        frame_column: Animation time column
        category_column: Animation grouping
        comparison_columns: 2 column names for comparison_bar
        trend_column: Sparkline time column
        top_n: Max entities for sparklines
    """
    all_types = {
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
    }
    if chart_type not in all_types:
        raise ToolError(f"Unsupported chart type '{chart_type}'. Use: {', '.join(sorted(all_types))}")

    try:
        fig = _build_chart(
            data=data,
            chart_type=chart_type,
            x_column=x_column,
            y_column=y_column,
            values_column=values_column,
            names_column=names_column,
            color_column=color_column,
            size_column=size_column,
            title=title,
            orientation=orientation,
            bins=bins,
            z_column=z_column,
            hierarchy_column=hierarchy_column,
            theme=theme,
            value=value,
            min_val=min_val,
            max_val=max_val,
            label=label,
            frame_column=frame_column,
            category_column=category_column,
            comparison_columns=comparison_columns,
            trend_column=trend_column,
            top_n=top_n,
        )
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Failed to create {chart_type} chart: {e}") from e

    if fig is None:
        raise ToolError(f"Failed to create {chart_type} chart")

    return {"figure": fig_to_dict(fig), "type": "plotly", "interactive": True, "chart_type": chart_type, "title": title}


def _build_chart(
    data: list[dict[str, Any]],
    chart_type: str,
    x_column: str,
    y_column: str,
    values_column: str,
    names_column: str,
    color_column: Optional[str],
    size_column: Optional[str],
    title: str,
    orientation: str,
    bins: Optional[int],
    z_column: str,
    hierarchy_column: Optional[str],
    theme: str,
    value: Optional[float],
    min_val: float,
    max_val: float,
    label: str,
    frame_column: str,
    category_column: Optional[str],
    comparison_columns: Optional[list[str]],
    trend_column: str,
    top_n: int,
):
    """Build the right chart type. Returns Plotly Figure or raises ToolError."""
    if chart_type == "line":
        if not x_column or not y_column:
            raise ToolError("line chart requires x_column and y_column")
        return ChartBuilder(data).line_chart(x_column, y_column, title=title, color_column=color_column)

    if chart_type == "bar":
        if not x_column or not y_column:
            raise ToolError("bar chart requires x_column and y_column")
        return ChartBuilder(data).bar_chart(
            x_column, y_column, title=title, color_column=color_column, orientation=orientation
        )

    if chart_type == "pie":
        if not values_column or not names_column:
            raise ToolError("pie chart requires values_column and names_column")
        return ChartBuilder(data).pie_chart(values_column, names_column, title=title)

    if chart_type == "scatter":
        if not x_column or not y_column:
            raise ToolError("scatter plot requires x_column and y_column")
        return ChartBuilder(data).scatter_plot(
            x_column, y_column, title=title, color_column=color_column, size_column=size_column
        )

    if chart_type == "histogram":
        col = x_column or y_column
        if not col:
            raise ToolError("histogram requires x_column or y_column")
        return ChartBuilder(data).histogram(col, title=title, bins=bins)

    if chart_type == "box":
        if not y_column:
            raise ToolError("box plot requires y_column")
        return ChartBuilder(data).box_plot(y_column, x_column=x_column, title=title)

    builder = AdvancedChartBuilder(data)

    if chart_type == "heatmap":
        if not x_column or not y_column or not z_column:
            raise ToolError("heatmap requires x_column, y_column, and z_column")
        return builder.heatmap(x_column, y_column, z_column, title=title, theme=theme)

    if chart_type == "treemap":
        if not names_column or not values_column:
            raise ToolError("treemap requires names_column and values_column")
        return builder.treemap(
            names_column,
            values_column,
            title=title,
            theme=theme,
            color_column=color_column,
            hierarchy_column=hierarchy_column,
        )

    if chart_type == "gauge":
        if value is None:
            raise ToolError("gauge requires 'value' parameter (float, 0-100)")
        return builder.gauge(value, title=title, theme=theme, min_val=min_val, max_val=max_val, label=label)

    if chart_type == "funnel":
        if not names_column or not values_column:
            raise ToolError("funnel requires names_column and values_column")
        return builder.funnel(names_column, values_column, title=title, theme=theme)

    if chart_type == "animated_line":
        if not x_column or not y_column or not frame_column:
            raise ToolError("animated_line requires x_column, y_column, and frame_column")
        return builder.animated_line(
            x_column, y_column, frame_column, title=title, theme=theme, category_column=category_column
        )

    if chart_type == "comparison_bar":
        if not x_column or not comparison_columns or len(comparison_columns) != 2:
            raise ToolError("comparison_bar requires x_column and comparison_columns (list of 2)")
        return builder.comparison_bar(x_column, comparison_columns, title=title, theme=theme)

    if chart_type == "sparklines":
        if not y_column or not x_column:
            raise ToolError("sparklines requires x_column and y_column")
        return builder.sparkline_container(
            y_column, x_column, trend_column, title=title, theme=theme, sort_by=x_column, top_n=top_n
        )

    return None


@mcp.tool()
async def apply_chart_theme(
    figure: dict[str, Any],
    theme: str = "dark",
    annotations: Optional[list[dict[str, Any]]] = None,
    highlight_zones: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Apply visual theme to a chart figure from create_chart().

    Themes: 'dark' (data-journalism), 'light' (clean), 'infographic' (large type).
    Add annotations: [{"text": "...", "x": val, "y": val}] for callouts.
    Add zones: [{"x_start": val, "x_end": val, "label": "..."}] for highlights.

    Args:
        figure: Plotly figure dict from create_chart()
        theme: 'dark', 'light', or 'infographic'
        annotations: Callout annotations
        highlight_zones: Shaded highlight regions
    """
    from plotly.graph_objects import Figure

    try:
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
    except Exception as e:
        raise ToolError(f"Theming failed: {e}") from e


@mcp.tool()
async def build_infographic(
    data: list[dict[str, Any]],
    title: str = "Serbian Data Story",
    chart_type: str = "bar",
    x_column: str = "",
    y_column: str = "",
    theme: str = "infographic",
    time_column: Optional[str] = None,
    entity_column: Optional[str] = None,
    filename: str = "infographic",
) -> dict[str, Any]:
    """Create a complete infographic HTML: headline + big number + chart + insights.

    Self-contained HTML with responsive design. Opens in any browser.
    Saved to exports/ directory.

    Returns: {filepath, metadata, insights, headline}

    Args:
        data: Row dicts from get_resource_data()
        title: Infographic title
        chart_type: Main chart (line, bar, pie, scatter, histogram, box)
        x_column: X-axis column
        y_column: Y-axis column
        theme: 'dark', 'light', or 'infographic'
        time_column: Optional time column for insight extraction
        entity_column: Optional entity column for insight extraction
        filename: Output filename (without .html)
    """
    try:
        result = create_infographic(
            data,
            title=title,
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
    except Exception as e:
        raise ToolError(f"Infographic failed: {e}") from e


@mcp.tool()
async def build_dashboard(
    panels: list[dict[str, Any]],
    title: str = "Serbia Data Dashboard",
    filename: str = "dashboard",
) -> dict[str, Any]:
    """Build multi-panel dashboard HTML. Each panel: chart, HTML, or big number.

    Panel types:
      - Chart: {"type": "chart", "title": "...", "figure": <plotly_dict>, "span": 1}
      - HTML: {"type": "html", "title": "...", "content": "<p>...</p>", "span": 1}
      - Big number: {"type": "big_number", "number": "7M", "label": "Population", "color": "red"}
    span=2 takes full row, span=1 is half width.

    Returns: {filepath, panel_count, filename}

    Args:
        panels: List of panel dicts
        title: Dashboard title
        filename: Output filename (without .html)
    """
    try:
        html = create_dashboard(panels, title=title)
        output_dir = config.export_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / f"{filename}.html"
        filepath.write_text(html, encoding="utf-8")
        return {"filepath": str(filepath), "panel_count": len(panels), "filename": f"{filename}.html"}
    except Exception as e:
        raise ToolError(f"Dashboard failed: {e}") from e
