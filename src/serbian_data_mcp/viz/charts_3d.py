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

from .themes import SEMANTIC_COLORS, apply_theme

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
        a 2D one without visual clash.
        """
        dark = theme != "light"
        grid = "rgba(255,255,255,0.08)" if dark else "#e9ecef"
        zeroline = "rgba(255,255,255,0.18)" if dark else "#adb5bd"
        tick = "#78909c" if dark else "#6c757d"
        title_color = "#90a4ae" if dark else "#495057"
        bgcolor = "#16213e" if dark else "#f8f9fa"

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
        fig = px.scatter_3d(
            self.data,
            x=x_column,
            y=y_column,
            z=z_column,
            color=color_column,
            symbol=symbol_column,
            size=size_column,
            title=title,
            color_discrete_sequence=SEMANTIC_COLORS,
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
        fig = px.line_3d(
            self.data,
            x=x_column,
            y=y_column,
            z=z_column,
            color=color_column,
            title=title,
            color_discrete_sequence=SEMANTIC_COLORS,
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
