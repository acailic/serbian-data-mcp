"""Export tools.

Contracts:
  - export_visualization(figure, format, filename) → filepath
  - export_data(data, format, filename) → filepath
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from fastmcp.exceptions import ToolError

from .. import mcp
from ..config import config
from ..viz.exporters import export_html, export_json


@mcp.tool()
async def export_visualization(
    figure: dict[str, Any],
    format: str = "html",
    filename: str = "chart",
) -> dict[str, Any]:
    """Save a chart from create_chart() to a file.

    Args:
        figure: Plotly figure dict from create_chart()
        format: 'html' or 'json'
        filename: Output name (without extension)

    Returns: {filepath, format, filename}
    """
    from plotly.graph_objects import Figure

    valid_formats = {"html", "json"}
    if format not in valid_formats:
        raise ToolError(f"Unsupported format '{format}'. Use: {', '.join(sorted(valid_formats))}")

    try:
        fig = Figure(figure.get("data", []), figure.get("layout", {}))
        out_dir = config.export_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        filepath = ""
        if format == "html":
            filepath = await export_html(fig, filename, output_dir=out_dir)
        elif format == "json":
            filepath = await export_json(fig, filename, output_dir=out_dir)
        return {"filepath": filepath, "format": format, "filename": filename}
    except Exception as e:
        raise ToolError(f"Export failed: {e}") from e


@mcp.tool()
async def export_data(
    data: list[dict[str, Any]],
    filename: str = "data",
    format: str = "csv",
) -> dict[str, Any]:
    """Save data from get_resource_data() or transform_data() to file.

    Formats: 'csv' (universal), 'json' (API-friendly), 'xlsx' (requires openpyxl).

    Args:
        data: Row dicts
        filename: Output name (without extension)
        format: 'csv', 'json', or 'xlsx'

    Returns: {filepath, format, rows, columns, filename}
    """
    if not data:
        raise ToolError("No data to export — pass data from get_resource_data()")

    valid_formats = {"csv", "json", "xlsx"}
    if format not in valid_formats:
        raise ToolError(f"Unsupported format '{format}'. Use: {', '.join(sorted(valid_formats))}")

    out_dir = config.export_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(data)
    filepath: Path

    try:
        if format == "csv":
            filepath = out_dir / f"{filename}.csv"
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
        elif format == "json":
            filepath = out_dir / f"{filename}.json"
            filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        elif format == "xlsx":
            try:
                filepath = out_dir / f"{filename}.xlsx"
                df.to_excel(filepath, index=False, engine="openpyxl")
            except ImportError:
                raise ToolError("XLSX export requires openpyxl. Install with: pip install openpyxl")
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Export failed: {e}") from e

    return {
        "filepath": str(filepath),
        "format": format,
        "rows": len(data),
        "columns": list(df.columns),
        "filename": f"{filename}.{format}",
    }
