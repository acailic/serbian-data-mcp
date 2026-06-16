"""Advanced map visualizations: bubble maps, multi-layer maps, animated maps.

Extends the base SerbiaMapBuilder with additional cartographic capabilities
for more expressive spatial data visualization.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go

from .maps import SerbiaMapBuilder, _load_serbia_geojson, _HEAT_RED, _SEQUENTIAL_BLUE, _RED_BLUE_DIVERGING
from .themes import apply_theme, SEMANTIC_COLORS

logger = logging.getLogger(__name__)


class AdvancedMapBuilder(SerbiaMapBuilder):
    """Extended map builder with bubble, multi-layer, and animated maps.

    Inherits all choropleth capabilities from SerbiaMapBuilder and adds:
    - Bubble maps for absolute values (population, budget)
    - Multi-layer maps for overlaying multiple indicators
    - Ranked scatter maps for district comparison
    """

    def bubble_map(
        self,
        data: list[dict[str, Any]],
        name_column: str,
        value_column: str,
        title: str = "",
        theme: str = "dark",
        bubble_color: str = "#1565c0",
        size_scale: float = 1.0,
        show_district_labels: bool = False,
        second_value_column: Optional[str] = None,
        second_color: str = "#c62828",
    ) -> go.Figure:
        """Create a bubble map showing absolute values per district.

        Unlike choropleth (which colors by value per area), bubble maps
        represent magnitude with circle size. This avoids the "large district
        bias" problem where sparsely-populated districts dominate the visual.

        Args:
            data: List of row dicts with district names and values
            name_column: Column containing district names
            value_column: Column containing numeric values (determines bubble size)
            title: Chart title
            theme: Visual theme
            bubble_color: Color for primary bubbles
            size_scale: Multiplier for bubble size
            show_district_labels: Show district name labels
            second_value_column: Optional second metric for overlay bubbles
            second_color: Color for second set of bubbles

        Returns:
            Plotly Figure
        """
        df = pd.DataFrame(data)
        df["_code"] = df[name_column].apply(self.resolve_name)
        df_valid = df.dropna(subset=["_code"])

        if df_valid.empty:
            logger.warning("No matching districts found for bubble map")
            return go.Figure()

        # Calculate district centroids from GeoJSON
        centroids = self._compute_centroids()
        df_valid["_lon"] = df_valid["_code"].map(centroids)
        df_valid = df_valid.dropna(subset=["_lon"])

        if df_valid.empty:
            return go.Figure()

        vals = df_valid[value_column].astype(float)
        min_size = 10 * size_scale
        max_size = 60 * size_scale
        val_range = vals.max() - vals.min() if vals.max() != vals.min() else 1
        sizes = min_size + (vals - vals.min()) / val_range * (max_size - min_size)

        fig = go.Figure(
            go.Scattergeo(
                lon=df_valid["_lon"].map(lambda v: v[0]),
                lat=df_valid["_lon"].map(lambda v: v[1]),
                text=df_valid[name_column],
                marker={
                    "size": sizes,
                    "color": bubble_color,
                    "opacity": 0.8,
                    "line": {"width": 1, "color": "rgba(255,255,255,0.5)"},
                    "sizemode": "area",
                },
                hovertemplate=(f"<b>%{{text}}</b><br>{value_column}: %{{customdata[0]:,.0f}}<extra></extra>"),
                customdata=df_valid[[value_column]].values.tolist(),
                name=value_column,
            )
        )

        # Second layer of bubbles
        if second_value_column:
            vals2 = df_valid[second_value_column].astype(float)
            sizes2 = min_size + (vals2 - vals2.min()) / (vals2.max() - vals2.min() + 1e-9) * (max_size - min_size)
            fig.add_trace(
                go.Scattergeo(
                    lon=df_valid["_lon"].map(lambda v: v[0]),
                    lat=df_valid["_lon"].map(lambda v: v[1]),
                    text=df_valid[name_column],
                    marker={
                        "size": sizes2,
                        "color": second_color,
                        "opacity": 0.6,
                        "line": {"width": 1, "color": "rgba(255,255,255,0.5)"},
                        "sizemode": "area",
                    },
                    hovertemplate=(
                        f"<b>%{{text}}</b><br>{second_value_column}: %{{customdata[0]:,.0f}}<extra></extra>"
                    ),
                    customdata=df_valid[[second_value_column]].values.tolist(),
                    name=second_value_column,
                )
            )

        # District labels
        if show_district_labels:
            fig.add_trace(
                go.Scattergeo(
                    lon=df_valid["_lon"].map(lambda v: v[0]),
                    lat=df_valid["_lon"].map(lambda v: v[1] + 0.15),
                    text=df_valid[name_column],
                    mode="text",
                    textfont={"size": 9, "color": "#b0bec5"},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

        fig.update_geos(
            scope="europe",
            resolution=50,
            showframe=False,
            showcountries=True,
            countrycolor="rgba(255,255,255,0.1)",
            showsubunits=False,
            fitbounds="locations",
            bgcolor="rgba(0,0,0,0)",
            projection={"type": "mercator"},
        )

        fig.update_layout(
            title={"text": title, "font": {"size": 22}, "x": 0.05, "xanchor": "left"},
            margin={"l": 20, "r": 20, "t": 70, "b": 20},
            legend={"orientation": "h", "yanchor": "bottom", "y": -0.05, "x": 0.05},
        )

        fig = apply_theme(fig, theme)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", geo={"bgcolor": "rgba(0,0,0,0)"})
        return fig

    def multi_layer_map(
        self,
        layers: list[dict[str, Any]],
        title: str = "",
        theme: str = "dark",
    ) -> go.Figure:
        """Create a multi-layer choropleth map with toggle controls.

        Each layer is a separate dataset rendered as a choropleth with a
        button to toggle between them. Ideal for comparing multiple
        indicators on the same geography.

        Args:
            layers: List of layer dicts, each with:
                - 'data' (list[dict]): Data for this layer
                - 'name_column' (str): District name column
                - 'value_column' (str): Value column
                - 'label' (str): Display name for this layer
                - 'colorscale' (str): 'blue', 'red', 'heat', or 'diverging'
            title: Map title
            theme: Visual theme

        Returns:
            Plotly Figure with layer toggle buttons
        """
        color_map = {
            "blue": _SEQUENTIAL_BLUE,
            "red": _HEAT_RED,
            "diverging": _RED_BLUE_DIVERGING,
            "heat": _HEAT_RED,
        }

        traces = []
        for layer in layers:
            df = pd.DataFrame(layer["data"])
            df["_code"] = df[layer["name_column"]].apply(self.resolve_name)
            df_valid = df.dropna(subset=["_code"])

            if df_valid.empty:
                continue

            cs = color_map.get(layer.get("colorscale", "blue"), _SEQUENTIAL_BLUE)

            trace = go.Choropleth(
                geojson=self.geojson,
                locations=df_valid["_code"].tolist(),
                z=df_valid[layer["value_column"]].tolist(),
                featureidkey="properties.adm1_code",
                colorscale=cs,
                marker_line_color="rgba(255,255,255,0.4)",
                marker_line_width=0.5,
                zmin=float(df_valid[layer["value_column"]].min()),
                zmax=float(df_valid[layer["value_column"]].max()),
                colorbar={
                    "title": {"text": layer["label"], "font": {"size": 12}},
                    "thickness": 12,
                    "len": 0.7,
                    "x": 0.85,
                },
                hovertemplate=(f"<b>%{{properties.name}}</b><br>{layer['value_column']}: %{{z:,.0f}}<extra></extra>"),
                name=layer["label"],
                visible=(layer == layers[0]),
            )
            traces.append(trace)

        if not traces:
            return go.Figure()

        # Build toggle buttons
        buttons = []
        for i, layer in enumerate(layers):
            visibility = [j == i for j in range(len(traces))]
            buttons.append(
                {
                    "label": layer["label"],
                    "method": "update",
                    "args": [{"visible": visibility}],
                }
            )

        fig = go.Figure(data=traces)
        fig.update_geos(
            scope="europe",
            resolution=50,
            showframe=False,
            showcountries=True,
            countrycolor="rgba(255,255,255,0.1)",
            fitbounds="locations",
            bgcolor="rgba(0,0,0,0)",
            projection={"type": "mercator"},
        )

        fig.update_layout(
            title={"text": title, "font": {"size": 22}, "x": 0.05, "xanchor": "left"},
            margin={"l": 20, "r": 20, "t": 70, "b": 20},
            updatemenus=[
                {
                    "type": "buttons",
                    "direction": "right",
                    "active": 0,
                    "x": 0.05,
                    "y": -0.05,
                    "xanchor": "right",
                    "yanchor": "top",
                    "buttons": buttons,
                    "showactive": True,
                    "font": {"size": 12},
                }
            ],
        )

        fig = apply_theme(fig, theme)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", geo={"bgcolor": "rgba(0,0,0,0)"})
        return fig

    def ranked_scatter_map(
        self,
        data: list[dict[str, Any]],
        name_column: str,
        x_value_column: str,
        y_value_column: str,
        title: str = "",
        theme: str = "dark",
        size_column: Optional[str] = None,
        label_column: Optional[str] = None,
    ) -> go.Figure:
        """Create a scatter plot positioned on the Serbia map.

        Districts are positioned by their geographic centroids but
        sized/colored by data values. Creates a cartogram-like effect.

        Args:
            data: List of row dicts
            name_column: District names
            x_value_column: Determines X position or value (e.g., population)
            y_value_column: Determines Y position or value (e.g., budget)
            title: Chart title
            theme: Visual theme
            size_column: Optional column for bubble size
            label_column: Optional column for custom labels

        Returns:
            Plotly Figure
        """
        df = pd.DataFrame(data)
        df["_code"] = df[name_column].apply(self.resolve_name)
        df_valid = df.dropna(subset=["_code"])

        if df_valid.empty:
            return go.Figure()

        centroids = self._compute_centroids()
        df_valid["_lon"] = df_valid["_code"].map(centroids)
        df_valid = df_valid.dropna(subset=["_lon"])

        if df_valid.empty:
            return go.Figure()

        # Color by y_value
        y_vals = df_valid[y_value_column].astype(float)

        sizes = [15] * len(df_valid)
        if size_column and size_column in df_valid.columns:
            s_vals = df_valid[size_column].astype(float)
            sizes = 10 + (s_vals - s_vals.min()) / (s_vals.max() - s_vals.min() + 1e-9) * 40

        display_labels = (
            df_valid[label_column].tolist()
            if label_column and label_column in df_valid.columns
            else df_valid[name_column].tolist()
        )

        fig = go.Figure(
            go.Scattergeo(
                lon=df_valid["_lon"].map(lambda v: v[0]),
                lat=df_valid["_lon"].map(lambda v: v[1]),
                text=display_labels,
                marker={
                    "size": sizes,
                    "color": y_vals,
                    "colorscale": _SEQUENTIAL_BLUE,
                    "opacity": 0.85,
                    "line": {"width": 1, "color": "white"},
                    "colorbar": {
                        "title": {"text": y_value_column, "font": {"size": 12}},
                        "thickness": 12,
                        "len": 0.7,
                        "x": 0.85,
                    },
                    "sizemode": "area",
                },
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    f"{x_value_column}: %{{customdata[0]:,.0f}}<br>"
                    f"{y_value_column}: %{{customdata[1]:,.0f}}<extra></extra>"
                ),
                customdata=df_valid[[x_value_column, y_value_column]].values.tolist(),
            )
        )

        fig.update_geos(
            scope="europe",
            resolution=50,
            showframe=False,
            showcountries=True,
            countrycolor="rgba(255,255,255,0.1)",
            fitbounds="locations",
            bgcolor="rgba(0,0,0,0)",
            projection={"type": "mercator"},
        )

        fig.update_layout(
            title={"text": title, "font": {"size": 22}, "x": 0.05, "xanchor": "left"},
            margin={"l": 20, "r": 20, "t": 70, "b": 20},
        )

        fig = apply_theme(fig, theme)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", geo={"bgcolor": "rgba(0,0,0,0)"})
        return fig

    def _compute_centroids(self) -> dict[str, tuple[float, float]]:
        """Compute geographic centroids for each district from GeoJSON."""
        if not hasattr(self, "_centroid_cache"):
            self._centroid_cache: dict[str, tuple[float, float]] = {}

        if self._centroid_cache:
            return self._centroid_cache

        for feature in self.geojson["features"]:
            props = feature["properties"]
            code = props.get("adm1_code", "")
            geom = feature.get("geometry", {})

            if geom.get("type") == "MultiPolygon":
                coords = geom["coordinates"]
                # Flatten all coordinates and compute centroid
                all_points = []
                for polygon in coords:
                    for ring in polygon:
                        all_points.extend(ring)
                if all_points:
                    lons = [p[0] for p in all_points]
                    lats = [p[1] for p in all_points]
                    self._centroid_cache[code] = (sum(lons) / len(lons), sum(lats) / len(lats))

        return self._centroid_cache
