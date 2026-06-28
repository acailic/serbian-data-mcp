"""Offline unit tests for tools/charts_3d.py — 3D chart MCP tools.

Covers the three MCP tools (create_scatter_3d, create_line_3d,
create_surface_3d). ``Chart3DBuilder`` is faked at the module-attribute seam,
and ``config.export_dir`` is redirected to a tmp dir so the HTML write is real
but sandboxed — fully deterministic, no network, no plotly rendering. Mirrors
the pattern in test_novel_charts_tools.py.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp.exceptions import ToolError

from serbian_data_mcp.tools import charts_3d as charts3d_mod
from serbian_data_mcp.tools.charts_3d import (
    create_isosurface_3d,
    create_line_3d,
    create_mesh_3d,
    create_scatter_3d,
    create_surface_3d,
)


class _Sentinel:
    """Stand-in Plotly figure so pass-through is traceable without plotly."""

    def __init__(self, tag: str = "fig") -> None:
        self.tag = tag


# Module-level spy dict: the fake builder records the last method call here.
CALLS: dict[str, Any] = {}


@pytest.fixture
def sandbox_export_dir(monkeypatch, tmp_path):
    """Redirect config.export_dir to a tmp dir so _save_html writes are sandboxed."""
    monkeypatch.setattr(
        type(charts3d_mod.config),
        "export_dir",
        property(lambda self: tmp_path),
    )
    return tmp_path


def _wire_export_html(monkeypatch, body: str = "<html>X</html>") -> None:
    """Patch export_html at the module-attribute seam."""
    monkeypatch.setattr(charts3d_mod, "export_html", lambda fig: body)


def _make_method(name: str):
    """Build a fake Chart3DBuilder method that records its call + returns a sentinel."""

    def _impl(self, x, y, z, **kwargs):
        CALLS["method"] = name
        CALLS["x"] = x
        CALLS["y"] = y
        CALLS["z"] = z
        CALLS["kwargs"] = kwargs
        return _Sentinel(name)

    return _impl


class _FakeBuilder:
    """Replacement Chart3DBuilder that records the data + method call kwargs."""

    def __init__(self, data: Any) -> None:
        self.data = data
        CALLS.setdefault("data", data)

    scatter_3d = _make_method("scatter_3d")
    line_3d = _make_method("line_3d")
    surface_3d = _make_method("surface_3d")
    mesh_3d = _make_method("mesh_3d")

    def isosurface_3d(self, x, y, z, value, **kwargs):
        # isosurface_3d takes a 4th positional (value_column), so it needs its
        # own recorder rather than the (x, y, z, **kw) _make_method shape.
        CALLS["method"] = "isosurface_3d"
        CALLS["x"] = x
        CALLS["y"] = y
        CALLS["z"] = z
        CALLS["value"] = value
        CALLS["kwargs"] = kwargs
        return _Sentinel("isosurface_3d")


@pytest.fixture(autouse=True)
def _reset_calls():
    CALLS.clear()
    yield
    CALLS.clear()


# ---------------------------------------------------------------------------
# create_scatter_3d
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_scatter_3d_success(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(charts3d_mod, "Chart3DBuilder", _FakeBuilder)
    _wire_export_html(monkeypatch, "<html>SC3D</html>")

    rows = [{"x": 1, "y": 2, "z": 3, "city": "BG"}, {"x": 2, "y": 3, "z": 1, "city": "NS"}]
    result = await create_scatter_3d(
        rows,
        x_column="x",
        y_column="y",
        z_column="z",
        title="Pts",
        theme="light",
        color_column="city",
        size_column="x",
        symbol_column="city",
        filename="sc_out",
    )

    calls = CALLS
    assert calls["method"] == "scatter_3d"
    assert (calls["x"], calls["y"], calls["z"]) == ("x", "y", "z")
    assert calls["kwargs"] == {
        "title": "Pts",
        "theme": "light",
        "color_column": "city",
        "size_column": "x",
        "symbol_column": "city",
    }
    assert result == {"filepath": str(sandbox_export_dir / "sc_out.html"), "title": "Pts", "rows": 2}
    assert (sandbox_export_dir / "sc_out.html").read_text(encoding="utf-8") == "<html>SC3D</html>"


@pytest.mark.asyncio
async def test_create_scatter_3d_defaults(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(charts3d_mod, "Chart3DBuilder", _FakeBuilder)
    _wire_export_html(monkeypatch)

    await create_scatter_3d([{"x": 1, "y": 1, "z": 1}], x_column="x", y_column="y", z_column="z")

    kw = CALLS["kwargs"]
    assert kw["theme"] == "dark"
    assert kw["color_column"] is None
    assert kw["size_column"] is None
    assert kw["symbol_column"] is None


@pytest.mark.asyncio
async def test_create_scatter_3d_viz_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(charts3d_mod, "Chart3DBuilder", _FakeBuilder)
    monkeypatch.setattr(
        _FakeBuilder,
        "scatter_3d",
        lambda self, x, y, z, **k: (_ for _ in ()).throw(ValueError("boom")),
    )

    with pytest.raises(ToolError, match=r"3D scatter chart failed: boom"):
        await create_scatter_3d([{"x": 1, "y": 1, "z": 1}], x_column="x", y_column="y", z_column="z")


# ---------------------------------------------------------------------------
# create_line_3d
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_line_3d_success(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(charts3d_mod, "Chart3DBuilder", _FakeBuilder)
    _wire_export_html(monkeypatch, "<html>L3D</html>")

    rows = [{"lon": 20.4, "lat": 44.8, "alt": 100, "route": "n"}]
    result = await create_line_3d(
        rows, x_column="lon", y_column="lat", z_column="alt", title="Route", color_column="route", filename="ln"
    )

    calls = CALLS
    assert calls["method"] == "line_3d"
    assert calls["kwargs"] == {"title": "Route", "theme": "dark", "color_column": "route"}
    assert result == {"filepath": str(sandbox_export_dir / "ln.html"), "title": "Route", "rows": 1}


@pytest.mark.asyncio
async def test_create_line_3d_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(charts3d_mod, "Chart3DBuilder", _FakeBuilder)
    monkeypatch.setattr(
        _FakeBuilder,
        "line_3d",
        lambda self, x, y, z, **k: (_ for _ in ()).throw(ValueError("nope")),
    )

    with pytest.raises(ToolError, match=r"3D line chart failed: nope"):
        await create_line_3d([{"lon": 1, "lat": 1, "alt": 1}], x_column="lon", y_column="lat", z_column="alt")


# ---------------------------------------------------------------------------
# create_surface_3d
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_surface_3d_success(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(charts3d_mod, "Chart3DBuilder", _FakeBuilder)
    _wire_export_html(monkeypatch, "<html>S3D</html>")

    rows = [{"x": 0, "y": 0, "h": 1}, {"x": 1, "y": 1, "h": 4}]
    result = await create_surface_3d(
        rows, x_column="x", y_column="y", z_column="h", title="Elev", colorscale="RdBu", filename="sf"
    )

    calls = CALLS
    assert calls["method"] == "surface_3d"
    assert calls["kwargs"] == {"title": "Elev", "theme": "dark", "colorscale": "RdBu"}
    assert result == {"filepath": str(sandbox_export_dir / "sf.html"), "title": "Elev", "rows": 2}


@pytest.mark.asyncio
async def test_create_surface_3d_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(charts3d_mod, "Chart3DBuilder", _FakeBuilder)
    monkeypatch.setattr(
        _FakeBuilder,
        "surface_3d",
        lambda self, x, y, z, **k: (_ for _ in ()).throw(ValueError("bad")),
    )

    with pytest.raises(ToolError, match=r"3D surface chart failed: bad"):
        await create_surface_3d([{"x": 0, "y": 0, "h": 1}], x_column="x", y_column="y", z_column="h")


# ---------------------------------------------------------------------------
# create_mesh_3d
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_mesh_3d_success(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(charts3d_mod, "Chart3DBuilder", _FakeBuilder)
    _wire_export_html(monkeypatch, "<html>M3D</html>")

    rows = [{"x": 0.0, "y": 0.0, "z": 1.0, "conc": 10.0}]
    result = await create_mesh_3d(
        rows,
        x_column="x",
        y_column="y",
        z_column="z",
        title="Hull",
        theme="light",
        intensity_column="conc",
        colorscale="RdBu",
        alphahull=0,
        face_color="#c62828",
        filename="mh",
    )

    calls = CALLS
    assert calls["method"] == "mesh_3d"
    assert (calls["x"], calls["y"], calls["z"]) == ("x", "y", "z")
    assert calls["kwargs"] == {
        "title": "Hull",
        "theme": "light",
        "intensity_column": "conc",
        "colorscale": "RdBu",
        "alphahull": 0,
        "face_color": "#c62828",
    }
    assert result == {"filepath": str(sandbox_export_dir / "mh.html"), "title": "Hull", "rows": 1}
    assert (sandbox_export_dir / "mh.html").read_text(encoding="utf-8") == "<html>M3D</html>"


@pytest.mark.asyncio
async def test_create_mesh_3d_defaults(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(charts3d_mod, "Chart3DBuilder", _FakeBuilder)
    _wire_export_html(monkeypatch)

    await create_mesh_3d([{"x": 0, "y": 0, "z": 1}], x_column="x", y_column="y", z_column="z")

    kw = CALLS["kwargs"]
    assert kw["theme"] == "dark"
    assert kw["intensity_column"] is None
    assert kw["colorscale"] == "Viridis"
    assert kw["alphahull"] == 1.0
    assert kw["face_color"] is None


@pytest.mark.asyncio
async def test_create_mesh_3d_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(charts3d_mod, "Chart3DBuilder", _FakeBuilder)
    monkeypatch.setattr(
        _FakeBuilder,
        "mesh_3d",
        lambda self, x, y, z, **k: (_ for _ in ()).throw(ValueError("hull-bad")),
    )

    with pytest.raises(ToolError, match=r"3D mesh chart failed: hull-bad"):
        await create_mesh_3d([{"x": 0, "y": 0, "z": 1}], x_column="x", y_column="y", z_column="z")


# ---------------------------------------------------------------------------
# create_isosurface_3d
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_isosurface_3d_success(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(charts3d_mod, "Chart3DBuilder", _FakeBuilder)
    _wire_export_html(monkeypatch, "<html>ISO</html>")

    rows = [{"x": 0.0, "y": 0.0, "z": 0.0, "temp": 5.0}, {"x": 1.0, "y": 1.0, "z": 1.0, "temp": 20.0}]
    result = await create_isosurface_3d(
        rows,
        x_column="x",
        y_column="y",
        z_column="z",
        value_column="temp",
        title="Iso",
        theme="light",
        isomin=10.0,
        isomax=15.0,
        colorscale="RdBu",
        opacity=0.3,
        filename="iso",
    )

    calls = CALLS
    assert calls["method"] == "isosurface_3d"
    assert (calls["x"], calls["y"], calls["z"], calls["value"]) == ("x", "y", "z", "temp")
    assert calls["kwargs"] == {
        "title": "Iso",
        "theme": "light",
        "isomin": 10.0,
        "isomax": 15.0,
        "colorscale": "RdBu",
        "opacity": 0.3,
    }
    assert result == {"filepath": str(sandbox_export_dir / "iso.html"), "title": "Iso", "rows": 2}
    assert (sandbox_export_dir / "iso.html").read_text(encoding="utf-8") == "<html>ISO</html>"


@pytest.mark.asyncio
async def test_create_isosurface_3d_defaults(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(charts3d_mod, "Chart3DBuilder", _FakeBuilder)
    _wire_export_html(monkeypatch)

    await create_isosurface_3d(
        [{"x": 0, "y": 0, "z": 0, "temp": 1}],
        x_column="x",
        y_column="y",
        z_column="z",
        value_column="temp",
    )

    kw = CALLS["kwargs"]
    assert kw["theme"] == "dark"
    assert kw["isomin"] is None
    assert kw["isomax"] is None
    assert kw["colorscale"] == "Viridis"
    assert kw["opacity"] == 0.5


@pytest.mark.asyncio
async def test_create_isosurface_3d_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    monkeypatch.setattr(charts3d_mod, "Chart3DBuilder", _FakeBuilder)
    monkeypatch.setattr(
        _FakeBuilder,
        "isosurface_3d",
        lambda self, x, y, z, value, **k: (_ for _ in ()).throw(ValueError("iso-bad")),
    )

    with pytest.raises(ToolError, match=r"3D isosurface chart failed: iso-bad"):
        await create_isosurface_3d(
            [{"x": 0, "y": 0, "z": 0, "temp": 1}],
            x_column="x",
            y_column="y",
            z_column="z",
            value_column="temp",
        )
