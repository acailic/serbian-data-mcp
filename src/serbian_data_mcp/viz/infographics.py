"""Infographic builder — creates single-page "big number + chart + insight" HTML pages.

Generates standalone, visually striking HTML files that present data
as a story: headline, big numbers, supporting chart, and auto-generated
narrative insights.

Supports multiple big number cards with sparklines, timeline ribbon,
count-up animations, print stylesheet, and enhanced hover states.
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
from .data_tables import data_table_html, data_table_css


# ── HTML Templates ──────────────────────────────────────────────────────────

_DARK_STYLES = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {
    --bg-primary: #0f0f23;
    --bg-secondary: #16213e;
    --bg-card: rgba(22, 33, 62, 0.85);
    --text-primary: #ffffff;
    --text-secondary: #b0bec5;
    --accent-red: #c62828;
    --accent-blue: #1565c0;
    --accent-gold: #ffab00;
    --accent-green: #2e7d32;
    --border: rgba(255,255,255,0.06);
    --radius: 20px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: var(--bg-primary);
    background-image: radial-gradient(ellipse at 20% 0%, rgba(21,101,192,0.08) 0%, transparent 50%),
                      radial-gradient(ellipse at 80% 100%, rgba(198,40,40,0.06) 0%, transparent 50%);
    color: var(--text-primary);
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    line-height: 1.6;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 48px 24px;
}
.header {
    text-align: center;
    margin-bottom: 56px;
    padding-bottom: 32px;
    border-bottom: 1px solid var(--border);
    position: relative;
}
.header::after {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 50%;
    transform: translateX(-50%);
    width: 80px;
    height: 3px;
    background: linear-gradient(90deg, var(--accent-blue), var(--accent-gold), var(--accent-red));
    border-radius: 2px;
}
.header h1 {
    font-size: 2.8rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin-bottom: 12px;
    background: linear-gradient(135deg, #ffffff 0%, #e0e0e0 40%, var(--accent-gold) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.15;
}
.header .subtitle {
    font-size: 1.1rem;
    color: var(--text-secondary);
    max-width: 700px;
    margin: 0 auto;
    font-weight: 400;
    line-height: 1.6;
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
    border-radius: var(--radius);
    padding: 32px 24px;
    text-align: center;
    transition: transform 0.25s cubic-bezier(0.4,0,0.2,1), border-color 0.25s, box-shadow 0.25s;
    backdrop-filter: blur(10px);
}
.big-number-card:hover {
    transform: translateY(-6px);
    border-color: rgba(255,171,0,0.3);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), 0 0 0 1px rgba(255,171,0,0.1);
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
    border-radius: var(--radius);
    padding: 32px;
    margin-bottom: 32px;
    backdrop-filter: blur(10px);
    box-shadow: 0 2px 16px rgba(0,0,0,0.15);
}
.chart-section h2 {
    font-size: 1.3rem;
    font-weight: 700;
    margin-bottom: 20px;
    color: var(--accent-gold);
    letter-spacing: -0.01em;
}
.insights-section {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 32px;
    margin-bottom: 32px;
    backdrop-filter: blur(10px);
    box-shadow: 0 2px 16px rgba(0,0,0,0.15);
}
.insights-section h2 {
    font-size: 1.3rem;
    font-weight: 700;
    margin-bottom: 20px;
    color: var(--accent-gold);
    letter-spacing: -0.01em;
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
    padding: 32px 24px 40px;
    border-top: 1px solid var(--border);
    color: var(--text-secondary);
    font-size: 0.8rem;
    letter-spacing: 0.02em;
}
.plotly-chart { width: 100%; min-height: 450px; }

/* ── Multi big-number cards ─────────────────────────────────────────── */
.big-number-card { position: relative; overflow: hidden; }
.big-number-card::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, transparent 50%);
    pointer-events: none;
}
.big-number-card .sparkline { margin-top: 12px; height: 40px; opacity: 0.7; }
.big-number-card .trend-indicator {
    font-size: 0.8rem; margin-top: 4px;
    display: flex; align-items: center; gap: 4px; justify-content: center;
}
.trend-up { color: var(--accent-green); }
.trend-down { color: var(--accent-red); }
.trend-flat { color: var(--accent-blue); }

/* ── Timeline ribbon ─────────────────────────────────────────────────── */
.timeline-ribbon { position: relative; padding: 32px 0 16px; margin-bottom: 32px; }
.timeline-ribbon .timeline-line {
    position: absolute; top: 48px; left: 32px; right: 32px;
    height: 3px; background: var(--border); border-radius: 2px;
}
.timeline-ribbon .events { display: flex; justify-content: space-between; position: relative; }
.timeline-ribbon .event { display: flex; flex-direction: column; align-items: center; flex: 1; position: relative; }
.timeline-ribbon .event-dot {
    width: 14px; height: 14px; border-radius: 50%;
    background: var(--accent-blue); border: 3px solid var(--bg-primary);
    position: relative; z-index: 1;
    transition: transform 0.2s, box-shadow 0.2s;
}
.timeline-ribbon .event:hover .event-dot {
    transform: scale(1.3); box-shadow: 0 0 12px var(--accent-blue);
}
.timeline-ribbon .event-dot.highlight { background: var(--accent-red); box-shadow: 0 0 8px rgba(198,40,40,0.5); }
.timeline-ribbon .event-dot.gold { background: var(--accent-gold); box-shadow: 0 0 8px rgba(255,171,0,0.5); }
.timeline-ribbon .event-label { font-size: 0.75rem; color: var(--text-secondary); margin-top: 8px; text-align: center; max-width: 100px; }
.timeline-ribbon .event-year { font-size: 0.85rem; font-weight: 700; color: var(--text-primary); margin-top: 4px; }

/* ── Chart entrance animation ───────────────────────────────────────── */
.chart-section {
    opacity: 0; transform: translateY(30px);
    transition: opacity 0.8s ease, transform 0.8s ease;
}
.chart-section.visible { opacity: 1; transform: translateY(0); }
.insights-section {
    opacity: 0; transform: translateY(30px);
    transition: opacity 0.8s ease 0.2s, transform 0.8s ease 0.2s;
}
.insights-section.visible { opacity: 1; transform: translateY(0); }
.big-number-grid {
    opacity: 0; transform: translateY(20px);
    transition: opacity 0.6s ease, transform 0.6s ease;
}
.big-number-grid.visible { opacity: 1; transform: translateY(0); }

/* ── Print stylesheet ─────────────────────────────────────────────────── */
@media print {
    body { background: white !important; color: #1a1a2e !important; }
    .container { max-width: 100%; padding: 20px; }
    .header { border-bottom: 2px solid #ccc; }
    .header h1 { -webkit-text-fill-color: #1a1a2e !important; background: none !important; font-size: 2rem; }
    .big-number-card { border: 1px solid #ccc !important; background: #f9f9f9 !important; break-inside: avoid; }
    .chart-section, .insights-section { border: 1px solid #ccc !important; background: #f9f9f9 !important; opacity: 1 !important; transform: none !important; break-inside: avoid; }
    .plotly-chart { min-height: 350px; }
    .timeline-ribbon { break-inside: avoid; }
    .footer { border-top: 1px solid #ccc; color: #666; }
    .js-plotly-plot .plotly .main-svg { background: white !important; }
}

@media (max-width: 768px) {
    .header h1 { font-size: 2rem; }
    .header .subtitle { font-size: 1rem; }
    .big-number-card .number { font-size: 2.2rem; }
    .big-number-grid { gap: 16px; }
    .dashboard-grid { grid-template-columns: 1fr; }
    .container { padding: 24px 16px; }
    .timeline-ribbon .event-label { font-size: 0.65rem; max-width: 70px; }
    .chart-section, .insights-section { padding: 20px 16px; border-radius: 16px; }
    .big-number-card { padding: 24px 16px; border-radius: 16px; }
}
"""

_PLOTLY_CDN = "https://cdn.plot.ly/plotly-3.6.0.min.js"

_INTER_FONT = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">'

_JS_CHART_RENDERER = r"""
function renderChart(containerId, figureJson) {
    const container = document.getElementById(containerId);
    if (!container) return;
    Plotly.newPlot(containerId, figureJson.data, figureJson.layout, {responsive: true, displayModeBar: false});
}

function animateCountUp(selector, duration) {
    var elements = document.querySelectorAll(selector);
    duration = duration || 1500;
    var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                var el = entry.target;
                var finalText = el.dataset.finalValue || el.textContent;
                var prefix = el.dataset.prefix || '';
                var suffix = el.dataset.suffix || '';
                var numMatch = finalText.match(/[\d,.-]+/);
                if (numMatch) {
                    var finalNum = parseFloat(numMatch[0].replace(/,/g, ''));
                    if (!isNaN(finalNum) && Math.abs(finalNum) > 1) {
                        var start = 0;
                        var startTime = performance.now();
                        function tick(now) {
                            var progress = Math.min((now - startTime) / duration, 1);
                            var eased = 1 - Math.pow(1 - progress, 3);
                            var current = start + (finalNum - start) * eased;
                            if (Math.abs(finalNum) >= 1000) {
                                el.textContent = prefix + current.toLocaleString('sr-RS', {maximumFractionDigits: 1}) + suffix;
                            } else {
                                el.textContent = prefix + current.toFixed(1) + suffix;
                            }
                            if (progress < 1) requestAnimationFrame(tick);
                        }
                        requestAnimationFrame(tick);
                    }
                }
                observer.unobserve(el);
            }
        });
    }, {threshold: 0.5});
    elements.forEach(function(el) { observer.observe(el); });
}

function initScrollReveal() {
    var sections = document.querySelectorAll('.chart-section, .insights-section, .big-number-grid');
    var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, {threshold: 0.1});
    sections.forEach(function(s) { observer.observe(s); });
}

document.addEventListener('DOMContentLoaded', function() {
    animateCountUp('.big-number-card .number');
    initScrollReveal();
});
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
    {_INTER_FONT}
    <script src="{_PLOTLY_CDN}" charset="utf-8"></script>
    <style>{_DARK_STYLES}
{data_table_css}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p class="subtitle">{subtitle}</p>
        </div>
        {body_html}
        <div class="footer">
            🇷🇸 Serbian Open Data Portal (data.gov.rs) &middot; Generated with serbian-data-mcp
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
    extra_big_numbers: list[dict[str, Any]] | None = None,
    timeline_events: list[dict[str, Any]] | None = None,
    data_table: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a complete infographic page: big numbers + chart + insights.

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
        time_column: Optional time column for insight extraction
        entity_column: Optional entity column for insight extraction
        annotations: Optional list of annotation dicts with 'text', 'x', 'y'
        extra_big_numbers: Additional big number cards:
            [{'number': '6.92M', 'label': 'Population', 'color': 'blue', 'trend': 'down'}]
        timeline_events: Timeline ribbon events:
            [{'year': '2020', 'label': 'COVID-19', 'dot_class': 'highlight'}]
        data_table: Optional data table config:
            {'columns': ['name', 'value'], 'highlight_column': 'value', 'title': 'Details'}

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

    # Build big number cards (auto-detected + extras)
    big_number_cards = ""
    all_big_numbers: list[dict[str, str]] = []

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

        all_big_numbers.append(
            {"number": str(number_display), "label": narrative.get("big_label", title), "color": color_class}
        )

    # Add extra big numbers
    if extra_big_numbers:
        for ebn in extra_big_numbers:
            all_big_numbers.append(
                {
                    "number": str(ebn.get("number", "")),
                    "label": ebn.get("label", ""),
                    "color": ebn.get("color", "blue"),
                    "trend": ebn.get("trend", ""),
                }
            )

    if all_big_numbers:
        cards = ""
        for bn in all_big_numbers:
            trend_html = ""
            if bn.get("trend"):
                if bn["trend"] == "up":
                    trend_html = '<div class="trend-indicator trend-up">▲ rast</div>'
                elif bn["trend"] == "down":
                    trend_html = '<div class="trend-indicator trend-down">▼ pad</div>'
                else:
                    trend_html = '<div class="trend-indicator trend-flat">● stabilno</div>'
            cards += f"""
            <div class="big-number-card {bn["color"]}">
                <div class="number" data-final-value="{bn["number"]}">{bn["number"]}</div>
                <div class="label">{bn["label"]}</div>
                {trend_html}
            </div>"""
        big_number_cards = '<div class="big-number-grid">' + cards + "</div>"

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

    # Build timeline ribbon
    timeline_html = ""
    if timeline_events and len(timeline_events) > 1:
        events_html = ""
        for ev in timeline_events:
            dot_class = ev.get("dot_class", "")
            events_html += f"""
            <div class="event">
                <div class="event-dot {dot_class}"></div>
                <div class="event-label">{ev.get("label", "")}</div>
                <div class="event-year">{ev.get("year", "")}</div>
            </div>"""
        timeline_html = f"""
        <div class="timeline-ribbon">
            <div class="timeline-line"></div>
            <div class="events">{events_html}</div>
        </div>"""

    # Build data table
    table_html = ""
    if data_table:
        table_html = data_table_html(
            data,
            columns=data_table.get("columns"),
            highlight_column=data_table.get("highlight_column"),
            max_rows=data_table.get("max_rows", 25),
            title=data_table.get("title", ""),
            caption=data_table.get("caption", ""),
        )

    # Assemble body
    body = f"{big_number_cards}\n{timeline_html}\n{summary_html}\n{table_html}\n{insights_html}"

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
