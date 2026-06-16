"""Novel and specialized chart types.

Contracts:
  - create_lollipop_chart(data, label_column, value_column) → HTML filepath
  - create_arrow_chart(data, label_column, value_column) → HTML filepath
  - create_dumbbell_chart(data, label_column, start_column, end_column) → HTML filepath
  - create_slope_chart(data, entity_column, start_column, end_column) → HTML filepath
  - create_waffle_chart(data, names_column, values_column) → HTML filepath
  - create_population_pyramid(data, age_column, male_column, female_column) → HTML filepath
  - create_sankey_diagram(data, source_column, target_column, value_column) → HTML filepath
  - create_radar_chart(data, category_column, value_columns) → HTML filepath
"""

from __future__ import annotations

from typing import Any, Optional

from fastmcp.exceptions import ToolError

from .. import mcp
from ..config import config
from ..viz.exporters import export_html
from ..viz.special_charts import arrow_chart, dumbbell_chart, lollipop_chart
from ..viz.novel_charts import slope_chart, waffle_chart, population_pyramid, sankey_diagram, radar_chart


def _save_html(fig, filename: str) -> str:
    """Save a Plotly figure to HTML and return the filepath."""
    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")
    return str(filepath)


@mcp.tool()
async def create_arrow_chart(
    data: list[dict[str, Any]],
    label_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    reference_value: Optional[float] = None,
    filename: str = "arrow_chart",
) -> dict[str, Any]:
    """Arrow-style chart showing directional changes. Green=positive, red=negative.

    Ideal for: rankings change, budget surplus/deficit, growth/decline.

    Returns: {filepath, title, rows}

    Args:
        data: Row dicts
        label_column: Category labels
        value_column: Numeric values (change, growth rate)
        title: Chart title
        theme: 'dark', 'light', or 'infographic'
        reference_value: Zero/baseline (default: 0)
        filename: Output filename (without .html)
    """
    try:
        fig = arrow_chart(
            data,
            label_column=label_column,
            value_column=value_column,
            title=title,
            theme=theme,
            reference_value=reference_value,
        )
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "title": title, "rows": len(data)}
    except Exception as e:
        raise ToolError(f"Arrow chart failed: {e}") from e


@mcp.tool()
async def create_dumbbell_chart(
    data: list[dict[str, Any]],
    label_column: str,
    start_column: str,
    end_column: str,
    title: str = "",
    theme: str = "dark",
    filename: str = "dumbbell_chart",
) -> dict[str, Any]:
    """Dumbbell chart: before/after comparison with connected dots.

    Green=increase, red=decrease. Shows magnitude and direction.

    Ideal for: population 2010 vs 2022, budget planned vs executed.

    Returns: {filepath, title, rows}

    Args:
        data: Row dicts with start and end values
        label_column: Category names
        start_column: Starting/baseline values
        end_column: Final/current values
        title: Chart title
        theme: Visual theme
        filename: Output filename
    """
    try:
        fig = dumbbell_chart(
            data,
            label_column=label_column,
            start_column=start_column,
            end_column=end_column,
            title=title,
            theme=theme,
        )
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "title": title, "rows": len(data)}
    except Exception as e:
        raise ToolError(f"Dumbbell chart failed: {e}") from e


@mcp.tool()
async def create_lollipop_chart(
    data: list[dict[str, Any]],
    label_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    highlight_column: Optional[str] = None,
    highlight_value: Optional[str] = None,
    filename: str = "lollipop_chart",
) -> dict[str, Any]:
    """Lollipop chart — dots on stems for clean ranking. Can highlight one entity.

    Ideal for: district population ranking, budget by ministry, top-N lists.

    Returns: {filepath, title, rows}

    Args:
        data: Row dicts
        label_column: Category labels
        value_column: Numeric values to rank by
        title: Chart title
        theme: Visual theme
        highlight_column: Column to match for highlighting
        highlight_value: Value to highlight (e.g., 'Grad Beograd')
        filename: Output filename
    """
    try:
        fig = lollipop_chart(
            data,
            label_column=label_column,
            value_column=value_column,
            title=title,
            theme=theme,
            highlight_column=highlight_column,
            highlight_value=highlight_value,
        )
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "title": title, "rows": len(data)}
    except Exception as e:
        raise ToolError(f"Lollipop chart failed: {e}") from e


@mcp.tool()
async def create_slope_chart(
    data: list[dict[str, Any]],
    entity_column: str,
    start_column: str,
    end_column: str,
    title: str = "",
    theme: str = "dark",
    top_n: int = 15,
    filename: str = "slope_chart",
) -> dict[str, Any]:
    """Slope chart: ranking changes between two periods with connecting lines.

    Green=gained rank, red=lost rank.

    Ideal for: census ranking 2002→2022, budget share shifts, district reorderings.

    Returns: {filepath, title, rows}

    Args:
        data: Row dicts with entity names and two period values
        entity_column: Entity/district names
        start_column: First period values
        end_column: Second period values
        title: Chart title
        theme: Visual theme
        top_n: Number of entities to show
        filename: Output filename
    """
    try:
        fig = slope_chart(data, entity_column, start_column, end_column, title=title, theme=theme, top_n=top_n)
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "title": title, "rows": len(data)}
    except Exception as e:
        raise ToolError(f"Slope chart failed: {e}") from e


@mcp.tool()
async def create_waffle_chart(
    data: list[dict[str, Any]],
    names_column: str,
    values_column: str,
    title: str = "",
    theme: str = "dark",
    total_icons: int = 100,
    filename: str = "waffle_chart",
) -> dict[str, Any]:
    """Waffle chart (icon grid) for proportional data. 'X out of 100' visualization.

    More intuitive than pie charts for showing proportions.

    Ideal for: '1 in 4 Serbs live in Belgrade', budget share, sector breakdown.

    Returns: {filepath, title, categories}

    Args:
        data: Row dicts
        names_column: Category labels
        values_column: Numeric values (normalized to fill grid)
        title: Chart title
        theme: Visual theme
        total_icons: Total icons in grid (100=10×10)
        filename: Output filename
    """
    try:
        fig = waffle_chart(data, names_column, values_column, title=title, theme=theme, total_icons=total_icons)
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "title": title, "categories": len(data)}
    except Exception as e:
        raise ToolError(f"Waffle chart failed: {e}") from e


@mcp.tool()
async def create_population_pyramid(
    data: list[dict[str, Any]],
    age_column: str,
    male_column: str,
    female_column: str,
    title: str = "",
    theme: str = "dark",
    filename: str = "population_pyramid",
) -> dict[str, Any]:
    """Population pyramid: age × sex distribution. Males left, females right.

    Essential for census data from RZS. Classic demographic visualization.

    Returns: {filepath, title, age_groups}

    Args:
        data: Row dicts with age groups and male/female counts
        age_column: Age group labels (e.g., '0-4', '5-9', '65+')
        male_column: Male population counts
        female_column: Female population counts
        title: Chart title
        theme: Visual theme
        filename: Output filename
    """
    try:
        fig = population_pyramid(data, age_column, male_column, female_column, title=title, theme=theme)
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "title": title, "age_groups": len(data)}
    except Exception as e:
        raise ToolError(f"Population pyramid failed: {e}") from e


@mcp.tool()
async def create_sankey_diagram(
    data: list[dict[str, Any]],
    source_column: str,
    target_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    filename: str = "sankey",
) -> dict[str, Any]:
    """Sankey (alluvial) diagram showing flow between categories.

    Ideal for: budget flow (revenue→ministry→spending), energy distribution,
    migration flows, supply chains.

    Returns: {filepath, title, flows}

    Args:
        data: Row dicts with source, target, and flow value
        source_column: Source/origin category
        target_column: Target/destination category
        value_column: Flow magnitude
        title: Chart title
        theme: Visual theme
        filename: Output filename
    """
    try:
        fig = sankey_diagram(data, source_column, target_column, value_column, title=title, theme=theme)
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "title": title, "flows": len(data)}
    except Exception as e:
        raise ToolError(f"Sankey diagram failed: {e}") from e


@mcp.tool()
async def create_radar_chart(
    data: list[dict[str, Any]],
    category_column: str,
    value_columns: list[str],
    title: str = "",
    theme: str = "dark",
    filename: str = "radar",
) -> dict[str, Any]:
    """Radar/spider chart for multi-metric comparison.

    Compare entities across multiple indicators on one radar plot.

    Ideal for: comparing districts on population+budget+schools+hospitals+air quality.

    Returns: {filepath, title, entities, metrics}

    Args:
        data: Row dicts
        category_column: Entity names
        value_columns: List of numeric columns to compare
        title: Chart title
        theme: Visual theme
        filename: Output filename
    """
    try:
        fig = radar_chart(data, category_column, value_columns, title=title, theme=theme)
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "title": title, "entities": len(data), "metrics": len(value_columns)}
    except Exception as e:
        raise ToolError(f"Radar chart failed: {e}") from e
