"""Offline deterministic tests for viz/scrollytelling.py.

Covers _generate_id and the scrollytelling HTML-story builder. The builder is a
pure string generator (writes a file only when output_path is given) with no
network, plotly rendering, or theme/export_dir coupling — assertions are plain
substring / regex reads against the returned HTML string.
"""

from __future__ import annotations

import re
from pathlib import Path

import plotly.graph_objects as go
import pytest

from serbian_data_mcp.viz.scrollytelling import _generate_id, scrollytelling


# -- helpers ------------------------------------------------------------------


def _story_id(html: str) -> str:
    """Extract the random story_id injected into progress-bar element id."""
    m = re.search(r"id=\"progress-([0-9a-f]{8})\"", html)
    assert m, "progress-bar id pattern not found"
    return m.group(1)


# -- _generate_id -------------------------------------------------------------


def test_generate_id_is_eight_hex_chars() -> None:
    assert re.fullmatch(r"[0-9a-f]{8}", _generate_id()) is not None


def test_generate_id_is_unique_across_calls() -> None:
    ids = {_generate_id() for _ in range(50)}
    assert len(ids) == 50


# -- scrollytelling: document skeleton ---------------------------------------


def test_returns_html_document_with_title() -> None:
    html = scrollytelling(steps=[], title="Test Story")
    assert html.startswith("<!DOCTYPE html>")
    assert "<title>Test Story</title>" in html
    assert html.rstrip().endswith("</html>")


def test_story_id_injected_into_progress_bar_and_story_js() -> None:
    html = scrollytelling(steps=[], title="T")
    sid = _story_id(html)
    assert f"const storyId = '{sid}'" in html
    # two references to the id: the progress element and the JS const
    assert html.count(sid) >= 2


def test_subtitle_and_byline_omitted_when_empty() -> None:
    html = scrollytelling(steps=[], title="T")
    assert 'class="subtitle"' not in html
    assert 'class="byline"' not in html


def test_subtitle_rendered_when_provided() -> None:
    html = scrollytelling(steps=[], title="T", subtitle="The Deck")
    assert '<p class="subtitle">The Deck</p>' in html


def test_byline_rendered_when_provided() -> None:
    html = scrollytelling(steps=[], title="T", byline="Author Name")
    assert '<p class="byline">Author Name</p>' in html


def test_footer_is_constant_serbian_credit() -> None:
    html = scrollytelling(steps=[], title="T")
    assert "data.gov.rs" in html
    assert "Serbian Data MCP" in html


# -- theme color branches -----------------------------------------------------


def test_theme_dark_colors() -> None:
    html = scrollytelling(steps=[], title="T", theme="dark")
    assert "#0d1117" in html  # bg
    assert "#e6edf3" in html  # fg
    assert "#8b949e" in html  # muted
    assert "#30363d" in html  # border


def test_theme_light_colors() -> None:
    html = scrollytelling(steps=[], title="T", theme="light")
    assert "#ffffff" in html  # bg
    assert "#1f2937" in html  # fg
    assert "#6b7280" in html  # muted
    assert "#e5e7eb" in html  # border


def test_header_color_and_accent_color_interpolated() -> None:
    html = scrollytelling(
        steps=[], title="T", header_color="#112233", accent_color="#445566"
    )
    assert "#112233" in html
    assert "#445566" in html


# -- include_plotly -----------------------------------------------------------


def test_include_plotly_default_includes_cdn_script() -> None:
    html = scrollytelling(steps=[], title="T")
    assert "cdn.plot.ly/plotly" in html


def test_include_plotly_false_omits_cdn_script() -> None:
    html = scrollytelling(steps=[], title="T", include_plotly=False)
    assert "cdn.plot.ly/plotly" not in html


# -- narrative steps ----------------------------------------------------------


def test_narrative_step_contains_headline_and_text() -> None:
    steps = [{"headline": "Section One", "text": "Some <b>narrative</b>"}]
    html = scrollytelling(steps=steps, title="T")
    assert "Section One" in html
    assert "Some <b>narrative</b>" in html
    assert 'data-step="0"' in html


def test_narrative_step_defaults_empty_headline_text() -> None:
    """Steps without headline/text render empty slots, not KeyError."""
    html = scrollytelling(steps=[{}], title="T")
    assert 'data-step="0"' in html
    assert html.startswith("<!DOCTYPE html>")


def test_highlight_color_default_uses_accent() -> None:
    steps = [{}]  # no highlight_color → accent_color
    html = scrollytelling(steps=steps, title="T", accent_color="#abcdef")
    assert "#abcdef" in html


def test_highlight_color_custom_overrides_accent() -> None:
    steps = [{"highlight_color": "#ff0000"}]
    html = scrollytelling(steps=steps, title="T", accent_color="#abcdef")
    assert "#ff0000" in html


# -- chart steps --------------------------------------------------------------


def _bar_fig() -> go.Figure:
    return go.Figure(data=[go.Bar(x=["a", "b"], y=[1, 2])])


def test_chart_step_includes_div_and_plotly_init() -> None:
    sid_seed: dict[str, str] = {}

    steps = [{"headline": "H", "text": "x", "chart": _bar_fig()}]
    html = scrollytelling(steps=steps, title="T")
    sid = _story_id(html)
    sid_seed["sid"] = sid

    div_id = f"chart-{sid}-0"
    assert div_id in html  # to_html emitted the div
    assert "Plotly.newPlot" in html
    assert f"'{div_id}'" in html  # JS references it


def test_chart_step_serializes_figure_json_into_js() -> None:
    fig = _bar_fig()
    html = scrollytelling(steps=[{"chart": fig}], title="T")
    # the chart_json is injected inline next to Plotly.newPlot
    assert "Plotly.newPlot" in html
    # bar trace marker family appears in serialized layout/data
    assert '"type": "bar"' in html


def test_step_without_chart_skips_plotly_init() -> None:
    html = scrollytelling(steps=[{"headline": "H", "text": "x"}], title="T")
    assert "Plotly.newPlot" not in html


def test_step_without_chart_omits_chart_div() -> None:
    html = scrollytelling(steps=[{"headline": "H", "text": "x"}], title="T")
    assert "plotly-graph-div" not in html


# -- big number ---------------------------------------------------------------


def test_big_number_rendered_with_highlight_color() -> None:
    steps = [{"headline": "H", "text": "x", "big_number": "42", "highlight_color": "#00ff00"}]
    html = scrollytelling(steps=steps, title="T")
    assert '<div class="big-number" style="color: #00ff00">42</div>' in html


def test_big_number_label_rendered_when_present() -> None:
    steps = [{"headline": "H", "text": "x", "big_number_label": "percent"}]
    html = scrollytelling(steps=steps, title="T")
    assert '<div class="big-number-label">percent</div>' in html


def test_big_number_div_omitted_when_absent() -> None:
    """The CSS .big-number rule is always present, but the rendered div only
    appears when big_number is truthy."""
    steps = [{"headline": "H", "text": "x"}]
    html = scrollytelling(steps=steps, title="T")
    assert 'class="big-number" style=' not in html


# -- output_path file write ---------------------------------------------------


def test_output_path_writes_file_and_returns_path(tmp_path: Path) -> None:
    out = tmp_path / "sub" / "story.html"
    returned = scrollytelling(steps=[], title="T", output_path=out)
    assert returned == str(out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert content.startswith("<!DOCTYPE html>")
    assert "<title>T</title>" in content


def test_output_path_creates_missing_parent_dirs(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "deep" / "dir" / "story.html"
    scrollytelling(steps=[], title="T", output_path=out)
    assert out.exists()


# -- multi-step integration ---------------------------------------------------


def test_multi_step_story_renders_each_index() -> None:
    steps = [
        {"headline": "First", "text": "t1", "chart": _bar_fig()},
        {"headline": "Second", "text": "t2"},
        {"headline": "Third", "text": "t3", "big_number": "99"},
    ]
    html = scrollytelling(steps=steps, title="T")
    sid = _story_id(html)
    for i in range(3):
        assert f'data-step="{i}"' in html
    # only step 0 carries a chart → only its chart div id is emitted
    assert f"chart-{sid}-0" in html
    assert f"chart-{sid}-1" not in html
    assert f"chart-{sid}-2" not in html
    assert "First" in html and "Second" in html and "Third" in html
    assert ">99</div>" in html


def test_invalid_theme_falls_through_to_dark_branch() -> None:
    """Unknown theme string is not 'dark' but only dark/light branches exist;
    the function does not validate theme — any non-'dark' value yields light
    palette (is_dark=False)."""
    html = scrollytelling(steps=[], title="T", theme="nonsense")
    assert "#ffffff" in html  # light bg branch
    assert "#0d1117" not in html


def test_chart_json_default_serializer_handles_non_serializable() -> None:
    """chart_fig.to_dict() with a non-JSON-native value must not crash; the
    default=lambda _x: None serializer swallows it."""

    class _Opaque:
        pass

    fig = go.Figure(data=[go.Bar(x=["a"], y=[1])])
    # attach a non-serializable attr into the layout to exercise the default=
    fig.layout.template = _Opaque()  # type: ignore[assignment]
    html = scrollytelling(steps=[{"chart": fig}], title="T")
    assert "Plotly.newPlot" in html
