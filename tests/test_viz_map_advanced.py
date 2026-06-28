"""Offline deterministic tests for viz/map_advanced.py.

Covers the three public methods on AdvancedMapBuilder (bubble_map,
multi_layer_map, ranked_scatter_map) plus the _compute_centroids helper.

The builder's real ``__init__`` downloads Natural Earth GeoJSON, so these
tests patch ``viz.maps._load_serbia_geojson`` to return a tiny in-memory
FeatureCollection. SerbiaMapBuilder.__init__ (inherited) then builds a real
name→code lookup and AdvancedMapBuilder._compute_centroids derives real
centroids from the fake MultiPolygon geometries — so every code path executes
against the genuine methods with no network and no file writes. Assertions are
plain reads of fig.data / fig.layout attributes (the inspect-the-figure pattern
from test_viz_tooltips/special_charts).
"""

from __future__ import annotations

import pytest
import plotly.graph_objects as go

from serbian_data_mcp.viz import maps as maps_mod
from serbian_data_mcp.viz.map_advanced import AdvancedMapBuilder
from serbian_data_mcp.viz.maps import _HEAT_RED, _RED_BLUE_DIVERGING, _SEQUENTIAL_BLUE


# Two-district fake GeoJSON. Centroids:
#   RS-1 (Alpha) = (20.2, 45.2)   RS-2 (Beta) = (21.2, 46.2)
# RS-3 (Gamma) has a Point geometry so it is in the lookup but has NO centroid,
# exercising the centroid-miss empty-result branches.
_FAKE_GEOJSON: dict = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"adm1_code": "RS-1", "name": "Alpha"},
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [[[[20.0, 45.0], [20.0, 45.4], [20.4, 45.4], [20.4, 45.0]]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"adm1_code": "RS-2", "name": "Beta"},
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [[[[21.0, 46.0], [21.0, 46.4], [21.4, 46.4], [21.4, 46.0]]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"adm1_code": "RS-3", "name": "Gamma"},
            "geometry": {"type": "Point", "coordinates": [22.0, 47.0]},
        },
    ],
}


@pytest.fixture
def builder(monkeypatch: pytest.MonkeyPatch) -> AdvancedMapBuilder:
    monkeypatch.setattr(maps_mod, "_load_serbia_geojson", lambda cache_dir: _FAKE_GEOJSON)
    return AdvancedMapBuilder()


# -- _compute_centroids --------------------------------------------------------


def test_compute_centroids_returns_centroid_per_multipolygon(builder: AdvancedMapBuilder) -> None:
    centroids = builder._compute_centroids()
    # Only the two MultiPolygon features get centroids; Point geometry is skipped.
    assert set(centroids.keys()) == {"RS-1", "RS-2"}
    assert centroids["RS-1"] == pytest.approx((20.2, 45.2))
    assert centroids["RS-2"] == pytest.approx((21.2, 46.2))


def test_compute_centroids_is_cached(builder: AdvancedMapBuilder) -> None:
    first = builder._compute_centroids()
    second = builder._compute_centroids()
    assert first is second


def test_resolve_name_lookups_names_case_and_strip_insensitive(builder: AdvancedMapBuilder) -> None:
    assert builder.resolve_name("Alpha") == "RS-1"
    assert builder.resolve_name("alpha") == "RS-1"
    assert builder.resolve_name("  Beta ") == "RS-2"
    assert builder.resolve_name("Unknown") is None


# -- bubble_map ----------------------------------------------------------------


def test_bubble_map_returns_single_scattergeo_trace(builder: AdvancedMapBuilder) -> None:
    data = [{"name": "Alpha", "v": 100}, {"name": "Beta", "v": 50}]
    fig = builder.bubble_map(data, "name", "v", title="Pop")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert isinstance(fig.data[0], go.Scattergeo)
    # Title flows into layout.
    assert fig.layout.title.text == "Pop"


def test_bubble_map_sizes_scale_value_range_to_min_max(builder: AdvancedMapBuilder) -> None:
    data = [{"name": "Alpha", "v": 100}, {"name": "Beta", "v": 50}]
    trace = builder.bubble_map(data, "name", "v").data[0]
    # min_size=10, max_size=60 → Alpha=60, Beta=10
    assert list(trace.marker.size) == pytest.approx([60.0, 10.0])
    assert trace.marker.color == "#1565c0"
    assert trace.marker.sizemode == "area"
    # customdata carries the raw value
    assert [row[0] for row in list(trace.customdata)] == [100, 50]


def test_bubble_map_size_scale_multiplier_stretches_range(builder: AdvancedMapBuilder) -> None:
    data = [{"name": "Alpha", "v": 100}, {"name": "Beta", "v": 50}]
    trace = builder.bubble_map(data, "name", "v", size_scale=2.0).data[0]
    # min_size=20, max_size=120 → Alpha=120, Beta=20
    assert list(trace.marker.size) == pytest.approx([120.0, 20.0])


def test_bubble_map_equal_values_avoids_zero_division(builder: AdvancedMapBuilder) -> None:
    data = [{"name": "Alpha", "v": 7}, {"name": "Beta", "v": 7}]
    trace = builder.bubble_map(data, "name", "v").data[0]
    # val_range falls back to 1 → both sizes collapse to min_size=10
    assert list(trace.marker.size) == pytest.approx([10.0, 10.0])


def test_bubble_map_second_value_column_adds_overlay_trace(builder: AdvancedMapBuilder) -> None:
    data = [{"name": "Alpha", "v": 100, "v2": 30}, {"name": "Beta", "v": 50, "v2": 10}]
    fig = builder.bubble_map(data, "name", "v", second_value_column="v2", second_color="#000000")
    assert len(fig.data) == 2
    primary, overlay = fig.data
    assert primary.marker.color == "#1565c0"
    assert overlay.marker.color == "#000000"
    assert overlay.name == "v2"


def test_bubble_map_show_district_labels_adds_text_trace(builder: AdvancedMapBuilder) -> None:
    data = [{"name": "Alpha", "v": 100}, {"name": "Beta", "v": 50}]
    fig = builder.bubble_map(data, "name", "v", show_district_labels=True)
    # primary + labels = 2 traces; the text trace uses mode='text'
    assert len(fig.data) == 2
    label_trace = fig.data[1]
    assert label_trace.mode == "text"
    assert list(label_trace.text) == ["Alpha", "Beta"]


def test_bubble_map_custom_bubble_color(builder: AdvancedMapBuilder) -> None:
    data = [{"name": "Alpha", "v": 100}]
    trace = builder.bubble_map(data, "name", "v", bubble_color="#abcdef").data[0]
    assert trace.marker.color == "#abcdef"


def test_bubble_map_unknown_districts_return_empty_figure(builder: AdvancedMapBuilder) -> None:
    fig = builder.bubble_map([{"name": "Nowhere", "v": 1}], "name", "v")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_bubble_map_point_geometry_districts_return_empty_figure(builder: AdvancedMapBuilder) -> None:
    # Gamma resolves to a code but its Point geometry yields no centroid → empty.
    fig = builder.bubble_map([{"name": "Gamma", "v": 1}], "name", "v")
    assert len(fig.data) == 0


# -- multi_layer_map -----------------------------------------------------------


def test_multi_layer_map_builds_one_choropleth_per_layer(builder: AdvancedMapBuilder) -> None:
    layers = [
        {
            "data": [{"name": "Alpha", "v": 10}, {"name": "Beta", "v": 20}],
            "name_column": "name",
            "value_column": "v",
            "label": "Layer A",
            "colorscale": "blue",
        },
        {
            "data": [{"name": "Alpha", "v": 1}, {"name": "Beta", "v": 2}],
            "name_column": "name",
            "value_column": "v",
            "label": "Layer B",
            "colorscale": "red",
        },
    ]
    fig = builder.multi_layer_map(layers, title="Multi")
    assert len(fig.data) == 2
    assert all(isinstance(t, go.Choropleth) for t in fig.data)
    # Only the first layer is visible by default.
    assert fig.data[0].visible is True
    assert fig.data[1].visible is False
    # Toggle buttons: one per layer, each setting a single-visible mask.
    menus = fig.layout.updatemenus
    assert len(list(fig.layout.updatemenus)) >= 1
    buttons = list(menus[0].buttons)
    assert len(buttons) == 2
    assert [b.label for b in buttons] == ["Layer A", "Layer B"]
    assert list(buttons[0].args[0]["visible"]) == [True, False]
    assert list(buttons[1].args[0]["visible"]) == [False, True]
    assert fig.layout.title.text == "Multi"


def test_multi_layer_map_colorscale_resolution(builder: AdvancedMapBuilder) -> None:
    base = {
        "data": [{"name": "Alpha", "v": 1}, {"name": "Beta", "v": 2}],
        "name_column": "name",
        "value_column": "v",
    }
    cases = [
        ("blue", _SEQUENTIAL_BLUE),
        ("red", _HEAT_RED),
        ("heat", _HEAT_RED),
        ("diverging", _RED_BLUE_DIVERGING),
        ("unknown", _SEQUENTIAL_BLUE),  # unknown → default blue
        (None, _SEQUENTIAL_BLUE),  # missing keyscale → default
    ]
    for scale, expected in cases:
        layer = {**base, "label": scale or "None", "colorscale": scale}
        fig = builder.multi_layer_map([layer])
        assert list(fig.data[0].colorscale) == list(expected), f"colorscale={scale!r}"


def test_multi_layer_map_empty_layer_is_skipped(builder: AdvancedMapBuilder) -> None:
    layers = [
        {
            "data": [{"name": "Nowhere", "v": 1}],  # no matching district
            "name_column": "name",
            "value_column": "v",
            "label": "Empty",
            "colorscale": "blue",
        },
        {
            "data": [{"name": "Alpha", "v": 10}, {"name": "Beta", "v": 20}],
            "name_column": "name",
            "value_column": "v",
            "label": "Real",
            "colorscale": "blue",
        },
    ]
    fig = builder.multi_layer_map(layers)
    # Only the real layer produces a trace.
    assert len(fig.data) == 1
    assert fig.data[0].name == "Real"


def test_multi_layer_map_all_empty_returns_empty_figure(builder: AdvancedMapBuilder) -> None:
    layers = [
        {
            "data": [{"name": "Nowhere", "v": 1}],
            "name_column": "name",
            "value_column": "v",
            "label": "Empty",
            "colorscale": "blue",
        }
    ]
    fig = builder.multi_layer_map(layers)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_multi_layer_map_zmin_zmax_from_data(builder: AdvancedMapBuilder) -> None:
    layer = {
        "data": [{"name": "Alpha", "v": 5}, {"name": "Beta", "v": 25}],
        "name_column": "name",
        "value_column": "v",
        "label": "L",
        "colorscale": "blue",
    }
    trace = builder.multi_layer_map([layer]).data[0]
    assert trace.zmin == 5.0
    assert trace.zmax == 25.0
    assert trace.locations == ("RS-1", "RS-2")
    assert list(trace.z) == [5, 25]


# -- ranked_scatter_map --------------------------------------------------------


def test_ranked_scatter_map_returns_single_trace_colored_by_y(builder: AdvancedMapBuilder) -> None:
    data = [{"name": "Alpha", "x": 100, "y": 200}, {"name": "Beta", "x": 50, "y": 400}]
    fig = builder.ranked_scatter_map(data, "name", "x", "y", title="Scatter")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    trace = fig.data[0]
    assert isinstance(trace, go.Scattergeo)
    assert list(trace.marker.color) == pytest.approx([200.0, 400.0])  # pyright: ignore[reportOptionalMemberAccess]
    assert list(trace.marker.colorscale) == list(_SEQUENTIAL_BLUE)  # pyright: ignore[reportOptionalMemberAccess]
    assert fig.layout.title.text == "Scatter"


def test_ranked_scatter_map_default_uniform_size(builder: AdvancedMapBuilder) -> None:
    data = [{"name": "Alpha", "x": 1, "y": 2}, {"name": "Beta", "x": 3, "y": 4}]
    trace = builder.ranked_scatter_map(data, "name", "x", "y").data[0]
    # No size_column → uniform size 15 per row.
    assert list(trace.marker.size) == [15, 15]


def test_ranked_scatter_map_size_column_scales_bubbles(builder: AdvancedMapBuilder) -> None:
    data = [{"name": "Alpha", "x": 1, "y": 2, "s": 100}, {"name": "Beta", "x": 3, "y": 4, "s": 10}]
    trace = builder.ranked_scatter_map(data, "name", "x", "y", size_column="s").data[0]
    # s normalized to [10, 50]: Alpha=50, Beta=10
    assert list(trace.marker.size) == pytest.approx([50.0, 10.0])


def test_ranked_scatter_map_label_column_overrides_text(builder: AdvancedMapBuilder) -> None:
    data = [
        {"name": "Alpha", "x": 1, "y": 2, "label": "Region A"},
        {"name": "Beta", "x": 3, "y": 4, "label": "Region B"},
    ]
    trace = builder.ranked_scatter_map(data, "name", "x", "y", label_column="label").data[0]
    assert list(trace.text) == ["Region A", "Region B"]


def test_ranked_scatter_map_customdata_carries_x_and_y(builder: AdvancedMapBuilder) -> None:
    data = [{"name": "Alpha", "x": 11, "y": 22}, {"name": "Beta", "x": 33, "y": 44}]
    trace = builder.ranked_scatter_map(data, "name", "x", "y").data[0]
    assert [list(row) for row in list(trace.customdata)] == [[11, 22], [33, 44]]


def test_ranked_scatter_map_unknown_districts_return_empty_figure(builder: AdvancedMapBuilder) -> None:
    fig = builder.ranked_scatter_map([{"name": "Nowhere", "x": 1, "y": 2}], "name", "x", "y")
    assert len(fig.data) == 0


def test_ranked_scatter_map_point_geometry_returns_empty_figure(builder: AdvancedMapBuilder) -> None:
    fig = builder.ranked_scatter_map([{"name": "Gamma", "x": 1, "y": 2}], "name", "x", "y")
    assert len(fig.data) == 0
