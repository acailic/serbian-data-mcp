"""Advanced chart types beyond the basic six.

Adds heatmap, treemap, gauge/donut, funnel, and animated time-series
using Plotly's full capabilities. All charts support theming via themes.py.
"""

from typing import Optional, List, Dict, Any

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from .themes import apply_theme, SEMANTIC_COLORS


class AdvancedChartBuilder:
    """Builder for advanced chart types with theming support."""

    def __init__(self, data: list[dict[str, Any]] | pd.DataFrame):
        if isinstance(data, list):
            self.data = pd.DataFrame(data)
        else:
            self.data = data

    def heatmap(
        self,
        x_column: str,
        y_column: str,
        z_column: str,
        title: str = "",
        theme: str = "dark",
        colorscale: str = "RdBu_r",
        annotation_text: Optional[str] = None,
    ) -> go.Figure:
        """Create a heatmap (ideal for air quality by city/day, correlations).

        Args:
            x_column: Categories for X axis (e.g., cities)
            y_column: Categories for Y axis (e.g., months)
            z_column: Values for cell color intensity
            title: Chart title
            theme: 'dark', 'light', or 'infographic'
            colorscale: Plotly colorscale name or list
            annotation_text: Optional text suffix for cell values (e.g., ' μg/m³')
        """
        fig = px.imshow(
            self.data.pivot_table(index=y_column, columns=x_column, values=z_column),
            labels={"x": x_column, "y": y_column, "color": z_column},
            title=title,
            color_continuous_scale=colorscale,
            aspect="auto",
        )
        if annotation_text:
            fig.update_traces(texttemplate=f"%{{z}}{annotation_text}", textfont={"size": 10})
        apply_theme(fig, theme)
        return fig

    def treemap(
        self,
        names_column: str,
        values_column: str,
        title: str = "",
        theme: str = "dark",
        color_column: Optional[str] = None,
        hierarchy_column: Optional[str] = None,
    ) -> go.Figure:
        """Create a treemap (budget breakdown, nested categories).

        Args:
            names_column: Labels for each segment
            values_column: Size values for each segment
            title: Chart title
            theme: 'dark', 'light', or 'infographic'
            color_column: Optional column for color grouping
            hierarchy_column: Optional parent column for nested treemap
        """
        path = [names_column]
        if hierarchy_column:
            path = [hierarchy_column, names_column]
        fig = px.treemap(
            self.data,
            path=path,
            values=values_column,
            color=color_column,
            title=title,
            color_discrete_sequence=SEMANTIC_COLORS,
        )
        apply_theme(fig, theme)
        return fig

    def gauge(
        self,
        value: float,
        title: str = "",
        theme: str = "dark",
        min_val: float = 0,
        max_val: float = 100,
        label: str = "",
        thresholds: Optional[dict[str, list[float]]] = None,
    ) -> go.Figure:
        """Create a gauge/donut chart (target vs actual, scores).

        Args:
            value: Current value to display
            title: Chart title
            theme: 'dark', 'light', or 'infographic'
            min_val: Minimum value
            max_val: Maximum value
            label: Label for the gauge value
            thresholds: Dict with 'green', 'yellow', 'red' as [start, end] lists
        """
        thresholds = thresholds or {
            "green": [max_val * 0.6, max_val],
            "yellow": [max_val * 0.3, max_val * 0.6],
            "red": [min_val, max_val * 0.3],
        }

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=value,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": label, "font": {"size": 16}},
                gauge={
                    "axis": {"range": [min_val, max_val], "tickwidth": 1},
                    "bar": {"color": "#1565c0", "thickness": 0.6},
                    "steps": [
                        {"range": thresholds["red"], "color": "rgba(198, 40, 40, 0.3)"},
                        {"range": thresholds["yellow"], "color": "rgba(255, 171, 0, 0.3)"},
                        {"range": thresholds["green"], "color": "rgba(46, 125, 50, 0.3)"},
                    ],
                    "threshold": {
                        "line": {"color": "#ffab00", "width": 4},
                        "thickness": 0.75,
                        "value": value,
                    },
                },
                number={"font": {"size": 48, "color": "#ffffff"}},
            )
        )
        fig.update_layout(title={"text": title, "font": {"size": 22}}, height=350, margin={"t": 80, "b": 40})
        apply_theme(fig, theme)
        return fig

    def funnel(
        self,
        labels_column: str,
        values_column: str,
        title: str = "",
        theme: str = "dark",
    ) -> go.Figure:
        """Create a funnel chart (budget flow, pipeline, cascading values).

        Args:
            labels_column: Labels for each funnel stage
            values_column: Values for each stage
            title: Chart title
            theme: 'dark', 'light', or 'infographic'
        """
        fig = px.funnel(
            self.data.sort_values(values_column, ascending=False),
            x=values_column,
            y=labels_column,
            title=title,
            color_discrete_sequence=[
                "#0d47a1",
                "#1565c0",
                "#1e88e5",
                "#42a5f5",
                "#64b5f6",
                "#90caf9",
            ],
        )
        apply_theme(fig, theme)
        return fig

    def animated_line(
        self,
        x_column: str,
        y_column: str,
        frame_column: str,
        title: str = "",
        theme: str = "dark",
        category_column: Optional[str] = None,
        color_map: Optional[dict[str, str]] = None,
    ) -> go.Figure:
        """Create an animated line chart with time-series playback.

        Args:
            x_column: X axis values (e.g., year)
            y_column: Y axis values (e.g., population)
            frame_column: Column that defines animation frames (e.g., year)
            title: Chart title
            theme: 'dark', 'light', or 'infographic'
            category_column: Optional column for multiple series (e.g., city names)
            color_map: Optional dict mapping category values to specific colors
        """
        kwargs: dict[str, Any] = {
            "x": x_column,
            "y": y_column,
            "animation_frame": frame_column,
            "title": title,
        }
        if category_column:
            kwargs["color"] = category_column
        if color_map:
            kwargs["color_discrete_map"] = color_map

        fig = px.line(self.data, **kwargs)

        # Animation settings
        fig.update_layout(
            updatemenus=[
                {
                    "type": "buttons",
                    "showactive": False,
                    "y": -0.15,
                    "x": 0.05,
                    "xanchor": "right",
                    "yanchor": "top",
                    "buttons": [
                        {
                            "label": "▶ Play",
                            "method": "animate",
                            "args": [
                                None,
                                {"fromcurrent": True, "frame": {"duration": 500}, "transition": {"duration": 300}},
                            ],
                        },
                        {
                            "label": "⏸ Pause",
                            "method": "animate",
                            "args": [[None], {"mode": "immediate", "frame": {"duration": 0}}],
                        },
                    ],
                }
            ],
            sliders=[
                {
                    "active": 0,
                    "y": -0.05,
                    "len": 0.9,
                    "x": 0.05,
                    "xanchor": "right",
                    "currentvalue": {"prefix": "", "font": {"size": 14, "color": "#ffffff"}},
                }
            ],
        )

        apply_theme(fig, theme)
        return fig

    def comparison_bar(
        self,
        category_column: str,
        value_columns: list[str],
        title: str = "",
        theme: str = "dark",
        labels: Optional[list[str]] = None,
        baseline_color: str = "#1565c0",
        comparison_color: str = "#c62828",
    ) -> go.Figure:
        """Create a side-by-side comparison bar chart (e.g., 2020 vs 2024, Serbia vs EU).

        Args:
            category_column: Category labels (e.g., city names)
            value_columns: Two numeric columns to compare
            title: Chart title
            theme: 'dark', 'light', or 'infographic'
            labels: Override legend labels for the two columns
            baseline_color: Color for the first (baseline) series
            comparison_color: Color for the second (comparison) series
        """
        if len(value_columns) != 2:
            raise ValueError("comparison_bar requires exactly 2 value_columns")

        fig = go.Figure()
        names = labels or value_columns
        fig.add_trace(
            go.Bar(
                name=names[0],
                x=self.data[category_column],
                y=self.data[value_columns[0]],
                marker_color=baseline_color,
            )
        )
        fig.add_trace(
            go.Bar(
                name=names[1],
                x=self.data[category_column],
                y=self.data[value_columns[1]],
                marker_color=comparison_color,
            )
        )
        fig.update_layout(barmode="group", title=title, barnorm=None)
        apply_theme(fig, theme)
        return fig

    def sparkline_container(
        self,
        label_column: str,
        value_column: str,
        trend_column: str,
        title: str = "",
        theme: str = "dark",
        sort_by: Optional[str] = None,
        top_n: int = 10,
    ) -> go.Figure:
        """Create a faceted sparkline view — one small line chart per category.

        Ideal for showing trends across many entities (cities, ministries, etc.)

        Args:
            label_column: Category names (entity names)
            value_column: Numeric values
            trend_column: Time/order column for line direction
            title: Chart title
            theme: 'dark', 'light', or 'infographic'
            sort_by: Optional column to sort entities by before selecting top_n
            top_n: Number of entities to show
        """
        df = self.data.copy()
        if sort_by:
            top_entities = df.groupby(label_column)[sort_by].last().nlargest(top_n).index
            df = df[df[label_column].isin(top_entities)]

        fig = px.scatter(
            df,
            x=trend_column,
            y=value_column,
            color=label_column,
            facet_col=label_column,
            facet_col_wrap=5,
            title=title,
        )
        fig.update_traces(showlegend=False, mode="lines+markers")
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1], font={"size": 12}))
        apply_theme(fig, theme)
        return fig
