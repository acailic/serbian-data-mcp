"""Custom Plotly themes for Serbian data visualizations.

Provides themed templates for different presentation contexts:
- Dark theme: Dramatic, data-journalism style
- Light theme: Clean, professional
- Infographic: Big-number focused layouts
- Serbian flag palette: Red, blue, white color system
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


def _dark_layout_dict() -> dict[str, Any]:
    """Raw layout dict for dark theme."""
    return {
        "paper_bgcolor": "#1a1a2e",
        "plot_bgcolor": "#16213e",
        "font": {"family": "'Segoe UI', Arial, sans-serif", "color": "#e0e0e0", "size": 14},
        "title": {"font": {"size": 22, "color": "#ffffff"}, "x": 0.05, "xanchor": "left"},
        "xaxis": {
            "gridcolor": "#2a3a5c",
            "linecolor": "#2a3a5c",
            "zerolinecolor": "#4a5a7c",
            "title": {"font": {"size": 14, "color": "#b0bec5"}},
            "tickfont": {"size": 12, "color": "#90a4ae"},
        },
        "yaxis": {
            "gridcolor": "#2a3a5c",
            "linecolor": "#2a3a5c",
            "zerolinecolor": "#4a5a7c",
            "title": {"font": {"size": 14, "color": "#b0bec5"}},
            "tickfont": {"size": 12, "color": "#90a4ae"},
        },
        "legend": {"bgcolor": "#1a1a2e", "font": {"color": "#e0e0e0", "size": 12}, "bordercolor": "#2a3a5c"},
        "colorway": SEMANTIC_COLORS,
        "hoverlabel": {"bgcolor": "#1a1a2e", "bordercolor": "#1565c0", "font": {"color": "#ffffff"}},
        "margin": {"l": 80, "r": 40, "t": 80, "b": 80},
    }


def _light_layout_dict() -> dict[str, Any]:
    """Raw layout dict for light theme."""
    return {
        "paper_bgcolor": "#ffffff",
        "plot_bgcolor": "#fafafa",
        "font": {"family": "'Segoe UI', Arial, sans-serif", "color": "#37474f", "size": 14},
        "title": {"font": {"size": 22, "color": "#1a1a2e"}, "x": 0.05, "xanchor": "left"},
        "xaxis": {
            "gridcolor": "#e0e0e0",
            "linecolor": "#bdbdbd",
            "zerolinecolor": "#9e9e9e",
            "title": {"font": {"size": 14, "color": "#455a64"}},
            "tickfont": {"size": 12, "color": "#616161"},
        },
        "yaxis": {
            "gridcolor": "#e0e0e0",
            "linecolor": "#bdbdbd",
            "zerolinecolor": "#9e9e9e",
            "title": {"font": {"size": 14, "color": "#455a64"}},
            "tickfont": {"size": 12, "color": "#616161"},
        },
        "legend": {"bgcolor": "#ffffff", "font": {"color": "#37474f", "size": 12}, "bordercolor": "#e0e0e0"},
        "colorway": SEMANTIC_COLORS,
        "hoverlabel": {"bgcolor": "#ffffff", "bordercolor": "#1565c0", "font": {"color": "#1a1a2e"}},
        "margin": {"l": 80, "r": 40, "t": 80, "b": 80},
    }


def _infographic_layout_dict() -> dict[str, Any]:
    """Raw layout dict for infographic theme."""
    return {
        "paper_bgcolor": "#1a1a2e",
        "plot_bgcolor": "#16213e",
        "font": {"family": "'Segoe UI', Arial, sans-serif", "color": "#ffffff", "size": 16},
        "title": {"font": {"size": 28, "color": "#ffffff"}, "x": 0.5, "xanchor": "center"},
        "xaxis": {
            "showgrid": False,
            "linecolor": "rgba(255,255,255,0.1)",
            "title": {"font": {"size": 15, "color": "#b0bec5"}},
            "tickfont": {"size": 13, "color": "#90a4ae"},
        },
        "yaxis": {
            "showgrid": True,
            "gridcolor": "rgba(255,255,255,0.08)",
            "linecolor": "rgba(255,255,255,0.1)",
            "title": {"font": {"size": 15, "color": "#b0bec5"}},
            "tickfont": {"size": 13, "color": "#90a4ae"},
        },
        "legend": {
            "bgcolor": "rgba(26,26,46,0.8)",
            "font": {"color": "#e0e0e0", "size": 13},
            "bordercolor": "rgba(255,255,255,0.1)",
        },
        "colorway": SEMANTIC_COLORS,
        "hoverlabel": {"bgcolor": "#1a1a2e", "bordercolor": "#ffab00", "font": {"color": "#ffffff", "size": 14}},
        "margin": {"l": 100, "r": 60, "t": 100, "b": 100},
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


def apply_theme(fig: go.Figure, theme: str = "dark") -> go.Figure:
    """Apply a named theme to a Plotly figure.

    Args:
        fig: Plotly Figure to theme
        theme: 'dark', 'light', or 'infographic'

    Returns:
        Themed Plotly Figure
    """
    templates = {
        "dark": _dark_layout_dict,
        "light": _light_layout_dict,
        "infographic": _infographic_layout_dict,
    }
    builder = templates.get(theme)
    if not builder:
        builder = _dark_layout_dict
    fig.update_layout(builder())
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
