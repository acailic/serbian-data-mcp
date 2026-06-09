"""Chart building using Plotly."""

from typing import Optional, List, Dict, Any, Union

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


class ChartBuilder:
    """Builder for creating interactive charts with Plotly."""

    def __init__(self, data: Union[pd.DataFrame, List[Dict[str, Any]]]):
        """Initialize chart builder with data.

        Args:
            data: DataFrame or list of dictionaries for charting
        """
        if isinstance(data, list):
            self.data = pd.DataFrame(data)
        else:
            self.data = data

    def line_chart(
        self, x_column: str, y_column: str, title: str = "", color_column: Optional[str] = None
    ) -> go.Figure:
        """Create a line chart.

        Args:
            x_column: Column name for X axis
            y_column: Column name for Y axis
            title: Chart title
            color_column: Optional column for color grouping

        Returns:
            Plotly Figure object
        """
        if color_column:
            fig = px.line(self.data, x=x_column, y=y_column, color=color_column, title=title)
        else:
            fig = px.line(self.data, x=x_column, y=y_column, title=title)

        return fig

    def bar_chart(
        self, x_column: str, y_column: str, title: str = "", color_column: Optional[str] = None, orientation: str = "v"
    ) -> go.Figure:
        """Create a bar chart.

        Args:
            x_column: Column name for X axis
            y_column: Column name for Y axis
            title: Chart title
            color_column: Optional column for color grouping
            orientation: 'v' for vertical, 'h' for horizontal

        Returns:
            Plotly Figure object
        """
        if orientation == "h":
            fig = px.bar(self.data, x=y_column, y=x_column, color=color_column, title=title, orientation="h")
        else:
            fig = px.bar(self.data, x=x_column, y=y_column, color=color_column, title=title)

        return fig

    def pie_chart(self, values_column: str, names_column: str, title: str = "") -> go.Figure:
        """Create a pie chart.

        Args:
            values_column: Column name for values
            names_column: Column name for labels
            title: Chart title

        Returns:
            Plotly Figure object
        """
        fig = px.pie(self.data, values=values_column, names=names_column, title=title)

        return fig

    def scatter_plot(
        self,
        x_column: str,
        y_column: str,
        title: str = "",
        color_column: Optional[str] = None,
        size_column: Optional[str] = None,
    ) -> go.Figure:
        """Create a scatter plot.

        Args:
            x_column: Column name for X axis
            y_column: Column name for Y axis
            title: Chart title
            color_column: Optional column for color grouping
            size_column: Optional column for size grouping

        Returns:
            Plotly Figure object
        """
        fig = px.scatter(self.data, x=x_column, y=y_column, color=color_column, size=size_column, title=title)

        return fig

    def histogram(self, column: str, title: str = "", bins: Optional[int] = None) -> go.Figure:
        """Create a histogram.

        Args:
            column: Column name to plot
            title: Chart title
            bins: Number of bins

        Returns:
            Plotly Figure object
        """
        fig = px.histogram(self.data, x=column, title=title, nbins=bins)

        return fig

    def box_plot(self, y_column: str, x_column: Optional[str] = None, title: str = "") -> go.Figure:
        """Create a box plot.

        Args:
            y_column: Column name for Y axis
            x_column: Optional column name for X axis (grouping)
            title: Chart title

        Returns:
            Plotly Figure object
        """
        fig = px.box(self.data, x=x_column, y=y_column, title=title)

        return fig
