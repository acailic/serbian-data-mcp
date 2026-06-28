"""Offline deterministic tests for viz/maps.py.

Covers the module-level ``_load_serbia_geojson`` (cache-hit + download paths),
``SerbiaMapBuilder`` lookup/resolve/list helpers, and the two public choropleth
builders (``choropleth`` + ``ranking_map``).

The builder's real ``__init__`` downloads Natural Earth GeoJSON, so the helper
tests patch ``viz.maps._load_serbia_geojson`` to return a tiny in-memory
FeatureCollection (the same pattern as test_viz_map_advanced). The download-path
test patches ``httpx.get`` and writes into a real tmp cache_dir to exercise the
file-cache write branch. Assertions are plain reads of fig.data / fig.layout
attributes (the inspect-the-figure pattern from prior viz tests).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import pytest

from serbian_data_mcp.viz import maps as maps_mod
from serbian_data_mcp.viz.maps import (
    _HEAT_RED,
    _RED_BLUE_DIVERGING,
    _SEQUENTIAL_BLUE,
    SerbiaMapBuilder,
    _load_serbia_geojson,
)

# Fake GeoJSON with name_local + an alias-matched name so _build_lookup's local
# and alias branches fire. Two MultiPolygon districts keep choropleth zmin/zmax
# deterministic.
_FAKE_GEOJSON: dict[str, Any] = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "adm1_code": "RS-1",
                "name": "Alpha",
                "name_local": "Alfa",
            },
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [[[[20.0, 45.0], [20.0, 45.4], [20.4, 45.4], [20.4, 45.0]]]],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "adm1_code": "RS-2",
                "name": "Beta",
                "name_local": "Beta",
            },
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [[[[21.0, 46.0], [21.0, 46.4], [21.4, 46.4], [21.4, 46.0]]]],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "adm1_code": "RS-3",
                "name": "Grad Beograd",
                "name_local": "Београд",
            },
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [[[[20.4, 44.7], [20.4, 44.9], [20.6, 44.9], [20.6, 44.7]]]],
            },
        },
    ],
}


@pytest.fixture
def builder(monkeypatch: pytest.MonkeyPatch) -> SerbiaMapBuilder:
    monkeypatch.setattr(maps_mod, "_load_serbia_geojson", lambda cache_dir: _FAKE_GEOJSON)
    return SerbiaMapBuilder()


# --------------------------------------------------------------------------- #
# _load_serbia_geojson
# --------------------------------------------------------------------------- #


class _FakeResp:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def test_load_geojson_cache_hit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cached file is read verbatim; no download attempted."""
    cache_path = tmp_path / "serbia_districts.geojson"
    cache_path.write_text('{"type": "FeatureCollection", "features": []}', encoding="utf-8")

    called = {"get": False}

    def _boom(*_a: Any, **_kw: Any) -> Any:
        called["get"] = True
        raise AssertionError("httpx.get must not be called on cache hit")

    monkeypatch.setattr(maps_mod.httpx, "get", _boom)

    data = _load_serbia_geojson(tmp_path)
    assert data == {"type": "FeatureCollection", "features": []}
    assert called["get"] is False


def test_load_geojson_download_filters_and_caches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Download path filters RS features and writes the cache file."""
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"adm1_code": "RS-1", "admin": "Republic of Serbia", "iso_a2": "RS", "name": "Alpha"},
                "geometry": {"type": "MultiPolygon", "coordinates": []},
            },
            {
                "type": "Feature",
                "properties": {
                    "adm1_code": "X-1",
                    "admin": "Some Other Land",
                    "iso_a2": "RS",
                    "name": "Other",
                },
                "geometry": {"type": "MultiPolygon", "coordinates": []},
            },
            {
                "type": "Feature",
                "properties": {
                    "adm1_code": "X-2",
                    "admin": "Republic of Serbia",
                    "iso_a2": "XX",
                    "name": "WrongISO",
                },
                "geometry": {"type": "MultiPolygon", "coordinates": []},
            },
        ],
    }
    monkeypatch.setattr(maps_mod.httpx, "get", lambda *_a, **_kw: _FakeResp(payload))

    data = _load_serbia_geojson(tmp_path)

    # Only the RS + Republic of Serbia feature survives the filter.
    assert len(data["features"]) == 1
    assert data["features"][0]["properties"]["adm1_code"] == "RS-1"
    # Cache file written.
    cache_path = tmp_path / "serbia_districts.geojson"
    assert cache_path.exists()


def test_load_geojson_cache_creates_parent_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Nested cache_dir is created on first download."""
    nested = tmp_path / "nested" / "cache"
    monkeypatch.setattr(
        maps_mod.httpx,
        "get",
        lambda *_a, **_kw: _FakeResp({"type": "FeatureCollection", "features": []}),
    )
    _load_serbia_geojson(nested)
    assert (nested / "serbia_districts.geojson").exists()


# --------------------------------------------------------------------------- #
# SerbiaMapBuilder lookup / resolve / list
# --------------------------------------------------------------------------- #


def test_build_lookup_records_name_local_and_aliases(builder: SerbiaMapBuilder) -> None:
    lookup = builder._name_to_code
    # Exact + lowercased canonical names.
    assert lookup["Alpha"] == "RS-1"
    assert lookup["alpha"] == "RS-1"
    # name_local differs from name → both forms recorded (Alpha → Alfa).
    assert lookup["Alfa"] == "RS-1"
    assert lookup["alfa"] == "RS-1"
    # Beta's name_local equals name → no duplicate-key divergence, still present.
    assert lookup["Beta"] == "RS-2"
    # Alias resolution: "beograd" → "Grad Beograd" code (alias branch fires only
    # when the canonical NE name is itself in the lookup).
    assert lookup["beograd"] == "RS-3"


def test_resolve_name_exact_strip_lower(builder: SerbiaMapBuilder) -> None:
    assert builder.resolve_name("Alpha") == "RS-1"
    # Whitespace-only → .strip() branch.
    assert builder.resolve_name("  Alpha  ") == "RS-1"
    # Case mismatch → .lower().strip() branch.
    assert builder.resolve_name("  ALPHA ") == "RS-1"
    # Alias resolves through lookup.
    assert builder.resolve_name("beograd") == "RS-3"
    # Unknown district.
    assert builder.resolve_name("Nowhere") is None


def test_list_districts_shape(builder: SerbiaMapBuilder) -> None:
    districts = builder.list_districts()
    assert len(districts) == 3
    codes = {d["code"] for d in districts}
    names = {d["name"] for d in districts}
    assert codes == {"RS-1", "RS-2", "RS-3"}
    assert {"Alpha", "Beta", "Grad Beograd"} <= names


# --------------------------------------------------------------------------- #
# choropleth
# --------------------------------------------------------------------------- #


_DATA = [
    {"okrug": "Alpha", "vrednost": 100},
    {"okrug": "Beta", "vrednost": 200},
    {"okrug": "Grad Beograd", "vrednost": 300},
]


def test_choropleth_builds_single_trace_with_locations_and_z(builder: SerbiaMapBuilder) -> None:
    fig = builder.choropleth(_DATA, name_column="okrug", value_column="vrednost", title="Naslov")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    trace = fig.data[0]
    # All three districts resolved (locations in featureidkey code space).
    assert set(trace.locations) == {"RS-1", "RS-2", "RS-3"}
    assert list(trace.z) == [100, 200, 300]
    assert trace.featureidkey == "properties.adm1_code"
    # Default colorscale (_SEQUENTIAL_BLUE) — plotly stores as tuple-of-tuples.
    assert list(trace.colorscale) == list(_SEQUENTIAL_BLUE)
    # zmin/zmax derived from data.
    assert trace.zmin == 100.0
    assert trace.zmax == 300.0
    # Title propagated.
    assert fig.layout.title.text == "Naslov"


def test_choropleth_custom_colorscale(builder: SerbiaMapBuilder) -> None:
    custom = [(0.0, "#000000"), (1.0, "#ffffff")]
    fig = builder.choropleth(_DATA, "okrug", "vrednost", colorscale=custom)
    assert list(fig.data[0].colorscale) == custom


def test_choropleth_no_match_returns_empty_figure(builder: SerbiaMapBuilder) -> None:
    """Unresolved district names → empty go.Figure (no data traces)."""
    fig = builder.choropleth(
        [{"okrug": "Nowhere", "vrednost": 1}],
        name_column="okrug",
        value_column="vrednost",
    )
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_choropleth_partial_match_drops_unresolved(builder: SerbiaMapBuilder) -> None:
    """Resolved rows survive; unresolved rows dropped before plotting."""
    fig = builder.choropleth(
        [
            {"okrug": "Alpha", "vrednost": 10},
            {"okrug": "Missing", "vrednost": 999},
        ],
        name_column="okrug",
        value_column="vrednost",
    )
    assert len(fig.data) == 1
    assert set(fig.data[0].locations) == {"RS-1"}
    assert list(fig.data[0].z) == [10]


def test_choropleth_highlight_top_adds_overlay_trace(builder: SerbiaMapBuilder) -> None:
    fig = builder.choropleth(_DATA, "okrug", "vrednost", highlight_top=2)
    assert len(fig.data) == 2
    overlay = fig.data[1]
    assert overlay.showscale is False
    assert overlay.marker.line.color == "#ffab00"
    # Top-2 by value (300, 200) → RS-3 and RS-2.
    assert set(overlay.locations) == {"RS-3", "RS-2"}


def test_choropleth_geo_config_and_theme(builder: SerbiaMapBuilder) -> None:
    fig = builder.choropleth(_DATA, "okrug", "vrednost", theme="light")
    geo = fig.layout.geo
    assert geo.scope == "europe"
    assert geo.fitbounds == "locations"
    assert geo.projection.type == "mercator"
    # Transparent map background applied after theme.
    assert geo.bgcolor == "rgba(0,0,0,0)"


# --------------------------------------------------------------------------- #
# ranking_map
# --------------------------------------------------------------------------- #


def test_ranking_map_diverging_colorscale(builder: SerbiaMapBuilder) -> None:
    fig = builder.ranking_map(_DATA, "okrug", "vrednost", diverging=True)
    assert len(fig.data) == 1
    trace = fig.data[0]
    assert list(trace.colorscale) == list(_RED_BLUE_DIVERGING)
    # customdata carries the vs-mean pct for each row.
    assert trace.customdata is not None
    assert len(trace.customdata) == 3


def test_ranking_map_heat_colorscale_when_not_diverging(builder: SerbiaMapBuilder) -> None:
    fig = builder.ranking_map(_DATA, "okrug", "vrednost", diverging=False)
    assert list(fig.data[0].colorscale) == list(_HEAT_RED)


def test_ranking_map_customdata_vs_mean(builder: SerbiaMapBuilder) -> None:
    """customdata = (value - mean) / mean; mean of [100,200,300] = 200."""
    fig = builder.ranking_map(_DATA, "okrug", "vrednost")
    # Alpha=100 → -50%, Beta=200 → 0%, Beograd=300 → +50%.
    expected = {"RS-1": -0.5, "RS-2": 0.0, "RS-3": 0.5}
    trace = fig.data[0]
    for code, cd in zip(trace.locations, trace.customdata, strict=True):
        assert cd[0] == pytest.approx(expected[code])


def test_ranking_map_no_match_returns_empty_figure(builder: SerbiaMapBuilder) -> None:
    fig = builder.ranking_map(
        [{"okrug": "Ghost", "vrednost": 1}],
        name_column="okrug",
        value_column="vrednost",
    )
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_ranking_map_mean_zero_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """When mean==0 the customdata delta falls back to 0 (no ZeroDivisionError)."""
    monkeypatch.setattr(maps_mod, "_load_serbia_geojson", lambda cache_dir: _FAKE_GEOJSON)
    b = SerbiaMapBuilder()
    zero_data = [
        {"okrug": "Alpha", "vrednost": 0},
        {"okrug": "Beta", "vrednost": 0},
    ]
    fig = b.ranking_map(zero_data, "okrug", "vrednost")
    for entry in fig.data[0].customdata:
        assert entry[0] == 0
