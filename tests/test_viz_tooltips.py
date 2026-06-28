"""Offline deterministic tests for viz/tooltips.py.

Covers the two pure formatting helpers (_fmt_num, _fmt_delta) plus the three
figure-enrichment functions (add_rich_tooltips, add_annotation_callouts,
add_comparison_markers) which operate on real plotly figures whose attributes
are directly inspectable — no network, no file writes, no theme/export coupling.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from serbian_data_mcp.viz.tooltips import (
    _fmt_delta,
    _fmt_num,
    add_annotation_callouts,
    add_comparison_markers,
    add_rich_tooltips,
)

# -- _fmt_num -----------------------------------------------------------------


def test_fmt_num_tiny_nonzero_shows_four_decimals() -> None:
    """abs<0.01 and !=0 → 4-decimal string."""
    assert _fmt_num(0.001) == "0.0010"


def test_fmt_num_zero_falls_through_to_percent_branch() -> None:
    """0 is not <0.01-and-!=0, but IS <1 → percent branch ('0.0%')."""
    assert _fmt_num(0) == "0.0%"


def test_fmt_num_subunit_fraction_shows_percent() -> None:
    """0<abs<1 → percent form."""
    assert _fmt_num(0.15) == "15.0%"


def test_fmt_num_exactly_one_uses_default_format() -> None:
    """1 is not <1 → falls to default '{:.1f}' (not a percent)."""
    assert _fmt_num(1) == "1.0"


def test_fmt_num_millions_suffix() -> None:
    """abs>=1_000_000 → 'M' suffix."""
    assert _fmt_num(2_500_000) == "2.5M"


def test_fmt_num_thousands_suffix() -> None:
    """1_000<=abs<1_000_000 → 'K' suffix."""
    assert _fmt_num(12_500) == "12.5K"


def test_fmt_num_small_whole_uses_default_format() -> None:
    """Plain small number → default one-decimal."""
    assert _fmt_num(42) == "42.0"


# -- _fmt_delta ---------------------------------------------------------------


def test_fmt_delta_positive_up_triangle_green() -> None:
    """value>0 → ▲ + green (#4caf50)."""
    out = _fmt_delta(5)
    assert "▲" in out
    assert "#4caf50" in out


def test_fmt_delta_negative_down_triangle_red() -> None:
    """value<0 → ▼ + red (#f44336)."""
    out = _fmt_delta(-3)
    assert "▼" in out
    assert "#f44336" in out


def test_fmt_delta_zero_neutral_grey_dot() -> None:
    """value==0 → ● + grey (#9e9e9e)."""
    out = _fmt_delta(0)
    assert "●" in out
    assert "#9e9e9e" in out


# -- add_rich_tooltips --------------------------------------------------------


def _bar_fig(values: list[float]) -> go.Figure:
    """Minimal bar figure with a y-trace."""
    return go.Figure(data=[go.Bar(y=values)])


def test_rich_tooltips_empty_values_returns_fig_unchanged() -> None:
    """No z/y values → returns fig without setting a hovertemplate."""
    fig = go.Figure(data=[go.Bar(y=[np.nan])])
    out = add_rich_tooltips(fig)
    assert out is fig
    assert fig.data[0].hovertemplate is None


def test_rich_tooltips_injects_mean_rank_delta_into_existing_extra() -> None:
    """Existing template with <extra> gets extra lines injected before <extra>."""
    fig = go.Figure(data=[go.Bar(y=[10.0, 20.0, 30.0])])
    fig.data[0].hovertemplate = "<b>%{x}</b><br>%{y}<extra></extra>"
    add_rich_tooltips(fig, base_column="base", unit=" u")
    tmpl = fig.data[0].hovertemplate
    assert tmpl is not None
    assert "Prosečno:" in tmpl
    assert " u" in tmpl
    assert "Rank:" in tmpl
    assert "Promena:" in tmpl
    assert tmpl.endswith("<extra></extra>")


def test_rich_tooltips_appends_extra_when_no_extra_tag() -> None:
    """Existing template lacking <extra> gets a fresh <extra></extra> appended."""
    fig = _bar_fig([1.0, 2.0])
    fig.data[0].hovertemplate = "custom-template"
    add_rich_tooltips(fig)
    tmpl = fig.data[0].hovertemplate
    assert tmpl is not None
    assert tmpl.startswith("custom-template<br>")
    assert tmpl.endswith("<extra></extra>")


def test_rich_tooltips_uses_default_template_when_none() -> None:
    """No existing hovertemplate → default '<b>%{x}</b>...' baseline is used."""
    fig = _bar_fig([5.0, 15.0])
    add_rich_tooltips(fig)
    tmpl = fig.data[0].hovertemplate
    assert tmpl is not None
    assert "<b>%{x}</b>" in tmpl
    assert "Prosečno:" in tmpl


def test_rich_tooltips_custom_fmt_fn_applied() -> None:
    """fmt_fn override is used for the mean line instead of _fmt_num."""
    fig = _bar_fig([10.0, 20.0])
    add_rich_tooltips(fig, fmt_fn=lambda _v: "ZZZ")
    assert "Prosečno: ZZZ" in (fig.data[0].hovertemplate or "")


def test_rich_tooltips_disabled_flags_skip_lines() -> None:
    """show_mean/show_rank/show_delta all off → no extra lines, template untouched."""
    fig = _bar_fig([10.0, 20.0])
    fig.data[0].hovertemplate = "keep-me"
    add_rich_tooltips(fig, show_mean=False, show_rank=False, show_delta=False)
    assert fig.data[0].hovertemplate == "keep-me"


def test_rich_tooltips_rank_customdata_built_and_indexed() -> None:
    """show_rank populates customdata with '#k od N' rank strings, 1-indexed."""
    fig = _bar_fig([30.0, 10.0, 20.0])
    add_rich_tooltips(fig, show_mean=False, show_delta=False)
    cd = fig.data[0].customdata
    assert cd is not None
    flat = [row[0] for row in cd]
    # 30 is rank #1, 10 is rank #3, 20 is rank #2; sorted desc
    assert "#1 od 3" in flat[0]
    assert "#3 od 3" in flat[1]
    assert "#2 od 3" in flat[2]


def test_rich_tooltips_rank_skipped_without_y_trace() -> None:
    """A z-backed trace (no y) → customdata rank branch is skipped, still enriches template."""
    fig = go.Figure(data=[go.Heatmap(z=[[1.0, 2.0], [3.0, 4.0]])])
    add_rich_tooltips(fig)
    # template still enriched via mean line
    assert "Prosečno:" in (fig.data[0].hovertemplate or "")
    # customdata not set (no y-trace path)
    assert fig.data[0].customdata is None


def test_rich_tooltips_nan_y_value_emits_blank_rank() -> None:
    """A NaN entry in the y-trace → its rank slot is '' (skipped, not indexed)."""
    fig = go.Figure(data=[go.Bar(y=[10.0, float("nan"), 20.0])])
    add_rich_tooltips(fig, show_mean=False, show_delta=False)
    cd = fig.data[0].customdata
    assert cd is not None
    flat = [row[0] for row in cd]
    assert flat[1] == ""  # NaN slot blank
    assert "#1 od 2" in flat[2]  # 20 ranks #1 among the 2 non-NaN values


# -- add_annotation_callouts --------------------------------------------------


def test_annotation_callouts_adds_one_annotation_per_point() -> None:
    """Each point dict → one annotation on the figure with x/y/text set."""
    fig = go.Figure(data=[go.Scatter(x=[0, 1], y=[0, 1])])
    out = add_annotation_callouts(
        fig,
        points=[
            {"x": 0, "y": 0, "text": "first"},
            {"x": 1, "y": 1, "text": "second", "color": "#abcdef"},
        ],
    )
    assert out is fig
    assert len(fig.layout.annotations) == 2
    ann = fig.layout.annotations[0]
    assert ann.x == 0
    assert ann.y == 0
    assert "first" in ann.text
    assert fig.layout.annotations[1].bgcolor == "#abcdef"


def test_annotation_callouts_prefix_suffix_and_offset_defaults() -> None:
    """prefix/suffix wrap text; ax/ay default to 0/-40; default bgcolor #1565c0."""
    fig = go.Figure(data=[go.Scatter(x=[0], y=[0])])
    add_annotation_callouts(fig, points=[{"x": 5, "y": 5, "text": "T"}], prefix="[", suffix="]")
    ann = fig.layout.annotations[0]
    assert ann.text == "[T]"
    assert ann.bgcolor == "#1565c0"
    assert ann.ax == 0
    assert ann.ay == -40


def test_annotation_callouts_respects_custom_ax_ay() -> None:
    """Explicit ax/ay in point dict override the -40/0 defaults."""
    fig = go.Figure(data=[go.Scatter(x=[0], y=[0])])
    add_annotation_callouts(fig, points=[{"x": 0, "y": 0, "text": "t", "ax": 20, "ay": 40}])
    ann = fig.layout.annotations[0]
    assert ann.ax == 20
    assert ann.ay == 40


def test_annotation_callouts_empty_points_noop() -> None:
    """No points → no annotations added."""
    fig = go.Figure(data=[go.Scatter(x=[0], y=[0])])
    add_annotation_callouts(fig, points=[])
    assert len(fig.layout.annotations) == 0


# -- add_comparison_markers ---------------------------------------------------


def test_comparison_markers_above_direction_adds_hline_with_label() -> None:
    """direction='above' + label → dashed hline shape + label annotation."""
    fig = go.Figure(data=[go.Scatter(x=[0, 1], y=[0, 2])])
    out = add_comparison_markers(fig, threshold=1.5, label="target", direction="above")
    assert out is fig
    assert len(fig.layout.shapes) == 1
    shape = fig.layout.shapes[0]
    assert shape.line.dash == "dash"
    assert shape.line.color == "#ffab00"
    assert shape.y0 == 1.5
    # label rendered as an annotation
    assert any(a.text == "target" for a in fig.layout.annotations)


def test_comparison_markers_below_direction_uses_top_right_position() -> None:
    """direction='below' → label still added (top-right positioning variant)."""
    fig = go.Figure(data=[go.Scatter(x=[0], y=[0])])
    add_comparison_markers(fig, threshold=0.5, label="t", direction="below")
    assert len(fig.layout.shapes) == 1
    assert any(a.text == "t" for a in fig.layout.annotations)


def test_comparison_markers_empty_label_does_not_crash() -> None:
    """Empty label → hline added, NO annotation (regression: used to ValueError)."""
    fig = go.Figure(data=[go.Scatter(x=[0], y=[0])])
    add_comparison_markers(fig, threshold=1.0, label="")
    assert len(fig.layout.shapes) == 1
    assert len(fig.layout.annotations) == 0
