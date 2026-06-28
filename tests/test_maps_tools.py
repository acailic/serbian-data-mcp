"""Offline unit tests for tools/maps.py — Serbia map visualization tools.

Covers all 4 MCP tools (create_serbia_map, list_serbia_districts,
create_bubble_map, create_multi_layer_map) which shipped with zero direct
test coverage. The viz-layer builders (SerbiaMapBuilder, AdvancedMapBuilder)
and ``export_html`` are faked at the module-attribute seam, and
``config.export_dir`` is redirected to a tmp dir so the HTML write is real but
sandboxed — fully deterministic, no network, no plotly rendering, no GeoJSON
download.

The builder singletons (``_map_builder`` / ``_adv_map_builder``) are reset to
None and the builder *classes* are patched, so the real lazy-init path in
``_get_map_builder`` / ``_get_adv_map_builder`` executes end-to-end against the
fake — covering the singleton-construction branch too.
"""

from __future__ import annotations

from typing import Any, Callable

import pytest
from fastmcp.exceptions import ToolError

from serbian_data_mcp.tools import maps as maps_mod
from serbian_data_mcp.tools.maps import (
    create_bubble_map,
    create_multi_layer_map,
    create_serbia_map,
    list_serbia_districts,
)


class _Sentinel:
    """Stand-in Plotly figure so pass-through is traceable without plotly."""

    def __init__(self, tag: str = "fig") -> None:
        self.tag = tag


class _FakeBuilder:
    """Capturing stand-in for SerbiaMapBuilder / AdvancedMapBuilder.

    Records every method call (name + kwargs) and returns a ``_Sentinel`` fig,
    so kwarg pass-through and the return-envelope post-processing in each tool
    can be asserted without the real GeoJSON-bound builders.
    """

    def __init__(
        self,
        *,
        resolve: Callable[[str], Any] = lambda name: name,
        raise_on: str | None = None,
        districts: list[str] | None = None,
    ) -> None:
        self._resolve = resolve
        self._raise_on = raise_on
        self._districts = districts if districts is not None else ["Beogradski", "Južnobački"]
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def choropleth(self, data: Any, **kwargs: Any) -> _Sentinel:
        self.calls.append(("choropleth", kwargs))
        if self._raise_on == "choropleth":
            raise ValueError("boom")
        return _Sentinel("serbia")

    def bubble_map(self, data: Any, **kwargs: Any) -> _Sentinel:
        self.calls.append(("bubble_map", kwargs))
        if self._raise_on == "bubble_map":
            raise RuntimeError("nope")
        return _Sentinel("bubble")

    def multi_layer_map(self, layers: Any, **kwargs: Any) -> _Sentinel:
        self.calls.append(("multi_layer_map", kwargs))
        if self._raise_on == "multi_layer_map":
            raise ValueError("bad layers")
        return _Sentinel("multi")

    def list_districts(self) -> list[str]:
        return list(self._districts)

    def resolve_name(self, name: str) -> Any:
        return self._resolve(name)


@pytest.fixture
def sandbox_export_dir(monkeypatch, tmp_path):
    """Redirect config.export_dir to a tmp dir so HTML writes are sandboxed.

    export_dir is a property on the Config class, so the property descriptor on
    the class is replaced (monkeypatch restores it after the test).
    """
    monkeypatch.setattr(
        type(maps_mod.config),
        "export_dir",
        property(lambda self: tmp_path),
    )
    return tmp_path


def _wire_export_html(monkeypatch, body: str = "<html>X</html>") -> None:
    """Patch export_html at the module-attribute seam."""
    monkeypatch.setattr(maps_mod, "export_html", lambda fig: body)


def _wire_map_builder(monkeypatch, fake: _FakeBuilder) -> _FakeBuilder:
    """Patch SerbiaMapBuilder + reset the singleton so _get_map_builder runs."""
    monkeypatch.setattr(maps_mod, "SerbiaMapBuilder", lambda: fake)
    monkeypatch.setattr(maps_mod, "_map_builder", None)
    return fake


def _wire_adv_builder(monkeypatch, fake: _FakeBuilder) -> _FakeBuilder:
    """Patch AdvancedMapBuilder + reset the singleton so _get_adv_map_builder runs."""
    monkeypatch.setattr(maps_mod, "AdvancedMapBuilder", lambda: fake)
    monkeypatch.setattr(maps_mod, "_adv_map_builder", None)
    return fake


# ---------------------------------------------------------------------------
# create_serbia_map
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_serbia_map_success_default(monkeypatch, sandbox_export_dir) -> None:
    fake = _wire_map_builder(monkeypatch, _FakeBuilder())
    _wire_export_html(monkeypatch, "<html>SERBIA</html>")

    rows = [{"d": "Beogradski", "pop": 100}, {"d": "Južnobački", "pop": 80}]
    result = await create_serbia_map(rows, name_column="d", value_column="pop", filename="map_out")

    # choropleth called with name/value columns, default theme, no colorscale, highlight_top=3
    name, kwargs = fake.calls[0]
    assert name == "choropleth"
    assert kwargs["name_column"] == "d"
    assert kwargs["value_column"] == "pop"
    assert kwargs["theme"] == "dark"
    assert kwargs["colorscale"] is None
    assert kwargs["highlight_top"] == 3
    # empty title → localized default passed to the builder
    assert kwargs["title"] == "pop po okruzima"

    # return envelope: original (empty) title echoed, both rows matched
    assert result == {
        "filepath": str(sandbox_export_dir / "map_out.html"),
        "districts_matched": 2,
        "total_districts": 2,
        "title": "",
    }
    assert (sandbox_export_dir / "map_out.html").read_text(encoding="utf-8") == "<html>SERBIA</html>"


@pytest.mark.asyncio
async def test_create_serbia_map_title_passthrough(monkeypatch, sandbox_export_dir) -> None:
    fake = _wire_map_builder(monkeypatch, _FakeBuilder())
    _wire_export_html(monkeypatch)

    await create_serbia_map(
        [{"d": "Beogradski", "pop": 1}],
        name_column="d",
        value_column="pop",
        title="Population",
        theme="light",
    )

    _, kwargs = fake.calls[0]
    # explicit title wins over the localized default
    assert kwargs["title"] == "Population"
    assert kwargs["theme"] == "light"


@pytest.mark.asyncio
async def test_create_serbia_map_colorscale_red(monkeypatch, sandbox_export_dir) -> None:
    fake = _wire_map_builder(monkeypatch, _FakeBuilder())
    _wire_export_html(monkeypatch)

    await create_serbia_map(
        [{"d": "Beogradski", "pop": 1}],
        name_column="d",
        value_column="pop",
        colorscale="red",
    )

    _, kwargs = fake.calls[0]
    assert kwargs["colorscale"] == [
        (0.0, "#fff9c4"),
        (0.25, "#ffcc80"),
        (0.5, "#ff8a65"),
        (0.75, "#e53935"),
        (1.0, "#b71c1c"),
    ]


@pytest.mark.asyncio
async def test_create_serbia_map_unmatched_districts_zero(monkeypatch, sandbox_export_dir) -> None:
    # resolve_name returns None for every row → districts_matched == 0
    _wire_map_builder(monkeypatch, _FakeBuilder(resolve=lambda name: None))
    _wire_export_html(monkeypatch)

    result = await create_serbia_map(
        [{"d": "???", "pop": 1}, {"d": "!!!", "pop": 2}],
        name_column="d",
        value_column="pop",
    )

    assert result["districts_matched"] == 0
    assert result["total_districts"] == 2


@pytest.mark.asyncio
async def test_create_serbia_map_viz_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    _wire_map_builder(monkeypatch, _FakeBuilder(raise_on="choropleth"))
    _wire_export_html(monkeypatch)

    with pytest.raises(ToolError, match=r"Map creation failed: boom"):
        await create_serbia_map(
            [{"d": "Beogradski", "pop": 1}],
            name_column="d",
            value_column="pop",
        )


# ---------------------------------------------------------------------------
# list_serbia_districts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_serbia_districts(monkeypatch) -> None:
    _wire_map_builder(monkeypatch, _FakeBuilder(districts=["Beogradski", "Južnobački", "Nišavski"]))

    result = await list_serbia_districts()

    # districts come from the builder; total is the hardcoded 25-district contract
    assert result == {"districts": ["Beogradski", "Južnobački", "Nišavski"], "total": 25}


# ---------------------------------------------------------------------------
# create_bubble_map
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_bubble_map_success(monkeypatch, sandbox_export_dir) -> None:
    fake = _wire_adv_builder(monkeypatch, _FakeBuilder())
    _wire_export_html(monkeypatch, "<html>BUBBLE</html>")

    rows = [{"d": "Beogradski", "pop": 100}, {"d": "Južnobački", "pop": 80}]
    result = await create_bubble_map(
        rows,
        name_column="d",
        value_column="pop",
        title="Bubbles",
        theme="light",
        filename="bubble_out",
    )

    name, kwargs = fake.calls[0]
    assert name == "bubble_map"
    assert kwargs == {"name_column": "d", "value_column": "pop", "title": "Bubbles", "theme": "light"}

    assert result == {
        "filepath": str(sandbox_export_dir / "bubble_out.html"),
        "districts_matched": 2,
        "title": "Bubbles",
    }
    assert (sandbox_export_dir / "bubble_out.html").read_text(encoding="utf-8") == "<html>BUBBLE</html>"


@pytest.mark.asyncio
async def test_create_bubble_map_viz_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    _wire_adv_builder(monkeypatch, _FakeBuilder(raise_on="bubble_map"))
    _wire_export_html(monkeypatch)

    with pytest.raises(ToolError, match=r"Bubble map failed: nope"):
        await create_bubble_map(
            [{"d": "Beogradski", "pop": 1}],
            name_column="d",
            value_column="pop",
        )


# ---------------------------------------------------------------------------
# create_multi_layer_map
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_multi_layer_map_success(monkeypatch, sandbox_export_dir) -> None:
    fake = _wire_adv_builder(monkeypatch, _FakeBuilder())
    _wire_export_html(monkeypatch, "<html>MULTI</html>")

    layers = [
        {"data": [{"d": "Beogradski", "v": 1}], "name_column": "d", "value_column": "v", "label": "A"},
        {"data": [{"d": "Južnobački", "v": 2}], "name_column": "d", "value_column": "v", "label": "B"},
    ]
    result = await create_multi_layer_map(layers, title="Layers", theme="light", filename="multi_out")

    name, kwargs = fake.calls[0]
    assert name == "multi_layer_map"
    assert kwargs == {"title": "Layers", "theme": "light"}

    assert result == {
        "filepath": str(sandbox_export_dir / "multi_out.html"),
        "layer_count": 2,
        "title": "Layers",
    }
    assert (sandbox_export_dir / "multi_out.html").read_text(encoding="utf-8") == "<html>MULTI</html>"


@pytest.mark.asyncio
async def test_create_multi_layer_map_viz_exception_wrapped(monkeypatch, sandbox_export_dir) -> None:
    _wire_adv_builder(monkeypatch, _FakeBuilder(raise_on="multi_layer_map"))
    _wire_export_html(monkeypatch)

    with pytest.raises(ToolError, match=r"Multi-layer map failed: bad layers"):
        await create_multi_layer_map([{"data": [], "name_column": "d", "value_column": "v"}])
