"""Deterministic offline tests for viz/charts_3d.py Chart3DBuilder.

All methods build real plotly go.Figure objects with no file/network/export_dir
coupling (apply_theme + scene layout only mutate fig.layout), so tests are plain
fig.data/fig.layout attribute reads — same inspect-the-figure pattern as the
advanced_charts / special_charts viz tests.
"""

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from serbian_data_mcp.viz import Chart3DBuilder
from serbian_data_mcp.viz.charts_3d import Chart3DBuilder as DirectImport

# ---------------------------------------------------------------------------
# Fixtures / data
# ---------------------------------------------------------------------------

SCATTER3D_DATA: list[dict[str, Any]] = [
    {"x": 1.0, "y": 2.0, "z": 3.0, "city": "BG", "pop": 10, "kind": "a"},
    {"x": 2.0, "y": 3.0, "z": 1.0, "city": "NS", "pop": 20, "kind": "b"},
    {"x": 3.0, "y": 1.0, "z": 2.0, "city": "NI", "pop": 30, "kind": "a"},
]

LINE3D_DATA: list[dict[str, Any]] = [
    {"lon": 20.4, "lat": 44.8, "alt": 100, "route": "north"},
    {"lon": 20.5, "lat": 45.0, "alt": 200, "route": "north"},
    {"lon": 20.6, "lat": 45.2, "alt": 150, "route": "south"},
    {"lon": 20.7, "lat": 45.4, "alt": 180, "route": "south"},
]

# 2x2 gridded scalar field for the surface
SURFACE_DATA: list[dict[str, Any]] = [
    {"x": 0, "y": 0, "h": 1.0},
    {"x": 1, "y": 0, "h": 2.0},
    {"x": 0, "y": 1, "h": 3.0},
    {"x": 1, "y": 1, "h": 4.0},
]

# scattered 3D point cloud for the mesh (irregular + a 4th intensity metric)
MESH_DATA: list[dict[str, Any]] = [
    {"x": 0.0, "y": 0.0, "z": 1.0, "conc": 10.0},
    {"x": 2.0, "y": 0.0, "z": 2.0, "conc": 20.0},
    {"x": 0.0, "y": 2.0, "z": 1.5, "conc": 30.0},
    {"x": 2.0, "y": 2.0, "z": 3.0, "conc": 40.0},
    {"x": 1.0, "y": 1.0, "z": 2.5, "conc": 50.0},
]

# volumetric scalar field for the iso-surface (scattered x,y,z samples + value)
ISOSURFACE_DATA: list[dict[str, Any]] = [
    {"x": 0.0, "y": 0.0, "z": 0.0, "temp": 5.0},
    {"x": 1.0, "y": 0.0, "z": 0.0, "temp": 8.0},
    {"x": 0.0, "y": 1.0, "z": 0.0, "temp": 12.0},
    {"x": 0.0, "y": 0.0, "z": 1.0, "temp": 15.0},
    {"x": 1.0, "y": 1.0, "z": 1.0, "temp": 20.0},
]


# ---------------------------------------------------------------------------
# __init__ + import surface
# ---------------------------------------------------------------------------


class TestInit:
    def test_accepts_list_and_wraps_dataframe(self) -> None:
        b = Chart3DBuilder(SCATTER3D_DATA)
        assert isinstance(b.data, pd.DataFrame)
        assert len(b.data) == 3
        assert "city" in b.data.columns

    def test_accepts_dataframe_passthrough(self) -> None:
        df = pd.DataFrame(SCATTER3D_DATA)
        b = Chart3DBuilder(df)
        assert b.data is df  # passthrough, no copy

    def test_reexported_from_viz_package(self) -> None:
        # viz.__init__ re-exports Chart3DBuilder
        assert Chart3DBuilder is DirectImport


# ---------------------------------------------------------------------------
# scatter_3d
# ---------------------------------------------------------------------------


class TestScatter3D:
    def test_returns_scatter3d_figure_with_themed_scene(self) -> None:
        fig = Chart3DBuilder(SCATTER3D_DATA).scatter_3d("x", "y", "z", title="T")
        assert isinstance(fig, go.Figure)
        assert isinstance(fig.data[0], go.Scatter3d)
        assert fig.layout.title.text == "T"
        # scene styled (3D equivalent of xaxis/yaxis)
        assert fig.layout.scene.xaxis.showbackground is True
        assert fig.layout.scene.camera.eye.x == 1.6

    def test_xyz_columns_mapped(self) -> None:
        fig = Chart3DBuilder(SCATTER3D_DATA).scatter_3d("x", "y", "z")
        tr = fig.data[0]
        assert list(tr.x) == [1.0, 2.0, 3.0]
        assert list(tr.y) == [2.0, 3.0, 1.0]
        assert list(tr.z) == [3.0, 1.0, 2.0]

    def test_color_column_splits_into_traces(self) -> None:
        fig = Chart3DBuilder(SCATTER3D_DATA).scatter_3d("x", "y", "z", color_column="city")
        # one Scatter3d trace per city (3 distinct)
        assert len(fig.data) == 3
        names = {t.name for t in fig.data}
        assert names == {"BG", "NS", "NI"}

    def test_symbol_column_assigns_markers(self) -> None:
        fig = Chart3DBuilder(SCATTER3D_DATA).scatter_3d("x", "y", "z", symbol_column="kind")
        # px.scatter_3d with symbol -> per-symbol traces; marker.symbol set
        assert any(t.marker.symbol is not None for t in fig.data)

    def test_light_theme_switches_scene_bgcolor(self) -> None:
        dark = Chart3DBuilder(SCATTER3D_DATA).scatter_3d("x", "y", "z", theme="dark")
        light = Chart3DBuilder(SCATTER3D_DATA).scatter_3d("x", "y", "z", theme="light")
        assert dark.layout.scene.xaxis.backgroundcolor == "#16213e"
        assert light.layout.scene.xaxis.backgroundcolor == "#f8f9fa"

    def test_professional_theme_salmon_scene_and_palette(self) -> None:
        from serbian_data_mcp.viz.themes import PROFESSIONAL_COLORS, PROFESSIONAL_PAPER

        prof = Chart3DBuilder(SCATTER3D_DATA).scatter_3d("x", "y", "z", theme="professional", color_column="city")
        # 3D scene honors the FT salmon-paper background + ink-dark axis text
        assert prof.layout.scene.xaxis.backgroundcolor == PROFESSIONAL_PAPER
        assert prof.layout.scene.xaxis.tickfont.color == "#333333"
        assert prof.layout.scene.xaxis.title.font.color == "#121212"
        # professional Okabe-Ito palette drives the per-city trace colors,
        # distinct from the default SEMANTIC_COLORS red-blue
        first_colors = {t.marker.color for t in prof.data if t.marker.color is not None}
        assert PROFESSIONAL_COLORS[0] in first_colors


# ---------------------------------------------------------------------------
# line_3d
# ---------------------------------------------------------------------------


class TestLine3D:
    def test_returns_lines_markers_mode(self) -> None:
        fig = Chart3DBuilder(LINE3D_DATA).line_3d("lon", "lat", "alt", title="Route")
        assert isinstance(fig, go.Figure)
        assert isinstance(fig.data[0], go.Scatter3d)
        # builder sets lines+markers mode
        assert fig.data[0].mode == "lines+markers"
        assert fig.layout.title.text == "Route"

    def test_color_column_splits_routes(self) -> None:
        fig = Chart3DBuilder(LINE3D_DATA).line_3d("lon", "lat", "alt", color_column="route")
        # two routes -> two traces
        assert len(fig.data) == 2
        assert {t.name for t in fig.data} == {"north", "south"}

    def test_scene_camera_set(self) -> None:
        fig = Chart3DBuilder(LINE3D_DATA).line_3d("lon", "lat", "alt")
        assert fig.layout.scene.camera.eye.z == 0.9


# ---------------------------------------------------------------------------
# surface_3d
# ---------------------------------------------------------------------------


class TestSurface3D:
    def test_returns_surface_trace_with_gridded_z(self) -> None:
        fig = Chart3DBuilder(SURFACE_DATA).surface_3d("x", "y", "h", title="Elevation")
        assert isinstance(fig, go.Figure)
        assert isinstance(fig.data[0], go.Surface)
        # 2x2 grid -> z matrix is 2 rows by 2 cols
        z = fig.data[0].z
        assert len(z) == 2 and all(len(row) == 2 for row in z)
        assert fig.layout.title.text == "Elevation"

    def test_default_viridis_colorscale(self) -> None:
        fig = Chart3DBuilder(SURFACE_DATA).surface_3d("x", "y", "h")
        # colorscale resolved to a list of [stop, color] pairs
        assert fig.data[0].colorscale is not None
        assert len(fig.data[0].colorscale) >= 2

    def test_custom_colorscale_override(self) -> None:
        # Plotly resolves a named colorscale to its rgb stop list at construction;
        # verify the override took effect by comparing first-stop colors.
        viridis = Chart3DBuilder(SURFACE_DATA).surface_3d("x", "y", "h", colorscale="Viridis")
        rdbu = Chart3DBuilder(SURFACE_DATA).surface_3d("x", "y", "h", colorscale="RdBu")
        viridis_first = viridis.data[0].colorscale[0][1]
        rdbu_first = rdbu.data[0].colorscale[0][1]
        assert viridis_first != rdbu_first
        # RdBu's low stop is a deep red, not Viridis's deep purple
        assert rdbu_first == "rgb(103,0,31)"

    def test_x_y_axes_carry_grid_labels(self) -> None:
        fig = Chart3DBuilder(SURFACE_DATA).surface_3d("x", "y", "h")
        # x = grid columns {0,1}, y = grid rows {0,1}
        assert set(fig.data[0].x) == {0, 1}
        assert set(fig.data[0].y) == {0, 1}


# ---------------------------------------------------------------------------
# mesh_3d
# ---------------------------------------------------------------------------


class TestMesh3D:
    def test_returns_mesh3d_trace_with_xyz_points(self) -> None:
        fig = Chart3DBuilder(MESH_DATA).mesh_3d("x", "y", "z", title="Hull")
        assert isinstance(fig, go.Figure)
        assert isinstance(fig.data[0], go.Mesh3d)
        tr = fig.data[0]
        assert list(tr.x) == [0.0, 2.0, 0.0, 2.0, 1.0]
        assert list(tr.z) == [1.0, 2.0, 1.5, 3.0, 2.5]
        assert fig.layout.title.text == "Hull"
        # scene styled by the 3D builder
        assert fig.layout.scene.xaxis.showbackground is True

    def test_default_alphahull_one(self) -> None:
        fig = Chart3DBuilder(MESH_DATA).mesh_3d("x", "y", "z")
        assert fig.data[0].alphahull == 1.0

    def test_alphahull_passthrough_zero_convex_hull(self) -> None:
        fig = Chart3DBuilder(MESH_DATA).mesh_3d("x", "y", "z", alphahull=0)
        assert fig.data[0].alphahull == 0

    def test_intensity_column_colors_vertices(self) -> None:
        fig = Chart3DBuilder(MESH_DATA).mesh_3d("x", "y", "z", intensity_column="conc", colorscale="RdBu")
        tr = fig.data[0]
        assert tr.intensity is not None
        assert list(tr.intensity) == [10.0, 20.0, 30.0, 40.0, 50.0]
        # colorscale resolved to [stop, color] pairs, distinct from Viridis
        rdbu_first = tr.colorscale[0][1]
        assert rdbu_first == "rgb(103,0,31)"

    def test_face_color_solid_mesh_no_intensity(self) -> None:
        fig = Chart3DBuilder(MESH_DATA).mesh_3d("x", "y", "z", face_color="#c62828")
        tr = fig.data[0]
        assert tr.intensity is None
        # go.Mesh3d's solid color lives on the trace-level `color` attribute
        # (facecolor is a per-triangle array); default facecolor stays unset.
        assert tr.color == "#c62828"

    def test_light_theme_switches_scene_bgcolor(self) -> None:
        dark = Chart3DBuilder(MESH_DATA).mesh_3d("x", "y", "z", theme="dark")
        light = Chart3DBuilder(MESH_DATA).mesh_3d("x", "y", "z", theme="light")
        assert dark.layout.scene.xaxis.backgroundcolor == "#16213e"
        assert light.layout.scene.xaxis.backgroundcolor == "#f8f9fa"


# ---------------------------------------------------------------------------
# isosurface_3d
# ---------------------------------------------------------------------------


class TestIsosurface3D:
    def test_returns_isosurface_trace_with_xyz_value(self) -> None:
        fig = Chart3DBuilder(ISOSURFACE_DATA).isosurface_3d("x", "y", "z", "temp", title="Iso")
        assert isinstance(fig, go.Figure)
        assert isinstance(fig.data[0], go.Isosurface)
        tr = fig.data[0]
        assert list(tr.x) == [0.0, 1.0, 0.0, 0.0, 1.0]
        assert list(tr.z) == [0.0, 0.0, 0.0, 1.0, 1.0]
        assert list(tr.value) == [5.0, 8.0, 12.0, 15.0, 20.0]
        assert fig.layout.title.text == "Iso"
        # scene styled by the 3D builder
        assert fig.layout.scene.xaxis.showbackground is True

    def test_default_iso_bounds_from_value_minmax(self) -> None:
        fig = Chart3DBuilder(ISOSURFACE_DATA).isosurface_3d("x", "y", "z", "temp")
        # isomin/isomax default to the value column's min/max
        assert fig.data[0].isomin == 5.0
        assert fig.data[0].isomax == 20.0

    def test_explicit_iso_bounds_passthrough(self) -> None:
        fig = Chart3DBuilder(ISOSURFACE_DATA).isosurface_3d("x", "y", "z", "temp", isomin=10.0, isomax=15.0)
        assert fig.data[0].isomin == 10.0
        assert fig.data[0].isomax == 15.0

    def test_opacity_passthrough(self) -> None:
        fig = Chart3DBuilder(ISOSURFACE_DATA).isosurface_3d("x", "y", "z", "temp", opacity=0.25)
        assert fig.data[0].opacity == 0.25

    def test_custom_colorscale_override(self) -> None:
        # Plotly resolves a named colorscale to its rgb stop list at construction;
        # verify the override took effect by comparing first-stop colors.
        viridis = Chart3DBuilder(ISOSURFACE_DATA).isosurface_3d("x", "y", "z", "temp")
        rdbu = Chart3DBuilder(ISOSURFACE_DATA).isosurface_3d("x", "y", "z", "temp", colorscale="RdBu")
        assert viridis.data[0].colorscale[0][1] != rdbu.data[0].colorscale[0][1]
        # RdBu's low stop is a deep red
        assert rdbu.data[0].colorscale[0][1] == "rgb(103,0,31)"

    def test_light_theme_switches_scene_bgcolor(self) -> None:
        dark = Chart3DBuilder(ISOSURFACE_DATA).isosurface_3d("x", "y", "z", "temp", theme="dark")
        light = Chart3DBuilder(ISOSURFACE_DATA).isosurface_3d("x", "y", "z", "temp", theme="light")
        assert dark.layout.scene.xaxis.backgroundcolor == "#16213e"
        assert light.layout.scene.xaxis.backgroundcolor == "#f8f9fa"

    def test_professional_theme_salmon_scene(self) -> None:
        from serbian_data_mcp.viz.themes import PROFESSIONAL_PAPER

        prof = Chart3DBuilder(ISOSURFACE_DATA).isosurface_3d("x", "y", "z", "temp", theme="professional")
        # 3D scene honors the FT salmon-paper background + ink-dark axis text
        assert prof.layout.scene.xaxis.backgroundcolor == PROFESSIONAL_PAPER
        assert prof.layout.scene.xaxis.tickfont.color == "#333333"
