"""Export charts to various formats."""

from pathlib import Path
from typing import Optional, Dict, Any
import json

import plotly.graph_objects as go

from ..config import config


async def export_html(
    fig: go.Figure,
    filename: str,
    output_dir: Optional[Path] = None
) -> str:
    """Export chart as HTML file.

    Args:
        fig: Plotly Figure object
        filename: Output filename
        output_dir: Output directory (defaults to config.export_dir)

    Returns:
        Path to exported HTML file
    """
    output_dir = output_dir or config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / filename
    fig.write_html(filepath, include_plotlyjs="cdn")

    return str(filepath)


async def export_png(
    fig: go.Figure,
    filename: str,
    output_dir: Optional[Path] = None,
    scale: float = 1.0
) -> str:
    """Export chart as PNG image.

    Args:
        fig: Plotly Figure object
        filename: Output filename
        output_dir: Output directory (defaults to config.export_dir)
        scale: Scale factor for resolution

    Returns:
        Path to exported PNG file

    Note:
        Requires kaleido package: pip install kaleido
    """
    output_dir = output_dir or config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / filename
    fig.write_image(filepath, scale=scale, engine="kaleido")

    return str(filepath)


async def export_json(
    fig: go.Figure,
    filename: str,
    output_dir: Optional[Path] = None
) -> str:
    """Export chart as JSON.

    Args:
        fig: Plotly Figure object
        filename: Output filename
        output_dir: Output directory (defaults to config.export_dir)

    Returns:
        Path to exported JSON file
    """
    output_dir = output_dir or config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / filename
    fig_json = fig.to_json()

    with open(filepath, "w") as f:
        f.write(fig_json)

    return str(filepath)


def fig_to_dict(fig: go.Figure) -> Dict[str, Any]:
    """Convert Plotly Figure to dictionary.

    Args:
        fig: Plotly Figure object

    Returns:
        Dictionary representation of the figure
    """
    return json.loads(fig.to_json())
