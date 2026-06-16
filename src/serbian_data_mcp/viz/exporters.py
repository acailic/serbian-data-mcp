"""Export charts to various formats: HTML, PNG, JSON, PDF, embed snippets.

Supports kaleido-based PNG export with graceful fallback when kaleido
is not installed, and generates iframe embed code for sharing.

HTML exports use a styled wrapper page with dark background, branded
header, and source attribution for a polished, professional look.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any, Optional

import plotly.graph_objects as go

from ..config import config

logger = logging.getLogger(__name__)

_PLOTLY_CDN = "https://cdn.plot.ly/plotly-3.6.0.min.js"

_HTML_WRAPPER = """<!DOCTYPE html>
<html lang="sr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="{plotly_cdn}" charset="utf-8"></script>
    <style>
        :root {{
            --bg-primary: #1a1a2e;
            --bg-card: #16213e;
            --border: rgba(255,255,255,0.08);
            --text-primary: #e0e0e0;
            --text-muted: #78909c;
            --accent: #ffab00;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        .chart-container {{
            flex: 1;
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
            padding: 32px 24px;
        }}
        .chart-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }}
        .chart-header h1 {{
            font-size: 1.3rem;
            font-weight: 700;
            color: var(--text-primary);
            letter-spacing: -0.01em;
        }}
        .chart-header .badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 20px;
            background: rgba(255,171,0,0.1);
            color: var(--accent);
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.03em;
        }}
        .chart-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.2);
        }}
        .chart-card .plotly {{ width: 100%; }}
        .chart-footer {{
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
            padding: 16px 24px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .chart-footer .source {{
            font-size: 0.75rem;
            color: var(--text-muted);
        }}
        .chart-footer .brand {{
            font-size: 0.75rem;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        @media print {{
            body {{ background: white; color: #1a1a2e; }}
            .chart-container {{ max-width: 100%; }}
            .chart-card {{ border: 1px solid #dee2e6; box-shadow: none; background: white; }}
            .chart-header {{ border-bottom: 2px solid #dee2e6; }}
            .chart-header h1 {{ color: #1a1a2e; }}
            .chart-footer .source, .chart-footer .brand {{ color: #6c757d; }}
        }}
        @media (max-width: 768px) {{
            .chart-container {{ padding: 16px; }}
            .chart-card {{ padding: 16px; border-radius: 12px; }}
            .chart-header h1 {{ font-size: 1.1rem; }}
        }}
    </style>
</head>
<body>
    <div class="chart-container">
        <div class="chart-header">
            <h1>{title}</h1>
            <span class="badge">🇷🇸 data.gov.rs</span>
        </div>
        <div class="chart-card">
            <div id="chart">{plotly_div}</div>
        </div>
    </div>
    <div class="chart-footer">
        <span class="source">{source}</span>
        <span class="brand">serbian-data-mcp</span>
    </div>
    <script>{plotly_render_js}</script>
</body>
</html>"""


def _validate_filename(filename: str) -> str:
    """Validate filename to prevent path traversal attacks."""
    if not filename:
        raise ValueError("Filename cannot be empty")
    if "/" in filename or "\\" in filename:
        raise ValueError(f"Path traversal detected in filename '{filename}'.")
    if len(filename) >= 2 and filename[1] == ":":
        raise ValueError(f"Path traversal detected in filename '{filename}'.")
    if ".." in filename:
        raise ValueError(f"Path traversal detected in filename '{filename}'.")
    for pattern in ["~", "$", "|", ";", "&", "<", ">", "*", "?", "[", "]", "!", "`"]:
        if pattern in filename:
            raise ValueError(f"Suspicious character '{pattern}' in filename.")
    if not filename or filename in (".", ".."):
        raise ValueError("Invalid filename after sanitization")
    return filename


async def export_html(
    fig: go.Figure,
    filename: str,
    output_dir: Optional[Path] = None,
    title: str = "",
    source: str = "Source: data.gov.rs",
) -> str:
    """Export chart as a styled HTML page with branded wrapper.

    Generates a standalone HTML file with dark background, branded header,
    rounded card container, and source attribution footer. Loads Plotly.js
    from CDN and renders the chart client-side for full interactivity.

    Args:
        fig: Plotly Figure object
        filename: Output filename
        output_dir: Output directory
        title: Chart title for page header
        source: Data source attribution text

    Returns:
        Path to exported HTML file
    """
    output_dir = output_dir or config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = _validate_filename(filename)
    filepath = output_dir / safe_filename

    # Extract title from figure if not provided
    if not title and fig.layout and fig.layout.title and fig.layout.title.text:
        title = str(fig.layout.title.text)

    fig_json = json.dumps(json.loads(fig.to_json()), default=str)
    render_js = f"Plotly.newPlot('chart', {fig_json}, {{responsive: true, displayModeBar: 'hover'}});"

    html = _HTML_WRAPPER.format(
        title=title or "Serbian Data Visualization",
        plotly_cdn=_PLOTLY_CDN,
        plotly_div="",
        plotly_render_js=render_js,
        source=source,
    )

    filepath.write_text(html, encoding="utf-8")
    return str(filepath)


async def export_png(
    fig: go.Figure,
    filename: str,
    output_dir: Optional[Path] = None,
    scale: float = 2.0,
    width: int = 1200,
    height: int = 700,
) -> str:
    """Export chart as PNG image with graceful kaleido fallback.

    Tries kaleido first, then falls back to orca. If neither is available,
    writes an HTML file and raises RuntimeError with instructions.

    Args:
        fig: Plotly Figure object
        filename: Output filename
        output_dir: Output directory
        scale: Scale factor for resolution (default 2.0 for retina)
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Path to exported PNG file

    Raises:
        RuntimeError: If no image export method is available
    """
    output_dir = output_dir or config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = _validate_filename(filename)
    filepath = output_dir / safe_filename

    # Try kaleido
    try:
        fig.write_image(filepath, scale=scale, width=width, height=height, engine="kaleido")
        return str(filepath)
    except Exception as e:
        logger.debug("Kaleido export failed: %s", e)

    # Try orca
    try:
        fig.write_image(filepath, scale=scale, width=width, height=height, engine="orca")
        return str(filepath)
    except Exception as e:
        logger.debug("Orca export failed: %s", e)

    # Fallback: write an HTML file and inform user
    html_path = filepath.with_suffix(".html")
    fig.write_html(html_path, include_plotlyjs="cdn")
    raise RuntimeError(
        f"PNG export requires kaleido (pip install kaleido). "
        f"Exported as HTML instead: {html_path}. "
        f"Open in browser and use File > Save As to get PNG."
    )


async def export_json(fig: go.Figure, filename: str, output_dir: Optional[Path] = None) -> str:
    """Export chart as JSON."""
    output_dir = output_dir or config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = _validate_filename(filename)
    filepath = output_dir / safe_filename
    fig_json = fig.to_json()
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(fig_json)
    return str(filepath)


async def export_pdf(
    fig: go.Figure,
    filename: str,
    output_dir: Optional[Path] = None,
    width: int = 1200,
    height: int = 700,
) -> str:
    """Export chart as PDF (requires kaleido).

    Args:
        fig: Plotly Figure object
        filename: Output filename
        output_dir: Output directory
        width: Page width in pixels
        height: Page height in pixels

    Returns:
        Path to exported PDF file

    Raises:
        RuntimeError: If kaleido is not available
    """
    output_dir = output_dir or config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = _validate_filename(filename)
    filepath = output_dir / safe_filename

    try:
        fig.write_image(filepath, format="pdf", width=width, height=height, engine="kaleido")
        return str(filepath)
    except Exception as e:
        raise RuntimeError(f"PDF export requires kaleido (pip install kaleido). Error: {e}") from e


def generate_embed_code(
    fig: go.Figure,
    width: int = 700,
    height: int = 450,
    title: str = "Chart",
) -> dict[str, str]:
    """Generate embed snippets for sharing a chart in websites/blogs.

    Returns iframe embed code and a self-contained HTML snippet that
    can be pasted into any website or CMS.

    Args:
        fig: Plotly Figure object
        width: Embed width in pixels
        height: Embed height in pixels
        title: Accessible title for the iframe

    Returns:
        Dict with 'iframe_code', 'html_snippet', 'data_url'
    """
    # Generate the self-contained HTML
    fig.write_html(
        "/tmp/_embed_chart.html",
        include_plotlyjs="cdn",
        full_html=True,
        auto_play=False,
    )
    with open("/tmp/_embed_chart.html", encoding="utf-8") as f:
        html_content = f.read()

    # Build data URL (for inline embedding)
    data_url = f"data:text/html;base64,{base64.b64encode(html_content.encode()).decode()}"

    # Build iframe code
    iframe_code = (
        f'<iframe title="{title}" '
        f'src="{data_url}" '
        f'width="{width}" height="{height}" '
        f'frameborder="0" scrolling="no" '
        f'style="border: 1px solid #e0e0e0; border-radius: 8px;"></iframe>'
    )

    return {
        "iframe_code": iframe_code,
        "html_snippet": html_content,
        "data_url": data_url,
        "width": width,
        "height": height,
    }


def fig_to_dict(fig: go.Figure) -> dict[str, Any]:
    """Convert Plotly Figure to dictionary."""
    return json.loads(fig.to_json())
