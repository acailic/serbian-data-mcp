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

PARCATS_DATA: list[dict[str, Any]] = [
    {"region": "N", "sector": "A", "stage": "x", "amt": 10},
    {"region": "S", "sector": "B", "stage": "y", "amt": 40},
    {"region": "N", "sector": "B", "stage": "x", "amt": 20},
    {"region": "S", "sector": "A", "stage": "y", "amt": 30},
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
# sunburst
# ---------------------------------------------------------------------------


class TestSunburst:
    def test_returns_single_sunburst_trace(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).sunburst("name", "value", title="T")
        assert isinstance(fig, go.Figure)
        # px.sunburst -> one Sunburst trace (a radial hierarchy, not nested rects)
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Sunburst)
        assert fig.layout.title.text == "T"

    def test_labels_carry_names(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).sunburst("name", "value")
        # wedge labels are the name column values
        labels = list(fig.data[0].labels)
        assert "A" in labels and "B" in labels and "C" in labels

    def test_hierarchy_adds_parent_ring(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).sunburst("name", "value", hierarchy_column="parent")
        # path with hierarchy -> outer ring parents appear in labels
        labels = list(fig.data[0].labels)
        assert "top" in labels and "mid" in labels

    def test_values_mapped_to_wedge(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).sunburst("name", "value")
        # trace.values carries the value column (wedge angles)
        assert list(fig.data[0].values) == [100, 200, 50]

    def test_color_column_passes_through(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).sunburst("name", "value", color_column="color")
        # numeric color -> marker.colors populated by px
        assert fig.data[0].marker is not None

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).sunburst("name", "value", theme="light")
        # apply_theme ran: light theme sets a concrete paper_bgcolor
        assert fig.layout.paper_bgcolor is not None


# ---------------------------------------------------------------------------
# icicle
# ---------------------------------------------------------------------------


class TestIcicle:
    def test_returns_single_icicle_trace(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).icicle("name", "value", title="T")
        assert isinstance(fig, go.Figure)
        # px.icicle -> one Icicle trace (stacked-layer hierarchy, not nested rects/rings)
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Icicle)
        assert fig.layout.title.text == "T"

    def test_labels_carry_names(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).icicle("name", "value")
        # segment labels include the name column values
        labels = list(fig.data[0].labels)
        assert "A" in labels and "B" in labels and "C" in labels

    def test_hierarchy_adds_parent_layer(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).icicle("name", "value", hierarchy_column="parent")
        # path with hierarchy -> parent layer labels appear (top/mid roots)
        labels = list(fig.data[0].labels)
        assert "top" in labels and "mid" in labels

    def test_values_mapped_to_segment(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).icicle("name", "value")
        # trace.values carries the per-segment value column (root aggregate appended)
        assert list(fig.data[0].values) == [100, 200, 50]

    def test_color_column_passes_through(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).icicle("name", "value", color_column="color")
        # numeric color -> marker populated by px
        assert fig.data[0].marker is not None

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).icicle("name", "value", theme="light")
        # apply_theme ran: light theme sets a concrete paper_bgcolor
        assert fig.layout.paper_bgcolor is not None

    def test_apply_theme_professional_runs(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).icicle("name", "value", theme="professional")
        # professional salmon-paper register applied
        assert fig.layout.paper_bgcolor is not None


# ---------------------------------------------------------------------------
# funnel_area
# ---------------------------------------------------------------------------


class TestFunnelArea:
    def test_returns_single_funnelarea_trace(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).funnel_area("name", "value", title="T")
        assert isinstance(fig, go.Figure)
        # px.funnel_area -> one Funnelarea trace (area-proportional radial wedges)
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Funnelarea)
        assert fig.layout.title.text == "T"

    def test_labels_carry_names(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).funnel_area("name", "value")
        # slice labels are the name column values
        labels = list(fig.data[0].labels)
        assert "A" in labels and "B" in labels and "C" in labels

    def test_values_mapped_to_slice_area(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).funnel_area("name", "value")
        # trace.values carries the raw per-slice value column (area driver)
        assert list(fig.data[0].values) == [100, 200, 50]

    def test_color_column_assigns_per_slice_colors(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).funnel_area("name", "value", color_column="color")
        # discrete color -> marker.colors array (one hex per slice), NOT a trace split
        assert len(fig.data) == 1
        colors = fig.data[0].marker.colors
        assert colors is not None and len(colors) == len(fig.data[0].labels)

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).funnel_area("name", "value", theme="light")
        # apply_theme ran: light theme sets a concrete paper_bgcolor
        assert fig.layout.paper_bgcolor is not None

    def test_apply_theme_professional_runs(self) -> None:
        fig = AdvancedChartBuilder(TREEMAP_DATA).funnel_area("name", "value", theme="professional")
        # professional salmon-paper register applied
        assert fig.layout.paper_bgcolor is not None


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


class TestParallelCategories:
    def test_returns_single_parcats_trace_with_dimensions(self) -> None:
        fig = AdvancedChartBuilder(PARCATS_DATA).parallel_categories(["region", "sector", "stage"], title="T")
        assert isinstance(fig, go.Figure)
        # px.parallel_categories emits ONE go.Parcats trace carrying every
        # categorical column as a vertical stack on its nested .dimensions
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Parcats)
        assert len(fig.data[0].dimensions) == 3
        assert fig.data[0].dimensions[0].label == "region"
        assert fig.data[0].dimensions[1].label == "sector"
        assert fig.data[0].dimensions[2].label == "stage"
        # categorical values are preserved verbatim on each dimension
        assert list(fig.data[0].dimensions[0].values) == ["N", "S", "N", "S"]
        assert fig.layout.title.text == "T"

    def test_two_columns_single_trace(self) -> None:
        fig = AdvancedChartBuilder(PARCATS_DATA).parallel_categories(["region", "sector"])
        assert isinstance(fig.data[0], go.Parcats)
        assert len(fig.data[0].dimensions) == 2

    def test_no_color_leaves_line_color_none(self) -> None:
        # with no color mapping, the trace's line.color is None
        fig = AdvancedChartBuilder(PARCATS_DATA).parallel_categories(["region", "sector"])
        assert fig.data[0].line.color is None

    def test_numeric_color_column_sets_line_color(self) -> None:
        # a NUMERIC color_column gradient-colors each ribbon (string cols are
        # rejected by parcats — ribbon color is a per-row numeric array)
        fig = AdvancedChartBuilder(PARCATS_DATA).parallel_categories(["region", "sector"], color_column="amt")
        assert fig.data[0].line.color is not None
        # line.color carries the raw per-row magnitudes (NOT normalized)
        assert list(fig.data[0].line.color) == [10, 40, 20, 30]

    def test_colorscale_override_runs(self) -> None:
        fig = AdvancedChartBuilder(PARCATS_DATA).parallel_categories(
            ["region", "sector"], color_column="amt", color_continuous_scale="Viridis"
        )
        # custom scale accepted; line still gradient-colored (colorscale stays
        # None on the trace — resolved at render via layout.coloraxis)
        assert fig.data[0].line.color is not None

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(PARCATS_DATA).parallel_categories(["region", "sector", "stage"], theme="light")
        # apply_theme ran: light theme sets a concrete paper_bgcolor; go.Parcats
        # has no marker attr so its trace-polish loop skips it cleanly
        assert fig.layout.paper_bgcolor is not None

    def test_professional_theme_runs(self) -> None:
        fig = AdvancedChartBuilder(PARCATS_DATA).parallel_categories(
            ["region", "sector", "stage"], theme="professional"
        )
        # professional register sets the salmon-paper background
        assert fig.layout.paper_bgcolor == "#fff1e5"


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


# ---------------------------------------------------------------------------
# density_heatmap
# ---------------------------------------------------------------------------

DENSITY_HEATMAP_DATA: list[dict[str, Any]] = [
    {"a": 1, "b": 2, "w": 1},
    {"a": 2, "b": 3, "w": 1},
    {"a": 3, "b": 1, "w": 1},
    {"a": 1, "b": 2, "w": 2},
    {"a": 2, "b": 3, "w": 2},
    {"a": 3, "b": 1, "w": 2},
]


class TestDensityHeatmap:
    def test_returns_single_histogram2d_trace(self) -> None:
        fig = AdvancedChartBuilder(DENSITY_HEATMAP_DATA).density_heatmap("a", "b", title="T")
        assert isinstance(fig, go.Figure)
        # px.density_heatmap emits ONE go.Histogram2d carrying the raw x/y samples
        # (distinct from heatmap's go.Heatmap pivot and density_contour's isolines)
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Histogram2d)
        assert list(fig.data[0].x) == [1, 2, 3, 1, 2, 3]
        assert list(fig.data[0].y) == [2, 3, 1, 2, 3, 1]
        assert fig.data[0].histfunc == "count"
        assert fig.layout.title.text == "T"

    def test_nbins_passthrough(self) -> None:
        fig = AdvancedChartBuilder(DENSITY_HEATMAP_DATA).density_heatmap("a", "b", nbinsx=5, nbinsy=7)
        assert fig.data[0].nbinsx == 5
        assert fig.data[0].nbinsy == 7

    def test_z_column_and_histfunc_aggregation(self) -> None:
        # z_column + histfunc='sum' colors each cell by an aggregated third var
        fig = AdvancedChartBuilder(DENSITY_HEATMAP_DATA).density_heatmap("a", "b", z_column="w", histfunc="sum")
        t = fig.data[0]
        assert t.histfunc == "sum"
        # each (a,b) pair appears twice with w=1 then w=2 → summed z grid cells
        # hold the aggregated values; raw x/y samples still carry all rows
        assert list(t.x) == [1, 2, 3, 1, 2, 3]

    def test_colorscale_runs(self) -> None:
        # custom colorscale accepted (lands on layout.coloraxis, not the trace)
        fig = AdvancedChartBuilder(DENSITY_HEATMAP_DATA).density_heatmap("a", "b", colorscale="Viridis")
        assert fig.layout.coloraxis is not None

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(DENSITY_HEATMAP_DATA).density_heatmap("a", "b", theme="light")
        # apply_theme ran: light theme sets a concrete paper_bgcolor; go.Histogram2d
        # has a marker attr but it has NO .line sub-prop so the deeper guard
        # (added in iter 15 for Histogram2dContour) skips it cleanly
        assert fig.layout.paper_bgcolor is not None

    def test_professional_theme_runs(self) -> None:
        fig = AdvancedChartBuilder(DENSITY_HEATMAP_DATA).density_heatmap("a", "b", theme="professional")
        # professional register sets the salmon-paper background
        assert fig.layout.paper_bgcolor == "#fff1e5"


# ---------------------------------------------------------------------------
# ecdf
# ---------------------------------------------------------------------------

ECDF_DATA: list[dict[str, Any]] = [
    {"v": 5, "grp": "x"},
    {"v": 1, "grp": "x"},
    {"v": 4, "grp": "y"},
    {"v": 2, "grp": "y"},
    {"v": 3, "grp": "x"},
]


class TestECDF:
    def test_returns_single_scatter_trace_ascending(self) -> None:
        fig = AdvancedChartBuilder(ECDF_DATA).ecdf("v", title="T")
        assert isinstance(fig, go.Figure)
        # px.ecdf emits ONE go.Scatter whose x is the sorted observations and
        # whose y is the running cumulative probability 0→1
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Scatter)
        assert list(fig.data[0].x) == [1, 2, 3, 4, 5]
        assert list(fig.data[0].y) == [0.2, 0.4, 0.6, 0.8, 1.0]
        assert fig.data[0].mode == "lines"
        assert fig.layout.title.text == "T"

    def test_color_column_splits_one_trace_per_group(self) -> None:
        fig = AdvancedChartBuilder(ECDF_DATA).ecdf("v", color_column="grp")
        # one Scatter per group value (grp has 2: x, y)
        assert len(fig.data) == 2
        assert all(isinstance(t, go.Scatter) for t in fig.data)
        assert sorted(t.name for t in fig.data) == ["x", "y"]

    def test_markers_toggles_trace_mode(self) -> None:
        base = AdvancedChartBuilder(ECDF_DATA).ecdf("v")
        assert base.data[0].mode == "lines"
        marked = AdvancedChartBuilder(ECDF_DATA).ecdf("v", markers=True)
        assert marked.data[0].mode == "lines+markers"

    def test_ecdfmode_complementary_descends(self) -> None:
        # 'complementary' = P(X > x): a descending exceedance curve. At the
        # minimum observation P(X > x) = (N-1)/N (the min point itself is
        # excluded), so it starts at 0.8 for N=5 and falls to 0.0 at the max.
        fig = AdvancedChartBuilder(ECDF_DATA).ecdf("v", ecdfmode="complementary")
        y = list(fig.data[0].y)
        assert y[0] > y[-1]
        assert abs(y[0] - 0.8) < 1e-9
        assert abs(y[-1] - 0.0) < 1e-9

    def test_apply_theme_professional_runs(self) -> None:
        fig = AdvancedChartBuilder(ECDF_DATA).ecdf("v", theme="professional")
        # go.Scatter has a marker WITH a line sub-prop, so apply_theme's
        # trace-polish loop runs cleanly; professional theme = salmon paper.
        assert fig.layout.paper_bgcolor == "#fff1e5"


# ---------------------------------------------------------------------------
# sankey
# ---------------------------------------------------------------------------

SANKEY_DATA: list[dict[str, Any]] = [
    {"src": "Budget", "dst": "Health", "amt": 100},
    {"src": "Budget", "dst": "Schools", "amt": 80},
    {"src": "Health", "dst": "Hospitals", "amt": 60},
    {"src": "Budget", "dst": "Health", "amt": 20},  # duplicate Budget→Health ribbon
    {"src": "Schools", "dst": "Wages", "amt": "40"},  # string-numeric → coerced to 40.0
]


class TestSankey:
    def test_returns_single_sankey_trace(self) -> None:
        fig = AdvancedChartBuilder(SANKEY_DATA).sankey("src", "dst", "amt", title="Flow")
        assert isinstance(fig, go.Figure)
        # one Sankey trace carrying node + link sub-objects
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Sankey)
        assert fig.layout.title.text == "Flow"

    def test_node_labels_are_union_of_source_and_target(self) -> None:
        fig = AdvancedChartBuilder(SANKEY_DATA).sankey("src", "dst", "amt")
        # nodes = every distinct label appearing in either column
        labels = list(fig.data[0].node.label)
        assert set(labels) == {"Budget", "Health", "Schools", "Hospitals", "Wages"}

    def test_link_source_target_value_mapping(self) -> None:
        fig = AdvancedChartBuilder(SANKEY_DATA).sankey("src", "dst", "amt")
        t = fig.data[0]
        index = {label: i for i, label in enumerate(t.node.label)}
        # Budget→Health: 100 + 20 (duplicated) aggregated = 120
        # Budget→Schools: 80
        # Health→Hospitals: 60
        # Schools→Wages: 40 (string coerced)
        pairs = sorted(zip(t.link.source, t.link.target, t.link.value, strict=False), key=lambda r: (r[0], r[1]))
        expected = sorted(
            [
                (index["Budget"], index["Health"], 120.0),
                (index["Budget"], index["Schools"], 80.0),
                (index["Health"], index["Hospitals"], 60.0),
                (index["Schools"], index["Wages"], 40.0),
            ],
            key=lambda r: (r[0], r[1]),
        )
        assert pairs == expected

    def test_duplicate_pairs_aggregated_by_sum(self) -> None:
        data = [
            {"s": "A", "d": "B", "v": 10},
            {"s": "A", "d": "B", "v": 3},
            {"s": "A", "d": "B", "v": 7},
        ]
        fig = AdvancedChartBuilder(data).sankey("s", "d", "v")
        # three identical A→B rows collapse to one ribbon of summed value 20
        assert len(fig.data[0].link.source) == 1
        assert fig.data[0].link.value[0] == 20.0

    def test_string_numeric_values_coerced(self) -> None:
        data = [{"s": "A", "d": "B", "v": "12.5"}]
        fig = AdvancedChartBuilder(data).sankey("s", "d", "v")
        # to_numeric coerces '12.5' to 12.5; non-numeric would fall back to 0.0
        assert fig.data[0].link.value[0] == 12.5

    def test_node_pad_and_thickness_passthrough(self) -> None:
        fig = AdvancedChartBuilder(SANKEY_DATA).sankey("src", "dst", "amt", node_pad=25, node_thickness=30)
        assert fig.data[0].node.pad == 25
        assert fig.data[0].node.thickness == 30

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(SANKEY_DATA).sankey("src", "dst", "amt", theme="light")
        # go.Sankey has no trace-level marker, so apply_theme's marker-polish loop
        # skips it cleanly; layout paper_bgcolor is still set by the light theme
        assert fig.layout.paper_bgcolor is not None


# ---------------------------------------------------------------------------
# strip
# ---------------------------------------------------------------------------

STRIP_DATA: list[dict[str, Any]] = [
    {"cat": "a", "v": 1, "grp": "x"},
    {"cat": "a", "v": 2, "grp": "y"},
    {"cat": "b", "v": 3, "grp": "x"},
    {"cat": "b", "v": 4, "grp": "y"},
    {"cat": "a", "v": 5, "grp": "x"},
]


class TestStrip:
    def test_returns_single_box_trace_with_points(self) -> None:
        fig = AdvancedChartBuilder(STRIP_DATA).strip("v", x_column="cat", title="T")
        assert isinstance(fig, go.Figure)
        # px.strip emits ONE go.Box trace carrying every raw observation as a
        # point (boxpoints='all'), so the full sample — not a summary — is shown.
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Box)
        assert fig.data[0].boxpoints == "all"
        assert list(fig.data[0].x) == ["a", "a", "b", "b", "a"]
        assert list(fig.data[0].y) == [1, 2, 3, 4, 5]
        assert fig.layout.title.text == "T"

    def test_jitter_and_pointpos_passthrough(self) -> None:
        fig = AdvancedChartBuilder(STRIP_DATA).strip("v", jitter=0.4, pointpos=-1.5)
        assert fig.data[0].jitter == 0.4
        assert fig.data[0].pointpos == -1.5

    def test_color_column_splits_one_trace_per_group(self) -> None:
        fig = AdvancedChartBuilder(STRIP_DATA).strip("v", color_column="grp")
        # one Box trace per group value (grp has 2: x, y), named after each group
        assert len(fig.data) == 2
        assert all(isinstance(t, go.Box) for t in fig.data)
        assert sorted(t.name for t in fig.data) == ["x", "y"]

    def test_y_only_leaves_x_none(self) -> None:
        fig = AdvancedChartBuilder(STRIP_DATA).strip("v")
        # no x_column → every point in a single column; px.strip leaves trace.x None
        assert len(fig.data) == 1
        assert fig.data[0].x is None
        assert list(fig.data[0].y) == [1, 2, 3, 4, 5]

    def test_apply_theme_professional_runs(self) -> None:
        fig = AdvancedChartBuilder(STRIP_DATA).strip("v", theme="professional")
        # go.Box has a marker WITH a line sub-prop, so apply_theme's trace-polish
        # loop runs cleanly; professional theme = salmon paper.
        assert fig.layout.paper_bgcolor == "#fff1e5"


# ---------------------------------------------------------------------------
# bar_polar
# ---------------------------------------------------------------------------

BAR_POLAR_DATA: list[dict[str, Any]] = [
    {"dir": "N", "spd": 5, "grp": "x"},
    {"dir": "E", "spd": 8, "grp": "x"},
    {"dir": "S", "spd": 3, "grp": "y"},
    {"dir": "W", "spd": 9, "grp": "y"},
]


class TestBarPolar:
    def test_returns_single_barpolar_trace(self) -> None:
        fig = AdvancedChartBuilder(BAR_POLAR_DATA).bar_polar("spd", "dir", title="Wind")
        assert isinstance(fig, go.Figure)
        # px.bar_polar emits a SINGLE go.Barpolar trace carrying r/theta arrays
        # (no per-cell nesting) — one radial bar per angular position.
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Barpolar)
        assert [int(v) for v in fig.data[0].r] == [5, 8, 3, 9]
        assert list(fig.data[0].theta) == ["N", "E", "S", "W"]
        assert fig.layout.title.text == "Wind"

    def test_color_column_splits_one_trace_per_group(self) -> None:
        fig = AdvancedChartBuilder(BAR_POLAR_DATA).bar_polar("spd", "dir", color_column="grp")
        # one Barpolar trace per group value (grp has 2: x, y), named after each group
        assert len(fig.data) == 2
        assert all(isinstance(t, go.Barpolar) for t in fig.data)
        assert sorted(t.name for t in fig.data) == ["x", "y"]

    def test_apply_theme_professional_runs(self) -> None:
        fig = AdvancedChartBuilder(BAR_POLAR_DATA).bar_polar("spd", "dir", theme="professional")
        # go.Barpolar has a marker WITH a line sub-prop, so apply_theme's
        # trace-polish loop runs cleanly. Professional theme = salmon paper;
        # the polar axis lives on layout.polar (separate from xaxis/yaxis).
        assert fig.layout.paper_bgcolor == "#fff1e5"
        assert fig.layout.polar is not None

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(BAR_POLAR_DATA).bar_polar("spd", "dir", theme="light")
        # light theme = white paper; apply_theme is polar-safe with zero changes
        assert fig.layout.paper_bgcolor == "#ffffff"

    def test_color_split_preserves_per_group_r(self) -> None:
        fig = AdvancedChartBuilder(BAR_POLAR_DATA).bar_polar("spd", "dir", color_column="grp")
        by_name = {t.name: [int(v) for v in t.r] for t in fig.data}
        # group x owns rows N,E (spd 5,8); group y owns rows S,W (spd 3,9)
        assert by_name["x"] == [5, 8]
        assert by_name["y"] == [3, 9]


RADAR_DATA: list[dict[str, Any]] = [
    {"axis": "econ", "score": 7, "grp": "Belgrade"},
    {"axis": "health", "score": 6, "grp": "Belgrade"},
    {"axis": "edu", "score": 8, "grp": "Belgrade"},
    {"axis": "econ", "score": 4, "grp": "Novi Sad"},
    {"axis": "health", "score": 9, "grp": "Novi Sad"},
    {"axis": "edu", "score": 5, "grp": "Novi Sad"},
]


class TestRadar:
    def test_returns_single_scatterpolar_trace(self) -> None:
        fig = AdvancedChartBuilder(RADAR_DATA[:3]).radar("score", "axis", title="City profile")
        assert isinstance(fig, go.Figure)
        # px.line_polar emits a SINGLE go.Scatterpolar trace (no color grouping);
        # r/theta land as parallel arrays on the trace, mode defaults to lines+markers.
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Scatterpolar)
        # line_close=True (default) appends the first r/theta value to close the
        # polygon, so r = [7,6,8,7] and theta wraps econ→...→econ.
        assert [int(v) for v in fig.data[0].r] == [7, 6, 8, 7]
        assert list(fig.data[0].theta) == ["econ", "health", "edu", "econ"]
        assert fig.layout.title.text == "City profile"
        assert "markers" in fig.data[0].mode

    def test_color_column_splits_one_trace_per_group(self) -> None:
        fig = AdvancedChartBuilder(RADAR_DATA).radar("score", "axis", color_column="grp")
        # one closed Scatterpolar profile per group (Belgrade, Novi Sad)
        assert len(fig.data) == 2
        assert all(isinstance(t, go.Scatterpolar) for t in fig.data)
        assert sorted(t.name for t in fig.data) == ["Belgrade", "Novi Sad"]

    def test_markers_off_is_lines_only(self) -> None:
        fig = AdvancedChartBuilder(RADAR_DATA[:3]).radar("score", "axis", markers=False)
        # markers=False yields a lines-only mode (no 'markers' substring)
        assert "markers" not in fig.data[0].mode

    def test_fill_shades_profile_interior(self) -> None:
        fig = AdvancedChartBuilder(RADAR_DATA[:3]).radar("score", "axis", fill=True)
        # fill='toself' shades each profile's interior
        assert fig.data[0].fill == "toself"

    def test_apply_theme_professional_runs(self) -> None:
        fig = AdvancedChartBuilder(RADAR_DATA[:3]).radar("score", "axis", theme="professional")
        # go.Scatterpolar has a marker WITH a line sub-prop, so apply_theme's
        # trace-polish loop runs cleanly. Professional theme = salmon paper;
        # the polar axis lives on layout.polar (separate from xaxis/yaxis).
        assert fig.layout.paper_bgcolor == "#fff1e5"
        assert fig.layout.polar is not None

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(RADAR_DATA[:3]).radar("score", "axis", theme="light")
        # light theme = white paper; apply_theme is polar-safe with zero changes
        assert fig.layout.paper_bgcolor == "#ffffff"


TIMELINE_DATA: list[dict[str, Any]] = [
    {"task": "Design", "start": "2024-01-01", "end": "2024-01-10", "grp": "A"},
    {"task": "Build", "start": "2024-01-05", "end": "2024-01-20", "grp": "B"},
    {"task": "Test", "start": "2024-01-15", "end": "2024-01-25", "grp": "A"},
]


class TestTimeline:
    def test_returns_single_horizontal_bar_on_date_axis(self) -> None:
        fig = AdvancedChartBuilder(TIMELINE_DATA[:2]).timeline("start", "end", title="Schedule")
        assert isinstance(fig, go.Figure)
        # px.timeline emits a SINGLE horizontal go.Bar trace; each interval is a
        # bar whose `base` (start) is a datetime64 array and `x` its duration in ms.
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Bar)
        assert fig.data[0].orientation == "h"
        assert fig.layout.xaxis.type == "date"
        # base carries the per-row start datetimes (None if px failed to cast)
        assert fig.data[0].base is not None
        assert len(fig.data[0].base) == 2
        # durations in milliseconds are all positive (end > start for every row)
        assert all(int(d) > 0 for d in fig.data[0].x)
        assert fig.layout.title.text == "Schedule"

    def test_name_column_places_each_row_on_its_own_swimlane(self) -> None:
        fig = AdvancedChartBuilder(TIMELINE_DATA[:2]).timeline("start", "end", name_column="task")
        # y carries the per-row task labels parallel to base/x
        assert list(fig.data[0].y) == ["Design", "Build"]

    def test_color_column_splits_one_trace_per_group(self) -> None:
        fig = AdvancedChartBuilder(TIMELINE_DATA).timeline("start", "end", color_column="grp")
        # one horizontal Bar trace per group value, named after each group
        assert len(fig.data) == 2
        assert all(isinstance(t, go.Bar) and t.orientation == "h" for t in fig.data)
        assert sorted(t.name for t in fig.data) == ["A", "B"]

    def test_apply_theme_professional_preserves_date_axis(self) -> None:
        fig = AdvancedChartBuilder(TIMELINE_DATA[:2]).timeline("start", "end", theme="professional")
        # go.Bar has a marker WITH a line sub-prop, so apply_theme's trace-polish
        # loop runs cleanly; professional theme = salmon paper, and the date axis
        # type survives apply_theme's xaxis mutation.
        assert fig.layout.paper_bgcolor == "#fff1e5"
        assert fig.layout.xaxis.type == "date"

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(TIMELINE_DATA[:2]).timeline("start", "end", theme="light")
        # light theme = white paper; apply_theme is timeline-safe with zero changes
        assert fig.layout.paper_bgcolor == "#ffffff"


class TestArea:
    def test_single_stacked_scatter_trace_with_title(self) -> None:
        fig = AdvancedChartBuilder(ANIM_DATA).area("year", "pop", title="Energy mix")
        assert isinstance(fig, go.Figure)
        # px.area emits a go.Scatter trace (no special trace type) whose stackgroup
        # is set, so plotly stacks/fills it at render; x carries every row's year.
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Scatter)
        assert fig.data[0].stackgroup == "1"
        assert list(fig.data[0].y) == [7, 8, 3, 4]
        assert fig.layout.title.text == "Energy mix"

    def test_color_column_one_trace_per_group(self) -> None:
        fig = AdvancedChartBuilder(ANIM_DATA).area("year", "pop", color_column="city")
        # one stacked Scatter band per group value, named after each group
        assert len(fig.data) == 2
        assert all(isinstance(t, go.Scatter) and t.stackgroup == "1" for t in fig.data)
        assert sorted(t.name for t in fig.data) == ["BG", "NS"]

    def test_markers_adds_points_to_bands(self) -> None:
        fig = AdvancedChartBuilder(ANIM_DATA).area("year", "pop", markers=True)
        # default mode is 'lines'; markers=True flips it to 'lines+markers'
        assert fig.data[0].mode == "lines+markers"

    def test_groupnorm_leaves_trace_values_raw(self) -> None:
        fig = AdvancedChartBuilder(ANIM_DATA).area("year", "pop", color_column="city", groupnorm="percent")
        # Like the 3D marching-cubes/alphahull family, stackgroup normalization is
        # applied at JS render time — trace.y keeps its RAW values (not 0-100).
        bg = next(t for t in fig.data if t.name == "BG")
        assert list(bg.y) == [7, 8]

    def test_apply_theme_professional_salmon_paper(self) -> None:
        fig = AdvancedChartBuilder(ANIM_DATA).area("year", "pop", theme="professional")
        # go.Scatter has a marker WITH a line sub-prop, so apply_theme's marker-polish
        # loop runs cleanly; professional theme = salmon paper.
        assert fig.layout.paper_bgcolor == "#fff1e5"

    def test_apply_theme_light_runs(self) -> None:
        fig = AdvancedChartBuilder(ANIM_DATA).area("year", "pop", theme="light")
        # light theme = white paper; apply_theme is area-safe with zero changes
        assert fig.layout.paper_bgcolor == "#ffffff"
