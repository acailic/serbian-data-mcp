"""Serbia map visualization tools.

Contracts:
  - create_serbia_map(data, name_column, value_column) → HTML filepath
  - list_serbia_districts() → 25 district names
"""

from __future__ import annotations

from typing import Any, Optional

from fastmcp.exceptions import ToolError

from .. import mcp
from ..config import config
from ..viz.maps import SerbiaMapBuilder
from ..viz.exporters import export_html
from ..viz.map_advanced import AdvancedMapBuilder

_map_builder: Optional[SerbiaMapBuilder] = None
_adv_map_builder: Optional[AdvancedMapBuilder] = None


def _get_map_builder() -> SerbiaMapBuilder:
    global _map_builder
    if _map_builder is None:
        _map_builder = SerbiaMapBuilder()
    return _map_builder


def _get_adv_map_builder() -> AdvancedMapBuilder:
    global _adv_map_builder
    if _adv_map_builder is None:
        _adv_map_builder = AdvancedMapBuilder()
    return _adv_map_builder


@mcp.tool()
async def create_serbia_map(
    data: list[dict[str, Any]],
    name_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    colorscale: Optional[str] = None,
    filename: str = "serbia_map",
) -> dict[str, Any]:
    """Choropleth map of Serbia by 25 administrative districts. Color-coded by metric.

    District names in Natural Earth format (English transliteration). Cyrillic and
    city shorthand also supported (e.g., 'Niš', 'Novi Sad').
    Use list_serbia_districts() to see all recognized names.

    Returns: {filepath, districts_matched, total_districts, title}

    Args:
        data: Row dicts with district names and values
        name_column: District names column
        value_column: Numeric values to color by
        title: Map title
        theme: 'dark', 'light', 'infographic'
        colorscale: 'red', 'blue', 'diverging', 'heat' (default: blue)
        filename: Output filename (without .html)
    """
    try:
        builder = _get_map_builder()
        color_map = {
            "red": [(0.0, "#fff9c4"), (0.25, "#ffcc80"), (0.5, "#ff8a65"), (0.75, "#e53935"), (1.0, "#b71c1c")],
            "blue": None,
            "diverging": [(0.0, "#1565c0"), (0.25, "#42a5f5"), (0.5, "#f5f5f5"), (0.75, "#ef5350"), (1.0, "#c62828")],
            "heat": [(0.0, "#fff9c4"), (0.25, "#ffcc80"), (0.5, "#ff8a65"), (0.75, "#e53935"), (1.0, "#b71c1c")],
        }
        cs = color_map.get(colorscale or "blue") if colorscale else None

        fig = builder.choropleth(
            data,
            name_column=name_column,
            value_column=value_column,
            title=title or f"{value_column} po okruzima",
            theme=theme,
            colorscale=cs,
            highlight_top=3,
        )

        output_dir = config.export_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / f"{filename}.html"
        filepath.write_text(export_html(fig), encoding="utf-8")

        import pandas as pd

        matched = pd.DataFrame(data)[name_column].apply(builder.resolve_name).notna().sum()

        return {
            "filepath": str(filepath),
            "districts_matched": int(matched),
            "total_districts": len(data),
            "title": title,
        }
    except Exception as e:
        raise ToolError(f"Map creation failed: {e}") from e


@mcp.tool()
async def list_serbia_districts() -> dict[str, Any]:
    """List 25 administrative districts for create_serbia_map(). Returns recognized names."""
    builder = _get_map_builder()
    return {"districts": builder.list_districts(), "total": 25}


@mcp.tool()
async def create_bubble_map(
    data: list[dict[str, Any]],
    name_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    filename: str = "bubble_map",
) -> dict[str, Any]:
    """Bubble map of Serbia — circle size = magnitude. Avoids large-district bias.

    Returns: {filepath, districts_matched, title}

    Args:
        data: Row dicts with district names and values
        name_column: District names column
        value_column: Numeric values (determines bubble size)
        title: Map title
        theme: Visual theme
        filename: Output filename (without .html)
    """
    try:
        builder = _get_adv_map_builder()
        fig = builder.bubble_map(data, name_column=name_column, value_column=value_column, title=title, theme=theme)

        output_dir = config.export_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / f"{filename}.html"
        filepath.write_text(export_html(fig), encoding="utf-8")

        import pandas as pd

        matched = pd.DataFrame(data)[name_column].apply(builder.resolve_name).notna().sum()

        return {"filepath": str(filepath), "districts_matched": int(matched), "title": title}
    except Exception as e:
        raise ToolError(f"Bubble map failed: {e}") from e


@mcp.tool()
async def create_multi_layer_map(
    layers: list[dict[str, Any]],
    title: str = "",
    theme: str = "dark",
    filename: str = "multi_layer_map",
) -> dict[str, Any]:
    """Multi-layer choropleth with toggle buttons between indicators.

    Each layer: {data, name_column, value_column, label, colorscale}

    Returns: {filepath, layer_count, title}

    Args:
        layers: List of layer dicts
        title: Map title
        theme: Visual theme
        filename: Output filename (without .html)
    """
    try:
        builder = _get_adv_map_builder()
        fig = builder.multi_layer_map(layers, title=title, theme=theme)

        output_dir = config.export_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / f"{filename}.html"
        filepath.write_text(export_html(fig), encoding="utf-8")

        return {"filepath": str(filepath), "layer_count": len(layers), "title": title}
    except Exception as e:
        raise ToolError(f"Multi-layer map failed: {e}") from e
