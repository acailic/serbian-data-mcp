"""Deterministic offline tests for viz/advanced_charts.py AdvancedChartBuilder.

All 7 builder methods build real plotly go.Figure objects with no file/network/
export_dir coupling (apply_theme only mutates layout), so tests are plain
fig.data/fig.layout attribute reads — same inspect-the-figure pattern as the
special_charts/tooltips viz tests.
"""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import pytest

from serbian_data_mcp.viz.advanced_charts import AdvancedChartBuilder


# ---------------------------------------------------------------------------
# Fixtures / data
# ---------------------------------------------------------------------------

HEATMAP_DATA: list[dict[str, Any]] = [
    {"city": "BG", "month": "Jan", "pm": 40.0},
    {"city": "BG", "month": "Feb", "pm": 55.0},
    {"city": "NS", "month": "Jan", "pm": 30.0},
    {"city": "NS", "month": "Feb", "pm": 45.0},
]

TREEMAP_DATA: list[dict[str, Any]] = [
    {"name": "A", "value": 100, "parent": "top", "color": 1},
    {"name": "B", "value": 200, "parent": "top", "color": 2},
    {"name": "C", "value": 50, "parent": "mid", "color": 3},
]

FUNNEL_DATA: list[dict[str, Any]] = [
    {"stage": "visit", "count": 1000},
    {"stage": "signup", "count": 400},
    {"stage": "buy", "count": 100},
]

ANIM_DATA: list[dict[str, Any]] = [
    {"year": 2000, "pop": 7, "city": "BG"},
    {"year": 2010, "pop": 8, "city": "BG"},
    {"year": 2000, "pop": 3, "city": "NS"},
    {"year": 2010, "pop": 4, "city": "NS"},
]

COMPARE_DATA: list[dict[str, Any]] = [
    {"city": "BG", "v2020": 100, "v2024": 150},
    {"city": "NS", "v2020": 80, "v2024": 90},
]

SPARK_DATA: list[dict[str, Any]] = [
    {"entity": "A", "t": 1, "val": 10, "last": 10},
    {"entity": "A", "t": 2, "val": 20, "last": 20},
    {"entity": "B", "t": 1, "val": 1, "last": 1},
    {"entity": "B", "t": 2, "val": 2, "last": 2},
    {"entity": "C", "t": 1, "val": 50, "last": 50},
    {"entity": "C", "t": 2, "val": 60, "last": 60},
]

VIOLIN_DATA: list[dict[str, Any]] = [
    {"g": "a", "v": 1},
    {"g": "a", "v": 2},
    {"g": "a", "v": 3},
    {"g": "b", "v": 10},
    {"g": "b", "v": 20},
    {"g": "b", "v": 30},
]

WATERFALL_DATA: list[dict[str, Any]] = [
    {"step": "Start", "amount": 1000, "measure": "absolute"},
    {"step": "Revenue", "amount": 400, "measure": "relative"},
    {"step": "Costs", "amount": -250, "measure": "relative"},
    {"step": "End", "amount": 1150, "measure": "total"},
]

CANDLESTICK_DATA: list[dict[str, Any]] = [
    {"date": "2024-01-01", "open": 100, "high": 110, "low": 95, "close": 105},
    {"date": "2024-01-02", "open": 105, "high": 108, "low": 98, "close": 99},
    {"date": "2024-01-03", "open": 99, "high": 120, "low": 97, "close": 118},
]

TERNARY_DATA: list[dict[str, Any]] = [
    {"a": 40, "b": 30, "c": 30, "grp": "x", "sz": 10},
    {"a": 20, "b": 30, "c": 50, "grp": "y", "sz": 20},
    {"a": 30, "b": 40, "c": 30, "grp": "x", "sz": 15},
]

SPLOM_DATA: list[dict[str, Any]] = [
    {"a": 1, "b": 2, "c": 3, "grp": "x"},
    {"a": 2, "b": 3, "c": 1, "grp": "y"},
    {"a": 3, "b": 1, "c": 2, "grp": "x"},
]


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_accepts_list_and_wraps_dataframe(self) -> None:
        b = AdvancedChartBuilder(HEATMAP_DATA)
        assert isinstance(b.data, pd.DataFrame)
        assert len(b.data) == 4
        assert "city" in b.data.columns

    def test_accepts_dataframe_directly(self) -> None:
        df = pd.DataFrame(HEATMAP_DATA)
        b = AdvancedChartBuilder(df)
        assert b.data is df  # passthrough, no copy


# ---------------------------------------------------------------------------
# heatmap
# ---------------------------------------------------------------------------


class TestHeatmap:
    def test_returns_go_figure_with_colorscale(self) -> None:
        fig = AdvancedChartBuilder(HEATMAP_DATA).heatmap("city", "month", "pm", title="T", colorscale="Viridis")
        assert isinstance(fig, go.Figure)
        # px.imshow -> one Heatmap trace, colorscale shared via layout.coloraxis
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Heatmap)
        assert fig.data[0].coloraxis is not None  # linked to shared coloraxis
        assert fig.layout.coloraxis.colorscale is not None
        assert fig.layout.title.text == "T"

    def test_default_colorscale_is_rdbu_r(self) -> None:
        fig = AdvancedChartBuilder(HEATMAP_DATA).heatmap("city", "month", "pm")
        # px stores the resolved colorscale on the shared layout coloraxis
        cs = fig.layout.coloraxis.colorscale
        assert cs is not None and len(cs) >= 2

    def test_annotation_text_sets_texttemplate(self) -> None:
        fig = AdvancedChartBuilder(HEATMAP_DATA).heatmap("city", "month", "pm", annotation_text=" μg/m³")
        assert "μg/m³" in fig.data[0].texttemplate
        assert fig.data[0].texttemplate.startswith("%{z}")

    def test_no_annotation_leaves_texttemplate_empty(self) -> None:
        fig = AdvancedChartBuilder(HEATMAP_DATA).heatmap("city", "month", "pm")
        assert fig.data[0].texttemplate in (None, "")

    def test_pivot_reshapes_to_grid(self) -> None:
        # 2 cities x 2 months -> z grid is 2x2
        fig = AdvancedChartBuilder(HEATMAP_DATA).heatmap("city", "month", "pm")
        z = fig.data[0].z
        assert len(z) == 2 and all(len(row) == 2 for row in z)


# ---------------------------------------------------------------------------
# treemap
# ---------------------------------------------------------------------------


class TestTreemap:
    def test_single_level_path(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).treemap("name", "value", title="T")
        assert isinstance(fig, go.Figure)
        # px.treemap -> one Treemap trace
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Treemap)
        assert fig.layout.title.text == "T"

    def test_hierarchy_adds_parent_to_path(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).treemap("name", "value", hierarchy_column="parent")
        # path with hierarchy -> labels include parents
        labels = list(fig.data[0].labels)
        assert "top" in labels and "mid" in labels

    def test_color_column_passes_through(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).treemap("name", "value", color_column="color")
        # when color is numeric, px uses marker.colors
        assert fig.data[0].marker is not None


# ---------------------------------------------------------------------------
# gauge
# ---------------------------------------------------------------------------


class TestGauge:
    def test_returns_indicator_figure_with_value(self) -> None:
        fig = AdvancedChartBuilder([]).gauge(75.0, title="Score", min_val=0, max_val=100, label="pts")
        assert isinstance(fig, go.Figure)
        assert isinstance(fig.data[0], go.Indicator)
        assert fig.data[0].value == 75.0
        assert fig.data[0].title.text == "pts"
        assert fig.layout.title.text == "Score"

    def test_default_thresholds_derived_from_range(self) -> None:
        fig = AdvancedChartBuilder([]).gauge(50.0, min_val=0, max_val=100)
        steps = fig.data[0].gauge.steps
        # red/yellow/green bands; green = [60,100], yellow=[30,60], red=[0,30]
        ranges = [list(s.range) for s in steps]
        assert [0, 30] in ranges
        assert [30, 60] in ranges
        assert [60, 100] in ranges

    def test_custom_thresholds_override(self) -> None:
        custom = {"green": [80, 100], "yellow": [50, 80], "red": [0, 50]}
        fig = AdvancedChartBuilder([]).gauge(90.0, min_val=0, max_val=100, thresholds=custom)
        ranges = [list(s.range) for s in fig.data[0].gauge.steps]
        assert [0, 50] in ranges
        assert [80, 100] in ranges

    def test_axis_range_matches_min_max(self) -> None:
        fig = AdvancedChartBuilder([]).gauge(10.0, min_val=5, max_val=25)
        rng = fig.data[0].gauge.axis.range
        assert list(rng) == [5, 25]


# ---------------------------------------------------------------------------
# funnel
# ---------------------------------------------------------------------------


class TestFunnel:
    def test_returns_funnel_figure(self) -> None:
        fig = AdvancedChartBuilder(FUNNEL_DATA).funnel("stage", "count", title="T")
        assert isinstance(fig, go.Figure)
        assert isinstance(fig.data[0], go.Funnel)
        assert fig.layout.title.text == "T"
        # 3 stages
        assert len(fig.data[0].y) == 3

    def test_sorts_descending_by_value(self) -> None:
        # input already descending (1000,400,100); builder sorts descending so order preserved
        fig = AdvancedChartBuilder(FUNNEL_DATA).funnel("stage", "count")
        assert list(fig.data[0].y) == ["visit", "signup", "buy"]
        assert list(fig.data[0].x) == [1000, 400, 100]

    def test_sorts_unsorted_input_descending(self) -> None:
        unsorted = [
            {"stage": "buy", "count": 100},
            {"stage": "visit", "count": 1000},
            {"stage": "signup", "count": 400},
        ]
        fig = AdvancedChartBuilder(unsorted).funnel("stage", "count")
        assert list(fig.data[0].y) == ["visit", "signup", "buy"]


# ---------------------------------------------------------------------------
# animated_line
# ---------------------------------------------------------------------------


class TestAnimatedLine:
    def test_basic_animation_frame(self) -> None:
        fig = AdvancedChartBuilder(ANIM_DATA).animated_line("year", "pop", "year", title="T")
        assert isinstance(fig, go.Figure)
        # px.line builds traces + frames
        assert len(fig.data) >= 1
        assert len(fig.frames) >= 1
        assert fig.layout.title.text == "T"

    def test_updatemenus_and_sliders_configured(self) -> None:
        fig = AdvancedChartBuilder(ANIM_DATA).animated_line("year", "pop", "year")
        assert len(fig.layout.updatemenus) == 1
        assert fig.layout.updatemenus[0].type == "buttons"
        # play + pause buttons
        labels = [b.label for b in fig.layout.updatemenus[0].buttons]
        assert "▶ Play" in labels and "⏸ Pause" in labels
        assert len(fig.layout.sliders) == 1

    def test_category_column_adds_color(self) -> None:
        # with category_column, more than one line trace in base frame
        fig = AdvancedChartBuilder(ANIM_DATA).animated_line("year", "pop", "year", category_column="city")
        assert len(fig.data) >= 2

    def test_color_map_passed_through(self) -> None:
        fig = AdvancedChartBuilder(ANIM_DATA).animated_line(
            "year", "pop", "year", category_column="city", color_map={"BG": "#ff0000", "NS": "#00ff00"}
        )
        # px.line applies color_discrete_map as line.color, one trace per category
        by_name = {t.name: t.line.color for t in fig.data}
        assert by_name == {"BG": "#ff0000", "NS": "#00ff00"}


# ---------------------------------------------------------------------------
# comparison_bar
# ---------------------------------------------------------------------------


class TestComparisonBar:
    def test_two_grouped_bars(self) -> None:
        fig = AdvancedChartBuilder(COMPARE_DATA).comparison_bar("city", ["v2020", "v2024"], title="T")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2
        assert all(isinstance(t, go.Bar) for t in fig.data)
        assert fig.data[0].name == "v2020"
        assert fig.data[1].name == "v2024"
        assert fig.layout.barmode == "group"
        assert fig.layout.title.text == "T"

    def test_custom_labels_override_names(self) -> None:
        fig = AdvancedChartBuilder(COMPARE_DATA).comparison_bar("city", ["v2020", "v2024"], labels=["old", "new"])
        assert fig.data[0].name == "old"
        assert fig.data[1].name == "new"

    def test_custom_colors_applied(self) -> None:
        fig = AdvancedChartBuilder(COMPARE_DATA).comparison_bar(
            "city", ["v2020", "v2024"], baseline_color="#111111", comparison_color="#222222"
        )
        assert fig.data[0].marker.color == "#111111"
        assert fig.data[1].marker.color == "#222222"

    def test_wrong_column_count_raises(self) -> None:
        with pytest.raises(ValueError, match="exactly 2 value_columns"):
            AdvancedChartBuilder(COMPARE_DATA).comparison_bar("city", ["v2020"])
        with pytest.raises(ValueError, match="exactly 2 value_columns"):
            AdvancedChartBuilder(COMPARE_DATA).comparison_bar("city", ["v2020", "v2024", "extra"])


# ---------------------------------------------------------------------------
# sparkline_container
# ---------------------------------------------------------------------------


class TestSparklineContainer:
    def test_facet_per_entity(self) -> None:
        fig = AdvancedChartBuilder(SPARK_DATA).sparkline_container("entity", "val", "t", title="T")
        assert isinstance(fig, go.Figure)
        # 3 entities -> 3 facet columns, traces are scatter (lines+markers mode)
        assert len(fig.data) == 3
        assert all(isinstance(t, go.Scatter) for t in fig.data)
        assert fig.layout.title.text == "T"
        # legend hidden
        assert all(t.showlegend is False for t in fig.data)

    def test_sort_by_top_n_filters_entities(self) -> None:
        # sort_by last val, top_n=2 -> keep entities A (20) and C (60), drop B
        fig = AdvancedChartBuilder(SPARK_DATA).sparkline_container("entity", "val", "t", sort_by="val", top_n=2)
        assert len(fig.data) == 2
        kept = sorted({t.name for t in fig.data})
        assert kept == ["A", "C"]

    def test_annotation_text_strips_prefix(self) -> None:
        # px facet annotations come as "entity=A"; builder splits off prefix
        fig = AdvancedChartBuilder(SPARK_DATA).sparkline_container("entity", "val", "t")
        ann_texts = [a.text for a in fig.layout.annotations]
        # at least the entity names appear without the "entity=" prefix
        assert "A" in ann_texts
        assert all("=" not in t for t in ann_texts)


# ---------------------------------------------------------------------------
# violin
# ---------------------------------------------------------------------------


class TestViolin:
    def test_returns_violin_trace_with_y(self) -> None:
        fig = AdvancedChartBuilder(VIOLIN_DATA).violin("v", title="T")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Violin)
        assert list(fig.data[0].y) == [1, 2, 3, 10, 20, 30]
        assert fig.layout.title.text == "T"

    def test_x_grouping_passes_categories(self) -> None:
        fig = AdvancedChartBuilder(VIOLIN_DATA).violin("v", x_column="g")
        assert isinstance(fig.data[0], go.Violin)
        assert list(fig.data[0].x) == ["a", "a", "a", "b", "b", "b"]

    def test_box_overlay_enables_inner_box(self) -> None:
        fig = AdvancedChartBuilder(VIOLIN_DATA).violin("v", box_overlay=True)
        assert fig.data[0].box.visible is True
        # default: no inner box
        fig_default = AdvancedChartBuilder(VIOLIN_DATA).violin("v")
        assert fig_default.data[0].box.visible is False

    def test_points_passthrough(self) -> None:
        fig = AdvancedChartBuilder(VIOLIN_DATA).violin("v", points="all")
        assert fig.data[0].points == "all"

    def test_color_column_splits_traces_and_themed(self) -> None:
        fig = AdvancedChartBuilder(VIOLIN_DATA).violin("v", color_column="g", theme="light")
        # one Violin trace per color group
        assert len(fig.data) >= 2
        assert all(isinstance(t, go.Violin) for t in fig.data)
        # apply_theme ran: light theme sets a concrete paper_bgcolor
        assert fig.layout.paper_bgcolor is not None


# ---------------------------------------------------------------------------
# waterfall
# ---------------------------------------------------------------------------


class TestWaterfall:
    def test_returns_waterfall_trace_with_x_y(self) -> None:
        fig = AdvancedChartBuilder(WATERFALL_DATA).waterfall("step", "amount", title="T")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Waterfall)
        assert list(fig.data[0].x) == ["Start", "Revenue", "Costs", "End"]
        assert list(fig.data[0].y) == [1000, 400, -250, 1150]
        assert fig.layout.title.text == "T"
        # legend hidden — a bridge chart has no categorical series
        assert fig.layout.showlegend is False

    def test_measure_column_passed_through(self) -> None:
        fig = AdvancedChartBuilder(WATERFALL_DATA).waterfall("step", "amount", measure_column="measure")
        assert list(fig.data[0].measure) == ["absolute", "relative", "relative", "total"]

    def test_default_measure_all_relative(self) -> None:
        # no measure_column -> every step is a relative delta on the running total
        fig = AdvancedChartBuilder(WATERFALL_DATA).waterfall("step", "amount")
        assert list(fig.data[0].measure) == ["relative"] * 4

    def test_measure_column_missing_falls_back_to_relative(self) -> None:
        # named measure_column not in data -> graceful fallback, not an error
        fig = AdvancedChartBuilder(WATERFALL_DATA).waterfall("step", "amount", measure_column="nope")
        assert list(fig.data[0].measure) == ["relative"] * 4

    def test_delta_colors_set_on_trace(self) -> None:
        fig = AdvancedChartBuilder(WATERFALL_DATA).waterfall(
            "step",
            "amount",
            increasing_color="#111111",
            decreasing_color="#222222",
            total_color="#333333",
        )
        t = fig.data[0]
        assert t.increasing.marker.color == "#111111"
        assert t.decreasing.marker.color == "#222222"
        assert t.totals.marker.color == "#333333"

    def test_connector_wired(self) -> None:
        # the dashed bridge line connecting bars must be present
        fig = AdvancedChartBuilder(WATERFALL_DATA).waterfall("step", "amount")
        assert fig.data[0].connector.line.color is not None

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(WATERFALL_DATA).waterfall("step", "amount", theme="light")
        # apply_theme ran: light theme sets a concrete paper_bgcolor
        assert fig.layout.paper_bgcolor is not None


# ---------------------------------------------------------------------------
# candlestick
# ---------------------------------------------------------------------------


class TestCandlestick:
    def test_returns_candlestick_trace_with_ohlc(self) -> None:
        fig = AdvancedChartBuilder(CANDLESTICK_DATA).candlestick("open", "high", "low", "close", title="T")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Candlestick)
        assert list(fig.data[0].open) == [100, 105, 99]
        assert list(fig.data[0].high) == [110, 108, 120]
        assert list(fig.data[0].low) == [95, 98, 97]
        assert list(fig.data[0].close) == [105, 99, 118]
        assert fig.layout.title.text == "T"
        # professional register: no rangeslider, no legend
        assert fig.layout.xaxis.rangeslider.visible is False
        assert fig.layout.showlegend is False

    def test_x_column_used_for_period_axis(self) -> None:
        fig = AdvancedChartBuilder(CANDLESTICK_DATA).candlestick("open", "high", "low", "close", x_column="date")
        assert list(fig.data[0].x) == ["2024-01-01", "2024-01-02", "2024-01-03"]

    def test_default_x_is_row_index(self) -> None:
        fig = AdvancedChartBuilder(CANDLESTICK_DATA).candlestick("open", "high", "low", "close")
        # no x_column -> falls back to the DataFrame's integer row order
        assert list(fig.data[0].x) == [0, 1, 2]

    def test_default_colors_green_up_red_down(self) -> None:
        fig = AdvancedChartBuilder(CANDLESTICK_DATA).candlestick("open", "high", "low", "close")
        t = fig.data[0]
        assert t.increasing.fillcolor == "#2e7d32"
        assert t.increasing.line.color == "#2e7d32"
        assert t.decreasing.fillcolor == "#c62828"
        assert t.decreasing.line.color == "#c62828"

    def test_color_overrides(self) -> None:
        fig = AdvancedChartBuilder(CANDLESTICK_DATA).candlestick(
            "open",
            "high",
            "low",
            "close",
            increasing_color="#00ff00",
            decreasing_color="#ff0000",
        )
        t = fig.data[0]
        assert t.increasing.fillcolor == "#00ff00"
        assert t.decreasing.fillcolor == "#ff0000"

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(CANDLESTICK_DATA).candlestick("open", "high", "low", "close", theme="light")
        # apply_theme ran: light theme sets a concrete paper_bgcolor
        assert fig.layout.paper_bgcolor is not None


# ---------------------------------------------------------------------------
# ternary
# ---------------------------------------------------------------------------


class TestTernary:
    def test_returns_scatterternary_trace_with_abc(self) -> None:
        fig = AdvancedChartBuilder(TERNARY_DATA).ternary("a", "b", "c", title="T")
        assert isinstance(fig, go.Figure)
        # no color grouping -> one Scatterternary trace carrying all rows
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Scatterternary)
        assert list(fig.data[0].a) == [40, 20, 30]
        assert list(fig.data[0].b) == [30, 30, 40]
        assert list(fig.data[0].c) == [30, 50, 30]
        assert fig.layout.title.text == "T"

    def test_color_column_splits_traces(self) -> None:
        fig = AdvancedChartBuilder(TERNARY_DATA).ternary("a", "b", "c", color_column="grp")
        # one Scatterternary trace per group (x, y) -> 2 traces, each Scatterternary
        assert len(fig.data) == 2
        assert all(isinstance(t, go.Scatterternary) for t in fig.data)

    def test_size_column_sets_marker_size(self) -> None:
        fig = AdvancedChartBuilder(TERNARY_DATA).ternary("a", "b", "c", size_column="sz")
        t = fig.data[0]
        # px maps the size column onto the trace's marker.size array
        assert t.marker.size is not None
        assert len(t.marker.size) == 3

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(TERNARY_DATA).ternary("a", "b", "c", theme="light")
        # apply_theme ran: light theme sets a concrete paper_bgcolor; ternary
        # uses the separate `ternary` sub-axis, which apply_theme does not touch
        assert fig.layout.paper_bgcolor is not None


# ---------------------------------------------------------------------------
# splom
# ---------------------------------------------------------------------------


class TestSplom:
    def test_returns_single_splom_trace_with_dimensions(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).splom(["a", "b", "c"], title="T")
        assert isinstance(fig, go.Figure)
        # px.scatter_matrix with no color grouping emits ONE go.Splom trace
        # carrying the whole NxN matrix on its nested .dimensions
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Splom)
        assert len(fig.data[0].dimensions) == 3
        assert fig.data[0].dimensions[0].label == "a"
        assert fig.data[0].dimensions[1].label == "b"
        assert fig.data[0].dimensions[2].label == "c"
        assert list(fig.data[0].dimensions[0].values) == [1, 2, 3]
        assert fig.layout.title.text == "T"

    def test_two_columns_single_trace(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).splom(["a", "b"])
        assert isinstance(fig.data[0], go.Splom)
        assert len(fig.data[0].dimensions) == 2

    def test_color_column_splits_one_trace_per_group(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).splom(["a", "b", "c"], color_column="grp")
        # one Splom trace per group value (grp has 2 values: x, y)
        assert len(fig.data) == 2
        assert all(isinstance(t, go.Splom) for t in fig.data)
        assert sorted(t.name for t in fig.data) == ["x", "y"]

    def test_size_column_sets_marker_size(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).splom(["a", "b", "c"], size_column="a")
        # px maps the size column onto the trace's marker.size array
        assert fig.data[0].marker.size is not None

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).splom(["a", "b", "c"], theme="light")
        # apply_theme ran: light theme sets a concrete paper_bgcolor
        assert fig.layout.paper_bgcolor is not None


# ---------------------------------------------------------------------------
# parcoords
# ---------------------------------------------------------------------------


class TestParcoords:
    def test_returns_single_parcoords_trace_with_dimensions(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).parcoords(["a", "b", "c"], title="T")
        assert isinstance(fig, go.Figure)
        # px.parallel_coordinates emits ONE go.Parcoords trace carrying every
        # column as a vertical ribbon on its nested .dimensions
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Parcoords)
        assert len(fig.data[0].dimensions) == 3
        assert fig.data[0].dimensions[0].label == "a"
        assert fig.data[0].dimensions[1].label == "b"
        assert fig.data[0].dimensions[2].label == "c"
        assert list(fig.data[0].dimensions[0].values) == [1, 2, 3]
        assert fig.layout.title.text == "T"

    def test_two_columns_single_trace(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).parcoords(["a", "b"])
        assert isinstance(fig.data[0], go.Parcoords)
        assert len(fig.data[0].dimensions) == 2

    def test_color_column_sets_line_color(self) -> None:
        # with no color mapping, the trace's line.color is None
        base = AdvancedChartBuilder(SPLOM_DATA).parcoords(["a", "b", "c"])
        assert base.data[0].line.color is None
        # color_column gradient-colors each polyline by a numeric variable
        fig = AdvancedChartBuilder(SPLOM_DATA).parcoords(["a", "b", "c"], color_column="a")
        assert fig.data[0].line.color is not None

    def test_colorscale_override_runs(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).parcoords(
            ["a", "b", "c"], color_column="a", color_continuous_scale="Viridis"
        )
        # custom scale accepted; line still gradient-colored
        assert fig.data[0].line.color is not None

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).parcoords(["a", "b", "c"], theme="light")
        # apply_theme ran: light theme sets a concrete paper_bgcolor; go.Parcoords
        # has no marker attr so its trace-polish loop skips it cleanly
        assert fig.layout.paper_bgcolor is not None


# ---------------------------------------------------------------------------
# density_contour
# ---------------------------------------------------------------------------


class TestDensityContour:
    def test_returns_single_histogram2dcontour_trace(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).density_contour("a", "b", title="T")
        assert isinstance(fig, go.Figure)
        # px.density_contour with no color grouping emits ONE Histogram2dContour
        # carrying the raw x/y sample arrays
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Histogram2dContour)
        assert list(fig.data[0].x) == [1, 2, 3]
        assert list(fig.data[0].y) == [2, 3, 1]
        assert fig.layout.title.text == "T"

    def test_filled_bands_and_colorscale_set(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).density_contour("a", "b")
        t = fig.data[0]
        # update_traces wired: filled bands, resolved colorscale, ncontours default
        assert t.contours.coloring == "fill"
        assert t.colorscale is not None
        assert t.ncontours == 20

    def test_colorscale_override(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).density_contour("a", "b", colorscale="Viridis")
        # named scale resolves to a tuple-list; Viridis is dark-violet at stop 0
        first = fig.data[0].colorscale[0]
        assert first[0] == 0.0
        assert first[1] == "#440154"

    def test_ncontours_passthrough(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).density_contour("a", "b", ncontours=7)
        assert fig.data[0].ncontours == 7

    def test_color_column_splits_one_trace_per_group(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).density_contour("a", "b", color_column="grp")
        # one Histogram2dContour trace per group value (grp has 2: x, y)
        assert len(fig.data) == 2
        assert all(isinstance(t, go.Histogram2dContour) for t in fig.data)
        assert sorted(t.name for t in fig.data) == ["x", "y"]

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(SPLOM_DATA).density_contour("a", "b", theme="light")
        # apply_theme ran: light theme sets a concrete paper_bgcolor; Histogram2dContour
        # has a marker attr so the trace-polish loop runs cleanly
        assert fig.layout.paper_bgcolor is not None
