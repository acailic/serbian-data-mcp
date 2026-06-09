"""Export charts to various formats."""

from pathlib import Path
from typing import Optional, Dict, Any
import json
import os

import plotly.graph_objects as go

from ..config import config


def _validate_filename(filename: str) -> str:
    """Validate filename to prevent path traversal attacks.

    Args:
        filename: Input filename to validate

    Returns:
        Safe filename with only basename

    Raises:
        ValueError: If filename contains path traversal attempts or invalid characters
    """
    if not filename:
        raise ValueError("Filename cannot be empty")

    # Check for path separators and drive letters first
    if "/" in filename or "\\" in filename:
        raise ValueError(
            f"Path traversal detected. Filename '{filename}' contains path separators. "
            "Only simple filenames are allowed (no directory paths)."
        )

    # Check for Windows drive letters (e.g., C:, D:, etc.)
    if len(filename) >= 2 and filename[1] == ":":
        raise ValueError(
            f"Path traversal detected. Filename '{filename}' appears to be a Windows path. "
            "Only simple filenames are allowed (no drive letters or absolute paths)."
        )

    # Check for path traversal attempts
    if ".." in filename:
        raise ValueError(
            f"Path traversal detected. Filename '{filename}' contains '..'. Only simple filenames are allowed."
        )

    # Check for suspicious patterns that might indicate shell injection or other attacks
    suspicious_patterns = ["~", "$", "|", ";", "&", "<", ">", "*", "?", "[", "]", "!", "`"]
    for pattern in suspicious_patterns:
        if pattern in filename:
            raise ValueError(
                f"Suspicious character '{pattern}' detected in filename. "
                "Only alphanumeric characters, underscores, hyphens, and dots are allowed."
            )

    # Ensure filename is not empty and not just dots
    if not filename or filename in (".", ".."):
        raise ValueError("Invalid filename after sanitization")

    return filename


async def export_html(fig: go.Figure, filename: str, output_dir: Optional[Path] = None) -> str:
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

    # Validate filename to prevent path traversal attacks
    safe_filename = _validate_filename(filename)
    filepath = output_dir / safe_filename
    fig.write_html(filepath, include_plotlyjs="cdn")

    return str(filepath)


async def export_png(fig: go.Figure, filename: str, output_dir: Optional[Path] = None, scale: float = 1.0) -> str:
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

    # Validate filename to prevent path traversal attacks
    safe_filename = _validate_filename(filename)
    filepath = output_dir / safe_filename
    fig.write_image(filepath, scale=scale, engine="kaleido")

    return str(filepath)


async def export_json(fig: go.Figure, filename: str, output_dir: Optional[Path] = None) -> str:
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

    # Validate filename to prevent path traversal attacks
    safe_filename = _validate_filename(filename)
    filepath = output_dir / safe_filename
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
