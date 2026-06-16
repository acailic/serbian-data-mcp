"""Specialized chart types for Serbian data journalism.

Adds slope charts, waffle/icon charts, population pyramids, and
sankey diagrams — chart types that appear frequently in Serbian
government data but aren't covered by the basic or advanced builders.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from .themes import apply_theme, SEMANTIC_COLORS


def slope_chart(
    data: list[dict[str, Any]],
    entity_column: str,
    start_column: str,
    end_column: str,
    title: str = "",
    theme: str = "dark",
    top_n: int = 15,
    color_by_direction: bool = True,
    sort_by: str = "change",
) -> go.Figure:
    """Create a slope chart showing ranking changes between two periods.

    Ideal for: census ranking changes (2002 vs 2022), budget share shifts,
    district population reorderings. Entities are ranked vertically in both
    periods and connected with lines showing how they moved.

    Args:
        data: List of row dicts with entity names and two period values
        entity_column: Category/entity names (e.g., district names)
        start_column: First period values (e.g., 'pop_2002')
        end_column: Second period values (e.g., 'pop_2022')
        title: Chart title
        theme: 'dark', 'light', or 'infographic'
        top_n: Number of entities to show (sorted by change magnitude)
        color_by_direction: Color lines green for gainers, red for losers
        sort_by: 'change' (biggest movers first), 'start' (start value), or column name

    Returns:
        Plotly Figure
    """
    df = pd.DataFrame(data)
    df["change"] = df[end_column] - df[start_column]
    df["pct_change"] = ((df[end_column] - df[start_column]) / df[start_column].abs().replace(0, 1)) * 100

    if sort_by == "change":
        df = df.reindex(df["change"].abs().sort_values(ascending=False).index)
    elif sort_by == "start":
        df = df.sort_values(start_column, ascending=True)
    else:
        df = df.sort_values(sort_by, ascending=True)

    df = df.head(top_n)

    # Create position-based layout (rank by value, not alphabetical)
    df["start_rank"] = df[start_column].rank(ascending=True).astype(int)
    df["end_rank"] = df[end_column].rank(ascending=True).astype(int)

    fig = go.Figure()

    for _, row in df.iterrows():
        if color_by_direction:
            color = "#2e7d32" if row["change"] >= 0 else "#c62828"
        else:
            color = "#1565c0"

        fig.add_trace(
            go.Scatter(
                x=["Početak", "Kraj"],
                y=[row["start_rank"], row["end_rank"]],
                mode="lines+markers",
                line={"width": 2.5, "color": color},
                marker={"size": 6, "color": color},
                hovertemplate=(
                    f"<b>{row[entity_column]}</b><br>"
                    f"Početak: {row[start_column]:,.0f}<br>"
                    f"Kraj: {row[end_column]:,.0f}<br>"
                    f"Promena: {row['pct_change']:+.1f}%<extra></extra>"
                ),
                name=row[entity_column],
                showlegend=False,
            )
        )

    # Add entity labels at start and end
    for _, row in df.iterrows():
        fig.add_annotation(
            x="Početak",
            y=row["start_rank"],
            text=str(row[entity_column]),
            showarrow=False,
            xanchor="right",
            xshift=-8,
            font={"size": 11, "color": "#e0e0e0"},
        )
        fig.add_annotation(
            x="Kraj",
            y=row["end_rank"],
            text=str(row[entity_column]),
            showarrow=False,
            xanchor="left",
            xshift=8,
            font={"size": 11, "color": "#e0e0e0"},
        )

    fig.update_layout(
        title={"text": title, "font": {"size": 22}, "x": 0.5, "xanchor": "center"},
        xaxis={
            "tickfont": {"size": 14, "color": "#b0bec5"},
            "showgrid": False,
        },
        yaxis={"visible": False, "showticklabels": False, "range": [0.5, top_n + 0.5]},
        height=max(400, top_n * 35 + 100),
        showlegend=False,
        hovermode="closest",
    )

    fig = apply_theme(fig, theme)
    return fig


def waffle_chart(
    data: list[dict[str, Any]],
    names_column: str,
    values_column: str,
    title: str = "",
    theme: str = "dark",
    total_icons: int = 100,
    icon_size: int = 20,
    gap: int = 2,
) -> go.Figure:
    """Create a waffle chart (icon grid) for proportional data.

    Shows each category as a block of small squares in a 10×10 (or NxN) grid.
    More intuitive than pie charts for showing "X out of 100".

    Ideal for: "1 in 4 Serbs live in Belgrade", budget share visualization,
    employment sector breakdown.

    Args:
        data: List of row dicts with category names and values
        names_column: Category labels
        values_column: Numeric values (will be normalized to fill the grid)
        title: Chart title
        theme: Visual theme
        total_icons: Total number of icons in the grid (default 100)
        icon_size: Size of each icon square in pixels
        gap: Gap between icons in pixels

    Returns:
        Plotly Figure (heatmap-based)
    """
    df = pd.DataFrame(data)
    total = df[values_column].sum()
    if total == 0:
        return go.Figure()

    # Calculate number of icons per category
    df["n_icons"] = (df[values_column] / total * total_icons).round().astype(int)
    # Adjust to exactly total_icons
    diff = total_icons - df["n_icons"].sum()
    if diff != 0 and len(df) > 0:
        df.loc[df.index[0], "n_icons"] += diff

    # Build grid (row, col) positions
    grid_rows: list[int] = []
    grid_cols: list[int] = []
    grid_colors: list[str] = []
    grid_labels: list[str] = []
    grid_texts: list[str] = []

    icons_per_row = int(np.ceil(np.sqrt(total_icons)))
    pos = 0
    color_map = dict(zip(df[names_column], SEMANTIC_COLORS[: len(df)], strict=False))

    for _, row in df.iterrows():
        name = row[names_column]
        color = color_map.get(name, SEMANTIC_COLORS[0])
        for _ in range(int(row["n_icons"])):
            r = pos // icons_per_row
            c = pos % icons_per_row
            grid_rows.append(r)
            grid_cols.append(c)
            grid_colors.append(color)
            grid_labels.append(name)
            grid_texts.append(f"{name}: {row[values_column]:,.0f} ({row[values_column] / total:.1%})")
            pos += 1

    # Fill remaining with transparent
    while pos < total_icons:
        r = pos // icons_per_row
        c = pos % icons_per_row
        grid_rows.append(r)
        grid_cols.append(c)
        grid_colors.append("rgba(0,0,0,0)")
        grid_labels.append("")
        grid_texts.append("")
        pos += 1

    fig = go.Figure(
        go.Scatter(
            x=grid_cols,
            y=grid_rows,
            mode="markers",
            marker={
                "size": icon_size,
                "color": grid_colors,
                "symbol": "square",
                "line": {"width": 0},
            },
            hovertemplate="%{text}<extra></extra>",
            text=grid_texts,
            showlegend=False,
        )
    )

    # Add legend
    for _, row in df.iterrows():
        color = color_map.get(row[names_column], SEMANTIC_COLORS[0])
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker={"size": 12, "color": color, "symbol": "square"},
                name=f"{row[names_column]} ({row[values_column]:,.0f}, {row[values_column] / total:.1%})",
                showlegend=True,
            )
        )

    fig.update_layout(
        title={"text": title, "font": {"size": 22}, "x": 0.5, "xanchor": "center"},
        xaxis={
            "visible": False,
            "range": [-0.5, icons_per_row + 0.5],
            "scaleanchor": "y",
            "scaleratio": 1,
        },
        yaxis={
            "visible": False,
            "range": [-0.5, (total_icons // icons_per_row) + 1.5],
            "autorange": "reversed",
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.15,
            "xanchor": "center",
            "x": 0.5,
        },
        height=max(400, (total_icons // icons_per_row + 2) * (icon_size + gap)),
    )

    fig = apply_theme(fig, theme)
    return fig


def population_pyramid(
    data: list[dict[str, Any]],
    age_column: str,
    male_column: str,
    female_column: str,
    title: str = "",
    theme: str = "dark",
    age_order: Optional[list[str]] = None,
    bar_gap: float = 0.15,
) -> go.Figure:
    """Create a population pyramid (age × sex distribution).

    Classic demographic visualization with age groups on the Y axis,
    males on the left (negative values) and females on the right.
    Essential for census and demographic data from RZS.

    Args:
        data: List of row dicts with age groups and male/female counts
        age_column: Age group labels (e.g., '0-4', '5-9', '65+')
        male_column: Male population counts (shown left/negative)
        female_column: Female population counts (shown right/positive)
        title: Chart title
        theme: Visual theme
        age_order: Optional list specifying age group order (bottom to top)
        bar_gap: Gap between bars (0-1)

    Returns:
        Plotly Figure
    """
    df = pd.DataFrame(data)

    if age_order:
        df["_sort_key"] = df[age_column].map({v: i for i, v in enumerate(age_order)})
        df = df.dropna(subset=["_sort_key"]).sort_values("_sort_key")
        df = df.drop(columns=["_sort_key"])
    else:
        df["_sort_num"] = df[age_column].str.extract(r"(\d+)").astype(float).fillna(0)
        df = df.sort_values("_sort_num").drop(columns=["_sort_num"])

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=df[age_column],
            x=-df[male_column],
            orientation="h",
            name="Muški",
            marker_color="#1565c0",
            hovertemplate="<b>%{y}</b><br>Muški: %{x:,.0f}<extra></extra>",
            text=[f"{v:,.0f}" for v in df[male_column]],
            textposition="outside",
            textfont={"size": 10, "color": "#90a4ae"},
        )
    )

    fig.add_trace(
        go.Bar(
            y=df[age_column],
            x=df[female_column],
            orientation="h",
            name="Ženski",
            marker_color="#c62828",
            hovertemplate="<b>%{y}</b><br>Ženski: %{x:,.0f}<extra></extra>",
            text=[f"{v:,.0f}" for v in df[female_column]],
            textposition="outside",
            textfont={"size": 10, "color": "#90a4ae"},
        )
    )

    max_val = max(df[male_column].max(), df[female_column].max()) * 1.1

    fig.update_layout(
        title={"text": title, "font": {"size": 22}, "x": 0.5, "xanchor": "center"},
        barmode="overlay",
        bargap=bar_gap,
        xaxis={
            "title": "",
            "tickfont": {"size": 11},
            "gridcolor": "#2a3a5c",
            "range": [-max_val, max_val],
            "tickformat": ",.0f",
            "tickvals": np.linspace(-max_val, max_val, 9),
            "ticktext": [f"{abs(v):,.0f}" for v in np.linspace(-max_val, max_val, 9)],
        },
        yaxis={"title": "", "tickfont": {"size": 11}},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "center",
            "x": 0.5,
        },
        height=max(400, len(df) * 30 + 120),
        annotations=[
            {
                "x": -max_val * 0.5,
                "y": 1.05,
                "yref": "paper",
                "text": "👨 Muški",
                "showarrow": False,
                "font": {"size": 14, "color": "#42a5f5"},
            },
            {
                "x": max_val * 0.5,
                "y": 1.05,
                "yref": "paper",
                "text": "👩 Ženski",
                "showarrow": False,
                "font": {"size": 14, "color": "#ef5350"},
            },
        ],
    )

    fig = apply_theme(fig, theme)
    return fig


def sankey_diagram(
    data: list[dict[str, Any]],
    source_column: str,
    target_column: str,
    value_column: str,
    title: str = "",
    theme: str = "dark",
    label_column: Optional[str] = None,
    node_colors: Optional[dict[str, str]] = None,
) -> go.Figure:
    """Create a Sankey (alluvial) diagram showing flow between categories.

    Ideal for budget flow (revenue source → ministry → spending category),
    migration flows, or energy distribution.

    Args:
        data: List of row dicts with source, target, and flow value
        source_column: Source category (flow origin)
        target_column: Target category (flow destination)
        value_column: Flow magnitude
        title: Chart title
        theme: Visual theme
        label_column: Optional column for custom node labels
        node_colors: Optional dict mapping node names to colors

    Returns:
        Plotly Figure
    """
    df = pd.DataFrame(data)

    # Build node list (unique source + target names)
    all_nodes = list(dict.fromkeys(list(df[source_column].unique()) + list(df[target_column].unique())))

    # Map names to indices
    node_index = {name: i for i, name in enumerate(all_nodes)}

    # Build link data
    sources = [node_index.get(s, 0) for s in df[source_column]]
    targets = [node_index.get(t, 0) for t in df[target_column]]
    values = df[value_column].tolist()

    # Build labels
    if label_column and label_column in df.columns:
        label_map = dict(zip(df[source_column], df[label_column], strict=False))
        label_map.update(dict(zip(df[target_column], df[label_column], strict=False)))
        labels = [label_map.get(n, n) for n in all_nodes]
    else:
        labels = all_nodes

    # Build node colors
    default_colors = SEMANTIC_COLORS * 3
    if node_colors:
        node_color_list = [node_colors.get(n, default_colors[i % len(default_colors)]) for i, n in enumerate(all_nodes)]
    else:
        node_color_list = [default_colors[i % len(default_colors)] for i in range(len(all_nodes))]

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node={
                "pad": 20,
                "thickness": 25,
                "line": {"color": "rgba(255,255,255,0.15)", "width": 0.5},
                "label": labels,
                "color": node_color_list,
            },
            link={
                "source": sources,
                "target": targets,
                "value": values,
                "hovertemplate": ("%{source.label} → %{target.label}<br>Iznos: %{value:,.0f}<extra></extra>"),
            },
        )
    )

    fig.update_layout(
        title={"text": title, "font": {"size": 22}, "x": 0.05, "xanchor": "left"},
        font={"size": 12},
        height=max(400, len(all_nodes) * 30 + 200),
    )

    fig = apply_theme(fig, theme)
    return fig


def radar_chart(
    data: list[dict[str, Any]],
    category_column: str,
    value_columns: list[str],
    title: str = "",
    theme: str = "dark",
    labels: Optional[list[str]] = None,
) -> go.Figure:
    """Create a radar/spider chart for multi-metric comparison.

    Ideal for comparing districts or cities across multiple indicators
    (population, budget, schools, hospitals, air quality).

    Args:
        data: List of row dicts
        category_column: Entity names (e.g., city names)
        value_columns: Numeric columns to compare (metrics)
        title: Chart title
        theme: Visual theme
        labels: Override metric display labels

    Returns:
        Plotly Figure
    """
    if not data:
        return go.Figure()

    df = pd.DataFrame(data)
    display_labels = labels or value_columns

    fig = go.Figure()

    for _, row in df.iterrows():
        entity = str(row[category_column])
        values = [float(row[col]) if pd.notna(row[col]) else 0 for col in value_columns]

        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=display_labels,
                fill="toself",
                name=entity,
                hovertemplate=f"<b>{entity}</b><br>%{{theta}}: %{{r:,.0f}}<extra></extra>",
            )
        )

    fig.update_layout(
        title={"text": title, "font": {"size": 22}, "x": 0.5, "xanchor": "center"},
        polar={"radialaxis": {"visible": True, "gridcolor": "#2a3a5c"}},
        showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.1, "xanchor": "center", "x": 0.5},
        height=500,
    )

    fig = apply_theme(fig, theme)
    return fig
