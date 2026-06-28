"""Offline deterministic tests for viz/novel_charts.py.

Covers the five specialized chart builders (slope_chart, waffle_chart,
population_pyramid, sankey_diagram, radar_chart). Every builder returns a real
plotly go.Figure from list[dict] input with no network, no file writes, and no
export_dir/theme-export coupling (apply_theme only mutates the layout), so
assertions are plain reads of fig.data / fig.layout attributes — the same
inspect-the-figure pattern used in test_viz_special_charts.py.
"""

from __future__ import annotations

import math

import plotly.graph_objects as go

from serbian_data_mcp.viz.novel_charts import (
    population_pyramid,
    radar_chart,
    sankey_diagram,
    slope_chart,
    waffle_chart,
)

GREEN = "#2e7d32"
RED = "#c62828"
BLUE = "#1565c0"
RED_SEM = "#c62828"  # SEMANTIC_COLORS[0]


# -- slope_chart ---------------------------------------------------------------


def test_slope_chart_colors_by_direction_and_builds_ranks() -> None:
    """color_by_direction=True → green for gainers, red for losers; one line per row."""
    data = [
        {"d": "Up", "s": 10, "e": 20},  # +10 gain → green
        {"d": "Down", "s": 20, "e": 5},  # -15 loss → red
    ]
    fig = slope_chart(data, "d", "s", "e", title="T")
    assert isinstance(fig, go.Figure)
    # 2 line traces (no legend markers), each lines+markers
    assert len(fig.data) == 2
    for tr in fig.data:
        assert tr.mode == "lines+markers"
        assert tr.x == ("Početak", "Kraj")
        assert tr.showlegend is False

    colors = {tr.name: tr.line.color for tr in fig.data}
    assert colors["Up"] == GREEN
    assert colors["Down"] == RED


def test_slope_chart_color_by_direction_false_uses_neutral_blue() -> None:
    """color_by_direction=False → every line is the neutral blue regardless of sign."""
    data = [
        {"d": "Up", "s": 10, "e": 20},
        {"d": "Down", "s": 20, "e": 5},
    ]
    fig = slope_chart(data, "d", "s", "e", color_by_direction=False)
    assert {tr.line.color for tr in fig.data} == {BLUE}


def test_slope_chart_sort_by_change_orders_by_magnitude_desc() -> None:
    """sort_by='change' (default) reindexes by abs(change) descending."""
    data = [
        {"d": "small", "s": 10, "e": 11},  # |change|=1
        {"d": "big", "s": 10, "e": 100},  # |change|=90
        {"d": "mid", "s": 10, "e": 50},  # |change|=40
    ]
    fig = slope_chart(data, "d", "s", "e", sort_by="change")
    # trace insertion order follows reindex: big, mid, small
    assert [tr.name for tr in fig.data] == ["big", "mid", "small"]


def test_slope_chart_sort_by_start_ascending() -> None:
    """sort_by='start' sorts ascending by the start column."""
    data = [
        {"d": "hi", "s": 30, "e": 31},
        {"d": "lo", "s": 5, "e": 6},
        {"d": "mid", "s": 20, "e": 21},
    ]
    fig = slope_chart(data, "d", "s", "e", sort_by="start")
    assert [tr.name for tr in fig.data] == ["lo", "mid", "hi"]


def test_slope_chart_sort_by_custom_column() -> None:
    """sort_by=<column name> sorts ascending by that column."""
    data = [
        {"d": "z", "s": 1, "e": 2, "rank": 3},
        {"d": "a", "s": 1, "e": 2, "rank": 1},
        {"d": "m", "s": 1, "e": 2, "rank": 2},
    ]
    fig = slope_chart(data, "d", "s", "e", sort_by="rank")
    assert [tr.name for tr in fig.data] == ["a", "m", "z"]


def test_slope_chart_top_n_clamps_row_count() -> None:
    """top_n limits the number of entities plotted."""
    data = [{"d": f"d{i}", "s": i, "e": i + 10} for i in range(6)]
    fig = slope_chart(data, "d", "s", "e", top_n=3)
    assert len(fig.data) == 3


def test_slope_chart_annotations_two_per_entity() -> None:
    """One annotation at Početak and one at Kraj per entity → 2*N annotations."""
    data = [
        {"d": "A", "s": 1, "e": 2},
        {"d": "B", "s": 3, "e": 4},
    ]
    fig = slope_chart(data, "d", "s", "e")
    annot_texts = [a.text for a in fig.layout.annotations]
    # each entity name appears once at start and once at end
    assert annot_texts.count("A") == 2
    assert annot_texts.count("B") == 2


def test_slope_chart_height_and_yaxis_range_scale_with_top_n() -> None:
    """height = max(400, top_n*35+100); yaxis.range = [0.5, top_n+0.5]."""
    data = [{"d": f"d{i}", "s": i, "e": i + 1} for i in range(4)]
    fig = slope_chart(data, "d", "s", "e", top_n=10)
    assert fig.layout.height == max(400, 10 * 35 + 100)
    assert list(fig.layout.yaxis.range) == [0.5, 10.5]


def test_slope_chart_hovertemplate_includes_entity_and_pct() -> None:
    """hovertemplate carries the entity name and the pct_change field."""
    data = [{"d": "X", "s": 10, "e": 20}]
    fig = slope_chart(data, "d", "s", "e")
    ht = fig.data[0].hovertemplate
    assert "<b>X</b>" in ht
    assert "Promena:" in ht


# -- waffle_chart --------------------------------------------------------------


def test_waffle_chart_zero_total_returns_empty_figure() -> None:
    """total == 0 → bare go.Figure() (guard before building the grid)."""
    data = [
        {"n": "A", "v": 0},
        {"n": "B", "v": 0},
    ]
    fig = waffle_chart(data, "n", "v")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_waffle_chart_main_scatter_plus_one_legend_trace_per_category() -> None:
    """1 grid Scatter + N legend-marker traces (one per category)."""
    data = [
        {"n": "A", "v": 25},
        {"n": "B", "v": 75},
    ]
    fig = waffle_chart(data, "n", "v", total_icons=20)
    # 1 grid scatter + 2 legend traces
    assert len(fig.data) == 3
    grid = fig.data[0]
    assert grid.mode == "markers"
    # legend traces are the subsequent ones with showlegend=True
    assert all(tr.showlegend for tr in fig.data[1:])
    # legend trace names embed value + pct
    names = [tr.name for tr in fig.data[1:]]
    assert any("A" in n and "25.0%" in n for n in names)
    assert any("B" in n and "75.0%" in n for n in names)


def test_waffle_chart_marker_colors_cover_full_grid() -> None:
    """Diff adjustment guarantees every grid icon is colored when data is present.

    diff = total_icons - n_icons.sum() is always added back to the first category,
    so pos reaches total_icons inside the per-category loop and the transparent-fill
    `while pos < total_icons` branch stays dead whenever len(df) > 0 — lock that
    contract so a future edit that drops the diff adjustment fails loudly.
    """
    data = [
        {"n": "A", "v": 40},
        {"n": "B", "v": 10},
    ]
    fig = waffle_chart(data, "n", "v", total_icons=20)
    colors = list(fig.data[0].marker.color)
    # exactly total_icons markers, all colored (no transparent fill)
    assert len(colors) == 20
    assert "rgba(0,0,0,0)" not in colors
    # category palette colors present (SEMANTIC_COLORS[0]=red, [1]=blue)
    assert RED_SEM in colors
    assert BLUE in colors


def test_waffle_chart_diff_adjustment_pads_first_category() -> None:
    """Rounding shortfall is added to the FIRST category so n_icons sums to total_icons."""
    data = [
        {"n": "A", "v": 1},  # 1/3 * 10 ≈ 3.33 → 3
        {"n": "B", "v": 2},  # 2/3 * 10 ≈ 6.67 → 7
    ]  # sum = 10 exactly here; use values that round-short to force the adjust
    data = [
        {"n": "A", "v": 1},
        {"n": "B", "v": 1},
        {"n": "C", "v": 1},
    ]  # 3.33 each → 3+3+3=9, diff=1 added to first → A gets 4
    fig = waffle_chart(data, "n", "v", total_icons=10)
    colors = list(fig.data[0].marker.color)
    # 9 colored + 1 transparent? No: diff(=1) added to first category so 10 colored, 0 fill
    # count non-transparent (colored) markers == total_icons (10)
    colored = [c for c in colors if c != "rgba(0,0,0,0)"]
    assert len(colored) == 10


def test_waffle_chart_height_scales_with_grid_rows() -> None:
    """height = max(400, (total_icons//icons_per_row + 2) * (icon_size + gap))."""
    data = [{"n": "A", "v": 100}]
    total_icons = 25
    icon_size = 20
    gap = 2
    fig = waffle_chart(data, "n", "v", total_icons=total_icons, icon_size=icon_size, gap=gap)
    icons_per_row = math.ceil(math.sqrt(total_icons))
    expected = max(400, (total_icons // icons_per_row + 2) * (icon_size + gap))
    assert fig.layout.height == expected


# -- population_pyramid --------------------------------------------------------


def test_population_pyramid_two_bars_male_negative_female_positive() -> None:
    """Male bar x is negated (left), female bar x is positive (right)."""
    data = [
        {"age": "0-4", "m": 100, "f": 90},
        {"age": "5-9", "m": 80, "f": 85},
    ]
    fig = population_pyramid(data, "age", "m", "f", title="Pyr")
    assert len(fig.data) == 2
    male, female = fig.data[0], fig.data[1]
    assert male.name == "Muški"
    assert female.name == "Ženski"
    assert male.orientation == "h"
    # male x negated
    assert list(male.x) == [-100, -80]
    assert list(female.x) == [90, 85]
    # colors
    assert male.marker.color == BLUE
    assert female.marker.color == RED


def test_population_pyramid_barmode_overlay_and_bargap() -> None:
    data = [{"age": "0-4", "m": 100, "f": 90}]
    fig = population_pyramid(data, "age", "m", "f", bar_gap=0.2)
    assert fig.layout.barmode == "overlay"
    assert fig.layout.bargap == 0.2


def test_population_pyramid_age_order_sorts_explicitly() -> None:
    """age_order list sorts rows bottom-to-top, ignoring string order."""
    data = [
        {"age": "65+", "m": 50, "f": 60},
        {"age": "0-4", "m": 100, "f": 90},
        {"age": "5-9", "m": 80, "f": 85},
    ]
    order = ["0-4", "5-9", "65+"]
    fig = population_pyramid(data, "age", "m", "f", age_order=order)
    assert list(fig.data[0].y) == order


def test_population_pyramid_default_sort_extracts_leading_digit() -> None:
    """Without age_order, sort by the leading digit extracted from the age label."""
    data = [
        {"age": "65+", "m": 50, "f": 60},
        {"age": "0-4", "m": 100, "f": 90},
        {"age": "15-19", "m": 70, "f": 75},
    ]
    fig = population_pyramid(data, "age", "m", "f")
    # sorted by extracted int: 0, 15, 65
    assert list(fig.data[0].y) == ["0-4", "15-19", "65+"]


def test_population_pyramid_height_scales_with_rows() -> None:
    data = [{"age": str(i), "m": i, "f": i} for i in range(5)]
    fig = population_pyramid(data, "age", "m", "f")
    assert fig.layout.height == max(400, 5 * 30 + 120)


def test_population_pyramid_has_muški_and_ženski_annotations() -> None:
    data = [{"age": "0-4", "m": 100, "f": 90}]
    fig = population_pyramid(data, "age", "m", "f")
    texts = [a.text for a in fig.layout.annotations]
    assert any("Muški" in t for t in texts)
    assert any("Ženski" in t for t in texts)


# -- sankey_diagram -----------------------------------------------------------


def test_sankey_builds_unique_nodes_and_links() -> None:
    """Nodes are unique source+target; links carry source/target/value lists."""
    data = [
        {"src": "A", "dst": "B", "v": 10},
        {"src": "A", "dst": "C", "v": 5},
        {"src": "B", "dst": "C", "v": 3},
    ]
    fig = sankey_diagram(data, "src", "dst", "v", title="Flow")
    assert isinstance(fig, go.Figure)
    sk = fig.data[0]
    assert isinstance(sk, go.Sankey)
    # unique nodes: A, B, C
    assert list(sk.node.label) == ["A", "B", "C"]  # pyright: ignore[reportOptionalMemberAccess]
    # 3 links
    assert len(sk.link.source) == 3  # pyright: ignore[reportOptionalMemberAccess]
    assert len(sk.link.target) == 3  # pyright: ignore[reportOptionalMemberAccess]
    assert list(sk.link.value) == [10, 5, 3]  # pyright: ignore[reportOptionalMemberAccess]
    # source A == index 0 for both A→B and A→C links
    assert sk.link.source[0] == 0  # pyright: ignore[reportOptionalMemberAccess]
    assert sk.link.source[1] == 0  # pyright: ignore[reportOptionalMemberAccess]


def test_sankey_label_column_overrides_node_labels() -> None:
    """label_column provides display labels mapped from source/target names."""
    data = [
        {"src": "A", "dst": "B", "v": 10, "lbl": "Alpha"},
        {"src": "B", "dst": "C", "v": 3, "lbl": "Beta"},
    ]
    fig = sankey_diagram(data, "src", "dst", "v", label_column="lbl")
    labels = list(fig.data[0].node.label)
    # mapping built from source then target rows; A→Alpha, B→Beta (then B→Beta again, C→Beta)
    assert "Alpha" in labels
    assert "Beta" in labels


def test_sankey_node_colors_dict_applied() -> None:
    """node_colors dict overrides default palette for named nodes."""
    data = [
        {"src": "A", "dst": "B", "v": 10},
        {"src": "B", "dst": "C", "v": 3},
    ]
    colors = {"A": "#111111", "B": "#222222", "C": "#333333"}
    fig = sankey_diagram(data, "src", "dst", "v", node_colors=colors)
    assert list(fig.data[0].node.color) == ["#111111", "#222222", "#333333"]


def test_sankey_default_node_colors_cycle_semantic_palette() -> None:
    """Without node_colors, default_colors = SEMANTIC_COLORS * 3, cycled by index."""
    data = [
        {"src": "A", "dst": "B", "v": 10},
        {"src": "B", "dst": "C", "v": 3},
    ]
    fig = sankey_diagram(data, "src", "dst", "v")
    from serbian_data_mcp.viz.themes import SEMANTIC_COLORS

    expected = [SEMANTIC_COLORS[0], SEMANTIC_COLORS[1], SEMANTIC_COLORS[2]]
    assert list(fig.data[0].node.color) == expected


def test_sankey_arrangement_snap_and_height() -> None:
    data = [{"src": "A", "dst": "B", "v": 10}]
    fig = sankey_diagram(data, "src", "dst", "v")
    assert fig.data[0].arrangement == "snap"
    # height = max(400, len(nodes)*30 + 200)
    assert fig.layout.height == max(400, 2 * 30 + 200)


# -- radar_chart --------------------------------------------------------------


def test_radar_empty_data_returns_empty_figure() -> None:
    """Empty input → bare go.Figure() before building any trace."""
    fig = radar_chart([], "entity", ["a", "b"])
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_radar_one_scatterpolar_per_entity() -> None:
    data = [
        {"e": "X", "a": 10, "b": 20},
        {"e": "Y", "a": 30, "b": 40},
    ]
    fig = radar_chart(data, "e", ["a", "b"], title="Rad")
    assert len(fig.data) == 2
    for tr in fig.data:
        assert isinstance(tr, go.Scatterpolar)
        assert tr.fill == "toself"
    # theta = value_columns (default labels)
    assert tuple(fig.data[0].theta) == ("a", "b")
    # entity name used as trace name
    assert {tr.name for tr in fig.data} == {"X", "Y"}
    # r values per entity
    assert list(fig.data[0].r) == [10.0, 20.0]
    assert list(fig.data[1].r) == [30.0, 40.0]


def test_radar_labels_override_theta() -> None:
    """labels kwarg overrides value_columns as the theta display labels."""
    data = [{"e": "X", "a": 10, "b": 20}]
    fig = radar_chart(data, "e", ["a", "b"], labels=["Metric A", "Metric B"])
    assert tuple(fig.data[0].theta) == ("Metric A", "Metric B")


def test_radar_nan_values_become_zero() -> None:
    """NaN cells are substituted with 0 in the r values."""
    data = [{"e": "X", "a": 10, "b": None}]
    fig = radar_chart(data, "e", ["a", "b"])
    assert list(fig.data[0].r) == [10.0, 0.0]


def test_radar_hovertemplate_carries_entity_name() -> None:
    data = [{"e": "Z", "a": 1, "b": 2}]
    fig = radar_chart(data, "e", ["a", "b"])
    assert "<b>Z</b>" in fig.data[0].hovertemplate


def test_radar_polar_radialaxis_visible() -> None:
    data = [{"e": "X", "a": 1, "b": 2}]
    fig = radar_chart(data, "e", ["a", "b"])
    assert fig.layout.polar.radialaxis.visible is True
