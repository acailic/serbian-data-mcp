"""Scrollytelling: scroll-driven HTML data stories.

Generates multi-section HTML pages where narrative text scrolls on the left
and a sticky chart area updates on the right — the visualise.admin.ch pattern.

Uses IntersectionObserver for triggering chart transitions on scroll.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Optional

from plotly.io import to_html


def _generate_id() -> str:
    return uuid.uuid4().hex[:8]


def scrollytelling(
    steps: list[dict[str, Any]],
    title: str = "",
    subtitle: str = "",
    byline: str = "",
    theme: str = "dark",
    output_path: Optional[Path] = None,
    include_plotly: bool = True,
    header_color: str = "#C6363C",
    accent_color: str = "#0C4076",
) -> str:
    """Create a scroll-driven HTML data story.

    Each step has a narrative and optional chart. As the user scrolls,
    the chart area transitions between states.

    Args:
        steps: List of step dicts, each with:
            - headline (str): Section headline
            - text (str): Narrative text (supports <br>, <b>, <em>)
            - chart (go.Figure, optional): Plotly figure for this step
            - big_number (str, optional): Big stat to show above chart
            - big_number_label (str, optional): Label for big number
            - highlight_color (str, optional): Step accent color
        title: Story title
        subtitle: Story subtitle / deck
        byline: Author credit line
        theme: 'dark' or 'light'
        output_path: If provided, write HTML to this file
        include_plotly: Include Plotly.js CDN (set False if using in iframe)
        header_color: Header background color
        accent_color: Accent/highlight color

    Returns:
        HTML string
    """
    story_id = _generate_id()

    is_dark = theme == "dark"
    bg = "#0d1117" if is_dark else "#ffffff"
    fg = "#e6edf3" if is_dark else "#1f2937"
    muted = "#8b949e" if is_dark else "#6b7280"
    _card_bg = "#161b22" if is_dark else "#f9fafb"  # noqa: F841
    border_color = "#30363d" if is_dark else "#e5e7eb"

    # Build chart HTML for each step
    chart_sections_html = []
    for i, step in enumerate(steps):
        chart_fig = step.get("chart")
        chart_html = ""
        if chart_fig is not None:
            chart_div_id = f"chart-{story_id}-{i}"
            div_only = to_html(chart_fig, full_html=False, include_plotlyjs=False, div_id=chart_div_id)
            chart_html = div_only

        big_num = step.get("big_number", "")
        big_label = step.get("big_number_label", "")
        highlight = step.get("highlight_color", accent_color)

        step_html = f"""
        <div class="chart-step" data-step="{i}" style="display: none;">
            {f'<div class="big-number" style="color: {highlight}">{big_num}</div>' if big_num else ""}
            {f'<div class="big-number-label">{big_label}</div>' if big_label else ""}
            {chart_html}
        </div>
        """
        chart_sections_html.append(step_html)

    # Build narrative HTML
    narrative_sections_html = []
    for i, step in enumerate(steps):
        highlight = step.get("highlight_color", accent_color)
        narrative_sections_html.append(f"""
        <section class="narrative-step" data-step="{i}">
            <div class="step-marker" style="background: {highlight}"></div>
            <h2 style="color: {highlight}">{step.get("headline", "")}</h2>
            <div class="step-text">{step.get("text", "")}</div>
        </section>
        """)

    # Generate chart initialization JS
    chart_init_js = ""
    for i, step in enumerate(steps):
        chart_fig = step.get("chart")
        if chart_fig is not None:
            chart_div_id = f"chart-{story_id}-{i}"
            chart_json = json.dumps(chart_fig.to_dict(), default=lambda _x: None)
            chart_init_js += f"""
            if (document.getElementById('{chart_div_id}')) {{
                Plotly.newPlot('{chart_div_id}', {chart_json}, {{
                    paper_bgcolor: 'transparent',
                    plot_bgcolor: 'transparent',
                    margin: {{l: 40, r: 20, t: 20, b: 40}},
                    font: {{ color: '{fg}' }},
                    xaxis: {{ gridcolor: '{border_color}' }},
                    yaxis: {{ gridcolor: '{border_color}' }},
                }}, {{responsive: true, displayModeBar: false}});
            }}
            """

    html = f"""<!DOCTYPE html>
<html lang="sr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{('<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>' if include_plotly else "")}
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: 'Inter', -apple-system, sans-serif;
    background: {bg};
    color: {fg};
    line-height: 1.7;
}}

/* Hero header */
.hero {{
    min-height: 80vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: 60px 20px;
    background: linear-gradient(180deg, {header_color}22 0%, transparent 100%);
}}

.hero h1 {{
    font-size: clamp(2.5rem, 6vw, 4.5rem);
    font-weight: 800;
    line-height: 1.1;
    margin-bottom: 20px;
    background: linear-gradient(135deg, {fg}, {accent_color});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

.hero .subtitle {{
    font-size: clamp(1.1rem, 2.5vw, 1.5rem);
    color: {muted};
    max-width: 700px;
    font-weight: 300;
}}

.hero .byline {{
    margin-top: 30px;
    color: {muted};
    font-size: 0.9rem;
}}

/* Story layout */
.story-container {{
    display: flex;
    max-width: 1400px;
    margin: 0 auto;
    min-height: 100vh;
}}

/* Left: scrolling narrative */
.narrative-column {{
    width: 45%;
    padding: 60px 40px;
    flex-shrink: 0;
}}

.narrative-step {{
    min-height: 90vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
    padding-left: 30px;
    opacity: 0.3;
    transform: translateY(20px);
    transition: opacity 0.6s ease, transform 0.6s ease;
}}

.narrative-step.active {{
    opacity: 1;
    transform: translateY(0);
}}

.step-marker {{
    width: 4px;
    height: 40px;
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    border-radius: 2px;
}}

.narrative-step h2 {{
    font-size: 1.8rem;
    font-weight: 700;
    margin-bottom: 16px;
    line-height: 1.2;
}}

.step-text {{
    font-size: 1.05rem;
    color: {muted};
    max-width: 480px;
    line-height: 1.8;
}}

/* Right: sticky chart area */
.chart-column {{
    width: 55%;
    position: sticky;
    top: 0;
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 40px;
}}

.chart-step {{
    position: absolute;
    inset: 40px;
    opacity: 0;
    transition: opacity 0.5s ease, transform 0.5s ease;
    transform: scale(0.98);
}}

.chart-step.active {{
    opacity: 1;
    transform: scale(1);
}}

/* Big number */
.big-number {{
    font-size: clamp(3rem, 8vw, 6rem);
    font-weight: 800;
    text-align: center;
    padding: 20px;
    line-height: 1;
}}

.big-number-label {{
    text-align: center;
    font-size: 1.1rem;
    color: {muted};
    margin-bottom: 20px;
}}

/* Progress indicator */
.progress-bar {{
    position: fixed;
    top: 0;
    left: 0;
    height: 3px;
    background: {accent_color};
    z-index: 100;
    transition: width 0.1s linear;
}}

/* Footer */
.footer {{
    text-align: center;
    padding: 60px 20px;
    color: {muted};
    font-size: 0.85rem;
    border-top: 1px solid {border_color};
}}

/* Responsive */
@media (max-width: 900px) {{
    .story-container {{
        flex-direction: column-reverse;
    }}
    .narrative-column,
    .chart-column {{
        width: 100%;
    }}
    .chart-column {{
        position: relative;
        height: auto;
        min-height: 50vh;
    }}
    .narrative-step {{
        min-height: 50vh;
        opacity: 1;
        transform: none;
        padding: 30px 20px;
    }}
}}

/* Plotly overrides for dark theme */
.js-plotly-plot .plotly .main-svg {{
    background: transparent !important;
}}
</style>
</head>
<body>

<!-- Progress bar -->
<div class="progress-bar" id="progress-{story_id}"></div>

<!-- Hero -->
<div class="hero">
    <h1>{title}</h1>
    {f'<p class="subtitle">{subtitle}</p>' if subtitle else ""}
    {f'<p class="byline">{byline}</p>' if byline else ""}
</div>

<!-- Story body -->
<div class="story-container">
    <div class="narrative-column">
        {"".join(narrative_sections_html)}
    </div>
    <div class="chart-column">
        {"".join(chart_sections_html)}
    </div>
</div>

<!-- Footer -->
<div class="footer">
    <p>Podaci: data.gov.rs | Vizualizacija: Serbian Data MCP</p>
</div>

<script>
// Scroll-driven step activation
document.addEventListener('DOMContentLoaded', function() {{
    const storyId = '{story_id}';
    const narrativeSteps = document.querySelectorAll(`.narrative-step[data-step]`);
    const chartSteps = document.querySelectorAll(`.chart-step[data-step]`);
    const progressBar = document.getElementById(`progress-${{storyId}}`);

    // Initialize charts
    {chart_init_js}

    // Show first chart
    if (chartSteps.length > 0) {{
        chartSteps[0].style.display = 'block';
        // Trigger reflow for transition
        requestAnimationFrame(function() {{
            chartSteps[0].classList.add('active');
            if (narrativeSteps[0]) narrativeSteps[0].classList.add('active');
        }});
    }}

    // IntersectionObserver for narrative steps
    const observer = new IntersectionObserver(function(entries) {{
        entries.forEach(function(entry) {{
            const step = entry.target.dataset.step;

            if (entry.isIntersecting && entry.intersectionRatio > 0.3) {{
                // Activate this step
                narrativeSteps.forEach(function(s) {{ s.classList.remove('active'); }});
                entry.target.classList.add('active');

                // Switch chart
                chartSteps.forEach(function(cs) {{
                    cs.classList.remove('active');
                    cs.style.display = 'none';
                }});
                var target = document.querySelector(`.chart-step[data-step="${{step}}"]`);
                if (target) {{
                    target.style.display = 'block';
                    requestAnimationFrame(function() {{
                        target.classList.add('active');
                    }});
                }}
            }}
        }});
    }}, {{
        rootMargin: '-20% 0px -20% 0px',
        threshold: [0.3, 0.5, 0.8]
    }});

    narrativeSteps.forEach(function(step) {{ observer.observe(step); }});

    // Progress bar
    window.addEventListener('scroll', function() {{
        var scrollTop = window.scrollY;
        var docHeight = document.documentElement.scrollHeight - window.innerHeight;
        var progress = (scrollTop / docHeight) * 100;
        if (progressBar) progressBar.style.width = progress + '%';
    }});
}});
</script>
</body>
</html>"""

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        return str(output_path)

    return html
