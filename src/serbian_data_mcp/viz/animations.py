"""Animated chart transitions using Plotly animation frames.

Create smooth morphing between chart states for data storytelling.
Supports bar→line transitions, time evolution, and type switches.
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go

from .themes import apply_theme


def animated_timeline(
    data: list[dict[str, Any]],
    time_column: str,
    category_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    frame_duration: int = 800,
    transition_duration: int = 300,
    final_type: str = "line",  # noqa: ARG001
) -> go.Figure:
    """Create an animated chart that morphs from bars to line over time.

    Shows data as animated bars for the first half of the timeline,
    then transitions to a line chart for the second half.

    Args:
        data: List of row dicts
        time_column: Time/period values (e.g., years)
        category_column: Category names
        value_column: Numeric values
        title: Chart title
        theme: Visual theme
        frame_duration: Milliseconds per frame
        transition_duration: Milliseconds for transitions
        final_type: Final chart type ('line', 'area', 'scatter')

    Returns:
        Plotly Figure with animation frames
    """
    df = pd.DataFrame(data)
    times = sorted(df[time_column].unique().tolist())
    categories = df[category_column].unique().tolist()

    frames = []
    slider_steps = []

    for i, t in enumerate(times):
        subset = df[df[time_column] == t]

        if i <= len(times) // 2:
            # Bar chart phase
            bar_trace = go.Bar(
                x=subset[category_column],
                y=subset[value_column],
                marker_color="#1565c0",
                hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra></extra>",
                name="",
            )
            frames.append(go.Frame(data=[bar_trace], name=str(t)))
        else:
            # Line chart phase — show full history up to this point
            hist = df[df[time_column] <= t]
            traces = []
            for cat in categories:
                cat_data = hist[hist[category_column] == cat].sort_values(time_column)
                if len(cat_data) > 1:
                    traces.append(
                        go.Scatter(
                            x=cat_data[time_column],
                            y=cat_data[value_column],
                            mode="lines+markers",
                            line={"width": 2},
                            name=cat,
                            hovertemplate="<b>" + cat + "</b><br>%{x}<br>%{y:,.0f}<extra></extra>",
                        )
                    )
            if not traces:
                traces = [
                    go.Bar(
                        x=subset[category_column],
                        y=subset[value_column],
                        marker_color="#1565c0",
                        name="",
                    )
                ]
            frames.append(go.Frame(data=traces, name=str(t)))

        slider_steps.append(
            {
                "label": str(t),
                "method": "animate",
                "args": [[str(t)], {"frame": {"duration": frame_duration, "redraw": True}}],
            }
        )

    # Initial frame
    first_data = df[df[time_column] == times[0]]
    fig = go.Figure(
        data=[
            go.Bar(
                x=first_data[category_column],
                y=first_data[value_column],
                marker_color="#1565c0",
                name="",
            )
        ],
        frames=frames,
    )

    fig.update_layout(
        title={"text": title, "font": {"size": 22}, "x": 0.05, "xanchor": "left"},
        xaxis={"title": ""},
        yaxis={"title": value_column},
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "x": 0.05,
                "y": 0,
                "buttons": [
                    {"label": "▶ Pokreni", "method": "animate", "args": [None]},
                    {"label": "⏸ Pauza", "method": "animate", "args": [[None], {"frame": {"duration": 0}}]},
                ],
            }
        ],
        sliders=[
            {
                "active": 0,
                "steps": slider_steps,
                "len": 0.9,
                "x": 0.05,
                "currentvalue": {"prefix": "Period: ", "font": {"size": 14}},
                "transition": {"easing": "cubic-in-out", "duration": transition_duration},
            }
        ],
        showlegend=False,
    )

    fig = apply_theme(fig, theme)
    return fig


def animated_bars_evolution(
    data: list[dict[str, Any]],
    time_column: str,
    category_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    frame_duration: int = 600,
) -> go.Figure:
    """Animated bar chart that shows time evolution with smooth bar transitions.

    Bars grow/shrink smoothly as you advance through time periods.
    Categories auto-sort by value in each frame.

    Args:
        data: List of row dicts
        time_column: Time period values
        category_column: Category names
        value_column: Numeric values
        title: Chart title
        theme: Visual theme
        frame_duration: Milliseconds per frame

    Returns:
        Plotly Figure with animation
    """
    df = pd.DataFrame(data)
    times = sorted(df[time_column].unique().tolist())

    frames = []
    slider_steps = []

    for t in times:
        subset = df[df[time_column] == t].sort_values(value_column, ascending=True)

        bar_trace = go.Bar(
            x=subset[category_column],
            y=subset[value_column],
            text=[f"{v:,.0f}" for v in subset[value_column]],
            textposition="outside",
            textfont={"size": 11, "color": "#e0e0e0"},
            marker_color=subset[value_column],
            marker_colorscale="Blues",
            hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra></extra>",
            name="",
        )

        frames.append(go.Frame(data=[bar_trace], name=str(t)))
        slider_steps.append(
            {
                "label": str(t),
                "method": "animate",
                "args": [[str(t)], {"frame": {"duration": frame_duration, "redraw": True}}],
            }
        )

    # Initial frame
    first = df[df[time_column] == times[0]].sort_values(value_column, ascending=True)
    fig = go.Figure(
        data=[
            go.Bar(
                x=first[category_column],
                y=first[value_column],
                marker_color=first[value_column],
                marker_colorscale="Blues",
                name="",
            )
        ],
        frames=frames,
    )

    fig.update_layout(
        title={"text": title, "font": {"size": 22}, "x": 0.05, "xanchor": "left"},
        yaxis={"title": value_column},
        xaxis={"tickangle": -45},
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "x": 0.05,
                "y": -0.1,
                "buttons": [
                    {"label": "▶ Pokreni", "method": "animate", "args": [None]},
                    {"label": "⏸ Pauza", "method": "animate", "args": [[None], {"frame": {"duration": 0}}]},
                ],
            }
        ],
        sliders=[
            {
                "active": 0,
                "steps": slider_steps,
                "len": 0.9,
                "x": 0.05,
                "currentvalue": {"prefix": "Period: ", "font": {"size": 14}},
                "transition": {"easing": "cubic-in-out", "duration": 300},
            }
        ],
        showlegend=False,
        barmode="relative",
    )

    fig = apply_theme(fig, theme)
    return fig


def animated_comparison(
    datasets: dict[str, list[dict[str, Any]]],
    category_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    colors: Optional[list[str]] = None,
) -> go.Figure:
    """Animate comparison between datasets (e.g., 2010 vs 2022).

    Toggles between datasets with smooth bar transition animation.

    Args:
        datasets: Dict of label → data
        category_column: Category names column
        value_column: Numeric values column
        title: Chart title
        theme: Visual theme
        colors: Color per dataset

    Returns:
        Plotly Figure with animation
    """
    colors = colors or ["#1565c0", "#c62828", "#2e7d32", "#ff8f00", "#6a1b9a"]
    frames = []
    slider_steps = []
    labels = list(datasets.keys())

    for i, (label, data) in enumerate(datasets.items()):
        df = pd.DataFrame(data).sort_values(value_column, ascending=True)
        bar_trace = go.Bar(
            x=df[category_column],
            y=df[value_column],
            marker_color=colors[i % len(colors)],
            text=[f"{v:,.0f}" for v in df[value_column]],
            textposition="outside",
            textfont={"size": 11, "color": "#e0e0e0"},
            hovertemplate=f"<b>{label}</b><br>%{{x}}<br>%{{y:,.0f}}<extra></extra>",
            name=label,
        )
        frames.append(go.Frame(data=[bar_trace], name=label))
        slider_steps.append(
            {
                "label": label,
                "method": "animate",
                "args": [[label], {"frame": {"duration": 600, "redraw": True}}],
            }
        )

    first_label = labels[0]
    first_df = pd.DataFrame(datasets[first_label]).sort_values(value_column, ascending=True)
    fig = go.Figure(
        data=[
            go.Bar(
                x=first_df[category_column],
                y=first_df[value_column],
                marker_color=colors[0],
                name=first_label,
            )
        ],
        frames=frames,
    )

    fig.update_layout(
        title={"text": title, "font": {"size": 22}, "x": 0.05, "xanchor": "left"},
        yaxis={"title": value_column},
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "x": 0.05,
                "y": -0.1,
                "buttons": [
                    {"label": "▶ Pokreni", "method": "animate", "args": [None]},
                    {"label": "⏸ Pauza", "method": "animate", "args": [[None], {"frame": {"duration": 0}}]},
                ],
            }
        ],
        sliders=[
            {
                "active": 0,
                "steps": slider_steps,
                "len": 0.9,
                "x": 0.05,
                "currentvalue": {"prefix": "Podaci: ", "font": {"size": 14}},
                "transition": {"easing": "cubic-in-out", "duration": 300},
            }
        ],
        showlegend=False,
    )

    fig = apply_theme(fig, theme)
    return fig
