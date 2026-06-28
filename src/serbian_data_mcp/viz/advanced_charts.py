"""Advanced chart types beyond the basic six.

Adds heatmap, treemap, gauge/donut, funnel, and animated time-series
using Plotly's full capabilities. All charts support theming via themes.py.
"""

from typing import Optional, Any

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

    def violin(
        self,
        y_column: str,
        title: str = "",
        theme: str = "dark",
        x_column: Optional[str] = None,
        color_column: Optional[str] = None,
        box_overlay: bool = False,
        points: Any = False,
    ) -> go.Figure:
        """Create a violin plot — the distribution shape + density of a metric.

        A richer cousin of the box plot: the mirrored kernel-density width shows
        the full shape of a distribution (where values cluster, whether it is
        bimodal, skewed), not just the quartile summary. Ideal for comparing
        how a measurement spreads across groups (e.g. PM2.5 readings per city,
        salaries per sector). Pass ``x_column`` to split violins side-by-side
        by category, ``color_column`` for a second grouping, ``box_overlay`` to
        draw a miniature box-and-whisker inside each violin, and ``points`` to
        jitter the raw observations ('outliers', 'all', or False).

        Args:
            y_column: Column whose distribution is plotted
            title: Chart title
            theme: 'dark', 'light', or 'infographic'
            x_column: Optional category column splitting violins across the X axis
            color_column: Optional second grouping column (one violin per group)
            box_overlay: Draw an inner box-and-whisker summary inside each violin
            points: Show raw points — 'outliers', 'all', or False (default)
        """
        kwargs: dict[str, Any] = {
            "y": y_column,
            "title": title,
            "box": box_overlay,
            "points": points,
        }
        if x_column:
            kwargs["x"] = x_column
        if color_column:
            kwargs["color"] = color_column
            kwargs["color_discrete_sequence"] = SEMANTIC_COLORS
        fig = px.violin(self.data, **kwargs)
        apply_theme(fig, theme)
        return fig

    def waterfall(
        self,
        x_column: str,
        values_column: str,
        title: str = "",
        theme: str = "dark",
        measure_column: Optional[str] = None,
        increasing_color: str = "#2e7d32",
        decreasing_color: str = "#c62828",
        total_color: str = "#1565c0",
    ) -> go.Figure:
        """Create a waterfall chart — a cumulative running-total bridge.

        Each bar starts where the previous one ended, so the chart shows how an
        opening value is built up or torn down by a sequence of signed
        contributions. The canonical professional chart for budget/revenue
        bridges ("start at X, +A, −B, +C → end at Y"), cash-flow walks, and
        variance analysis — far clearer than a plain bar chart for
        part-to-whole movement.

        By default every step is 'relative' (a +/− delta on the running total).
        Pass ``measure_column`` with per-row values of 'relative' | 'absolute' |
        'total' to mark non-delta steps: an 'absolute' row sets a fixed base,
        a 'total' row draws a full-height subtotal bar from zero.

        Args:
            x_column: Step labels (e.g., budget line items)
            values_column: Signed per-step values (+ increase, − decrease)
            title: Chart title
            theme: 'dark', 'light', 'professional', or 'infographic'
            measure_column: Optional per-row measure column ('relative'/'absolute'/'total')
            increasing_color: Bar color for positive deltas
            decreasing_color: Bar color for negative deltas
            total_color: Bar color for 'total' subtotal steps
        """
        if measure_column and measure_column in self.data.columns:
            measure = [str(m).lower() for m in self.data[measure_column]]
        else:
            measure = ["relative"] * len(self.data)

        fig = go.Figure(
            go.Waterfall(
                x=self.data[x_column],
                y=self.data[values_column],
                measure=measure,
                connector={"line": {"color": "rgba(120,144,156,0.45)", "width": 1}},
                increasing={"marker": {"color": increasing_color}},
                decreasing={"marker": {"color": decreasing_color}},
                totals={"marker": {"color": total_color}},
                hovertemplate="<b>%{x}</b><br>%{initialValue:,.0f} → %{finalValue:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(title=title, showlegend=False, waterfallgroupgap=0.2)
        apply_theme(fig, theme)
        return fig

    def candlestick(
        self,
        open_column: str,
        high_column: str,
        low_column: str,
        close_column: str,
        title: str = "",
        theme: str = "dark",
        x_column: Optional[str] = None,
        increasing_color: str = "#2e7d32",
        decreasing_color: str = "#c62828",
    ) -> go.Figure:
        """Create a candlestick chart — the professional OHLC price chart.

        Each bar's body spans the open→close range (green when close ≥ open,
        red when close < open), with thin wicks to the period high and low.
        The canonical professional chart for financial time series — stock,
        FX, commodity prices, or any ordered open/high/low/close data — far
        denser than a line chart because it encodes four values per point and
        the direction of each move.

        ``x_column`` sets the period axis (e.g. a date/time column). When
        omitted, the DataFrame's row order is used. The Plotly rangeslider
        is disabled for a clean editorial register.

        Args:
            open_column: Period-open price column
            high_column: Period-high price column
            low_column: Period-low price column
            close_column: Period-close price column
            title: Chart title
            theme: 'dark', 'light', 'professional', or 'infographic'
            x_column: Optional period/date column for the X axis
            increasing_color: Body color for up (close ≥ open) candles
            decreasing_color: Body color for down (close < open) candles
        """
        x = self.data[x_column] if (x_column and x_column in self.data.columns) else self.data.index
        fig = go.Figure(
            go.Candlestick(
                x=x,
                open=self.data[open_column],
                high=self.data[high_column],
                low=self.data[low_column],
                close=self.data[close_column],
                increasing={"fillcolor": increasing_color, "line": {"color": increasing_color}},
                decreasing={"fillcolor": decreasing_color, "line": {"color": decreasing_color}},
                hoverlabel={"namelength": 0},
            )
        )
        fig.update_layout(title=title, showlegend=False, xaxis_rangeslider_visible=False)
        apply_theme(fig, theme)
        return fig

    def ternary(
        self,
        a_column: str,
        b_column: str,
        c_column: str,
        title: str = "",
        theme: str = "dark",
        color_column: Optional[str] = None,
        size_column: Optional[str] = None,
    ) -> go.Figure:
        """Create a ternary scatter — compositional data on a 3-part whole.

        Each point is a 3-component mix that sums to a constant (clay/silt/sand,
        spending-share across three sectors, vote-share across three candidates).
        The canonical professional chart for compositional / mixture data where
        the three parts are mutually exclusive and exhaustive — a 3-way split a
        plain scatter cannot represent because the three axes are not
        independent (every point's coordinates are constrained to sum to a
        whole). Ideal for geology/soil texture, budget-share decomposition, and
        election-share triangles.

        Args:
            a_column: First component column (A vertex)
            b_column: Second component column (B vertex)
            c_column: Third component column (C vertex)
            title: Chart title
            theme: 'dark', 'light', 'professional', or 'infographic'
            color_column: Optional grouping column (one series per group)
            size_column: Optional per-point marker-size column
        """
        kwargs: dict[str, Any] = {
            "a": a_column,
            "b": b_column,
            "c": c_column,
            "title": title,
        }
        if color_column:
            kwargs["color"] = color_column
            kwargs["color_discrete_sequence"] = SEMANTIC_COLORS
        if size_column:
            kwargs["size"] = size_column
        fig = px.scatter_ternary(self.data, **kwargs)
        apply_theme(fig, theme)
        return fig

    def splom(
        self,
        columns: list[str],
        title: str = "",
        theme: str = "dark",
        color_column: Optional[str] = None,
        size_column: Optional[str] = None,
    ) -> go.Figure:
        """Create a scatter plot matrix (SPLOM) — pairwise scatter for N columns.

        One matrix cell per ordered pair of columns (every column plotted against
        every other), so the full pairwise-correlation structure of a multivariate
        dataset is visible at a glance. The canonical professional chart for
        exploratory correlation analysis — spotting which variables move together,
        which trade off, and which clusters form — that no single scatter can show
        because it only handles two variables. Ideal for multi-indicator datasets
        (pollutants + weather + population, socioeconomic indices).

        Args:
            columns: Columns to scatter pairwise (≥ 2 recommended)
            title: Chart title
            theme: 'dark', 'light', 'professional', or 'infographic'
            color_column: Optional grouping column (one splom trace per group)
            size_column: Optional per-point marker-size column
        """
        kwargs: dict[str, Any] = {
            "dimensions": columns,
            "title": title,
        }
        if color_column:
            kwargs["color"] = color_column
            kwargs["color_discrete_sequence"] = SEMANTIC_COLORS
        if size_column:
            kwargs["size"] = size_column
        fig = px.scatter_matrix(self.data, **kwargs)
        apply_theme(fig, theme)
        return fig

    def parcoords(
        self,
        columns: list[str],
        title: str = "",
        theme: str = "dark",
        color_column: Optional[str] = None,
        color_continuous_scale: str = "RdBu_r",
    ) -> go.Figure:
        """Create a parallel coordinates plot — one vertical axis per variable.

        Each numeric column becomes a parallel vertical ribbon; every row is a
        single polyline threaded across all ribbons. The canonical professional
        chart for high-dimensional / multivariate comparison — unlike a SPLOM
        (whose cell count grows as N²) it scales to many variables at once and
        lets the eye trace how a single record moves through every dimension
        simultaneously. Ideal for multi-indicator records (a city's pollution +
        population + income + temperature as one connected line each), outlier
        detection across many metrics, and spotting which variables separate
        clusters. Pass ``color_column`` (numeric) to gradient-color each line by
        a continuous variable.

        Args:
            columns: Numeric columns to lay out as parallel axes (≥ 2 recommended)
            title: Chart title
            theme: 'dark', 'light', 'professional', or 'infographic'
            color_column: Optional numeric column gradient-coloring each line
            color_continuous_scale: Plotly colorscale name when color_column is set
        """
        kwargs: dict[str, Any] = {
            "dimensions": columns,
            "title": title,
        }
        if color_column:
            kwargs["color"] = color_column
            kwargs["color_continuous_scale"] = color_continuous_scale
        fig = px.parallel_coordinates(self.data, **kwargs)
        apply_theme(fig, theme)
        return fig

    def density_contour(
        self,
        x_column: str,
        y_column: str,
        title: str = "",
        theme: str = "dark",
        color_column: Optional[str] = None,
        colorscale: str = "RdBu_r",
        ncontours: int = 20,
    ) -> go.Figure:
        """Create a 2D density contour — continuous bivariate density estimation.

        Smooth filled contour bands show where points are most concentrated in a
        two-variable plane, so the joint distribution of two continuous variables
        is visible at a glance. The canonical professional chart for spotting
        clustering, correlation shape, and multimodality in a scatter — a plain
        scatter only plots the raw points and hides where they pile up; a heatmap
        shows a categorical grid, not continuous density. Ideal for large
        point-clouds (every pollutant reading by city × weather reading), survey
        microdata (income × age), and any case where overplotting buries the
        structure. Pass ``color_column`` to overlay one contour set per group.

        Args:
            x_column: First continuous variable (X axis)
            y_column: Second continuous variable (Y axis)
            title: Chart title
            theme: 'dark', 'light', 'professional', or 'infographic'
            color_column: Optional grouping column (one contour set per group)
            colorscale: Plotly colorscale name for the density bands
            ncontours: Number of contour bands (higher = finer resolution)
        """
        kwargs: dict[str, Any] = {
            "x": x_column,
            "y": y_column,
            "title": title,
        }
        if color_column:
            kwargs["color"] = color_column
        fig = px.density_contour(self.data, **kwargs)
        # Filled bands colored by density (default px output is line-only contours).
        fig.update_traces(
            contours_coloring="fill",
            colorscale=colorscale,
            ncontours=ncontours,
            line_width=0,
        )
        apply_theme(fig, theme)
        return fig

    def ecdf(
        self,
        x_column: str,
        title: str = "",
        theme: str = "dark",
        color_column: Optional[str] = None,
        ecdfmode: str = "standard",
        markers: bool = False,
    ) -> go.Figure:
        """Create an empirical cumulative distribution (ECDF) — the share ≤ x.

        The running fraction of observations at-or-below each value: the curve
        steps up 1/N per point, rising monotonically from 0 to 1 across the
        sorted range. The canonical professional chart for the percentile /
        exceedance view a histogram (bin counts) and violin (density shape)
        cannot give directly — "what share of cities fall below this PM2.5",
        "60% of salaries are under X", test-score percentiles, return-period
        probabilities. No binning means no bin-width artefacts, so it is also
        the cleanest way to compare two distributions side by side.

        Pass ``color_column`` to overlay one ECDF curve per group, ``ecdfmode``
        for a survival / complementary curve ('complementary' = P(X > x), a
        descending 1→0 exceedance curve), and ``markers`` to draw a marker at
        each observation as well as the connecting line.

        Args:
            x_column: Numeric column whose cumulative distribution is plotted
            title: Chart title
            theme: 'dark', 'light', 'professional', or 'infographic'
            color_column: Optional grouping column (one ECDF curve per group)
            ecdfmode: 'standard' (P(X ≤ x), default ascending 0→1),
                'complementary' (P(X > x), descending 1→0), 'reversed', or
                'reversed-complementary'
            markers: Show a marker at each observation (default: line only)
        """
        kwargs: dict[str, Any] = {
            "x": x_column,
            "title": title,
            "ecdfmode": ecdfmode,
        }
        if color_column:
            kwargs["color"] = color_column
            kwargs["color_discrete_sequence"] = SEMANTIC_COLORS
        fig = px.ecdf(self.data, **kwargs)
        # px.ecdf defaults to a connecting line; opt into per-point markers.
        if markers:
            fig.update_traces(mode="lines+markers")
        apply_theme(fig, theme)
        return fig

    def strip(
        self,
        y_column: str,
        title: str = "",
        theme: str = "dark",
        x_column: Optional[str] = None,
        color_column: Optional[str] = None,
        jitter: float = 0.2,
        pointpos: float = 0,
    ) -> go.Figure:
        """Create a strip plot — one jittered dot per raw observation.

        Every individual data point is plotted as a marker, nudged horizontally
        within its category so overlapping points separate. The canonical
        professional chart for showing the *actual sample* rather than a summary
        shape: a box plot reduces the data to five quartile numbers and a violin
        to a density curve, so both hide the sample size, individual outliers,
        clustering, and gaps that a strip plot lays bare. Ideal for
        small-to-moderate samples where every observation counts (test scores per
        class, survey responses per district, sensor readings per site). Pass
        ``x_column`` to split points into category columns, ``color_column`` for
        a second grouping (one point set per group), and tune ``jitter`` /
        ``pointpos`` to spread or stack the points.

        Args:
            y_column: Column whose values are plotted (one dot per value)
            title: Chart title
            theme: 'dark', 'light', 'professional', or 'infographic'
            x_column: Optional category column splitting points into columns
            color_column: Optional second grouping column (one point set per group)
            jitter: Horizontal jitter spread (0–1, 0 = stacked in a line)
            pointpos: Vertical offset of points relative to the box (-2 to 2)
        """
        kwargs: dict[str, Any] = {
            "y": y_column,
            "title": title,
        }
        if x_column:
            kwargs["x"] = x_column
        if color_column:
            kwargs["color"] = color_column
            kwargs["color_discrete_sequence"] = SEMANTIC_COLORS
        fig = px.strip(self.data, **kwargs)
        # px.strip emits go.Box traces with boxpoints='all'; jitter/pointpos are
        # trace-level knobs applied after construction (px has no strip-level arg).
        fig.update_traces(jitter=jitter, pointpos=pointpos)
        apply_theme(fig, theme)
        return fig

    def bar_polar(
        self,
        r_column: str,
        theta_column: str,
        title: str = "",
        theme: str = "dark",
        color_column: Optional[str] = None,
    ) -> go.Figure:
        """Create a polar bar / wind-rose chart — radial bars around a circle.

        Each angular position (``theta``) carries a radial bar whose length
        encodes ``r``. The canonical professional chart for *directional* or
        *cyclical* data: wind speed by compass direction (wind rose), rainfall
        by wind direction, sales/traffic by weekday arranged around a clock,
        resource allocation by compass sector. Distinct from a linear bar chart
        (whose x axis does not wrap) because the angular axis is cyclic
        (N→E→S→W→N) and from a radar/scatter_polar because magnitude is shown
        as a filled bar sector rather than a point/line. Pass
        ``color_column`` to stack a second grouping as one bar set per group.

        Args:
            r_column: Numeric radial magnitude column (bar length)
            theta_column: Angular/directional category column (compass, weekday, sector)
            title: Chart title
            theme: 'dark', 'light', 'professional', or 'infographic'
            color_column: Optional second grouping column (one bar set per group)
        """
        kwargs: dict[str, Any] = {
            "r": r_column,
            "theta": theta_column,
            "title": title,
        }
        if color_column:
            kwargs["color"] = color_column
            kwargs["color_discrete_sequence"] = SEMANTIC_COLORS
        fig = px.bar_polar(self.data, **kwargs)
        apply_theme(fig, theme)
        return fig

    def radar(
        self,
        r_column: str,
        theta_column: str,
        title: str = "",
        theme: str = "dark",
        color_column: Optional[str] = None,
        line_close: bool = True,
        markers: bool = True,
        fill: bool = False,
    ) -> go.Figure:
        """Create a radar / spider chart — a closed line shape on a polar axis.

        Each angular position (``theta``) carries a radial value (``r``) and the
        points are connected into a closed polygon spanning the full circle. The
        canonical professional chart for comparing one or more entities across a
        fixed set of qualitative axes (a city's performance on economy / health /
        education / safety, a candidate's ratings across policy areas, sensor
        readings around the compass) where the *shape* of the profile matters, not
        the absolute x position. Distinct from bar_polar (whose magnitude is a
        filled bar sector, not a connected profile) and from a plain line chart
        (linear x, no cyclic closure): radar overlays multiple entities' profiles
        on the same polar grid so their strengths/weaknesses read at a glance.

        Pass ``color_column`` to overlay one closed profile per group (the classic
        multi-entity spider), ``markers`` to draw a marker at each vertex,
        ``line_close`` to leave the polygon open (False) or closed (True, default),
        and ``fill`` to shade the interior of each profile (area radar).

        Args:
            r_column: Numeric radial value column (distance from center)
            theta_column: Angular category column (the profile's axes, e.g. metric names)
            title: Chart title
            theme: 'dark', 'light', 'professional', or 'infographic'
            color_column: Optional grouping column (one closed profile per group)
            line_close: Close the polygon by linking the last vertex back to the first
            markers: Show a marker at each vertex (default: line + markers)
            fill: Shade each profile's interior ('toself' area fill)
        """
        kwargs: dict[str, Any] = {
            "r": r_column,
            "theta": theta_column,
            "title": title,
            "line_close": line_close,
        }
        if markers:
            kwargs["markers"] = True
        if color_column:
            kwargs["color"] = color_column
            kwargs["color_discrete_sequence"] = SEMANTIC_COLORS
        fig = px.line_polar(self.data, **kwargs)
        # px.line_polar emits go.Scatterpolar; opt into a filled area profile.
        if fill:
            fig.update_traces(fill="toself")
        apply_theme(fig, theme)
        return fig

    def sunburst(
        self,
        names_column: str,
        values_column: str,
        title: str = "",
        theme: str = "dark",
        color_column: Optional[str] = None,
        hierarchy_column: Optional[str] = None,
    ) -> go.Figure:
        """Create a sunburst chart — radial hierarchy of concentric rings.

        A rooted hierarchy laid out as nested rings around a center: each level
        is one ring, each branch a wedge, wedge angle proportional to its value.
        The canonical professional chart for part-to-whole hierarchy where the
        *depth* matters as much as the size — budget by department→team→line,
        website traffic by source→page→exit, organisational headcount. Distinct
        from treemap (nested rectangles, easier for flat totals but depth and
        adjacency are harder to read) and funnel/pie (single level only):
        sunburst makes multi-level composition legible at a glance.

        Args:
            names_column: Labels for each segment/wedge
            values_column: Size values for each wedge (angle)
            title: Chart title
            theme: 'dark', 'light', 'professional', or 'infographic'
            color_column: Optional column for color grouping
            hierarchy_column: Optional parent column for nested rings
        """
        path = [names_column]
        if hierarchy_column:
            path = [hierarchy_column, names_column]
        fig = px.sunburst(
            self.data,
            path=path,
            values=values_column,
            color=color_column,
            title=title,
            color_discrete_sequence=SEMANTIC_COLORS,
        )
        apply_theme(fig, theme)
        return fig

    def sankey(
        self,
        source_column: str,
        target_column: str,
        values_column: str,
        title: str = "",
        theme: str = "dark",
        node_pad: int = 15,
        node_thickness: int = 20,
        arrangement: str = "snap",
    ) -> go.Figure:
        """Create a Sankey diagram — proportional flow between source→target nodes.

        Each row is one directed transfer from a ``source_column`` category to a
        ``target_column`` category, sized by ``values_column``: a ribbon whose
        width encodes the magnitude flowing between two nodes. The canonical
        professional chart for transfers that a bar or pie cannot express —
        budget allocation ministry→programme→project, energy source→sector→use,
        migration country→country, or user journey stage→stage. Distinct from
        funnel (a single linear cascade with no branching) and treemap/sunburst
        (part-to-whole of a fixed total, not directed flow): Sankey shows where
        a quantity comes from AND where it goes, including splits and merges.

        Duplicate (source, target) rows are aggregated by summing their values,
        since a Sankey link between the same two nodes must be a single ribbon.
        Nodes are the union of all source and target labels.

        Args:
            source_column: Origin node labels for each flow
            target_column: Destination node labels for each flow
            values_column: Flow magnitude (ribbon width) per row
            title: Chart title
            theme: 'dark', 'light', 'professional', or 'infographic'
            node_pad: Vertical padding between nodes (px)
            node_thickness: Node bar thickness (px)
            arrangement: Node placement — 'snap' (default), 'perpendicular', 'freeform', 'fixed'
        """
        sources = self.data[source_column].astype(str)
        targets = self.data[target_column].astype(str)
        values = pd.to_numeric(self.data[values_column], errors="coerce").fillna(0.0)

        # Union of all node labels, preserving first-seen order for stable indices.
        labels = list(dict.fromkeys([*sources.tolist(), *targets.tolist()]))
        index = {label: i for i, label in enumerate(labels)}

        # Aggregate duplicate source→target pairs into single ribbons by summing.
        link_df = pd.DataFrame({"s": sources.values, "t": targets.values, "v": values.values})
        agg = link_df.groupby(["s", "t"], sort=False, as_index=False)["v"].sum()

        fig = go.Figure(
            go.Sankey(
                arrangement=arrangement,
                node={
                    "label": labels,
                    "pad": node_pad,
                    "thickness": node_thickness,
                    "color": [SEMANTIC_COLORS[i % len(SEMANTIC_COLORS)] for i in range(len(labels))],
                    "line": {"color": "rgba(0,0,0,0)", "width": 0},
                },
                link={
                    "source": [index[s] for s in agg["s"]],
                    "target": [index[t] for t in agg["t"]],
                    "value": agg["v"].tolist(),
                },
            )
        )
        fig.update_layout(title=title)
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
