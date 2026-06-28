"""MCP tool wrappers for interactive 3D charts.

Contracts:
  - create_scatter_3d(data, x_column, y_column, z_column) → HTML filepath
  - create_line_3d(data, x_column, y_column, z_column) → HTML filepath
  - create_surface_3d(data, x_column, y_column, z_column) → HTML filepath
  - create_mesh_3d(data, x_column, y_column, z_column) → HTML filepath
  - create_isosurface_3d(data, x_column, y_column, z_column, value_column) → HTML filepath
  - create_cone_3d(data, x_column, y_column, z_column, u_column, v_column, w_column) → HTML filepath

These expose the WebGL-rendered 3D builders from ``viz.charts_3d.Chart3DBuilder``
as MCP tools so the server's clients can produce orbit-able, depth-rich charts
(lat/lon/altitude, multi-metric relationships, gridded scalar fields) alongside
the existing 2D chart families.
"""

from __future__ import annotations

from typing import Any, Optional

from fastmcp.exceptions import ToolError

from .. import mcp
from ..config import config
from ..viz.charts_3d import Chart3DBuilder
from ..viz.exporters import export_html


def _save_html(fig, filename: str) -> str:
    """Save a Plotly figure to HTML and return the filepath."""
    output_dir = config.export_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{filename}.html"
    filepath.write_text(export_html(fig), encoding="utf-8")
    return str(filepath)


@mcp.tool()
async def create_scatter_3d(
    data: list[dict[str, Any]],
    x_column: str,
    y_column: str,
    z_column: str,
    title: str = "",
    theme: str = "dark",
    color_column: Optional[str] = None,
    size_column: Optional[str] = None,
    symbol_column: Optional[str] = None,
    filename: str = "scatter_3d",
) -> dict[str, Any]:
    """Interactive 3D scatter / bubble chart (WebGL, orbit-able).

    Plots three numeric dimensions as points in 3-space, with optional color,
    bubble size, and marker shape encoding up to three more variables.

    Ideal for: spatial data (lat/lon/altitude), district × year × population,
    exploring three census indicators at once.

    Returns: {filepath, title, rows}

    Args:
        data: Row dicts
        x_column: Column for the X axis
        y_column: Column for the Y axis
        z_column: Column for the Z axis (depth)
        title: Chart title
        theme: 'dark', 'light', or 'infographic'
        color_column: Optional column driving marker color
        size_column: Optional column driving bubble size
        symbol_column: Optional column driving marker shape
        filename: Output filename (without .html)
    """
    try:
        fig = Chart3DBuilder(data).scatter_3d(
            x_column,
            y_column,
            z_column,
            title=title,
            theme=theme,
            color_column=color_column,
            size_column=size_column,
            symbol_column=symbol_column,
        )
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "title": title, "rows": len(data)}
    except Exception as e:
        raise ToolError(f"3D scatter chart failed: {e}") from e


@mcp.tool()
async def create_line_3d(
    data: list[dict[str, Any]],
    x_column: str,
    y_column: str,
    z_column: str,
    title: str = "",
    theme: str = "dark",
    color_column: Optional[str] = None,
    filename: str = "line_3d",
) -> dict[str, Any]:
    """Interactive 3D line / trajectory chart (WebGL, orbit-able).

    Connects points through 3-space — a trajectory. Split into one line per
    category via color_column.

    Ideal for: a route through lat/lon/altitude, a metric evolving across
    region × time, multi-decade demographic trajectories.

    Returns: {filepath, title, rows}

    Args:
        data: Row dicts
        x_column: Column for the X axis
        y_column: Column for the Y axis
        z_column: Column for the Z axis (depth)
        title: Chart title
        theme: 'dark', 'light', or 'infographic'
        color_column: Optional column splitting points into separate lines
        filename: Output filename (without .html)
    """
    try:
        fig = Chart3DBuilder(data).line_3d(
            x_column,
            y_column,
            z_column,
            title=title,
            theme=theme,
            color_column=color_column,
        )
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "title": title, "rows": len(data)}
    except Exception as e:
        raise ToolError(f"3D line chart failed: {e}") from e


@mcp.tool()
async def create_surface_3d(
    data: list[dict[str, Any]],
    x_column: str,
    y_column: str,
    z_column: str,
    title: str = "",
    theme: str = "dark",
    colorscale: str = "Viridis",
    filename: str = "surface_3d",
) -> dict[str, Any]:
    """Interactive 3D surface (landscape) chart from gridded data (WebGL, orbit-able).

    Long-format (x, y, z) rows are pivoted into a z-value grid and rendered as
    a continuous surface. Suited to elevation, density, or any scalar field
    sampled on a regular grid.

    Ideal for: temperature/air-quality across city × month, terrain surfaces,
    optimization landscapes.

    Returns: {filepath, title, rows}

    Args:
        data: Row dicts (one per (x, y) grid cell)
        x_column: Column forming the surface's X grid
        y_column: Column forming the surface's Y grid
        z_column: Column giving the surface height
        title: Chart title
        theme: 'dark', 'light', or 'infographic'
        colorscale: Plotly colorscale name for height mapping
        filename: Output filename (without .html)
    """
    try:
        fig = Chart3DBuilder(data).surface_3d(
            x_column,
            y_column,
            z_column,
            title=title,
            theme=theme,
            colorscale=colorscale,
        )
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "title": title, "rows": len(data)}
    except Exception as e:
        raise ToolError(f"3D surface chart failed: {e}") from e


@mcp.tool()
async def create_mesh_3d(
    data: list[dict[str, Any]],
    x_column: str,
    y_column: str,
    z_column: str,
    title: str = "",
    theme: str = "dark",
    intensity_column: Optional[str] = None,
    colorscale: str = "Viridis",
    alphahull: float = 1.0,
    face_color: Optional[str] = None,
    filename: str = "mesh_3d",
) -> dict[str, Any]:
    """Interactive 3D mesh from scattered points (WebGL, orbit-able).

    Triangulates *scattered* (x, y, z) points into a connected surface or
    enclosing hull — unlike ``create_surface_3d`` which needs a regular grid.
    An optional ``intensity_column`` colors each vertex by a fourth metric.

    Ideal for: irregular terrain/field point clouds, region bounding shapes,
    sparse 3D samples (e.g. pollution at uneven monitoring stations).

    Returns: {filepath, title, rows}

    Args:
        data: Row dicts (one per scattered sample point)
        x_column: Column for the X axis
        y_column: Column for the Y axis
        z_column: Column for the Z axis (depth)
        title: Chart title
        theme: 'dark', 'light', or 'infographic'
        intensity_column: Optional column driving per-vertex color
        colorscale: Plotly colorscale name for intensity mapping
        alphahull: 0 = convex hull, >0 = alpha shape, -1 = Delaunay (SciPy)
        face_color: Solid mesh color when no intensity_column is given
        filename: Output filename (without .html)
    """
    try:
        fig = Chart3DBuilder(data).mesh_3d(
            x_column,
            y_column,
            z_column,
            title=title,
            theme=theme,
            intensity_column=intensity_column,
            colorscale=colorscale,
            alphahull=alphahull,
            face_color=face_color,
        )
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "title": title, "rows": len(data)}
    except Exception as e:
        raise ToolError(f"3D mesh chart failed: {e}") from e


@mcp.tool()
async def create_isosurface_3d(
    data: list[dict[str, Any]],
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
    filename: str = "isosurface_3d",
) -> dict[str, Any]:
    """Interactive 3D iso-surface from a volumetric scalar field (WebGL, orbit-able).

    Renders the 3D boundary where ``value_column`` falls within [isomin, isomax] —
    a level set of a continuous fourth variable sampled across (x, y, z). The
    marching-cubes extraction runs client-side at render, so scattered samples
    are accepted without a regular grid or SciPy.

    Ideal for: pollution/concentration thresholds across a 3D monitoring volume,
    isotherms, groundwater head surfaces, any "region where value ≥ threshold".

    Returns: {filepath, title, rows}

    Args:
        data: Row dicts (one per volumetric sample point)
        x_column: Column for the X axis
        y_column: Column for the Y axis
        z_column: Column for the Z axis (depth)
        value_column: Column whose level sets define the surface
        title: Chart title
        theme: 'dark', 'light', or 'professional'
        isomin: Lower scalar bound (defaults to column min)
        isomax: Upper scalar bound (defaults to column max)
        colorscale: Plotly colorscale name for value mapping
        opacity: Surface opacity (0–1)
        filename: Output filename (without .html)
    """
    try:
        fig = Chart3DBuilder(data).isosurface_3d(
            x_column,
            y_column,
            z_column,
            value_column,
            title=title,
            theme=theme,
            isomin=isomin,
            isomax=isomax,
            colorscale=colorscale,
            opacity=opacity,
        )
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "title": title, "rows": len(data)}
    except Exception as e:
        raise ToolError(f"3D isosurface chart failed: {e}") from e


@mcp.tool()
async def create_cone_3d(
    data: list[dict[str, Any]],
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
    filename: str = "cone_3d",
) -> dict[str, Any]:
    """Interactive 3D vector field / quiver plot (WebGL, orbit-able).

    Renders a cone at each (x, y, z) anchor pointing along the vector
    (u, v, w) — a 3D arrow field of direction + magnitude. Cones are colored
    by vector magnitude and sized by sizeref. Distinct from the scalar 3D
    charts: a cone field encodes a *vector* (flow, gradient, force) at each
    sample point.

    Ideal for: wind / air-flow fields, magnetic or electric fields, fluid-flow
    simulations, gradient directions across a 3D domain.

    Returns: {filepath, title, rows}

    Args:
        data: Row dicts (one per vector sample)
        x_column: Column for the anchor X position
        y_column: Column for the anchor Y position
        z_column: Column for the anchor Z position (depth)
        u_column: Column for the vector X component
        v_column: Column for the vector Y component
        w_column: Column for the vector Z component
        title: Chart title
        theme: 'dark', 'light', or 'professional'
        sizemode: 'scaled' (default) or 'absolute'
        sizeref: Cone length scale factor
        anchor: 'tail' (default), 'center', or 'tip'
        colorscale: Plotly colorscale name for magnitude mapping
        filename: Output filename (without .html)
    """
    try:
        fig = Chart3DBuilder(data).cone_3d(
            x_column,
            y_column,
            z_column,
            u_column,
            v_column,
            w_column,
            title=title,
            theme=theme,
            sizemode=sizemode,
            sizeref=sizeref,
            anchor=anchor,
            colorscale=colorscale,
        )
        filepath = _save_html(fig, filename)
        return {"filepath": filepath, "title": title, "rows": len(data)}
    except Exception as e:
        raise ToolError(f"3D cone chart failed: {e}") from e
