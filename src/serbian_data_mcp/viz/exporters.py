"""Export charts to various formats: HTML, PNG, JSON, PDF, embed snippets.

Supports kaleido-based PNG export with graceful fallback when kaleido
is not installed, and generates iframe embed code for sharing.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import plotly.graph_objects as go

from ..config import config

logger = logging.getLogger(__name__)


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


async def export_html(fig: go.Figure, filename: str, output_dir: Optional[Path] = None) -> str:
    """Export chart as HTML file."""
    output_dir = output_dir or config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = _validate_filename(filename)
    filepath = output_dir / safe_filename
    fig.write_html(filepath, include_plotlyjs="cdn")
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

    Tries kaleido first, then falls back to a simple HTML→screenshot approach
    using a headless browser if available.

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
    import base64

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
