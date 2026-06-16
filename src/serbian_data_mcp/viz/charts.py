"""Chart building using Plotly with auto-theming and polished defaults.

All charts are automatically themed with the Serbian data-journalism dark
theme for consistent, professional output. Callers can override via
``apply_theme(fig, "light")`` or ``apply_theme(fig, "infographic")``.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from .themes import apply_theme

logger = logging.getLogger(__name__)


class ChartBuilder:
    """Builder for creating interactive, themed charts with Plotly.

    All charts are automatically styled with the dark Serbian data-journalism
    theme. Use ``apply_theme(fig, "light")`` to switch.
    """

    def __init__(self, data: pd.DataFrame | list[dict[str, Any]]):
        """Initialize chart builder with data.

        Args:
            data: DataFrame or list of dictionaries for charting
        """
        if isinstance(data, list):
            self.data = pd.DataFrame(data)
        else:
            self.data = data
        logger.debug(f"ChartBuilder initialized with {len(self.data)} rows, {len(self.data.columns)} columns")

    def line_chart(
        self,
        x_column: str,
        y_column: str,
        title: str = "",
        color_column: Optional[str] = None,
    ) -> go.Figure:
        """Create a styled line chart.

        Args:
            x_column: Column name for X axis
            y_column: Column name for Y axis
            title: Chart title
            color_column: Optional column for color grouping

        Returns:
            Plotly Figure object with dark theme applied
        """
        fig = px.line(
            self.data,
            x=x_column,
            y=y_column,
            color=color_column,
            title=title,
        )
        fig.update_traces(mode="lines+markers", marker={"size": 6})
        return apply_theme(fig)

    def bar_chart(
        self,
        x_column: str,
        y_column: str,
        title: str = "",
        color_column: Optional[str] = None,
        orientation: str = "v",
    ) -> go.Figure:
        """Create a styled bar chart.

        Args:
            x_column: Column name for X axis
            y_column: Column name for Y axis
            title: Chart title
            color_column: Optional column for color grouping
            orientation: 'v' for vertical, 'h' for horizontal

        Returns:
            Plotly Figure object with dark theme applied
        """
        fig = px.bar(
            self.data,
            x=x_column,
            y=y_column,
            color=color_column,
            title=title,
            orientation=orientation,
        )
        fig.update_traces(
            marker_line={"width": 0},
            marker={"opacity": 0.9},
        )
        if orientation == "h":
            fig.update_yaxes(categoryorder="total ascending")
        return apply_theme(fig)

    def pie_chart(
        self,
        values_column: str,
        names_column: str,
        title: str = "",
    ) -> go.Figure:
        """Create a styled pie chart.

        Args:
            values_column: Column name for values
            names_column: Column name for labels
            title: Chart title

        Returns:
            Plotly Figure object with dark theme applied
        """
        fig = px.pie(
            self.data,
            values=values_column,
            names=names_column,
            title=title,
            hole=0.35,
        )
        fig.update_traces(
            textposition="inside",
            textinfo="percent+label",
            textfont={"size": 12, "color": "#ffffff"},
            marker_line={"width": 2, "color": "rgba(26,26,46,0.8)"},
            pull=[0.02] * len(self.data),
        )
        return apply_theme(fig)

    def scatter_plot(
        self,
        x_column: str,
        y_column: str,
        title: str = "",
        color_column: Optional[str] = None,
        size_column: Optional[str] = None,
    ) -> go.Figure:
        """Create a styled scatter plot.

        Args:
            x_column: Column name for X axis
            y_column: Column name for Y axis
            title: Chart title
            color_column: Optional column for color grouping
            size_column: Optional column for bubble sizes

        Returns:
            Plotly Figure object with dark theme applied
        """
        fig = px.scatter(
            self.data,
            x=x_column,
            y=y_column,
            color=color_column,
            size=size_column,
            title=title,
        )
        fig.update_traces(
            marker_line={"width": 1, "color": "rgba(255,255,255,0.3)"},
            marker_opacity=0.85,
        )
        return apply_theme(fig)

    def histogram(
        self,
        column: str,
        title: str = "",
        bins: Optional[int] = None,
    ) -> go.Figure:
        """Create a styled histogram.

        Args:
            column: Column name to plot
            title: Chart title
            bins: Number of bins

        Returns:
            Plotly Figure object with dark theme applied
        """
        fig = px.histogram(self.data, x=column, title=title, nbins=bins)
        fig.update_traces(
            marker_line={"width": 1, "color": "rgba(255,255,255,0.3)"},
            marker_opacity=0.85,
            selector={"type": "histogram"},
        )
        return apply_theme(fig)

    def box_plot(
        self,
        y_column: str,
        x_column: Optional[str] = None,
        title: str = "",
    ) -> go.Figure:
        """Create a styled box plot.

        Args:
            y_column: Column name for Y axis
            x_column: Optional column name for X axis (grouping)
            title: Chart title

        Returns:
            Plotly Figure object with dark theme applied
        """
        fig = px.box(self.data, x=x_column, y=y_column, title=title)
        fig.update_traces(
            marker_line={"width": 1, "color": "rgba(255,255,255,0.3)"},
            marker_opacity=0.7,
            line_width=2,
            selector={"type": "box"},
        )
        return apply_theme(fig)
