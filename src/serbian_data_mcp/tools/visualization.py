"""Visualization tools.

Contracts:
  - create_chart(data, chart_type, ...) → Plotly figure dict
  - apply_theme(figure, ...) → themed figure dict
  - build_infographic(data, ...) → HTML file
  - build_dashboard(panels, ...) → HTML file
"""

from __future__ import annotations

from typing import Any, Optional

from fastmcp.exceptions import ToolError

from .. import mcp
from ..config import config
from ..viz.charts import ChartBuilder
from ..viz.exporters import fig_to_dict
from ..viz.themes import apply_theme, add_annotation, add_highlight_zone
from ..viz.advanced_charts import AdvancedChartBuilder
from ..viz.infographics import create_infographic, create_dashboard
from ..viz.tooltips import add_rich_tooltips, add_annotation_callouts, add_comparison_markers
from ..viz.data_tables import data_table_html, data_table_css


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
    comparison_columns: list[str] = [],
    trend_column: str = "",
    top_n: int = 10,
    open_column: str = "",
    high_column: str = "",
    low_column: str = "",
    close_column: str = "",
    a_column: str = "",
    b_column: str = "",
    c_column: str = "",
    columns: list[str] = [],
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
      - "violin": y_column (+ optional x_column) → distribution shape + density
      - "waterfall": x_column + values_column → cumulative running-total bridge
      - "candlestick": open/high/low/close columns → OHLC price candles
      - "ternary": a/b/c columns → 3-part compositional mixture triangle
      - "splom": columns (list) → pairwise scatter matrix for N variables
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
        "violin",
        "waterfall",
        "candlestick",
        "ternary",
        "splom",
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
            open_column=open_column,
            high_column=high_column,
            low_column=low_column,
            close_column=close_column,
            a_column=a_column,
            b_column=b_column,
            c_column=c_column,
            columns=columns,
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
    comparison_columns: list[str] = [],
    trend_column: str = "",
    top_n: int = 10,
    open_column: str = "",
    high_column: str = "",
    low_column: str = "",
    close_column: str = "",
    a_column: str = "",
    b_column: str = "",
    c_column: str = "",
    columns: list[str] = [],
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

    if chart_type == "violin":
        if not y_column:
            raise ToolError("violin requires y_column")
        return builder.violin(y_column, x_column=x_column or None, title=title, theme=theme)

    if chart_type == "waterfall":
        if not x_column or not values_column:
            raise ToolError("waterfall requires x_column and values_column")
        return builder.waterfall(x_column, values_column, title=title, theme=theme)

    if chart_type == "candlestick":
        if not open_column or not high_column or not low_column or not close_column:
            raise ToolError("candlestick requires open_column, high_column, low_column, and close_column")
        return builder.candlestick(
            open_column,
            high_column,
            low_column,
            close_column,
            title=title,
            theme=theme,
            x_column=x_column or None,
        )

    if chart_type == "ternary":
        if not a_column or not b_column or not c_column:
            raise ToolError("ternary requires a_column, b_column, and c_column")
        return builder.ternary(
            a_column,
            b_column,
            c_column,
            title=title,
            theme=theme,
            color_column=color_column,
            size_column=size_column,
        )

    if chart_type == "splom":
        if not columns or len(columns) < 2:
            raise ToolError("splom requires columns (list of 2 or more)")
        return builder.splom(
            columns,
            title=title,
            theme=theme,
            color_column=color_column,
            size_column=size_column,
        )

    if chart_type == "animated_line":
        if not x_column or not y_column or not frame_column:
            raise ToolError("animated_line requires x_column, y_column, and frame_column")
        return builder.animated_line(
            x_column, y_column, frame_column, title=title, theme=theme, category_column=category_column
        )

    if chart_type == "comparison_bar":
        if not x_column or len(comparison_columns) != 2:
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
    annotations: list[dict[str, Any]] = [],
    highlight_zones: list[dict[str, Any]] = [],
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


@mcp.tool()
async def enhance_chart_tooltips(
    figure: dict[str, Any],
    value_column: str = "value",
    unit: str = "",
    show_mean: bool = True,
    show_rank: bool = True,
) -> dict[str, Any]:
    """Add rich contextual tooltips to any Plotly figure.

    Enriches hover with formatted values, deviation from mean, and rank.
    Without: 'Value: 7150000'. With: 'Value: 7.15M / Prosečno: 4.2M / Rank: #1'.

    Returns: Enhanced figure dict

    Args:
        figure: Plotly figure dict from create_chart()
        value_column: Name of the value axis
        unit: Unit suffix (e.g., ' stanovnika', ' RSD')
        show_mean: Show average and deviation
        show_rank: Show rank position
    """
    from plotly.graph_objects import Figure

    try:
        fig = Figure(figure.get("data", []), figure.get("layout", {}))
        fig = add_rich_tooltips(
            fig,
            value_column=value_column,
            unit=unit,
            show_mean=show_mean,
            show_rank=show_rank,
        )
        return fig_to_dict(fig)
    except Exception as e:
        raise ToolError(f"Tooltip enhancement failed: {e}") from e


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
    """Add a callout annotation to a chart for storytelling.

    Text box with optional arrow pointing to a data point.

    Workflow:
        1. create_chart() → figure dict
        2. add_chart_annotation(figure, text='Peak: 7.2M', x=2022, y=7200000)

    Returns: Enhanced figure dict

    Args:
        figure: Plotly figure dict from create_chart()
        text: Annotation text
        x: X position (data coordinate)
        y: Y position (data coordinate)
        arrow_color: Arrow color (default: gold)
        font_size: Text size
        show_arrow: Show arrow pointing to data
    """
    from plotly.graph_objects import Figure

    try:
        fig = Figure(figure.get("data", []), figure.get("layout", {}))
        fig = add_annotation(
            fig, text=text, x=x, y=y, arrow_color=arrow_color, font_size=font_size, show_arrow=show_arrow
        )
        return fig_to_dict(fig)
    except Exception as e:
        raise ToolError(f"Annotation failed: {e}") from e


@mcp.tool()
async def add_chart_highlight_zone(
    figure: dict[str, Any],
    x_start: float | str,
    x_end: float | str,
    fill_color: str = "rgba(198, 40, 40, 0.1)",
    annotation_text: str = "",
) -> dict[str, Any]:
    """Add a shaded vertical highlight zone to a chart.

    Highlights a time period with a colored band.
    Ideal for: COVID years, crisis periods, policy changes.

    Returns: Enhanced figure dict

    Args:
        figure: Plotly figure dict from create_chart()
        x_start: Start of zone
        x_end: End of zone
        fill_color: RGBA fill color
        annotation_text: Optional label above the zone
    """
    from plotly.graph_objects import Figure

    try:
        fig = Figure(figure.get("data", []), figure.get("layout", {}))
        fig = add_highlight_zone(
            fig, x_start=x_start, x_end=x_end, fill_color=fill_color, annotation_text=annotation_text
        )
        return fig_to_dict(fig)
    except Exception as e:
        raise ToolError(f"Highlight zone failed: {e}") from e


@mcp.tool()
async def add_chart_callouts(
    figure: dict[str, Any],
    points: list[dict[str, Any]],
    prefix: str = "",
    suffix: str = "",
) -> dict[str, Any]:
    """Add multiple annotation callout boxes to highlight data points.

    Each box has arrow pointing to data. Points: {x, y, text, color?, ax?, ay?}

    Returns: Enhanced figure dict

    Args:
        figure: Plotly figure dict from create_chart()
        points: List of {x, y, text, color?} dicts
        prefix: Text before each callout
        suffix: Text after each callout
    """
    from plotly.graph_objects import Figure

    try:
        fig = Figure(figure.get("data", []), figure.get("layout", {}))
        fig = add_annotation_callouts(fig, points=points, prefix=prefix, suffix=suffix)
        return fig_to_dict(fig)
    except Exception as e:
        raise ToolError(f"Callouts failed: {e}") from e


@mcp.tool()
async def add_chart_threshold_line(
    figure: dict[str, Any],
    threshold: float,
    label: str = "",
    direction: str = "above",
    color: str = "#ffab00",
) -> dict[str, Any]:
    """Add a horizontal threshold/reference line with label.

    Ideal for: EU average benchmark, target/goal line, critical threshold.

    Returns: Enhanced figure dict

    Args:
        figure: Plotly figure dict from create_chart()
        threshold: Y-value of the line
        label: Label text
        direction: 'above' or 'below'
        color: Line color (default: gold)
    """
    from plotly.graph_objects import Figure

    try:
        fig = Figure(figure.get("data", []), figure.get("layout", {}))
        fig = add_comparison_markers(fig, threshold=threshold, label=label, direction=direction, color=color)
        return fig_to_dict(fig)
    except Exception as e:
        raise ToolError(f"Threshold line failed: {e}") from e


@mcp.tool()
async def create_data_table(
    data: list[dict[str, Any]],
    columns: list[str] = [],
    title: str = "",
    caption: str = "",
    highlight_column: Optional[str] = None,
    highlight_max: bool = True,
    max_rows: int = 50,
    format_columns: Optional[dict[str, str]] = None,
    filename: str = "data_table",
) -> dict[str, Any]:
    """Create a styled, responsive HTML data table with conditional formatting.

    Professional table with ranking indicators and value formatting.
    Highlights max or min value row.

    Ideal for: district statistics, budget breakdowns, top-N listings.

    Returns: {filepath, title, rows, total_rows, columns}

    Args:
        data: Row dicts
        columns: Columns to include (auto-detected if None)
        title: Table title
        caption: Table caption text
        highlight_column: Column to highlight max/min row
        highlight_max: True=max, False=min
        max_rows: Maximum rows to display
        format_columns: {column: 'number'|'pct'|'currency'}
        filename: Output filename
    """
    if not data:
        raise ToolError("No data to create table")

    try:
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
    <title>{title or "Data Table"}</title>
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
    except Exception as e:
        raise ToolError(f"Data table failed: {e}") from e
