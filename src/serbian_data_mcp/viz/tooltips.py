"""Rich tooltip enrichment for any Plotly figure.

Adds contextual information to hover tooltips: formatted values,
percentage change, deviation from mean, comparison context.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def _fmt_num(value: float) -> str:
    """Format number for display: 1234 → '1.234', 0.15 → '15%'."""
    if abs(value) < 0.01 and value != 0:
        return f"{value:.4f}"
    if abs(value) < 1:
        return f"{value * 100:.1f}%"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.1f}"


def _fmt_delta(value: float) -> str:
    """Format a delta/change value with arrow indicator."""
    sign = "▲" if value > 0 else "▼" if value < 0 else "●"
    color = "#4caf50" if value > 0 else "#f44336" if value < 0 else "#9e9e9e"
    return f"<b style='color:{color}'>{sign} {_fmt_num(value)}</b>"


def add_rich_tooltips(
    fig: go.Figure,
    value_column: str = "value",  # noqa: ARG001
    base_column: Optional[str] = None,
    category_column: str = "name",  # noqa: ARG001
    unit: str = "",
    show_mean: bool = True,
    show_rank: bool = True,
    show_delta: bool = True,
    fmt_fn: Optional[callable] = None,
) -> go.Figure:
    """Enrich a Plotly figure's tooltips with contextual information.

    Adds to each trace's hovertemplate:
    - Formatted value with unit
    - Deviation from mean (if show_mean)
    - Rank among peers (if show_rank)
    - Delta/change from base column (if show_delta and base_column provided)

    Args:
        fig: Any Plotly figure
        value_column: Name used in z/y values
        base_column: Column name containing baseline values for delta calc
        category_column: Name used in x/y category labels
        unit: Unit suffix (e.g., " stanovnika", " RSD", "%")
        show_mean: Show deviation from mean
        show_rank: Show rank position
        show_delta: Show change from baseline
        fmt_fn: Custom formatting function (value) -> str

    Returns:
        The same figure with enriched tooltips
    """
    # Extract all z/y values across traces to compute mean/rank
    all_values: list[float] = []
    for trace in fig.data:
        if hasattr(trace, "z") and trace.z is not None:
            arr = np.array(trace.z).flatten()
            all_values.extend(arr[~np.isnan(arr)].tolist())
        elif hasattr(trace, "y") and trace.y is not None:
            arr = np.array(trace.y).flatten()
            all_values.extend(arr[~np.isnan(arr)].tolist())

    if not all_values:
        return fig

    mean_val = np.mean(all_values)
    sorted_vals = sorted(all_values, reverse=True)

    fmt = fmt_fn or _fmt_num

    for trace in fig.data:
        # Build extra tooltip lines
        extra_lines: list[str] = []

        if show_mean:
            _deviation_pct = ((np.mean(all_values) - mean_val) / mean_val * 100) if mean_val != 0 else 0  # noqa: F841
            extra_lines.append(f"Prosečno: {fmt(mean_val)}{unit}")

        if show_rank and all_values:
            extra_lines.append("Rank: %{_rank}")

        if show_delta and base_column:
            extra_lines.append("Promena: %{_delta}")

        if not extra_lines:
            continue

        extra_text = "<br>".join(extra_lines)
        existing = trace.hovertemplate or "<b>%{x}</b><br>%{y}<extra></extra>"

        # Inject extra lines before <extra>
        if "<extra>" in existing:
            new_template = existing.replace("<extra>", f"{extra_text}<extra>")
        else:
            new_template = f"{existing}<br>{extra_text}<extra></extra>"

        trace.hovertemplate = new_template

        # Add custom data for rank
        if show_rank and hasattr(trace, "y") and trace.y is not None:
            ranks = []
            for v in np.array(trace.y).flatten():
                if np.isnan(v):
                    ranks.append("")
                else:
                    idx = next((i for i, sv in enumerate(sorted_vals) if abs(sv - v) < 1e-9), 0)
                    ranks.append(f"#{idx + 1} od {len(sorted_vals)}")
            trace.customdata = np.column_stack([ranks]) if hasattr(trace, "customdata") else np.array(ranks)

    return fig


def add_annotation_callouts(
    fig: go.Figure,
    points: list[dict[str, Any]],
    prefix: str = "",
    suffix: str = "",
) -> go.Figure:
    """Add annotation callout boxes to highlight specific data points.

    Args:
        fig: Plotly figure with scatter/bar traces
        points: List of dicts with keys:
            - x, y: Position
            - text: Callout text
            - color: Optional background color (default: #1565c0)
        prefix, suffix: Text before/after callout

    Returns:
        Figure with annotation callouts
    """
    for pt in points:
        color = pt.get("color", "#1565c0")
        fig.add_annotation(
            x=pt["x"],
            y=pt["y"],
            text=f"{prefix}{pt['text']}{suffix}",
            font=dict(size=13, color="white"),
            bgcolor=color,
            bordercolor="rgba(255,255,255,0.3)",
            borderwidth=1,
            borderpad=8,
            arrowsize=1.5,
            arrowcolor="rgba(255,255,255,0.5)",
            ax=pt.get("ax", 0),
            ay=pt.get("ay", -40),
            arrowhead=2,
        )
    return fig


def add_comparison_markers(
    fig: go.Figure,
    threshold: float,
    label: str = "",
    direction: str = "above",
    color: str = "#ffab00",
) -> go.Figure:
    """Add a horizontal threshold/reference line with label.

    Args:
        fig: Plotly figure
        threshold: Y-value of the threshold line
        label: Label text (empty for no label)
        direction: 'above' or 'below' — where to position the label
        color: Line and label color

    Returns:
        Figure with threshold line
    """
    fig.add_hline(
        y=threshold,
        line_dash="dash",
        line_color=color,
        line_width=1.5,
        annotation_text=label,
        annotation_position=f"top {'left' if direction == 'above' else 'right'}" if label else "",
        annotation_font_color=color,
        annotation_font_size=12,
    )
    return fig
