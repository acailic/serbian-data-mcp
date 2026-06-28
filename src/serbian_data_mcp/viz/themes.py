"""Custom Plotly themes for Serbian data visualizations.

Provides themed templates for different presentation contexts:
- Dark theme: Dramatic, data-journalism style
- Light theme: Clean, professional
- Infographic: Big-number focused layouts
- Serbian flag palette: Red, blue, white color system

All themes include: custom font stacks, refined hover styles,
consistent spacing, and professional color treatment.
"""

import copy
from typing import Any

import plotly.graph_objects as go

# ── Serbian Flag Color Palette ──────────────────────────────────────────────
SERBIAN_PALETTE = {
    "red": "#c62828",
    "dark_red": "#8e0000",
    "blue": "#1565c0",
    "dark_blue": "#003c8f",
    "white": "#f5f5f5",
    "light_gray": "#eceff1",
    "mid_gray": "#90a4ae",
    "dark_gray": "#37474f",
    "black": "#1a1a2e",
    "accent_gold": "#ffab00",
    "accent_green": "#2e7d32",
    "accent_orange": "#ef6c00",
    "accent_cyan": "#00acc1",
}

# Semantic color mapping for data categories
SEMANTIC_COLORS = [
    "#c62828",  # red — danger, deficit, loss
    "#1565c0",  # blue — neutral, baseline
    "#2e7d32",  # green — positive, gain, growth
    "#ef6c00",  # orange — warning, caution
    "#7b1fa2",  # purple — special categories
    "#00acc1",  # cyan — comparison, alternative
    "#ffab00",  # gold — highlight, record
    "#5d4037",  # brown — earthy, rural
    "#37474f",  # dark gray — institutional
    "#e91e63",  # pink — social, health
]

# Diverging palette for comparison charts (negative → positive)
DIVERGING_COLORS = ["#c62828", "#e57373", "#ef9a9a", "#ffebee", "#f5f5f5", "#e3f2fd", "#90caf9", "#42a5f5", "#1565c0"]

# Sequential palette for ordered data (low → high)
SEQUENTIAL_COLORS = ["#bbdefb", "#90caf9", "#64b5f6", "#42a5f5", "#1e88e5", "#1565c0", "#0d47a1"]

# Professional editorial palette — Okabe-Ito (colorblind-safe), used by the
# 'professional' theme for FT/Bloomberg/Economist-style reporting. Muted and
# perceptually distinct, unlike the saturated Serbian-flag SEMANTIC_COLORS.
PROFESSIONAL_COLORS = [
    "#0072b2",  # blue — baseline / neutral
    "#d55e00",  # vermillion — emphasis / loss
    "#009e73",  # bluish-green — gain / positive
    "#cc79a7",  # reddish-purple — special category
    "#56b4e9",  # sky blue — comparison
    "#e69f00",  # orange — warning / highlight
    "#000000",  # black — ink / reference
    "#f0e442",  # yellow — sparse accent
]


def _dark_layout_dict() -> dict[str, Any]:
    """Raw layout dict for dark theme."""
    return {
        "paper_bgcolor": "#1a1a2e",
        "plot_bgcolor": "#16213e",
        "font": {
            "family": "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif",
            "color": "#e0e0e0",
            "size": 14,
        },
        "title": {
            "font": {"size": 22, "color": "#ffffff", "family": "'Inter', 'Segoe UI', system-ui, sans-serif"},
            "x": 0.05,
            "xanchor": "left",
        },
        "xaxis": {
            "gridcolor": "rgba(255,255,255,0.06)",
            "linecolor": "rgba(255,255,255,0.1)",
            "zerolinecolor": "rgba(255,255,255,0.15)",
            "title": {"font": {"size": 13, "color": "#90a4ae", "family": "'Inter', 'Segoe UI', system-ui, sans-serif"}},
            "tickfont": {"size": 12, "color": "#78909c"},
            "tickformat": ",",
        },
        "yaxis": {
            "gridcolor": "rgba(255,255,255,0.06)",
            "linecolor": "rgba(255,255,255,0.1)",
            "zerolinecolor": "rgba(255,255,255,0.15)",
            "title": {"font": {"size": 13, "color": "#90a4ae", "family": "'Inter', 'Segoe UI', system-ui, sans-serif"}},
            "tickfont": {"size": 12, "color": "#78909c"},
            "tickformat": ",",
        },
        "legend": {
            "bgcolor": "rgba(26,26,46,0.9)",
            "font": {"color": "#cfd8dc", "size": 12},
            "bordercolor": "rgba(255,255,255,0.08)",
            "borderwidth": 1,
            "groupclick": "toggleitem",
        },
        "colorway": SEMANTIC_COLORS,
        "hoverlabel": {
            "bgcolor": "#0d1b2a",
            "bordercolor": "#1565c0",
            "font": {"color": "#ffffff", "size": 13, "family": "'Inter', 'Segoe UI', system-ui, sans-serif"},
            "namelength": 0,
        },
        "margin": {"l": 80, "r": 40, "t": 80, "b": 80},
        "modebar": {"bgcolor": "rgba(0,0,0,0)", "color": "#78909c", "activecolor": "#ffab00"},
    }


def _light_layout_dict() -> dict[str, Any]:
    """Raw layout dict for light theme."""
    return {
        "paper_bgcolor": "#ffffff",
        "plot_bgcolor": "#f8f9fa",
        "font": {
            "family": "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif",
            "color": "#37474f",
            "size": 14,
        },
        "title": {
            "font": {"size": 22, "color": "#1a1a2e", "family": "'Inter', 'Segoe UI', system-ui, sans-serif"},
            "x": 0.05,
            "xanchor": "left",
        },
        "xaxis": {
            "gridcolor": "#e9ecef",
            "linecolor": "#dee2e6",
            "zerolinecolor": "#adb5bd",
            "title": {"font": {"size": 13, "color": "#495057", "family": "'Inter', 'Segoe UI', system-ui, sans-serif"}},
            "tickfont": {"size": 12, "color": "#6c757d"},
            "tickformat": ",",
        },
        "yaxis": {
            "gridcolor": "#e9ecef",
            "linecolor": "#dee2e6",
            "zerolinecolor": "#adb5bd",
            "title": {"font": {"size": 13, "color": "#495057", "family": "'Inter', 'Segoe UI', system-ui, sans-serif"}},
            "tickfont": {"size": 12, "color": "#6c757d"},
            "tickformat": ",",
        },
        "legend": {
            "bgcolor": "rgba(255,255,255,0.95)",
            "font": {"color": "#495057", "size": 12},
            "bordercolor": "#e9ecef",
            "borderwidth": 1,
            "groupclick": "toggleitem",
        },
        "colorway": SEMANTIC_COLORS,
        "hoverlabel": {
            "bgcolor": "#ffffff",
            "bordercolor": "#1565c0",
            "font": {"color": "#1a1a2e", "size": 13, "family": "'Inter', 'Segoe UI', system-ui, sans-serif"},
            "namelength": 0,
        },
        "margin": {"l": 80, "r": 40, "t": 80, "b": 80},
        "modebar": {"bgcolor": "rgba(0,0,0,0)", "color": "#6c757d", "activecolor": "#1565c0"},
    }


def _infographic_layout_dict() -> dict[str, Any]:
    """Raw layout dict for infographic theme."""
    return {
        "paper_bgcolor": "#1a1a2e",
        "plot_bgcolor": "#16213e",
        "font": {
            "family": "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif",
            "color": "#ffffff",
            "size": 16,
        },
        "title": {
            "font": {"size": 28, "color": "#ffffff", "family": "'Inter', 'Segoe UI', system-ui, sans-serif"},
            "x": 0.5,
            "xanchor": "center",
        },
        "xaxis": {
            "showgrid": False,
            "linecolor": "rgba(255,255,255,0.1)",
            "title": {"font": {"size": 15, "color": "#b0bec5", "family": "'Inter', 'Segoe UI', system-ui, sans-serif"}},
            "tickfont": {"size": 13, "color": "#90a4ae"},
            "tickformat": ",",
        },
        "yaxis": {
            "showgrid": True,
            "gridcolor": "rgba(255,255,255,0.06)",
            "linecolor": "rgba(255,255,255,0.1)",
            "title": {"font": {"size": 15, "color": "#b0bec5", "family": "'Inter', 'Segoe UI', system-ui, sans-serif"}},
            "tickfont": {"size": 13, "color": "#90a4ae"},
            "tickformat": ",",
        },
        "legend": {
            "bgcolor": "rgba(26,26,46,0.8)",
            "font": {"color": "#e0e0e0", "size": 13},
            "bordercolor": "rgba(255,255,255,0.1)",
            "groupclick": "toggleitem",
        },
        "colorway": SEMANTIC_COLORS,
        "hoverlabel": {
            "bgcolor": "#0d1b2a",
            "bordercolor": "#ffab00",
            "font": {"color": "#ffffff", "size": 14, "family": "'Inter', 'Segoe UI', system-ui, sans-serif"},
            "namelength": 0,
        },
        "margin": {"l": 100, "r": 60, "t": 100, "b": 100},
        "modebar": {"bgcolor": "rgba(0,0,0,0)", "color": "#78909c", "activecolor": "#ffab00"},
    }


# Warm off-white used by the professional theme — the FT/Economist editorial
# salmon paper. Centralizing it so the 3D scene builder can reuse the exact
# background tone for visual consistency with 2D charts.
PROFESSIONAL_PAPER = "#fff1e5"
_PROFESSIONAL_SERIF = "'Georgia', 'Times New Roman', 'PT Serif', serif"
_PROFESSIONAL_SANS = "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif"


def _professional_layout_dict() -> dict[str, Any]:
    """Raw layout dict for the professional editorial theme.

    Modeled on FT/Bloomberg/Economist report graphics: warm salmon paper,
    serif headlines over sans body, a solid baseline axis line (Tufte-style),
    faint gridlines, and the colorblind-safe Okabe-Ito palette. Deliberately
    distinct from ``light`` (gray plot bg, sans title, flag palette) — use it
    when the output must read as a published, editorial-grade figure.
    """
    return {
        "paper_bgcolor": PROFESSIONAL_PAPER,
        "plot_bgcolor": PROFESSIONAL_PAPER,
        "font": {
            "family": _PROFESSIONAL_SANS,
            "color": "#1c1c1c",
            "size": 14,
        },
        "title": {
            "font": {"size": 22, "color": "#121212", "family": _PROFESSIONAL_SERIF},
            "x": 0.0,
            "xanchor": "left",
        },
        "xaxis": {
            "gridcolor": "rgba(0,0,0,0)",
            "linecolor": "#1c1c1c",
            "zerolinecolor": "#1c1c1c",
            "title": {"font": {"size": 13, "color": "#333333", "family": _PROFESSIONAL_SANS}},
            "tickfont": {"size": 12, "color": "#333333", "family": _PROFESSIONAL_SANS},
            "tickformat": ",",
            "showline": True,
            "mirror": False,
        },
        "yaxis": {
            "gridcolor": "#e8dcd0",
            "linecolor": "rgba(0,0,0,0)",
            "zerolinecolor": "#bdb3a7",
            "title": {"font": {"size": 13, "color": "#333333", "family": _PROFESSIONAL_SANS}},
            "tickfont": {"size": 12, "color": "#333333", "family": _PROFESSIONAL_SANS},
            "tickformat": ",",
            "showline": False,
        },
        "legend": {
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "#1c1c1c", "size": 12, "family": _PROFESSIONAL_SANS},
            "bordercolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "groupclick": "toggleitem",
        },
        "colorway": PROFESSIONAL_COLORS,
        "hoverlabel": {
            "bgcolor": "#ffffff",
            "bordercolor": "#0072b2",
            "font": {"color": "#1c1c1c", "size": 13, "family": _PROFESSIONAL_SANS},
            "namelength": 0,
        },
        "margin": {"l": 70, "r": 30, "t": 70, "b": 60},
        "modebar": {"bgcolor": "rgba(0,0,0,0)", "color": "#7a6f63", "activecolor": "#0072b2"},
    }


def dark_template() -> dict[str, Any]:
    """Dark theme layout dict for dramatic data-journalism presentations."""
    return copy.deepcopy(_dark_layout_dict())


def light_template() -> dict[str, Any]:
    """Light theme layout dict for clean professional presentations."""
    return copy.deepcopy(_light_layout_dict())


def infographic_template() -> dict[str, Any]:
    """Infographic theme layout dict with large typography and minimal chrome."""
    return copy.deepcopy(_infographic_layout_dict())


def professional_template() -> dict[str, Any]:
    """Professional editorial theme layout dict (FT/Bloomberg/Economist style)."""
    return copy.deepcopy(_professional_layout_dict())


def apply_theme(fig: go.Figure, theme: str = "dark") -> go.Figure:
    """Apply a named theme to a Plotly figure.

    Sets layout styles, refines trace appearance for consistency,
    and configures interactive features like legend toggle.

    Args:
        fig: Plotly Figure to theme
        theme: 'dark', 'light', 'infographic', or 'professional'

    Returns:
        Themed Plotly Figure
    """
    templates = {
        "dark": _dark_layout_dict,
        "light": _light_layout_dict,
        "infographic": _infographic_layout_dict,
        "professional": _professional_layout_dict,
    }
    builder = templates.get(theme)
    if not builder:
        builder = _dark_layout_dict
    layout = builder()
    fig.update_layout(layout)

    # Polish trace defaults for visual consistency
    trace_updates: dict[str, Any] = {
        "marker": {"line": {"width": 0}},
        "line": {"shape": "spline", "smoothing": 0.8},
    }
    if theme == "dark":
        trace_updates["marker"]["opacity"] = 0.9

    for trace in fig.data:
        if hasattr(trace, "marker") and hasattr(trace.marker, "line"):
            trace.marker.update({"line": trace_updates["marker"]["line"]})

    return fig


def polish_for_export(fig: go.Figure, title: str = "", subtitle: str = "", source: str = "") -> go.Figure:
    """Apply final polish pass before export: watermark, source attribution, sizing.

    Adds a subtle watermark footer and source attribution to the chart,
    sets optimal dimensions for export, and ensures consistent typography.

    Args:
        fig: Plotly Figure to polish
        title: Override chart title (optional)
        subtitle: Subtitle text to show below title
        source: Data source attribution (e.g., 'data.gov.rs')

    Returns:
        Polished Plotly Figure
    """
    if title:
        fig.update_layout(title={"text": title, "x": 0.05, "xanchor": "left"})

    # Add subtitle as annotation below title
    if subtitle:
        fig.add_annotation(
            text=subtitle,
            xref="paper",
            yref="paper",
            x=0.05,
            y=1.0,
            showarrow=False,
            font={"size": 13, "color": "#90a4ae"},
        )

    # Source watermark
    source_text = source or "Source: data.gov.rs | serbian-data-mcp"
    fig.add_annotation(
        text=source_text,
        xref="paper",
        yref="paper",
        x=1,
        y=-0.06,
        xanchor="right",
        showarrow=False,
        font={"size": 10, "color": "#546e7a"},
    )

    # Ensure consistent dimensions
    layout = fig.layout
    if not layout.height or layout.height < 400:
        fig.update_layout(height=500)
    fig.update_layout(width=None, autosize=True)

    return fig


def add_annotation(
    fig: go.Figure,
    text: str,
    x: float | str,
    y: float | str,
    arrow_color: str = "#ffab00",
    font_size: int = 14,
    show_arrow: bool = True,
    bgcolor: str = "rgba(26,26,46,0.85)",
) -> go.Figure:
    """Add a callout annotation to a chart for data storytelling.

    Args:
        fig: Plotly Figure
        text: Annotation text (the insight/callout)
        x: X position (data coordinate)
        y: Y position (data coordinate)
        arrow_color: Color of the annotation arrow
        font_size: Text size
        show_arrow: Whether to show arrow pointing to data
        bgcolor: Background color of annotation box

    Returns:
        Figure with annotation added
    """
    fig.add_annotation(
        text=text,
        x=x,
        y=y,
        showarrow=show_arrow,
        arrowhead=2,
        arrowcolor=arrow_color,
        arrowwidth=2,
        font={"size": font_size, "color": "#ffffff"},
        bgcolor=bgcolor,
        bordercolor=arrow_color,
        borderwidth=1.5,
        borderpad=8,
    )
    return fig


def add_highlight_zone(
    fig: go.Figure,
    x_start: float | str,
    x_end: float | str,
    fill_color: str = "rgba(198, 40, 40, 0.1)",
    annotation_text: str = "",
) -> go.Figure:
    """Add a shaded vertical highlight zone (e.g., crisis period, pandemic years).

    Args:
        fig: Plotly Figure
        x_start: Start of zone
        x_end: End of zone
        fill_color: RGBA fill color
        annotation_text: Optional label above the zone

    Returns:
        Figure with highlight zone added
    """
    annotation_arg: dict[str, Any] | None = None
    if annotation_text:
        annotation_arg = {"text": annotation_text, "font": {"size": 12, "color": "#e0e0e0"}}

    fig.add_vrect(
        x0=x_start,
        x1=x_end,
        fillcolor=fill_color,
        layer="below",
        annotation=annotation_arg,
    )
    return fig
