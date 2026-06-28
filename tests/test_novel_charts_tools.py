"""Offline unit tests for tools/novel_charts.py — specialized chart tools.

Covers all 8 MCP tools (create_arrow_chart, create_dumbbell_chart,
create_lollipop_chart, create_slope_chart, create_waffle_chart,
create_population_pyramid, create_sankey_diagram, create_radar_chart) which
shipped with zero direct test coverage. The viz-layer functions
(arrow_chart, dumbbell_chart, lollipop_chart, slope_chart, waffle_chart,
population_pyramid, sankey_diagram, radar_chart, export_html) are faked at the
module-attribute seam, and ``config.export_dir`` is redirected to a tmp dir so
the HTML write is real but sandboxed — fully deterministic, no network, no
plotly rendering.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp.exceptions import ToolError

from serbian_data_mcp.tools import novel_charts as novel_mod
from serbian_data_mcp.tools.novel_charts import (
    create_arrow_chart,
    create_dumbbell_chart,
    create_lollipop_chart,
    create_population_pyramid,
    create_radar_chart,
    create_sankey_diagram,
    create_slope_chart,
    create_waffle_chart,
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
        type(novel_mod.config),
        "export_dir",
        property(lambda self: tmp_path),
    )
    return tmp_path


def _wire_export_html(monkeypatch, body: str = "<html>X</html>") -> None:
    """Patch export_html at the module-attribute seam."""
    monkeypatch.setattr(novel_mod, "export_html", lambda fig: body)


# ---------------------------------------------------------------------------
# create_arrow_chart
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_arrow_chart_success(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}

    def fake_arrow(data, *, label_column, value_column, title, theme, reference_value):
        captured["data"] = data
        captured["kwargs"] = {
            "label_column": label_column,
            "value_column": value_column,
            "title": title,
            "theme": theme,
            "reference_value": reference_value,
        }
        return _Sentinel("arrow")

    monkeypatch.setattr(novel_mod, "arrow_chart", fake_arrow)
    _wire_export_html(monkeypatch, "<html>ARROW</html>")

    rows = [{"label": "A", "change": 5}, {"label": "B", "change": -3}]
    result = await create_arrow_chart(
        rows,
        label_column="label",
        value_column="change",
        title="Shifts",
        theme="light",
        reference_value=0,
        filename="arrow_out",
    )

    assert captured["data"] == rows
    assert captured["kwargs"] == {
        "label_column": "label",
        "value_column": "change",
        "title": "Shifts",
        "theme": "light",
        "reference_value": 0,
    }
    assert result == {
        "filepath": str(sandbox_export_dir / "arrow_out.html"),
        "title": "Shifts",
        "rows": 2,
    }
    assert (sandbox_export_dir / "arrow_out.html").read_text(encoding="utf-8") == "<html>ARROW</html>"


@pytest.mark.asyncio
async def test_create_arrow_chart_default_reference_none(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        novel_mod,
        "arrow_chart",
        lambda data, **k: captured.setdefault("k", k) or _Sentinel(),
    )
    _wire_export_html(monkeypatch)

    await create_arrow_chart([{"l": "x", "v": 1}], label_column="l", value_column="v")

    assert captured["k"]["reference_value"] is None
    assert captured["k"]["theme"] == "dark"


@pytest.mark.asyncio
async def test_create_arrow_chart_viz_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(novel_mod, "arrow_chart", lambda *a, **k: (_ for _ in ()).throw(ValueError("boom")))
    with pytest.raises(ToolError, match=r"Arrow chart failed: boom"):
        await create_arrow_chart([{"l": "x", "v": 1}], label_column="l", value_column="v")


# ---------------------------------------------------------------------------
# create_dumbbell_chart
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_dumbbell_chart_success(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}

    def fake_dumbbell(data, *, label_column, start_column, end_column, title, theme):
        captured.update(label_column=label_column, start_column=start_column, end_column=end_column)
        captured["title"] = title
        captured["theme"] = theme
        return _Sentinel("dumbbell")

    monkeypatch.setattr(novel_mod, "dumbbell_chart", fake_dumbbell)
    _wire_export_html(monkeypatch, "<html>DB</html>")

    rows = [{"c": "BG", "a": 100, "b": 120}]
    result = await create_dumbbell_chart(
        rows,
        label_column="c",
        start_column="a",
        end_column="b",
        title="Before/After",
        filename="db_out",
    )

    assert captured == {
        "label_column": "c",
        "start_column": "a",
        "end_column": "b",
        "title": "Before/After",
        "theme": "dark",
    }
    assert result == {
        "filepath": str(sandbox_export_dir / "db_out.html"),
        "title": "Before/After",
        "rows": 1,
    }


@pytest.mark.asyncio
async def test_create_dumbbell_chart_viz_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    def boom(*a, **k):
        raise RuntimeError("nope")

    monkeypatch.setattr(novel_mod, "dumbbell_chart", boom)
    with pytest.raises(ToolError, match=r"Dumbbell chart failed: nope"):
        await create_dumbbell_chart([{"c": "x", "a": 1, "b": 2}], label_column="c", start_column="a", end_column="b")


# ---------------------------------------------------------------------------
# create_lollipop_chart
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_lollipop_chart_success(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}

    def fake_lollipop(data, *, label_column, value_column, title, theme, highlight_column, highlight_value):
        captured["highlight_column"] = highlight_column
        captured["highlight_value"] = highlight_value
        return _Sentinel("lollipop")

    monkeypatch.setattr(novel_mod, "lollipop_chart", fake_lollipop)
    _wire_export_html(monkeypatch)

    rows = [{"d": "BG", "pop": 100}, {"d": "NS", "pop": 80}]
    result = await create_lollipop_chart(
        rows,
        label_column="d",
        value_column="pop",
        title="Ranking",
        highlight_column="d",
        highlight_value="BG",
        filename="lol_out",
    )

    assert captured == {"highlight_column": "d", "highlight_value": "BG"}
    assert result == {
        "filepath": str(sandbox_export_dir / "lol_out.html"),
        "title": "Ranking",
        "rows": 2,
    }


@pytest.mark.asyncio
async def test_create_lollipop_chart_default_no_highlight(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        novel_mod,
        "lollipop_chart",
        lambda data, **k: captured.setdefault("k", k) or _Sentinel(),
    )
    _wire_export_html(monkeypatch)

    await create_lollipop_chart([{"d": "x", "pop": 1}], label_column="d", value_column="pop")

    assert captured["k"]["highlight_column"] is None
    assert captured["k"]["highlight_value"] is None


@pytest.mark.asyncio
async def test_create_lollipop_chart_viz_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    def boom(*a, **k):
        raise ValueError("bad")

    monkeypatch.setattr(novel_mod, "lollipop_chart", boom)
    with pytest.raises(ToolError, match=r"Lollipop chart failed: bad"):
        await create_lollipop_chart([{"d": "x", "pop": 1}], label_column="d", value_column="pop")


# ---------------------------------------------------------------------------
# create_slope_chart
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_slope_chart_success(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}

    def fake_slope(data, entity_column, start_column, end_column, *, title, theme, top_n):
        captured["positional"] = (entity_column, start_column, end_column)
        captured["kwargs"] = {"title": title, "theme": theme, "top_n": top_n}
        return _Sentinel("slope")

    monkeypatch.setattr(novel_mod, "slope_chart", fake_slope)
    _wire_export_html(monkeypatch, "<html>SLOPE</html>")

    rows = [{"e": "BG", "s": 10, "f": 20}]
    result = await create_slope_chart(
        rows,
        entity_column="e",
        start_column="s",
        end_column="f",
        title="Shifts",
        top_n=5,
        filename="slope_out",
    )

    assert captured["positional"] == ("e", "s", "f")
    assert captured["kwargs"] == {"title": "Shifts", "theme": "dark", "top_n": 5}
    assert result == {
        "filepath": str(sandbox_export_dir / "slope_out.html"),
        "title": "Shifts",
        "rows": 1,
    }


@pytest.mark.asyncio
async def test_create_slope_chart_default_top_n(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        novel_mod,
        "slope_chart",
        lambda *a, **k: captured.setdefault("k", k) or _Sentinel(),
    )
    _wire_export_html(monkeypatch)

    await create_slope_chart([{"e": "x", "s": 1, "f": 2}], entity_column="e", start_column="s", end_column="f")

    assert captured["k"]["top_n"] == 15


@pytest.mark.asyncio
async def test_create_slope_chart_viz_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    def boom(*a, **k):
        raise ValueError("x")

    monkeypatch.setattr(novel_mod, "slope_chart", boom)
    with pytest.raises(ToolError, match=r"Slope chart failed: x"):
        await create_slope_chart([{"e": "x", "s": 1, "f": 2}], entity_column="e", start_column="s", end_column="f")


# ---------------------------------------------------------------------------
# create_waffle_chart
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_waffle_chart_success(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}

    def fake_waffle(data, names_column, values_column, *, title, theme, total_icons):
        captured["positional"] = (names_column, values_column)
        captured["kwargs"] = {"title": title, "theme": theme, "total_icons": total_icons}
        return _Sentinel("waffle")

    monkeypatch.setattr(novel_mod, "waffle_chart", fake_waffle)
    _wire_export_html(monkeypatch, "<html>WAFFLE</html>")

    rows = [{"n": "A", "v": 25}, {"n": "B", "v": 75}]
    result = await create_waffle_chart(
        rows,
        names_column="n",
        values_column="v",
        title="Share",
        total_icons=200,
        filename="waffle_out",
    )

    assert captured["positional"] == ("n", "v")
    assert captured["kwargs"] == {"title": "Share", "theme": "dark", "total_icons": 200}
    assert result == {
        "filepath": str(sandbox_export_dir / "waffle_out.html"),
        "title": "Share",
        "categories": 2,
    }
    assert (sandbox_export_dir / "waffle_out.html").read_text(encoding="utf-8") == "<html>WAFFLE</html>"


@pytest.mark.asyncio
async def test_create_waffle_chart_viz_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    def boom(*a, **k):
        raise ValueError("nope")

    monkeypatch.setattr(novel_mod, "waffle_chart", boom)
    with pytest.raises(ToolError, match=r"Waffle chart failed: nope"):
        await create_waffle_chart([{"n": "x", "v": 1}], names_column="n", values_column="v")


# ---------------------------------------------------------------------------
# create_population_pyramid
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_population_pyramid_success(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}

    def fake_pyramid(data, age_column, male_column, female_column, *, title, theme):
        captured["positional"] = (age_column, male_column, female_column)
        captured["kwargs"] = {"title": title, "theme": theme}
        return _Sentinel("pyramid")

    monkeypatch.setattr(novel_mod, "population_pyramid", fake_pyramid)
    _wire_export_html(monkeypatch)

    rows = [{"age": "0-4", "m": 100, "f": 95}, {"age": "5-9", "m": 90, "f": 88}]
    result = await create_population_pyramid(
        rows,
        age_column="age",
        male_column="m",
        female_column="f",
        title="Demographics",
        filename="pyr_out",
    )

    assert captured["positional"] == ("age", "m", "f")
    assert captured["kwargs"] == {"title": "Demographics", "theme": "dark"}
    assert result == {
        "filepath": str(sandbox_export_dir / "pyr_out.html"),
        "title": "Demographics",
        "age_groups": 2,
    }


@pytest.mark.asyncio
async def test_create_population_pyramid_viz_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    def boom(*a, **k):
        raise ValueError("bad")

    monkeypatch.setattr(novel_mod, "population_pyramid", boom)
    with pytest.raises(ToolError, match=r"Population pyramid failed: bad"):
        await create_population_pyramid(
            [{"age": "x", "m": 1, "f": 2}],
            age_column="age",
            male_column="m",
            female_column="f",
        )


# ---------------------------------------------------------------------------
# create_sankey_diagram
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_sankey_diagram_success(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}

    def fake_sankey(data, source_column, target_column, value_column, *, title, theme):
        captured["positional"] = (source_column, target_column, value_column)
        captured["kwargs"] = {"title": title, "theme": theme}
        return _Sentinel("sankey")

    monkeypatch.setattr(novel_mod, "sankey_diagram", fake_sankey)
    _wire_export_html(monkeypatch, "<html>SANKEY</html>")

    rows = [{"src": "rev", "dst": "edu", "v": 50}, {"src": "edu", "dst": "schools", "v": 30}]
    result = await create_sankey_diagram(
        rows,
        source_column="src",
        target_column="dst",
        value_column="v",
        title="Flow",
        filename="sankey_out",
    )

    assert captured["positional"] == ("src", "dst", "v")
    assert captured["kwargs"] == {"title": "Flow", "theme": "dark"}
    assert result == {
        "filepath": str(sandbox_export_dir / "sankey_out.html"),
        "title": "Flow",
        "flows": 2,
    }
    assert (sandbox_export_dir / "sankey_out.html").read_text(encoding="utf-8") == "<html>SANKEY</html>"


@pytest.mark.asyncio
async def test_create_sankey_diagram_viz_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    def boom(*a, **k):
        raise RuntimeError("x")

    monkeypatch.setattr(novel_mod, "sankey_diagram", boom)
    with pytest.raises(ToolError, match=r"Sankey diagram failed: x"):
        await create_sankey_diagram(
            [{"src": "a", "dst": "b", "v": 1}],
            source_column="src",
            target_column="dst",
            value_column="v",
        )


# ---------------------------------------------------------------------------
# create_radar_chart
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_radar_chart_success(monkeypatch, sandbox_export_dir) -> None:
    captured: dict[str, Any] = {}

    def fake_radar(data, category_column, value_columns, *, title, theme):
        captured["positional"] = (category_column, value_columns)
        captured["kwargs"] = {"title": title, "theme": theme}
        return _Sentinel("radar")

    monkeypatch.setattr(novel_mod, "radar_chart", fake_radar)
    _wire_export_html(monkeypatch, "<html>RADAR</html>")

    rows = [{"e": "BG", "pop": 100, "bud": 50}, {"e": "NS", "pop": 80, "bud": 40}]
    result = await create_radar_chart(
        rows,
        category_column="e",
        value_columns=["pop", "bud"],
        title="Compare",
        filename="radar_out",
    )

    assert captured["positional"] == ("e", ["pop", "bud"])
    assert captured["kwargs"] == {"title": "Compare", "theme": "dark"}
    assert result == {
        "filepath": str(sandbox_export_dir / "radar_out.html"),
        "title": "Compare",
        "entities": 2,
        "metrics": 2,
    }
    assert (sandbox_export_dir / "radar_out.html").read_text(encoding="utf-8") == "<html>RADAR</html>"


@pytest.mark.asyncio
async def test_create_radar_chart_viz_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    def boom(*a, **k):
        raise ValueError("z")

    monkeypatch.setattr(novel_mod, "radar_chart", boom)
    with pytest.raises(ToolError, match=r"Radar chart failed: z"):
        await create_radar_chart([{"e": "x", "pop": 1}], category_column="e", value_columns=["pop"])
