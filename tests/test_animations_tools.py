"""Offline unit tests for tools/animations.py — animated chart + scrollytelling tools.

Covers ``create_animated_chart`` and ``create_scrollytelling_story`` which shipped
with zero direct test coverage. The viz-layer functions
(animated_bars_evolution, animated_timeline, animated_comparison, apply_theme,
export_html, scrollytelling) are faked at the module-attribute seam, and
``config.export_dir`` is redirected to a tmp dir so the HTML write is real but
sandboxed — fully deterministic, no network, no plotly rendering.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp.exceptions import ToolError

from serbian_data_mcp.tools import animations as animations_mod
from serbian_data_mcp.tools.animations import (
    create_animated_chart,
    create_scrollytelling_story,
)


class _Sentinel:
    """Stand-in Plotly figure so pass-through is traceable without plotly."""

    def __init__(self, tag: str = "fig") -> None:
        self.tag = tag


@pytest.fixture
def sandbox_export_dir(monkeypatch, tmp_path):
    """Redirect config.export_dir to a tmp dir so _save_html writes are sandboxed.

    export_dir is a property on the Config class, so the property descriptor on
    the class is replaced (monkeypatch restores it after the test).
    """
    monkeypatch.setattr(
        type(animations_mod.config),
        "export_dir",
        property(lambda self: tmp_path),
    )
    return tmp_path


# ---------------------------------------------------------------------------
# create_animated_chart — input validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_animated_chart_invalid_type_raises(sandbox_export_dir) -> None:
    with pytest.raises(ToolError, match="Invalid type"):
        await create_animated_chart(animation_type="bogus", data=[{"t": 1}])


@pytest.mark.asyncio
async def test_create_animated_chart_no_data_raises_failed_to_create(monkeypatch, sandbox_export_dir) -> None:
    """bars_evolution with empty data leaves fig None → ToolError 'Failed to create'."""
    monkeypatch.setattr(animations_mod, "animated_bars_evolution", lambda *a, **k: _Sentinel())

    with pytest.raises(ToolError, match=r"Failed to create bars_evolution"):
        await create_animated_chart(animation_type="bars_evolution", data=[])


# ---------------------------------------------------------------------------
# create_animated_chart — per-branch success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_animated_chart_bars_evolution_writes_html_and_returns(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}

    def fake_bars(data, **kwargs):
        captured["args"] = (data, kwargs)
        return _Sentinel("bars")

    monkeypatch.setattr(animations_mod, "animated_bars_evolution", fake_bars)
    monkeypatch.setattr(animations_mod, "apply_theme", lambda fig, theme: fig)
    monkeypatch.setattr(animations_mod, "export_html", lambda fig: "<html>BARS</html>")

    result = await create_animated_chart(
        animation_type="bars_evolution",
        data=[{"t": 1, "c": "BG", "v": 10}],
        time_column="t",
        category_column="c",
        value_column="v",
        title="Pop",
        theme="dark",
        filename="bars_out",
    )

    data_arg, kwargs = captured["args"]
    assert data_arg == [{"t": 1, "c": "BG", "v": 10}]
    assert kwargs == {
        "time_column": "t",
        "category_column": "c",
        "value_column": "v",
        "title": "Pop",
        "theme": "dark",
    }
    assert result == {
        "filepath": str(sandbox_export_dir / "bars_out.html"),
        "animation_type": "bars_evolution",
        "title": "Pop",
    }
    written = (sandbox_export_dir / "bars_out.html").read_text(encoding="utf-8")
    assert written == "<html>BARS</html>"


@pytest.mark.asyncio
async def test_create_animated_chart_timeline_branch(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}

    def fake_timeline(data, **kwargs):
        captured["kwargs"] = kwargs
        return _Sentinel("timeline")

    monkeypatch.setattr(animations_mod, "animated_timeline", fake_timeline)
    monkeypatch.setattr(animations_mod, "apply_theme", lambda fig, theme: fig)
    monkeypatch.setattr(animations_mod, "export_html", lambda fig: "<html>TL</html>")

    result = await create_animated_chart(
        animation_type="timeline",
        data=[{"t": 1}],
        filename="tl_out",
        title="T",
    )

    assert result["animation_type"] == "timeline"
    assert captured["kwargs"]["title"] == "T"
    assert (sandbox_export_dir / "tl_out.html").exists()


@pytest.mark.asyncio
async def test_create_animated_chart_comparison_branch(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}

    def fake_comparison(datasets, **kwargs):
        captured["datasets"] = datasets
        captured["kwargs"] = kwargs
        return _Sentinel("cmp")

    monkeypatch.setattr(animations_mod, "animated_comparison", fake_comparison)
    monkeypatch.setattr(animations_mod, "apply_theme", lambda fig, theme: fig)
    monkeypatch.setattr(animations_mod, "export_html", lambda fig: "<html>CMP</html>")

    datasets = {"a": [{"x": 1}], "b": [{"x": 2}]}
    result = await create_animated_chart(
        animation_type="comparison",
        datasets=datasets,
        category_column="c",
        value_column="v",
        filename="cmp_out",
    )

    assert result["animation_type"] == "comparison"
    assert captured["datasets"] == datasets
    assert captured["kwargs"]["category_column"] == "c"
    assert (sandbox_export_dir / "cmp_out.html").exists()


@pytest.mark.asyncio
async def test_create_animated_chart_apply_theme_receives_theme(monkeypatch, sandbox_export_dir) -> None:
    """apply_theme must be called with the user-supplied theme."""
    monkeypatch.setattr(animations_mod, "animated_bars_evolution", lambda *a, **k: _Sentinel())
    theme_seen: dict[str, Any] = {}
    monkeypatch.setattr(
        animations_mod,
        "apply_theme",
        lambda fig, theme: theme_seen.setdefault("theme", theme) or fig,
    )
    monkeypatch.setattr(animations_mod, "export_html", lambda fig: "x")

    await create_animated_chart(
        animation_type="bars_evolution",
        data=[{"t": 1}],
        theme="light",
        filename="themed",
    )

    assert theme_seen["theme"] == "light"


# ---------------------------------------------------------------------------
# create_animated_chart — viz-layer failure wrapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_animated_chart_viz_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    def boom(*a, **k):
        raise ValueError("nope")

    monkeypatch.setattr(animations_mod, "animated_bars_evolution", boom)

    with pytest.raises(ToolError, match=r"Animated chart failed: nope"):
        await create_animated_chart(animation_type="bars_evolution", data=[{"t": 1}])


# ---------------------------------------------------------------------------
# create_scrollytelling_story
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_scrollytelling_story_success(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}

    def fake_scrollytelling(steps, *, title, subtitle, byline, theme, output_path):
        captured["steps"] = steps
        captured["title"] = title
        captured["output_path"] = output_path
        # Emulate the real fn: write the file and return its path.
        output_path.write_text("<html>STORY</html>", encoding="utf-8")
        return output_path

    monkeypatch.setattr(animations_mod, "scrollytelling", fake_scrollytelling)

    steps = [{"headline": "H1", "text": "T1"}, {"headline": "H2", "text": "T2"}]
    result = await create_scrollytelling_story(
        steps,
        title="My Story",
        subtitle="sub",
        byline="me",
        theme="light",
        filename="story_out",
    )

    assert result["step_count"] == 2
    assert result["title"] == "My Story"
    assert result["filepath"] == captured["output_path"]
    # Steps pass through unchanged when no chart dict is present.
    assert captured["steps"][0]["headline"] == "H1"
    assert captured["title"] == "My Story"
    assert (sandbox_export_dir / "story_out.html").read_text(encoding="utf-8") == "<html>STORY</html>"


@pytest.mark.asyncio
async def test_create_scrollytelling_story_converts_chart_dict_to_figure(monkeypatch, sandbox_export_dir) -> None:
    """A step carrying a Plotly figure dict must be converted to a Figure object."""
    from plotly.graph_objects import Figure

    captured: dict[str, Any] = {}

    def fake_scrollytelling(steps, *, title, subtitle, byline, theme, output_path):
        captured["chart"] = steps[0]["chart"]
        output_path.write_text("x", encoding="utf-8")
        return output_path

    monkeypatch.setattr(animations_mod, "scrollytelling", fake_scrollytelling)

    chart_dict = {"data": [{"type": "bar", "x": [1], "y": [2]}], "layout": {"title": "T"}}
    await create_scrollytelling_story(
        [{"headline": "H", "chart": chart_dict}],
        filename="with_chart",
    )

    assert isinstance(captured["chart"], Figure)


@pytest.mark.asyncio
async def test_create_scrollytelling_story_failure_wrapped(monkeypatch, sandbox_export_dir) -> None:
    def boom(*a, **k):
        raise RuntimeError("broken")

    monkeypatch.setattr(animations_mod, "scrollytelling", boom)

    with pytest.raises(ToolError, match=r"Scrollytelling failed: broken"):
        await create_scrollytelling_story([{"headline": "H"}], filename="fail_out")
