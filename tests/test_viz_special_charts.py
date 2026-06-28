"""Offline deterministic tests for viz/special_charts.py.

Covers the three specialized chart builders (arrow_chart, dumbbell_chart,
lollipop_chart). All three build real plotly go.Figure objects from list[dict]
input with no network and no file writes, so assertions are plain reads of
fig.data / fig.layout attributes — the same inspect-the-figure pattern used in
test_viz_tooltips.py.
"""

from __future__ import annotations

import plotly.graph_objects as go

from serbian_data_mcp.viz.special_charts import (
    arrow_chart,
    dumbbell_chart,
    lollipop_chart,
)

GREEN = "#2e7d32"
RED = "#c62828"
AMBER = "#ffab00"
BLUE = "#1565c0"


# -- arrow_chart ---------------------------------------------------------------


def test_arrow_chart_returns_figure_and_sorts_ascending_by_default() -> None:
    """sort=True sorts ascending by value; y order reflects sort."""
    data = [
        {"d": "A", "v": 5},
        {"d": "B", "v": -3},
        {"d": "C", "v": 10},
    ]
    fig = arrow_chart(data, "d", "v", title="T")
    assert isinstance(fig, go.Figure)
    bar = fig.data[0]
    assert bar.orientation == "h"
    # ascending sort → [-3, 5, 10] → labels [B, A, C]
    assert list(bar.y) == ["B", "A", "C"]
    assert list(bar.x) == [-3, 5, 10]


def test_arrow_chart_sort_false_preserves_input_order() -> None:
    data = [{"d": "A", "v": 5}, {"d": "B", "v": -3}]
    bar = arrow_chart(data, "d", "v", sort=False).data[0]
    assert list(bar.y) == ["A", "B"]


def test_arrow_chart_default_reference_colors_by_sign() -> None:
    """reference_value=None → green for >=0, red for <0."""
    data = [{"d": "A", "v": 5}, {"d": "B", "v": -3}, {"d": "C", "v": 0}]
    bar = arrow_chart(data, "d", "v", sort=False).data[0]
    # input order A(5) green, B(-3) red, C(0) green
    assert list(bar.marker.color) == [GREEN, RED, GREEN]


def test_arrow_chart_explicit_reference_value_colors_and_draws_baseline() -> None:
    """reference_value set → color threshold shifts + vline + annotation added."""
    data = [{"d": "A", "v": 5}, {"d": "B", "v": 3}]
    fig = arrow_chart(data, "d", "v", reference_value=4, sort=False)
    bar = fig.data[0]
    # A(5)>=4 green, B(3)<4 red
    assert list(bar.marker.color) == [GREEN, RED]
    # vline lands in layout.shapes
    shapes = list(fig.layout.shapes)
    assert shapes, "expected a baseline vline shape"
    assert shapes[0].x0 == 4 and shapes[0].x1 == 4
    # annotation text present
    anns = list(fig.layout.annotations)
    assert anns and "Baseline: 4" in anns[0].text


def test_arrow_chart_no_reference_value_draws_no_shapes() -> None:
    fig = arrow_chart([{"d": "A", "v": 5}], "d", "v")
    assert len(list(fig.layout.shapes)) == 0


def test_arrow_chart_show_values_formats_with_sign() -> None:
    """show_values=True (default) → text is '+,.1f' signed string per value."""
    bar = arrow_chart(
        [{"d": "A", "v": 10.5}, {"d": "B", "v": -3}],
        "d",
        "v",
        show_values=True,
        sort=False,
    ).data[0]
    assert list(bar.text) == ["+10.5", "-3.0"]


def test_arrow_chart_show_values_false_blanks_text() -> None:
    bar = arrow_chart(
        [{"d": "A", "v": 10.5}],
        "d",
        "v",
        show_values=False,
    ).data[0]
    assert list(bar.text) == [""]


def test_arrow_chart_title_and_axis_labels() -> None:
    fig = arrow_chart([{"d": "A", "v": 1}], "d", "v", title="My Title")
    assert fig.layout.title.text == "My Title"
    assert fig.layout.xaxis.title.text == "v"
    assert fig.layout.yaxis.autorange == "reversed"


def test_arrow_chart_height_scales_with_row_count() -> None:
    one = arrow_chart([{"d": "A", "v": 1}], "d", "v").layout.height
    many = arrow_chart(
        [{"d": f"d{i}", "v": i} for i in range(10)],
        "d",
        "v",
    ).layout.height
    assert many > one
    assert many == 10 * 45 + 100


def test_arrow_chart_theme_light_still_returns_figure() -> None:
    fig = arrow_chart([{"d": "A", "v": 1}], "d", "v", theme="light")
    assert isinstance(fig, go.Figure)


# -- dumbbell_chart -----------------------------------------------------------


def test_dumbbell_chart_builds_three_traces_and_sorts_by_change() -> None:
    """Default sort_by='change' ascending; traces = connector, start dots, end dots."""
    data = [
        {"d": "A", "s": 100, "e": 120},
        {"d": "B", "s": 100, "e": 80},
    ]
    fig = dumbbell_chart(data, "d", "s", "e", title="T")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 3
    # change A=+20, B=-20 → ascending sort → [B, A]
    end_trace = fig.data[2]
    assert list(end_trace.y) == ["B", "A"]
    assert list(end_trace.x) == [80, 120]


def test_dumbbell_chart_connector_trace_is_first_and_links_points() -> None:
    """First trace is the connector scatter; x/y interleave points with None separators."""
    data = [{"d": "A", "s": 100, "e": 120}]
    connector = dumbbell_chart(data, "d", "s", "e").data[0]
    # one row → [start, end, None]
    assert list(connector.x) == [100, 120, None]
    assert list(connector.y) == ["A", "A", None]


def test_dumbbell_chart_end_colors_by_direction() -> None:
    data = [{"d": "A", "s": 100, "e": 120}, {"d": "B", "s": 100, "e": 80}]
    end_trace = dumbbell_chart(data, "d", "s", "e", sort_by="absolute").data[2]
    # after absolute sort (both |20|), end colors map to each row's change sign
    # build expected by mapping sorted order
    colors = list(end_trace.marker.color)
    assert GREEN in colors and RED in colors
    assert len(colors) == 2


def test_dumbbell_chart_customdata_carries_pct_change() -> None:
    data = [{"d": "A", "s": 100, "e": 120}, {"d": "B", "s": 100, "e": 80}]
    end_trace = dumbbell_chart(data, "d", "s", "e", sort_by="absolute").data[2]
    cd = list(end_trace.customdata)
    # each entry is [pct_change]; A=+20.0, B=-20.0
    flat = {row[0] for row in cd}
    assert 20.0 in flat and -20.0 in flat


def test_dumbbell_chart_start_trace_labels() -> None:
    data = [{"d": "A", "s": 100, "e": 120}]
    start_trace = dumbbell_chart(data, "d", "s", "e").data[1]
    assert start_trace.name == "Početak"
    assert list(start_trace.x) == [100]
    assert list(start_trace.text) == ["100"]


def test_dumbbell_chart_end_trace_names_and_hover() -> None:
    data = [{"d": "A", "s": 100, "e": 120}]
    end_trace = dumbbell_chart(data, "d", "s", "e").data[2]
    assert end_trace.name == "Kraj"
    assert "Promena" in end_trace.hovertemplate


def test_dumbbell_chart_sort_by_absolute() -> None:
    """sort_by='absolute' sorts by |change| ascending."""
    data = [
        {"d": "A", "s": 100, "e": 120},  # |change|=20
        {"d": "B", "s": 100, "e": 110},  # |change|=10
    ]
    end_trace = dumbbell_chart(data, "d", "s", "e", sort_by="absolute").data[2]
    # ascending absolute → B(10) before A(20)
    assert list(end_trace.y) == ["B", "A"]


def test_dumbbell_chart_sort_by_column_name() -> None:
    """sort_by=<column> sorts by that column ascending."""
    data = [
        {"d": "A", "s": 100, "e": 120},
        {"d": "B", "s": 50, "e": 70},
    ]
    end_trace = dumbbell_chart(data, "d", "s", "e", sort_by="s").data[2]
    # ascending by start s → B(50) before A(100)
    assert list(end_trace.y) == ["B", "A"]


def test_dumbbell_chart_zero_start_does_not_divide_by_zero() -> None:
    """start=0 → pct_change uses abs().replace(0,1) so no ZeroDivisionError."""
    data = [{"d": "A", "s": 0, "e": 50}]
    fig = dumbbell_chart(data, "d", "s", "e")
    assert isinstance(fig, go.Figure)
    # customdata present and finite
    cd = list(fig.data[2].customdata)
    assert len(cd) == 1


def test_dumbbell_chart_title_and_height() -> None:
    fig = dumbbell_chart(
        [{"d": "A", "s": 100, "e": 120}],
        "d",
        "s",
        "e",
        title="DB",
    )
    assert fig.layout.title.text == "DB"
    # height = max(300, len*50+120); 1 row → floored at 300
    assert fig.layout.height == 300
    assert fig.layout.yaxis.autorange == "reversed"


# -- lollipop_chart -----------------------------------------------------------


def test_lollipop_chart_builds_stem_per_row_plus_one_dot_trace() -> None:
    """N rows → N stem traces + 1 dot trace."""
    data = [{"d": "A", "v": 5}, {"d": "B", "v": 10}, {"d": "C", "v": 3}]
    fig = lollipop_chart(data, "d", "v")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 4  # 3 stems + 1 dot


def test_lollipop_chart_sorts_ascending_by_value() -> None:
    data = [{"d": "A", "v": 5}, {"d": "B", "v": 10}, {"d": "C", "v": 3}]
    dot = lollipop_chart(data, "d", "v").data[-1]
    # ascending → C(3), A(5), B(10)
    assert list(dot.y) == ["C", "A", "B"]


def test_lollipop_chart_highlight_matches_amber_and_larger() -> None:
    """highlight_column+highlight_value → matched row amber/size14, rest blue/size8."""
    data = [
        {"d": "A", "v": 5, "cat": "x"},
        {"d": "B", "v": 10, "cat": "y"},
    ]
    dot = lollipop_chart(
        data,
        "d",
        "v",
        highlight_column="cat",
        highlight_value="x",
    ).data[-1]
    # ascending sort → A(5) first, B(10) second; A matches cat=x
    assert list(dot.marker.color) == [AMBER, BLUE]
    assert list(dot.marker.size) == [14, 8]


def test_lollipop_chart_no_highlight_uses_palette_and_uniform_size() -> None:
    data = [{"d": "A", "v": 5}, {"d": "B", "v": 10}]
    dot = lollipop_chart(data, "d", "v").data[-1]
    sizes = list(dot.marker.size)
    colors = list(dot.marker.color)
    assert len(colors) == 2
    assert all(s == 8 for s in sizes)


def test_lollipop_chart_highlight_only_column_given_falls_back_to_palette() -> None:
    """highlight_column set but highlight_value None → falsy condition → palette branch."""
    data = [{"d": "A", "v": 5, "cat": "x"}]
    dot = lollipop_chart(data, "d", "v", highlight_column="cat").data[-1]
    sizes = list(dot.marker.size)
    assert sizes == [8]  # uniform, no highlight


def test_lollipop_chart_dot_text_and_hover() -> None:
    data = [{"d": "A", "v": 1000}]
    dot = lollipop_chart(data, "d", "v").data[-1]
    assert list(dot.text) == ["1,000"]
    assert "%{y}" in dot.hovertemplate


def test_lollipop_chart_stem_connects_zero_to_value() -> None:
    data = [{"d": "A", "v": 7}]
    stem = lollipop_chart(data, "d", "v").data[0]
    assert list(stem.x) == [0, 7]
    assert list(stem.y) == ["A", "A"]


def test_lollipop_chart_title_and_axis() -> None:
    fig = lollipop_chart([{"d": "A", "v": 1}], "d", "v", title="LP")
    assert fig.layout.title.text == "LP"
    assert fig.layout.xaxis.title.text == "v"
    assert fig.layout.showlegend is False
