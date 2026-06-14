"""Infographic builder — creates single-page "big number + chart + insight" HTML pages.

Generates standalone, visually striking HTML files that present data
as a story: headline, big number, supporting chart, and auto-generated
narrative insights.
"""

import contextlib
import json
from pathlib import Path
from typing import Any, Optional

import plotly.graph_objects as go
import pandas as pd

from .charts import ChartBuilder
from .themes import (
    apply_theme,
    SERBIAN_PALETTE,
    add_annotation,
    add_highlight_zone,
    infographic_template,
)


# ── HTML Templates ──────────────────────────────────────────────────────────

_DARK_STYLES = """
:root {
    --bg-primary: #1a1a2e;
    --bg-secondary: #16213e;
    --bg-card: rgba(22, 33, 62, 0.9);
    --text-primary: #ffffff;
    --text-secondary: #b0bec5;
    --accent-red: #c62828;
    --accent-blue: #1565c0;
    --accent-gold: #ffab00;
    --accent-green: #2e7d32;
    --border: rgba(255,255,255,0.08);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: var(--bg-primary);
    color: var(--text-primary);
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    line-height: 1.6;
    min-height: 100vh;
}
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 40px 24px;
}
.header {
    text-align: center;
    margin-bottom: 48px;
    padding-bottom: 32px;
    border-bottom: 2px solid var(--border);
}
.header h1 {
    font-size: 2.5rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin-bottom: 8px;
    background: linear-gradient(135deg, var(--text-primary), var(--accent-gold));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.header .subtitle {
    font-size: 1.1rem;
    color: var(--text-secondary);
    max-width: 700px;
    margin: 0 auto;
}
.big-number-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 24px;
    margin-bottom: 48px;
}
.big-number-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px 24px;
    text-align: center;
    transition: transform 0.2s, border-color 0.2s;
}
.big-number-card:hover {
    transform: translateY(-4px);
    border-color: var(--accent-gold);
}
.big-number-card .number {
    font-size: 3rem;
    font-weight: 900;
    letter-spacing: -0.03em;
    line-height: 1.1;
}
.big-number-card .label {
    font-size: 0.9rem;
    color: var(--text-secondary);
    margin-top: 8px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.big-number-card.red .number { color: var(--accent-red); }
.big-number-card.blue .number { color: var(--accent-blue); }
.big-number-card.gold .number { color: var(--accent-gold); }
.big-number-card.green .number { color: var(--accent-green); }
.chart-section {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px;
    margin-bottom: 32px;
}
.chart-section h2 {
    font-size: 1.4rem;
    font-weight: 700;
    margin-bottom: 20px;
    color: var(--accent-gold);
}
.insights-section {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px;
    margin-bottom: 32px;
}
.insights-section h2 {
    font-size: 1.4rem;
    font-weight: 700;
    margin-bottom: 20px;
    color: var(--accent-gold);
}
.insight-item {
    padding: 16px 0;
    border-bottom: 1px solid var(--border);
}
.insight-item:last-child { border-bottom: none; }
.insight-item .insight-headline {
    font-size: 1.15rem;
    font-weight: 700;
    margin-bottom: 6px;
}
.insight-item .insight-detail {
    font-size: 0.95rem;
    color: var(--text-secondary);
    line-height: 1.5;
}
.insight-item.critical .insight-headline { color: var(--accent-red); }
.insight-item.high .insight-headline { color: var(--accent-red); }
.insight-item.medium .insight-headline { color: var(--accent-gold); }
.insight-item.low .insight-headline { color: var(--accent-blue); }
.severity-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-left: 8px;
    vertical-align: middle;
}
.severity-badge.critical { background: var(--accent-red); color: white; }
.severity-badge.high { background: rgba(198,40,40,0.3); color: #ef9a9a; }
.severity-badge.medium { background: rgba(255,171,0,0.2); color: var(--accent-gold); }
.severity-badge.low { background: rgba(21,101,192,0.2); color: #90caf9; }
.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
    gap: 24px;
    margin-bottom: 32px;
}
.footer {
    text-align: center;
    padding-top: 32px;
    border-top: 1px solid var(--border);
    color: var(--text-secondary);
    font-size: 0.85rem;
}
.plotly-chart { width: 100%; min-height: 450px; }
@media (max-width: 768px) {
    .header h1 { font-size: 1.8rem; }
    .big-number-card .number { font-size: 2.2rem; }
    .dashboard-grid { grid-template-columns: 1fr; }
    .container { padding: 24px 16px; }
}
"""

_PLOTLY_CDN = "https://cdn.plot.ly/plotly-3.6.0.min.js"

_JS_CHART_RENDERER = """
function renderChart(containerId, figureJson) {
    const container = document.getElementById(containerId);
    if (!container) return;
    Plotly.newPlot(containerId, figureJson.data, figureJson.layout, {responsive: true, displayModeBar: false});
}
"""


def _build_html(
    title: str,
    subtitle: str,
    body_html: str,
    chart_specs: Optional[list[tuple[str, dict]]] = None,
) -> str:
    """Build a complete infographic HTML page.

    Args:
        title: Page title
        subtitle: Subtitle text
        body_html: HTML for the body content (big numbers, insights)
        chart_specs: List of (container_id, plotly_figure_dict) tuples

    Returns:
        Complete HTML string
    """
    chart_render_js = ""
    if chart_specs:
        for container_id, fig_dict in chart_specs:
            json_str = json.dumps(fig_dict, default=str)
            chart_render_js += f"renderChart('{container_id}', {json_str});\n"

    return f"""<!DOCTYPE html>
<html lang="sr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="{_PLOTLY_CDN}" charset="utf-8"></script>
    <style>{_DARK_STYLES}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p class="subtitle">{subtitle}</p>
        </div>
        {body_html}
        <div class="footer">
            🇷🇸 Serbian Open Data — data.gov.rs | Generated with serbian-data-mcp
        </div>
    </div>
    <script>{_JS_CHART_RENDERER}</script>
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        {chart_render_js}
    }});
    </script>
</body>
</html>"""


def create_infographic(
    data: list[dict[str, Any]],
    title: str = "Serbian Data Story",
    subtitle: str = "",
    chart_type: str = "bar",
    x_column: str = "",
    y_column: str = "",
    theme: str = "infographic",
    time_column: str | None = None,
    entity_column: str | None = None,
    annotations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a complete infographic page: big number + chart + insights.

    Auto-generates insights, formats them into a visually striking
    single-page HTML with a dark data-journalism aesthetic.

    Args:
        data: List of row dicts
        title: Infographic title
        subtitle: Subtitle text
        chart_type: Type of main chart (line, bar, pie, scatter, histogram, box)
        x_column: X axis column
        y_column: Y axis column
        theme: 'dark', 'light', or 'infographic'
        highlight_entity: Entity name to highlight in the chart
        time_column: Optional time column for insight extraction
        entity_column: Optional entity column for insight extraction
        annotations: Optional list of annotation dicts with 'text', 'x', 'y'

    Returns:
        Dict with 'html' (full page HTML), 'insights', 'chart_figure', 'metadata'
    """
    from .insights import generate_narrative, extract_insights

    if not data:
        return {"error": "No data provided", "html": "", "insights": [], "chart_figure": None, "metadata": {}}

    # Generate insights
    narrative = generate_narrative(
        data, title=title, time_column=time_column, entity_column=entity_column, max_insights=8
    )
    insights = narrative.get("insights", [])

    # Build chart
    df = pd.DataFrame(data)
    fig = None

    if x_column and y_column:
        builder = ChartBuilder(data)
        chart_fn = getattr(builder, f"{chart_type}_chart", None)
        if chart_fn:
            kwargs = {"x_column": x_column, "y_column": y_column, "title": ""}
            if chart_type == "pie":
                kwargs = {"values_column": y_column, "names_column": x_column, "title": ""}
            with contextlib.suppress(Exception):
                fig = chart_fn(**kwargs)
        else:
            fig = None

    if fig is None and x_column and y_column:
        try:
            fig = go.Figure(data=[go.Bar(x=df[x_column], y=df[y_column])])
        except Exception:
            fig = go.Figure()

    if fig is None:
        fig = go.Figure()

    # Apply theme
    apply_theme(fig, theme)

    # Add annotations
    if annotations:
        for ann in annotations:
            fig = add_annotation(fig, ann["text"], ann.get("x", 0), ann.get("y", 0))

    fig.update_layout(margin={"l": 60, "r": 30, "t": 30, "b": 60}, showlegend=True)
    fig_dict = json.loads(fig.to_json())

    # Build big number cards
    big_number_cards = ""
    if narrative.get("big_number") is not None:
        color_class = "red"
        if isinstance(narrative["big_number"], (int, float)):
            if narrative["big_number"] > 0:
                color_class = "gold"
            elif narrative["big_number"] < 0:
                color_class = "red"
            else:
                color_class = "blue"

        number_display = narrative["big_number"]
        if isinstance(number_display, float):
            if abs(number_display) < 1 and number_display != 0:
                number_display = f"{number_display:.1%}"
            elif abs(number_display) > 100:
                if abs(number_display) >= 1_000_000:
                    number_display = f"{number_display / 1_000_000:.1f}M"
                elif abs(number_display) >= 1_000:
                    number_display = f"{number_display / 1_000:.1f}K"
                else:
                    number_display = f"{number_display:,.0f}"

        big_number_cards = f"""
        <div class="big-number-grid">
            <div class="big-number-card {color_class}">
                <div class="number">{number_display}</div>
                <div class="label">{narrative.get("big_label", title)}</div>
            </div>
        </div>"""

    # Build insights HTML
    insights_html = ""
    if insights:
        items = ""
        for insight in insights:
            sev = insight.get("severity", "medium")
            items += f"""
            <div class="insight-item {sev}">
                <div class="insight-headline">
                    {insight.get("headline", "")}
                    <span class="severity-badge {sev}">{sev}</span>
                </div>
                <div class="insight-detail">{insight.get("detail", "")}</div>
            </div>"""
        insights_html = f"""
        <div class="insights-section">
            <h2>📊 Key Findings</h2>
            {items}
        </div>"""

    # Build summary
    summary_html = ""
    if narrative.get("summary"):
        summary_html = f"""
        <div class="insights-section">
            <p style="font-size: 1.05rem; color: var(--text-secondary); line-height: 1.7;">
                {narrative["summary"]}
            </p>
        </div>"""

    # Assemble body
    body = f"{big_number_cards}\n{summary_html}\n{insights_html}"

    full_html = _build_html(
        title=title,
        subtitle=subtitle or narrative.get("headline", ""),
        body_html=body,
        chart_specs=[("main-chart", fig_dict)] if fig_dict.get("data") else [],
    )

    # Wrap chart in a section
    if fig_dict.get("data"):
        full_html = full_html.replace(
            '</div>\n        <div class="footer">',
            f"""</div>
        <div class="chart-section">
            <h2>{title}</h2>
            <div id="main-chart" class="plotly-chart"></div>
        </div>
        <div class="footer">""",
        )

    return {
        "html": full_html,
        "insights": insights,
        "chart_figure": fig_dict,
        "metadata": {
            "title": title,
            "subtitle": subtitle,
            "total_rows": len(data),
            "total_insights": len(insights),
            "big_number": narrative.get("big_number"),
            "big_label": narrative.get("big_label"),
            "headline": narrative.get("headline"),
        },
    }


def create_dashboard(
    panels: list[dict[str, Any]],
    title: str = "Serbia Data Dashboard",
    subtitle: str = "",
) -> str:
    """Create a multi-panel dashboard HTML page.

    Each panel can contain a chart figure dict or an HTML block.

    Args:
        panels: List of panel dicts:
            - {'type': 'chart', 'title': str, 'figure': dict, 'span': 1|2}
            - {'type': 'html', 'title': str, 'content': str, 'span': 1|2}
            - {'type': 'big_number', 'number': str, 'label': str, 'color': str}
        title: Dashboard title
        subtitle: Dashboard subtitle

    Returns:
        Complete HTML string for the dashboard
    """
    chart_specs: list[tuple[str, dict]] = []

    big_number_html = ""
    chart_panels_html = ""

    big_numbers = [p for p in panels if p.get("type") == "big_number"]
    content_panels = [p for p in panels if p.get("type") != "big_number"]

    # Build big number cards if any
    if big_numbers:
        cards = ""
        for bn in big_numbers:
            cards += f"""
            <div class="big-number-card {bn.get("color", "blue")}">
                <div class="number">{bn.get("number", "—")}</div>
                <div class="label">{bn.get("label", "")}</div>
            </div>"""
        big_number_html = f'<div class="big-number-grid">{cards}</div>'

    # Build content panels
    for i, panel in enumerate(content_panels, 1):
        container_id = f"panel-{i}"
        span = panel.get("span", 1)
        width_style = f"grid-column: span {span};" if span == 2 else ""

        if panel.get("type") == "chart" and panel.get("figure"):
            fig_dict = panel["figure"]
            chart_specs.append((container_id, fig_dict))
            chart_panels_html += f"""
            <div class="chart-section" style="{width_style}">
                <h2>{panel.get("title", "")}</h2>
                <div id="{container_id}" class="plotly-chart"></div>
            </div>"""
        elif panel.get("type") == "html":
            chart_panels_html += f"""
            <div class="insights-section" style="{width_style}">
                <h2>{panel.get("title", "")}</h2>
                {panel.get("content", "")}
            </div>"""

    body = f"{big_number_html}\n<div class='dashboard-grid'>{chart_panels_html}</div>"

    return _build_html(title=title, subtitle=subtitle, body_html=body, chart_specs=chart_specs)
