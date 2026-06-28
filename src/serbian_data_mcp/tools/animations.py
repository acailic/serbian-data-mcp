"""Animated charts and scrollytelling tools.

Contracts:
  - create_animated_chart(animation_type, data, ...) → HTML filepath
  - create_scrollytelling_story(steps, ...) → HTML filepath
"""

from __future__ import annotations

from typing import Any

from fastmcp.exceptions import ToolError

from .. import mcp
from ..config import config
from ..viz.exporters import export_html
from ..viz.themes import apply_theme
from ..viz.animations import animated_timeline, animated_bars_evolution, animated_comparison
from ..viz.scrollytelling import scrollytelling


def _save_html(fig, filename: str) -> str:
    """Save a Plotly figure to HTML and return the filepath."""
    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")
    return str(filepath)


@mcp.tool()
async def create_animated_chart(
    animation_type: str = "bars_evolution",
    data: list[dict[str, Any]] = [],
    datasets: dict[str, list[dict[str, Any]]] = {},
    time_column: str = "",
    category_column: str = "",
    value_column: str = "",
    title: str = "",
    theme: str = "dark",
    filename: str = "animated",
) -> dict[str, Any]:
    """Create animated charts with smooth transitions and play/pause.

    Three animation types:
      - 'bars_evolution': Bar chart time evolution with auto-sorting. Needs time_column, category_column, value_column.
      - 'timeline': Morphs bar→line chart over time. Needs time_column, category_column, value_column.
      - 'comparison': Toggle between datasets. Needs datasets={label: data}, category_column, value_column.

    All include play/pause and slider scrubber.

    Returns: {filepath, animation_type, title}

    Args:
        animation_type: 'bars_evolution', 'timeline', or 'comparison'
        data: Single dataset (for bars_evolution and timeline)
        datasets: Dict of label→data (for comparison)
        time_column: Time periods column
        category_column: Entity names column
        value_column: Numeric values column
        title: Chart title
        theme: Visual theme
        filename: Output filename (without .html)
    """
    valid_types = {"bars_evolution", "timeline", "comparison"}
    if animation_type not in valid_types:
        raise ToolError(f"Invalid type. Use: {', '.join(sorted(valid_types))}")

    try:
        fig = None
        if animation_type == "bars_evolution" and data:
            fig = animated_bars_evolution(
                data,
                time_column=time_column,
                category_column=category_column,
                value_column=value_column,
                title=title,
                theme=theme,
            )
        elif animation_type == "timeline" and data:
            fig = animated_timeline(
                data,
                time_column=time_column,
                category_column=category_column,
                value_column=value_column,
                title=title,
                theme=theme,
            )
        elif animation_type == "comparison" and datasets:
            fig = animated_comparison(
                datasets,
                category_column=category_column,
                value_column=value_column,
                title=title,
                theme=theme,
            )

        if fig is None:
            raise ToolError(f"Failed to create {animation_type}. Check parameters.")

        fig = apply_theme(fig, theme)
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "animation_type": animation_type, "title": title}
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Animated chart failed: {e}") from e


@mcp.tool()
async def create_scrollytelling_story(
    steps: list[dict[str, Any]],
    title: str = "Serbian Data Story",
    subtitle: str = "",
    byline: str = "",
    theme: str = "dark",
    filename: str = "story",
) -> dict[str, Any]:
    """Create a scroll-driven HTML data story (scrollytelling).

    Multi-section page with narrative text scrolling left and interactive
    charts updating right — the visualise.admin.ch pattern.

    Each step:
      - 'headline': Section headline
      - 'text': Narrative (supports <br>, <b>, <em>)
      - 'chart': Plotly figure dict (from create_chart())
      - 'big_number': Large stat (e.g., '-12%')
      - 'big_number_label': Label for stat
      - 'highlight_color': Accent color (default: #0C4076)

    Output: hero header, progress bar, sticky chart area, scroll animations.

    Returns: {filepath, step_count, title}

    Args:
        steps: List of step dicts
        title: Story title
        subtitle: Story subtitle
        byline: Author credit
        theme: 'dark' or 'light'
        filename: Output filename (without .html)
    """
    from plotly.graph_objects import Figure

    # Convert figure dicts back to Plotly figures
    processed_steps = []
    for step in steps:
        proc = dict(step)
        if "chart" in step and step["chart"] and isinstance(step["chart"], dict):
            proc["chart"] = Figure(step["chart"].get("data", []), step["chart"].get("layout", {}))
        processed_steps.append(proc)

    try:
        output_dir = config.export_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / f"{filename}.html"

        html_path = scrollytelling(
            processed_steps,
            title=title,
            subtitle=subtitle,
            byline=byline,
            theme=theme,
            output_path=filepath,
        )

        return {
            "filepath": html_path,
            "step_count": len(steps),
            "title": title,
        }
    except Exception as e:
        raise ToolError(f"Scrollytelling failed: {e}") from e
