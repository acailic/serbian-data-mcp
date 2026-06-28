"""Interactive 3D charts rendered via Plotly's WebGL engine.

True 3D — rotatable, zoomable, rendered client-side via WebGL. Adds a third
visual dimension to datasets where two axes are not enough: spatial data
(lat/lon/altitude), multi-metric relationships, or a surface over a grid.

All charts are themed via :func:`serbian_data_mcp.viz.themes.apply_theme`, with
a matching ``scene`` (the 3D equivalent of xaxis/yaxis) styled for a
professional look. Use ``apply_theme(fig, "light")`` to switch themes.
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .themes import PROFESSIONAL_COLORS, PROFESSIONAL_PAPER, SEMANTIC_COLORS, apply_theme

__all__ = ["Chart3DBuilder"]


class Chart3DBuilder:
    """Builder for interactive 3D charts with themed, professional defaults.

    Every chart returns a :class:`plotly.graph_objects.Figure` whose ``scene``
    (3D axes + camera) is styled to match the chosen theme. The figure renders
    client-side via WebGL, so end users can orbit, zoom, and pan.
    """

    def __init__(self, data: list[dict[str, Any]] | pd.DataFrame) -> None:
        """Initialize the 3D builder with tabular data.

        Args:
            data: DataFrame or list of dicts. Columns are referenced by name
                in each chart method.
        """
        if isinstance(data, list):
            self.data = pd.DataFrame(data)
        else:
            self.data = data

    @staticmethod
    def _scene_layout(theme: str) -> dict[str, Any]:
        """Build a themed 3D ``scene`` layout dict.

        Mirrors the 2D themes' grid/axis treatment so a 3D chart sits next to
        a 2D one without visual clash. The ``professional`` theme gets the FT
        salmon-paper scene + ink-dark axis text; ``light`` gets soft gray;
        anything else (``dark``/``infographic``) gets the dark space scene.
        """
        if theme == "light":
            grid, zeroline, tick, title_color, bgcolor = (
                "#e9ecef",
                "#adb5bd",
                "#6c757d",
                "#495057",
                "#f8f9fa",
            )
        elif theme == "professional":
            grid, zeroline, tick, title_color, bgcolor = (
                "#e8dcd0",
                "#bdb3a7",
                "#333333",
                "#121212",
                PROFESSIONAL_PAPER,
            )
        else:  # dark / infographic
            grid = "rgba(255,255,255,0.08)"
            zeroline = "rgba(255,255,255,0.18)"
            tick = "#78909c"
            title_color = "#90a4ae"
            bgcolor = "#16213e"

        def _axis() -> dict[str, Any]:
            return {
                "backgroundcolor": bgcolor,
                "gridcolor": grid,
                "zerolinecolor": zeroline,
                "showbackground": True,
                "tickfont": {"color": tick, "size": 11},
                "title": {"font": {"color": title_color, "size": 13}},
            }

        return {
            "xaxis": _axis(),
            "yaxis": _axis(),
            "zaxis": _axis(),
            # Slightly elevated camera for a depth-revealing default angle.
            "camera": {"eye": {"x": 1.6, "y": 1.6, "z": 0.9}},
            "aspectmode": "auto",
        }

    def scatter_3d(
        self,
        x_column: str,
        y_column: str,
        z_column: str,
        title: str = "",
        theme: str = "dark",
        color_column: Optional[str] = None,
        size_column: Optional[str] = None,
        symbol_column: Optional[str] = None,
    ) -> go.Figure:
        """Create a 3D scatter / bubble chart.

        Ideal for showing relationships across three numeric dimensions plus an
        optional categorical color (e.g. city), an optional bubble size, and an
        optional marker shape.

        Args:
            x_column: Column for the X axis
            y_column: Column for the Y axis
            z_column: Column for the Z axis (depth)
            title: Chart title
            theme: 'dark', 'light', or 'infographic'
            color_column: Optional column for color grouping
            size_column: Optional column driving bubble size
            symbol_column: Optional column driving marker shape
        """
        palette = PROFESSIONAL_COLORS if theme == "professional" else SEMANTIC_COLORS
        fig = px.scatter_3d(
            self.data,
            x=x_column,
            y=y_column,
            z=z_column,
            color=color_column,
            symbol=symbol_column,
            size=size_column,
            title=title,
            color_discrete_sequence=palette,
        )
        fig.update_traces(marker_line={"width": 0}, selector={"type": "scatter3d"})
        fig.update_layout(
            scene=self._scene_layout(theme),
            margin={"l": 0, "r": 0, "t": 60, "b": 0},
        )
        apply_theme(fig, theme)
        return fig

    def line_3d(
        self,
        x_column: str,
        y_column: str,
        z_column: str,
        title: str = "",
        theme: str = "dark",
        color_column: Optional[str] = None,
    ) -> go.Figure:
        """Create a 3D line chart — a trajectory through 3-space.

        Use for spatial tracks (lat/lon/altitude over a route), parameter
        sweeps, or any ordered progression through three dimensions.

        Args:
            x_column: Column for the X axis
            y_column: Column for the Y axis
            z_column: Column for the Z axis (depth)
            title: Chart title
            theme: 'dark', 'light', or 'infographic'
            color_column: Optional column splitting points into separate lines
        """
        palette = PROFESSIONAL_COLORS if theme == "professional" else SEMANTIC_COLORS
        fig = px.line_3d(
            self.data,
            x=x_column,
            y=y_column,
            z=z_column,
            color=color_column,
            title=title,
            color_discrete_sequence=palette,
        )
        fig.update_traces(mode="lines+markers", selector={"type": "scatter3d"})
        fig.update_layout(
            scene=self._scene_layout(theme),
            margin={"l": 0, "r": 0, "t": 60, "b": 0},
        )
        apply_theme(fig, theme)
        return fig

    def surface_3d(
        self,
        x_column: str,
        y_column: str,
        z_column: str,
        title: str = "",
        theme: str = "dark",
        colorscale: str = "Viridis",
    ) -> go.Figure:
        """Create a 3D surface chart from gridded data.

        Long-format (x, y, z) rows are pivoted into a z-value grid, then
        rendered as a continuous surface mesh — suited to elevation, density,
        or any scalar field sampled on a regular grid.

        Args:
            x_column: Column for the X axis (grid columns)
            y_column: Column for the Y axis (grid rows)
            z_column: Column for the surface height
            title: Chart title
            theme: 'dark', 'light', or 'infographic'
            colorscale: Plotly colorscale name for height mapping
        """
        pivot = self.data.pivot_table(index=y_column, columns=x_column, values=z_column)
        surface = go.Surface(
            z=pivot.values,
            x=list(pivot.columns),
            y=list(pivot.index),
            colorscale=colorscale,
        )
        fig = go.Figure(data=[surface])
        if title:
            fig.update_layout(title={"text": title})
        fig.update_layout(
            scene=self._scene_layout(theme),
            margin={"l": 0, "r": 0, "t": 60, "b": 0},
        )
        apply_theme(fig, theme)
        return fig

    def mesh_3d(
        self,
        x_column: str,
        y_column: str,
        z_column: str,
        title: str = "",
        theme: str = "dark",
        intensity_column: Optional[str] = None,
        colorscale: str = "Viridis",
        alphahull: float = 1.0,
        face_color: Optional[str] = None,
    ) -> go.Figure:
        """Create a 3D mesh from scattered points (a surface or volume hull).

        Unlike :meth:`surface_3d` (which needs a regular z=f(x,y) grid), a mesh
        triangulates *scattered* (x, y, z) points into a connected surface or
        enclosing hull — suited to irregular point clouds: terrain surveyed at
        uneven stations, a 3D field probed at sparse sample sites, or the
        bounding shape of a multi-dimensional region.

        An optional ``intensity_column`` colors each vertex by a fourth metric
        (e.g. pollution concentration at each station) via a Plotly colorscale;
        otherwise the mesh is a single solid ``face_color``.

        Args:
            x_column: Column for the X axis
            y_column: Column for the Y axis
            z_column: Column for the Z axis (depth)
            title: Chart title
            theme: 'dark', 'light', or 'infographic'
            intensity_column: Optional column driving per-vertex color
            colorscale: Plotly colorscale name for intensity mapping
            alphahull: Plotly alpha-shape parameter — 0 = convex hull, >0 =
                alpha shape (tighter hull), -1 = Delaunay (needs SciPy). The
                triangulation runs client-side at render, not at build time.
            face_color: Solid mesh color when no intensity_column is given
        """
        intensity = self.data[intensity_column].tolist() if intensity_column else None
        mesh = go.Mesh3d(
            x=self.data[x_column].tolist(),
            y=self.data[y_column].tolist(),
            z=self.data[z_column].tolist(),
            intensity=intensity,
            colorscale=colorscale,
            alphahull=alphahull,
            # go.Mesh3d's facecolor expects a per-triangle array; a single solid
            # color is the trace-level `color` attribute instead.
            color=face_color,
        )
        fig = go.Figure(data=[mesh])
        if title:
            fig.update_layout(title={"text": title})
        fig.update_layout(
            scene=self._scene_layout(theme),
            margin={"l": 0, "r": 0, "t": 60, "b": 0},
        )
        apply_theme(fig, theme)
        return fig

    def isosurface_3d(
        self,
        x_column: str,
        y_column: str,
        z_column: str,
        value_column: str,
        title: str = "",
        theme: str = "dark",
        isomin: Optional[float] = None,
        isomax: Optional[float] = None,
        colorscale: str = "Viridis",
        opacity: float = 0.5,
    ) -> go.Figure:
        """Create a 3D iso-surface from a volumetric scalar field.

        An iso-surface is the 3D locus where a scalar ``value_column`` equals a
        threshold — the boundary of a region (e.g. the surface enclosing every
        point where PM2.5 concentration ≥ 50 µg/m³, or the 15°C isotherm in a
        temperature volume). Distinct from :meth:`surface_3d` (a single
        z=f(x,y) height sheet) and :meth:`mesh_3d` (a hull through scattered
        points with no scalar field): an iso-surface extracts *level sets* of a
        fourth continuous variable sampled across (x, y, z).

        Plotly accepts scattered (x, y, z, value) samples and runs the
        marching-cubes iso-extraction client-side at JS render time, so no
        SciPy or regular grid is required to build the figure.

        Args:
            x_column: Column for the X axis
            y_column: Column for the Y axis
            z_column: Column for the Z axis (depth)
            value_column: Column whose level sets define the surface
            title: Chart title
            theme: 'dark', 'light', or 'professional'
            isomin: Lower scalar bound of the iso region; defaults to the
                column minimum
            isomax: Upper scalar bound of the iso region; defaults to the
                column maximum
            colorscale: Plotly colorscale name for value mapping
            opacity: Surface opacity (0–1) so nested/overlapping level sets
                remain legible
        """
        values = self.data[value_column].tolist()
        iso = go.Isosurface(
            x=self.data[x_column].tolist(),
            y=self.data[y_column].tolist(),
            z=self.data[z_column].tolist(),
            value=values,
            isomin=isomin if isomin is not None else float(min(values)),
            isomax=isomax if isomax is not None else float(max(values)),
            colorscale=colorscale,
            opacity=opacity,
        )
        fig = go.Figure(data=[iso])
        if title:
            fig.update_layout(title={"text": title})
        fig.update_layout(
            scene=self._scene_layout(theme),
            margin={"l": 0, "r": 0, "t": 60, "b": 0},
        )
        apply_theme(fig, theme)
        return fig

    def cone_3d(
        self,
        x_column: str,
        y_column: str,
        z_column: str,
        u_column: str,
        v_column: str,
        w_column: str,
        title: str = "",
        theme: str = "dark",
        sizemode: str = "scaled",
        sizeref: float = 1.0,
        anchor: str = "tail",
        colorscale: str = "Viridis",
    ) -> go.Figure:
        """Create a 3D vector field (quiver plot) of direction + magnitude.

        Renders a cone at each (x, y, z) anchor pointing along the vector
        (u, v, w) — a 3D arrow field. Distinct from the other five 3D types,
        which encode scalar position / height / intensity: a cone field encodes
        a *vector* (direction + magnitude) at each sample, so it reveals flow,
        gradient, or force structure rather than a surface or locus.

        Cones are colored by vector magnitude (|(u, v, w)|) via the colorscale,
        sized by ``sizeref``, and anchored tail/center/tip via ``anchor``.
        Plotly renders client-side over WebGL — no SciPy or regular grid needed.

        Args:
            x_column: Column for the anchor X position
            y_column: Column for the anchor Y position
            z_column: Column for the anchor Z position (depth)
            u_column: Column for the vector X component
            v_column: Column for the vector Y component
            w_column: Column for the vector Z component
            title: Chart title
            theme: 'dark', 'light', or 'professional'
            sizemode: 'scaled' (cones scale with magnitude, default) or
                'absolute' (uniform length)
            sizeref: Scale factor controlling cone length (larger = longer)
            anchor: Where the cone attaches to the point — 'tail' (default),
                'center', or 'tip'
            colorscale: Plotly colorscale name for magnitude mapping
        """
        cone = go.Cone(
            x=self.data[x_column].tolist(),
            y=self.data[y_column].tolist(),
            z=self.data[z_column].tolist(),
            u=self.data[u_column].tolist(),
            v=self.data[v_column].tolist(),
            w=self.data[w_column].tolist(),
            sizemode=sizemode,
            sizeref=sizeref,
            anchor=anchor,
            colorscale=colorscale,
        )
        fig = go.Figure(data=[cone])
        if title:
            fig.update_layout(title={"text": title})
        fig.update_layout(
            scene=self._scene_layout(theme),
            margin={"l": 0, "r": 0, "t": 60, "b": 0},
        )
        apply_theme(fig, theme)
        return fig
