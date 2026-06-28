"""Offline unit tests for tools/visualization.py.

Covers the MCP tools that shipped with zero or transport-only coverage:
  - create_chart (advanced chart-type branches, validation, fig-None,
    viz-exception wrapping — the basic types are already exercised via
    test_mcp_client's in-process transport)
  - apply_chart_theme, build_infographic, build_dashboard,
    enhance_chart_tooltips, add_chart_annotation, add_chart_highlight_zone,
    add_chart_callouts, add_chart_threshold_line, create_data_table

All viz-layer functions (ChartBuilder, AdvancedChartBuilder, fig_to_dict,
apply_theme, add_annotation, create_infographic, create_dashboard,
add_rich_tooltips, add_annotation_callouts, add_comparison_markers,
data_table_html, data_table_css) are faked at the module-attribute seam, and
config.export_dir is redirected to a tmp dir so HTML writes are real but
sandboxed — fully deterministic, no network, no plotly rendering.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp.exceptions import ToolError

from serbian_data_mcp.tools import visualization as viz_mod
from serbian_data_mcp.tools.visualization import (
    add_chart_annotation,
    add_chart_callouts,
    add_chart_highlight_zone,
    add_chart_threshold_line,
    apply_chart_theme,
    build_dashboard,
    build_infographic,
    create_chart,
    create_data_table,
    enhance_chart_tooltips,
)


class _Sentinel:
    """Stand-in Plotly figure so pass-through is traceable without plotly."""

    def __init__(self, tag: str = "fig") -> None:
        self.tag = tag


def _boom(*_a: Any, **_k: Any) -> Any:
    """Raise a ValueError — used to drive viz-layer exception-wrapping paths."""
    raise ValueError("bad")


class _FakeBuilder:
    """Captures the method name + kwargs the tool invoked on the builder.

    Returns the sink's ``return`` value (default a _Sentinel) so the tool sees
    a non-None figure; set sink["return"] = None to drive the fig-None branch,
    or sink["raise"] = Exc to drive the viz-exception branch.
    """

    def __init__(self, data: Any, sink: dict[str, Any], tag: str) -> None:
        self.data = data
        self.sink = sink
        self.tag = tag

    def __getattr__(self, name: str) -> Any:
        def method(*args: Any, **kwargs: Any) -> Any:
            self.sink["builder"] = self.tag
            self.sink["method"] = name
            self.sink["args"] = args
            self.sink["kwargs"] = kwargs
            if self.sink.get("raise"):
                raise self.sink["raise"]
            return self.sink.get("return", _Sentinel(tag=self.tag))

        return method


def _wire_builders(monkeypatch, sink: dict[str, Any]) -> None:
    """Patch ChartBuilder + AdvancedChartBuilder + fig_to_dict to use ``sink``."""
    monkeypatch.setattr(viz_mod, "ChartBuilder", lambda data: _FakeBuilder(data, sink, "basic"))
    monkeypatch.setattr(viz_mod, "AdvancedChartBuilder", lambda data: _FakeBuilder(data, sink, "adv"))
    monkeypatch.setattr(viz_mod, "fig_to_dict", lambda fig: {"converted": True})


@pytest.fixture
def sandbox_export_dir(monkeypatch, tmp_path):
    """Redirect config.export_dir to a tmp dir so HTML writes are sandboxed.

    export_dir is a property on the Config class, so the property descriptor on
    the class is replaced (monkeypatch restores it after the test).
    """
    monkeypatch.setattr(
        type(viz_mod.config),
        "export_dir",
        property(lambda self: tmp_path),
    )
    return tmp_path


# ---------------------------------------------------------------------------
# create_chart — input validation + dispatcher
# ---------------------------------------------------------------------------


async def test_create_chart_unsupported_type_raises() -> None:
    with pytest.raises(ToolError, match="Unsupported chart type"):
        await create_chart(data=[{"x": 1}], chart_type="radar")


async def test_create_chart_unsupported_message_lists_all_types() -> None:
    try:
        await create_chart(data=[{"x": 1}], chart_type="bogus")
    except ToolError as e:
        msg = str(e)
        # Every supported type must be listed in the error so clients can self-correct.
        for t in ("line", "bar", "pie", "heatmap", "gauge", "sparklines", "violin", "waterfall", "candlestick"):
            assert t in msg
    else:  # pragma: no cover - defensive
        raise AssertionError("expected ToolError")


# ---------------------------------------------------------------------------
# create_chart — basic-chart branches (kwarg passthrough + envelope)
# ---------------------------------------------------------------------------


async def test_create_chart_line_passthrough_and_envelope(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)

    result = await create_chart(
        data=[{"year": 2020, "pop": 7}],
        chart_type="line",
        x_column="year",
        y_column="pop",
        title="T",
        color_column="c",
    )

    assert sink["builder"] == "basic"
    assert sink["method"] == "line_chart"
    assert sink["args"] == ("year", "pop")
    assert sink["kwargs"] == {"title": "T", "color_column": "c"}
    assert result == {
        "figure": {"converted": True},
        "type": "plotly",
        "interactive": True,
        "chart_type": "line",
        "title": "T",
    }


async def test_create_chart_line_missing_columns_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="line chart requires x_column and y_column"):
        await create_chart(data=[{"x": 1}], chart_type="line", x_column="", y_column="")


async def test_create_chart_bar_orientation_passthrough(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    await create_chart(
        data=[{"r": "BG", "g": 1}],
        chart_type="bar",
        x_column="r",
        y_column="g",
        orientation="h",
    )
    assert sink["method"] == "bar_chart"
    assert sink["kwargs"]["orientation"] == "h"


async def test_create_chart_bar_missing_columns_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="bar chart requires x_column and y_column"):
        await create_chart(data=[{"x": 1}], chart_type="bar", x_column="x")


async def test_create_chart_pie_passthrough(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    await create_chart(
        data=[{"s": "A", "v": 1}],
        chart_type="pie",
        values_column="v",
        names_column="s",
    )
    assert sink["method"] == "pie_chart"
    assert sink["args"] == ("v", "s")


async def test_create_chart_pie_missing_columns_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="pie chart requires values_column and names_column"):
        await create_chart(data=[{"x": 1}], chart_type="pie", values_column="v", names_column="")


async def test_create_chart_scatter_size_column_passthrough(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    await create_chart(
        data=[{"a": 1, "b": 2}],
        chart_type="scatter",
        x_column="a",
        y_column="b",
        size_column="sz",
        color_column="c",
    )
    assert sink["method"] == "scatter_plot"
    assert sink["kwargs"]["size_column"] == "sz"
    assert sink["kwargs"]["color_column"] == "c"


async def test_create_chart_scatter_missing_columns_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="scatter plot requires x_column and y_column"):
        await create_chart(data=[{"x": 1}], chart_type="scatter", x_column="x", y_column="")


async def test_create_chart_histogram_falls_back_to_y_column(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    # x_column empty → col must resolve from y_column.
    await create_chart(data=[{"v": 1}], chart_type="histogram", x_column="", y_column="v", bins=7)
    assert sink["method"] == "histogram"
    assert sink["args"] == ("v",)
    assert sink["kwargs"]["bins"] == 7


async def test_create_chart_histogram_missing_column_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="histogram requires x_column or y_column"):
        await create_chart(data=[{"x": 1}], chart_type="histogram")


async def test_create_chart_box_passthrough(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    await create_chart(data=[{"v": 1, "g": "a"}], chart_type="box", y_column="v", x_column="g")
    assert sink["method"] == "box_plot"
    assert sink["args"] == ("v",)
    assert sink["kwargs"]["x_column"] == "g"


async def test_create_chart_box_missing_y_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="box plot requires y_column"):
        await create_chart(data=[{"x": 1}], chart_type="box", y_column="")


# ---------------------------------------------------------------------------
# create_chart — advanced-chart branches (AdvancedChartBuilder)
# ---------------------------------------------------------------------------


async def test_create_chart_heatmap_passthrough(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    await create_chart(
        data=[{"x": 1, "y": 2, "z": 3}],
        chart_type="heatmap",
        x_column="x",
        y_column="y",
        z_column="z",
        theme="light",
    )
    assert sink["builder"] == "adv"
    assert sink["method"] == "heatmap"
    assert sink["args"] == ("x", "y", "z")
    assert sink["kwargs"]["theme"] == "light"


async def test_create_chart_heatmap_missing_columns_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="heatmap requires x_column, y_column, and z_column"):
        await create_chart(data=[{"x": 1}], chart_type="heatmap", x_column="x", y_column="y", z_column="")


async def test_create_chart_violin_passthrough(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    await create_chart(data=[{"v": 1, "g": "a"}], chart_type="violin", y_column="v", x_column="g", theme="light")
    assert sink["builder"] == "adv"
    assert sink["method"] == "violin"
    assert sink["args"] == ("v",)
    assert sink["kwargs"]["x_column"] == "g"
    assert sink["kwargs"]["theme"] == "light"


async def test_create_chart_violin_missing_y_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="violin requires y_column"):
        await create_chart(data=[{"x": 1}], chart_type="violin", y_column="")


async def test_create_chart_waterfall_passthrough(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    await create_chart(
        data=[{"step": "A", "amount": 10}],
        chart_type="waterfall",
        x_column="step",
        values_column="amount",
        theme="light",
    )
    assert sink["builder"] == "adv"
    assert sink["method"] == "waterfall"
    assert sink["args"] == ("step", "amount")
    assert sink["kwargs"]["theme"] == "light"


async def test_create_chart_waterfall_missing_values_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="waterfall requires x_column and values_column"):
        await create_chart(data=[{"step": "A"}], chart_type="waterfall", x_column="step", values_column="")


async def test_create_chart_candlestick_passthrough(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    await create_chart(
        data=[{"date": "d", "open": 1, "high": 2, "low": 0, "close": 1.5}],
        chart_type="candlestick",
        open_column="open",
        high_column="high",
        low_column="low",
        close_column="close",
        x_column="date",
        theme="light",
    )
    assert sink["builder"] == "adv"
    assert sink["method"] == "candlestick"
    assert sink["args"] == ("open", "high", "low", "close")
    assert sink["kwargs"]["x_column"] == "date"
    assert sink["kwargs"]["theme"] == "light"


async def test_create_chart_candlestick_missing_close_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="candlestick requires open_column, high_column, low_column, and close_column"):
        await create_chart(
            data=[{"open": 1, "high": 2, "low": 0}],
            chart_type="candlestick",
            open_column="open",
            high_column="high",
            low_column="low",
            close_column="",
        )


async def test_create_chart_treemap_passthrough(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    await create_chart(
        data=[{"n": "A", "v": 1}],
        chart_type="treemap",
        names_column="n",
        values_column="v",
        hierarchy_column="h",
        color_column="c",
        theme="dark",
    )
    assert sink["method"] == "treemap"
    assert sink["args"] == ("n", "v")
    assert sink["kwargs"]["hierarchy_column"] == "h"
    assert sink["kwargs"]["color_column"] == "c"


async def test_create_chart_treemap_missing_columns_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="treemap requires names_column and values_column"):
        await create_chart(data=[{"x": 1}], chart_type="treemap", names_column="n", values_column="")


async def test_create_chart_gauge_passthrough(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    await create_chart(
        data=[],
        chart_type="gauge",
        value=42.0,
        min_val=0,
        max_val=100,
        label="Pct",
    )
    assert sink["method"] == "gauge"
    assert sink["args"] == (42.0,)
    assert sink["kwargs"]["min_val"] == 0
    assert sink["kwargs"]["max_val"] == 100
    assert sink["kwargs"]["label"] == "Pct"


async def test_create_chart_gauge_missing_value_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="gauge requires 'value' parameter"):
        await create_chart(data=[], chart_type="gauge", value=None)


async def test_create_chart_funnel_passthrough(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    await create_chart(
        data=[{"n": "A", "v": 1}],
        chart_type="funnel",
        names_column="n",
        values_column="v",
    )
    assert sink["method"] == "funnel"
    assert sink["args"] == ("n", "v")


async def test_create_chart_funnel_missing_columns_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="funnel requires names_column and values_column"):
        await create_chart(data=[{"x": 1}], chart_type="funnel", names_column="", values_column="")


async def test_create_chart_animated_line_passthrough(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    await create_chart(
        data=[{"x": 1, "y": 2, "f": 2020}],
        chart_type="animated_line",
        x_column="x",
        y_column="y",
        frame_column="f",
        category_column="c",
    )
    assert sink["method"] == "animated_line"
    assert sink["args"] == ("x", "y", "f")
    assert sink["kwargs"]["category_column"] == "c"


async def test_create_chart_animated_line_missing_columns_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="animated_line requires x_column, y_column, and frame_column"):
        await create_chart(data=[{"x": 1}], chart_type="animated_line", x_column="x", y_column="y", frame_column="")


async def test_create_chart_comparison_bar_requires_two_columns(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="comparison_bar requires x_column and comparison_columns"):
        await create_chart(
            data=[{"x": 1}],
            chart_type="comparison_bar",
            x_column="x",
            comparison_columns=["only_one"],
        )


async def test_create_chart_comparison_bar_passthrough(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    await create_chart(
        data=[{"x": 1}],
        chart_type="comparison_bar",
        x_column="x",
        comparison_columns=["a", "b"],
    )
    assert sink["method"] == "comparison_bar"
    assert sink["args"] == ("x", ["a", "b"])


async def test_create_chart_sparklines_passthrough(monkeypatch) -> None:
    sink: dict[str, Any] = {}
    _wire_builders(monkeypatch, sink)
    await create_chart(
        data=[{"x": 1, "y": 2, "t": 2020}],
        chart_type="sparklines",
        x_column="x",
        y_column="y",
        trend_column="t",
        top_n=5,
    )
    assert sink["method"] == "sparkline_container"
    assert sink["args"] == ("y", "x", "t")
    assert sink["kwargs"]["top_n"] == 5


async def test_create_chart_sparklines_missing_columns_raises(monkeypatch) -> None:
    _wire_builders(monkeypatch, {})
    with pytest.raises(ToolError, match="sparklines requires x_column and y_column"):
        await create_chart(data=[{"x": 1}], chart_type="sparklines", x_column="", y_column="")


# ---------------------------------------------------------------------------
# create_chart — fig-None + viz-exception wrapping
# ---------------------------------------------------------------------------


async def test_create_chart_fig_none_raises_failed_to_create(monkeypatch) -> None:
    sink: dict[str, Any] = {"return": None}
    _wire_builders(monkeypatch, sink)
    with pytest.raises(ToolError, match=r"Failed to create line chart"):
        await create_chart(data=[{"x": 1}], chart_type="line", x_column="x", y_column="y")


async def test_create_chart_viz_exception_wrapped(monkeypatch) -> None:
    sink: dict[str, Any] = {"raise": ValueError("boom")}
    _wire_builders(monkeypatch, sink)
    with pytest.raises(ToolError, match=r"Failed to create bar chart: boom"):
        await create_chart(data=[{"x": 1}], chart_type="bar", x_column="x", y_column="y")


# ---------------------------------------------------------------------------
# apply_chart_theme
# ---------------------------------------------------------------------------


async def test_apply_chart_theme_applies_theme_annotations_and_zones(monkeypatch) -> None:
    calls: dict[str, Any] = {}

    def fake_apply_theme(fig, theme):
        calls["theme"] = theme
        return fig

    monkeypatch.setattr(viz_mod, "apply_theme", fake_apply_theme)
    monkeypatch.setattr(viz_mod, "add_annotation", lambda fig, text, x, y: fig)
    monkeypatch.setattr(viz_mod, "add_highlight_zone", lambda fig, *a, **k: fig)
    monkeypatch.setattr(viz_mod, "fig_to_dict", lambda fig: {"themed": True})

    result = await apply_chart_theme(
        figure={"data": [], "layout": {}},
        theme="infographic",
        annotations=[{"text": "peak", "x": 1, "y": 2}],
        highlight_zones=[{"x_start": 0, "x_end": 5, "label": "zone"}],
    )

    assert calls["theme"] == "infographic"
    assert result == {"themed": True}


async def test_apply_chart_theme_exception_wrapped(monkeypatch) -> None:
    monkeypatch.setattr(viz_mod, "apply_theme", _boom)
    with pytest.raises(ToolError, match="Theming failed: bad"):
        await apply_chart_theme(figure={"data": [], "layout": {}})


# ---------------------------------------------------------------------------
# build_infographic
# ---------------------------------------------------------------------------


async def test_build_infographic_writes_html_and_returns_envelope(monkeypatch, sandbox_export_dir) -> None:
    def fake_create(data, **kwargs):
        return {
            "html": "<html>INFO</html>",
            "metadata": {"headline": "Big"},
            "insights": ["i1", "i2"],
        }

    monkeypatch.setattr(viz_mod, "create_infographic", fake_create)

    data = [{"r": "BG", "v": 7}]
    result = await build_infographic(data, title="Story", filename="info_out")

    assert result == {
        "filepath": str(sandbox_export_dir / "info_out.html"),
        "metadata": {"headline": "Big"},
        "insights": ["i1", "i2"],
        "headline": "Big",
        "total_rows": 1,
    }
    assert (sandbox_export_dir / "info_out.html").read_text(encoding="utf-8") == "<html>INFO</html>"


async def test_build_infographic_no_html_returns_error_envelope(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(viz_mod, "create_infographic", lambda data, **kwargs: {"metadata": {}})
    result = await build_infographic([{"x": 1}], filename="empty")
    assert result == {"error": True, "message": "Failed to generate infographic"}


async def test_build_infographic_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    def boom(*a, **k):
        raise RuntimeError("broken")

    monkeypatch.setattr(viz_mod, "create_infographic", boom)
    with pytest.raises(ToolError, match="Infographic failed: broken"):
        await build_infographic([{"x": 1}], filename="fail")


# ---------------------------------------------------------------------------
# build_dashboard
# ---------------------------------------------------------------------------


async def test_build_dashboard_writes_html_and_returns_envelope(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(viz_mod, "create_dashboard", lambda panels, title: "<html>DASH</html>")
    panels = [{"type": "big_number", "number": "7M", "label": "Pop"}]
    result = await build_dashboard(panels, title="Dash", filename="dash_out")

    assert result == {
        "filepath": str(sandbox_export_dir / "dash_out.html"),
        "panel_count": 1,
        "filename": "dash_out.html",
    }
    assert (sandbox_export_dir / "dash_out.html").read_text(encoding="utf-8") == "<html>DASH</html>"


async def test_build_dashboard_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(viz_mod, "create_dashboard", _boom)
    with pytest.raises(ToolError, match="Dashboard failed: bad"):
        await build_dashboard([{"type": "html", "content": "c"}], filename="fail")


# ---------------------------------------------------------------------------
# enhance_chart_tooltips
# ---------------------------------------------------------------------------


async def test_enhance_chart_tooltips_passthrough(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_tooltips(fig, **kwargs):
        captured["kwargs"] = kwargs
        return fig

    monkeypatch.setattr(viz_mod, "add_rich_tooltips", fake_tooltips)
    monkeypatch.setattr(viz_mod, "fig_to_dict", lambda fig: {"tt": True})

    result = await enhance_chart_tooltips(
        figure={"data": [], "layout": {}},
        value_column="pop",
        unit=" stanovnika",
        show_mean=False,
        show_rank=True,
    )
    assert captured["kwargs"] == {
        "value_column": "pop",
        "unit": " stanovnika",
        "show_mean": False,
        "show_rank": True,
    }
    assert result == {"tt": True}


async def test_enhance_chart_tooltips_exception_wrapped(monkeypatch) -> None:
    monkeypatch.setattr(viz_mod, "add_rich_tooltips", _boom)
    with pytest.raises(ToolError, match="Tooltip enhancement failed: bad"):
        await enhance_chart_tooltips(figure={"data": [], "layout": {}})


# ---------------------------------------------------------------------------
# add_chart_annotation / add_chart_highlight_zone
# ---------------------------------------------------------------------------


async def test_add_chart_annotation_passthrough(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_add(fig, *, text, x, y, arrow_color, font_size, show_arrow):
        captured.update(text=text, x=x, y=y, arrow_color=arrow_color, font_size=font_size, show_arrow=show_arrow)
        return fig

    monkeypatch.setattr(viz_mod, "add_annotation", fake_add)
    monkeypatch.setattr(viz_mod, "fig_to_dict", lambda fig: {"ann": True})

    result = await add_chart_annotation(
        figure={"data": [], "layout": {}},
        text="Peak",
        x=2022,
        y=7200000,
        arrow_color="#fff",
        font_size=12,
        show_arrow=False,
    )
    assert captured == {
        "text": "Peak",
        "x": 2022,
        "y": 7200000,
        "arrow_color": "#fff",
        "font_size": 12,
        "show_arrow": False,
    }
    assert result == {"ann": True}


async def test_add_chart_annotation_exception_wrapped(monkeypatch) -> None:
    monkeypatch.setattr(viz_mod, "add_annotation", _boom)
    with pytest.raises(ToolError, match="Annotation failed: bad"):
        await add_chart_annotation(figure={"data": [], "layout": {}}, text="x")


async def test_add_chart_highlight_zone_passthrough(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_zone(fig, *, x_start, x_end, fill_color, annotation_text):
        captured.update(x_start=x_start, x_end=x_end, fill_color=fill_color, annotation_text=annotation_text)
        return fig

    monkeypatch.setattr(viz_mod, "add_highlight_zone", fake_zone)
    monkeypatch.setattr(viz_mod, "fig_to_dict", lambda fig: {"zone": True})

    result = await add_chart_highlight_zone(
        figure={"data": [], "layout": {}},
        x_start=2020,
        x_end=2021,
        fill_color="rgba(0,0,0,0.1)",
        annotation_text="Crisis",
    )
    assert captured == {
        "x_start": 2020,
        "x_end": 2021,
        "fill_color": "rgba(0,0,0,0.1)",
        "annotation_text": "Crisis",
    }
    assert result == {"zone": True}


async def test_add_chart_highlight_zone_exception_wrapped(monkeypatch) -> None:
    monkeypatch.setattr(viz_mod, "add_highlight_zone", _boom)
    with pytest.raises(ToolError, match="Highlight zone failed: bad"):
        await add_chart_highlight_zone(figure={"data": [], "layout": {}}, x_start=0, x_end=1)


# ---------------------------------------------------------------------------
# add_chart_callouts / add_chart_threshold_line
# ---------------------------------------------------------------------------


async def test_add_chart_callouts_passthrough(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_callouts(fig, *, points, prefix, suffix):
        captured.update(points=points, prefix=prefix, suffix=suffix)
        return fig

    monkeypatch.setattr(viz_mod, "add_annotation_callouts", fake_callouts)
    monkeypatch.setattr(viz_mod, "fig_to_dict", lambda fig: {"co": True})

    points = [{"x": 1, "y": 2, "text": "a"}]
    result = await add_chart_callouts(
        figure={"data": [], "layout": {}},
        points=points,
        prefix=">>",
        suffix="<<",
    )
    assert captured == {"points": points, "prefix": ">>", "suffix": "<<"}
    assert result == {"co": True}


async def test_add_chart_callouts_exception_wrapped(monkeypatch) -> None:
    monkeypatch.setattr(viz_mod, "add_annotation_callouts", _boom)
    with pytest.raises(ToolError, match="Callouts failed: bad"):
        await add_chart_callouts(figure={"data": [], "layout": {}}, points=[])


async def test_add_chart_threshold_line_passthrough(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_markers(fig, *, threshold, label, direction, color):
        captured.update(threshold=threshold, label=label, direction=direction, color=color)
        return fig

    monkeypatch.setattr(viz_mod, "add_comparison_markers", fake_markers)
    monkeypatch.setattr(viz_mod, "fig_to_dict", lambda fig: {"thr": True})

    result = await add_chart_threshold_line(
        figure={"data": [], "layout": {}},
        threshold=4.5,
        label="EU avg",
        direction="below",
        color="#00ff00",
    )
    assert captured == {"threshold": 4.5, "label": "EU avg", "direction": "below", "color": "#00ff00"}
    assert result == {"thr": True}


async def test_add_chart_threshold_line_exception_wrapped(monkeypatch) -> None:
    monkeypatch.setattr(viz_mod, "add_comparison_markers", _boom)
    with pytest.raises(ToolError, match="Threshold line failed: bad"):
        await add_chart_threshold_line(figure={"data": [], "layout": {}}, threshold=1.0)


# ---------------------------------------------------------------------------
# create_data_table
# ---------------------------------------------------------------------------


async def test_create_data_table_empty_raises() -> None:
    with pytest.raises(ToolError, match="No data to create table"):
        await create_data_table(data=[])


async def test_create_data_table_writes_html_and_returns_envelope(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(viz_mod, "data_table_html", lambda data, **k: "<table>HTML</table>")
    monkeypatch.setattr(viz_mod, "data_table_css", lambda: "/*css*/")

    data = [{"region": "BG", "gdp": 100}, {"region": "NS", "gdp": 50}]
    result = await create_data_table(
        data,
        columns=["region", "gdp"],
        title="GDP",
        caption="cap",
        highlight_column="gdp",
        filename="tbl_out",
        max_rows=1,
    )

    assert result == {
        "filepath": str(sandbox_export_dir / "tbl_out.html"),
        "title": "GDP",
        "rows": 1,  # min(len(data), max_rows) = min(2, 1)
        "total_rows": 2,
        "columns": ["region", "gdp"],
    }
    written = (sandbox_export_dir / "tbl_out.html").read_text(encoding="utf-8")
    assert "<table>HTML</table>" in written
    assert "/*css*/" in written


async def test_create_data_table_auto_detects_columns(monkeypatch, sandbox_export_dir) -> None:
    """columns=[] must fall back to the keys of the first row."""
    monkeypatch.setattr(viz_mod, "data_table_html", lambda data, **k: "<table/>")
    monkeypatch.setattr(viz_mod, "data_table_css", lambda: "")
    result = await create_data_table([{"a": 1, "b": 2}], columns=[])
    assert result["columns"] == ["a", "b"]


async def test_create_data_table_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    def boom(*a, **k):
        raise ValueError("css fail")

    monkeypatch.setattr(viz_mod, "data_table_html", boom)
    with pytest.raises(ToolError, match="Data table failed: css fail"):
        await create_data_table([{"a": 1}], filename="fail")
