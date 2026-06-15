"""Specialized chart types for data journalism: arrow and dumbbell charts.

Arrow charts show directional change with color-coded bars.
Dumbbell charts show before/after comparisons with connected dots.
"""

from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go

from .themes import apply_theme, SEMANTIC_COLORS


def arrow_chart(
    data: list[dict[str, Any]],
    label_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    reference_value: Optional[float] = None,
    sort: bool = True,
    show_values: bool = True,
) -> go.Figure:
    """Create an arrow-style chart showing directional changes.

    Horizontal bars colored green (positive) or red (negative)
    relative to a reference value (default: 0).

    Ideal for "rankings change", "budget surplus/deficit", "growth/decline".

    Args:
        data: List of row dicts
        label_column: Category labels (e.g., district names)
        value_column: Numeric values (change, growth rate, etc.)
        title: Chart title
        theme: 'dark', 'light', or 'infographic'
        reference_value: Zero line (default 0)
        sort: Sort by value (biggest change first)
        show_values: Show numeric labels on bars

    Returns:
        Plotly Figure
    """
    df = pd.DataFrame(data)
    if sort:
        df = df.sort_values(value_column, ascending=True)

    colors = []
    for val in df[value_column]:
        if reference_value is not None:
            colors.append("#2e7d32" if val >= reference_value else "#c62828")
        else:
            colors.append("#2e7d32" if val >= 0 else "#c62828")

    fig = go.Figure(
        go.Bar(
            orientation="h",
            x=df[value_column],
            y=df[label_column],
            marker_color=colors,
            text=[f"{v:+,.1f}" if show_values else "" for v in df[value_column]],
            textposition="outside",
            textfont={"size": 12, "color": "#e0e0e0"},
            hovertemplate=("<b>%{y}</b><br>%{x:,.1f}<extra></extra>"),
            name="",
        )
    )

    if reference_value is not None:
        fig.add_vline(x=reference_value, line_dash="dash", line_color="#ffab00", line_width=2)
        fig.add_annotation(
            text=f"Baseline: {reference_value:,.0f}",
            x=reference_value,
            y=1.02,
            yref="paper",
            font={"size": 11, "color": "#ffab00"},
            showarrow=False,
        )

    fig.update_layout(
        title={"text": title, "font": {"size": 22}, "x": 0.05, "xanchor": "left"},
        xaxis={"title": value_column},
        yaxis={"autorange": "reversed"},
        height=max(300, len(df) * 45 + 100),
        showlegend=False,
        bargap=0.15,
    )

    fig = apply_theme(fig, theme)
    return fig


def dumbbell_chart(
    data: list[dict[str, Any]],
    label_column: str,
    start_column: str,
    end_column: str,
    title: str = "",
    theme: str = "dark",
    sort_by: str = "change",
) -> go.Figure:
    """Create a dumbbell chart showing before/after comparison.

    Two dots per category connected by a line, showing the change
    between start and end values. Color-coded by direction.

    Ideal for "2010 vs 2022 population", "before vs after policy", "start vs end price".

    Args:
        data: List of row dicts
        label_column: Category labels
        start_column: Start/before value
        end_column: End/after value
        title: Chart title
        theme: 'dark', 'light', or 'infographic'
        sort_by: How to sort — 'change' (biggest change first), 'absolute', or column name

    Returns:
        Plotly Figure
    """
    df = pd.DataFrame(data)
    df["change"] = df[end_column] - df[start_column]
    df["pct_change"] = ((df[end_column] - df[start_column]) / df[start_column].abs().replace(0, 1)) * 100

    if sort_by == "change":
        df = df.sort_values("change", ascending=True)
    elif sort_by == "absolute":
        df = df.sort_values("change", key=abs, ascending=True)
    else:
        df = df.sort_values(sort_by, ascending=True)

    # Connector lines
    line_x = []
    line_y = []
    for _, row in df.iterrows():
        line_x.extend([row[start_column], row[end_column], None])
        line_y.extend([row[label_column], row[label_column], None])

    fig = go.Figure()

    # Connector lines
    fig.add_trace(
        go.Scatter(
            x=line_x,
            y=line_y,
            mode="lines",
            line={"color": "rgba(255,255,255,0.2)", "width": 2},
            hoverinfo="skip",
            showlegend=False,
            name="",
        )
    )

    # Start dots
    fig.add_trace(
        go.Scatter(
            x=df[start_column],
            y=df[label_column],
            mode="markers+text",
            marker={"size": 10, "color": "#1565c0"},
            text=[f"{v:,.0f}" for v in df[start_column]],
            textposition="middle left",
            textfont={"size": 11, "color": "#90a4ae"},
            hovertemplate="<b>%{y}</b><br>Početak: %{x:,.0f}<extra></extra>",
            name="Početak",
            legendgroup="dots",
        )
    )

    # End dots (color by direction)
    end_colors = ["#2e7d32" if c >= 0 else "#c62828" for c in df["change"]]
    fig.add_trace(
        go.Scatter(
            x=df[end_column],
            y=df[label_column],
            mode="markers+text",
            marker={"size": 10, "color": end_colors},
            text=[f"{row[end_column]:,.0f} ({row['pct_change']:+.1f}%)" for _, row in df.iterrows()],
            textposition="middle right",
            textfont={"size": 11, "color": "#e0e0e0"},
            hovertemplate=("<b>%{y}</b><br>Kraj: %{x:,.0f}<br>Promena: %{customdata[0]:+.1f}%<extra></extra>"),
            customdata=df[["pct_change"]].values.tolist(),
            name="Kraj",
            legendgroup="dots",
        )
    )

    fig.update_layout(
        title={"text": title, "font": {"size": 22}, "x": 0.05, "xanchor": "left"},
        xaxis={"title": ""},
        yaxis={"autorange": "reversed"},
        height=max(300, len(df) * 50 + 120),
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        hovermode="closest",
    )

    fig = apply_theme(fig, theme)
    return fig


def lollipop_chart(
    data: list[dict[str, Any]],
    label_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    highlight_column: Optional[str] = None,
    highlight_value: Optional[str] = None,
) -> go.Figure:
    """Create a lollipop chart — dots on stems for clean ranking visualization.

    Like a bar chart but with dots instead of bars, giving a cleaner look.
    Can highlight a specific category.

    Args:
        data: List of row dicts
        label_column: Category labels
        value_column: Numeric values
        title: Chart title
        theme: Visual theme
        highlight_column: Column to match for highlighting
        highlight_value: Value to highlight

    Returns:
        Plotly Figure
    """
    df = pd.DataFrame(data)
    df = df.sort_values(value_column, ascending=True)

    if highlight_column and highlight_value:
        colors = ["#ffab00" if row[highlight_column] == highlight_value else "#1565c0" for _, row in df.iterrows()]
        sizes = [14 if row[highlight_column] == highlight_value else 8 for _, row in df.iterrows()]
    else:
        colors = SEMANTIC_COLORS[: len(df)] * 2
        colors = colors[: len(df)]
        sizes = [8] * len(df)

    fig = go.Figure()

    # Stems (vertical lines)
    for _, row in df.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[0, row[value_column]],
                y=[row[label_column], row[label_column]],
                mode="lines",
                line={"color": "rgba(255,255,255,0.15)", "width": 2},
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # Dots
    fig.add_trace(
        go.Scatter(
            x=df[value_column],
            y=df[label_column],
            mode="markers+text",
            marker={"size": sizes, "color": colors, "line": {"width": 1, "color": "rgba(255,255,255,0.5)"}},
            text=[f"{v:,.0f}" for v in df[value_column]],
            textposition="middle right",
            textfont={"size": 12, "color": "#e0e0e0"},
            hovertemplate="<b>%{y}</b><br>%{x:,.0f}<extra></extra>",
            name="",
        )
    )

    fig.update_layout(
        title={"text": title, "font": {"size": 22}, "x": 0.05, "xanchor": "left"},
        xaxis={"title": value_column},
        yaxis={"autorange": "reversed"},
        height=max(300, len(df) * 45 + 100),
        showlegend=False,
    )

    fig = apply_theme(fig, theme)
    return fig
