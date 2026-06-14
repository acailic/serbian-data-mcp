"""Choropleth maps of Serbia with real district boundaries.

Downloads and caches Natural Earth GeoJSON (25 Serbian districts),
then renders choropleth maps via Plotly with custom theming.
"""

import json
import logging
import urllib.request
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from .themes import apply_theme, SEMANTIC_COLORS

logger = logging.getLogger(__name__)

_NATURAL_EARTH_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_10m_admin_1_states_provinces.geojson"
)

# Common name aliases: user-facing → Natural Earth English name
_DISTRICT_ALIASES: dict[str, str] = {
    # Cyrillic → Latin
    "град београд": "Grad Beograd",
    "шумадијски": "Šumadijski",
    "јужнобанатски": "Južno-Banatski",
    "севернобачки": "Severno-Backi",
    "севернобанатски": "Severno-Banatski",
    "средњебанатски": "Srednje-Banatski",
    "западнобачки": "Zapadno-Backi",
    "борски": "Borski",
    "зајечарски": "Zajecarski",
    "златиборски": "Zlatiborski",
    "моравички": "Moravicki",
    "рачки": "Raški",
    "колубарски": "Kolubarski",
    "мачвански": "Macvanski",
    "подунавски": "Podunavski",
    "браничевски": "Branicevski",
    "пиротски": "Pirotski",
    "топлички": "Toplicki",
    "њишавски": "Nišavski",
    "сремски": "Sremski",
    "јабланички": "Jablanicki",
    "пчињски": "Pcinjski",
    # City shorthand → district
    "beograd": "Grad Beograd",
    "belgrade": "Grad Beograd",
    "novi sad": "Južno-Backi",
    "nis": "Nišavski",
    "niš": "Nišavski",
    "kragujevac": "Šumadijski",
    "subotica": "Severno-Backi",
    "leskovac": "Jablanicki",
    "zajecar": "Zajecarski",
    "cacak": "Moravicki",
    "smederevo": "Podunavski",
    "valjevo": "Kolubarski",
    "kraljevo": "Raški",
    "novi pazar": "Raški",
    "vrsac": "Južno-Banatski",
    "vršac": "Južno-Banatski",
    "sombor": "Zapadno-Backi",
    "zrenjanin": "Srednje-Banatski",
    "sremska mitrovica": "Sremski",
    "vranje": "Pcinjski",
    "pirot": "Pirotski",
    "krusevac": "Pomoravski",
    "kruševac": "Pomoravski",
    "pancevo": "Južno-Banatski",
    "pančevo": "Južno-Banatski",
    "uzice": "Zlatiborski",
    "užice": "Zlatiborski",
    "loznica": "Macvanski",
    "sabac": "Macvanski",
    "šabac": "Macvanski",
    "požarevac": "Pomoravski",
    "pozarevac": "Pomoravski",
    "prokuplje": "Toplicki",
}

# Color scales for different use cases
_RED_BLUE_DIVERGING = [
    (0.0, "#1565c0"),
    (0.25, "#42a5f5"),
    (0.5, "#f5f5f5"),
    (0.75, "#ef5350"),
    (1.0, "#c62828"),
]

_HEAT_RED = [
    (0.0, "#fff9c4"),
    (0.25, "#ffcc80"),
    (0.5, "#ff8a65"),
    (0.75, "#e53935"),
    (1.0, "#b71c1c"),
]

_SEQUENTIAL_BLUE = [
    (0.0, "#e3f2fd"),
    (0.25, "#90caf9"),
    (0.5, "#42a5f5"),
    (0.75, "#1e88e5"),
    (1.0, "#0d47a1"),
]


def _load_serbia_geojson(cache_dir: Path) -> dict[str, Any]:
    """Load or download and cache Serbian district boundaries from Natural Earth."""
    geojson_path = cache_dir / "serbia_districts.geojson"

    if geojson_path.exists():
        logger.debug("Loading cached Serbia GeoJSON from %s", geojson_path)
        with open(geojson_path, encoding="utf-8") as f:
            return json.load(f)

    logger.info("Downloading Serbian district boundaries from Natural Earth...")
    req = urllib.request.Request(_NATURAL_EARTH_URL, headers={"User-Agent": "serbian-data-mcp/0.1"})
    resp = urllib.request.urlopen(req, timeout=60)
    data = json.loads(resp.read().decode("utf-8"))

    serbia_features = [
        f
        for f in data["features"]
        if f["properties"].get("admin") == "Republic of Serbia" and f["properties"].get("iso_a2") == "RS"
    ]

    serbia_geojson = {"type": "FeatureCollection", "features": serbia_features}

    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(serbia_geojson, f, ensure_ascii=False)

    logger.info("Cached %d Serbian districts to %s", len(serbia_features), geojson_path)
    return serbia_geojson


class SerbiaMapBuilder:
    """Build choropleth maps of Serbia's 25 administrative districts.

    Usage:
        builder = SerbiaMapBuilder()
        fig = builder.choropleth(data, name_column="okrug", value_column="populacija")
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        cache_dir = cache_dir or Path(".cache")
        self.cache_dir = cache_dir
        self.geojson = _load_serbia_geojson(cache_dir)
        self._name_to_code = self._build_lookup()

    def _build_lookup(self) -> dict[str, str]:
        """Build name→adm1_code mapping from GeoJSON plus aliases."""
        lookup: dict[str, str] = {}
        for feature in self.geojson["features"]:
            props = feature["properties"]
            code = props.get("adm1_code", "")
            name = props.get("name", "")
            if name and code:
                lookup[name] = code
                lookup[name.lower()] = code
                lookup[name.strip()] = code
                # Add local name if different
                local = props.get("name_local", "")
                if local and local != name:
                    lookup[local] = code
                    lookup[local.lower()] = code

        # Add aliases
        for alias, ne_name in _DISTRICT_ALIASES.items():
            if ne_name in lookup:
                lookup[alias] = lookup[ne_name]

        return lookup

    def resolve_name(self, name: str) -> Optional[str]:
        """Resolve a district name to its adm1_code."""
        if name in self._name_to_code:
            return self._name_to_code[name]
        if name.strip() in self._name_to_code:
            return self._name_to_code[name.strip()]
        if name.lower().strip() in self._name_to_code:
            return self._name_to_code[name.lower().strip()]
        return None

    def list_districts(self) -> list[dict[str, str]]:
        """List all available Serbian districts with codes."""
        return [
            {"name": f["properties"].get("name", ""), "code": f["properties"].get("adm1_code", "")}
            for f in self.geojson["features"]
        ]

    def choropleth(
        self,
        data: list[dict[str, Any]],
        name_column: str,
        value_column: str,
        title: str = "",
        theme: str = "dark",
        colorscale: Optional[list] = None,
        show_labels: bool = True,  # noqa: ARG002
        highlight_top: int = 0,
    ) -> go.Figure:
        """Create a choropleth map of Serbia by district.

        Args:
            data: List of row dicts with district names and values
            name_column: Column containing district names
            value_column: Column containing numeric values
            title: Chart title
            theme: 'dark', 'light', or 'infographic'
            colorscale: Custom colorscale (list of (position, color) tuples)
            show_labels: Whether to show district labels
            highlight_top: Number of top districts to highlight (0 = all equal)

        Returns:
            Plotly Figure with Serbia choropleth map
        """
        df = pd.DataFrame(data)
        df["_code"] = df[name_column].apply(self.resolve_name)
        df_valid = df.dropna(subset=["_code"])

        if df_valid.empty:
            logger.warning("No matching districts found. Available: %s", list(self._name_to_code.keys())[:10])
            return go.Figure()

        colorscale = colorscale or _SEQUENTIAL_BLUE

        fig = go.Figure(
            go.Choropleth(
                geojson=self.geojson,
                locations=df_valid["_code"].tolist(),
                z=df_valid[value_column].tolist(),
                featureidkey="properties.adm1_code",
                colorscale=colorscale,
                marker_line_color="rgba(255,255,255,0.4)",
                marker_line_width=0.5,
                zmin=float(df_valid[value_column].min()),
                zmax=float(df_valid[value_column].max()),
                colorbar=dict(
                    title=dict(text=value_column, font=dict(size=13)),
                    thickness=15,
                    len=0.8,
                    x=0.85,
                ),
                hovertemplate=(f"<b>%{{properties.name}}</b><br>{value_column}: %{{z:,.0f}}<extra></extra>"),
                name="",
            )
        )

        # Highlight top N districts with thicker borders
        if highlight_top > 0:
            top_codes = set(df_valid.nlargest(highlight_top, value_column)["_code"].tolist())
            fig.add_trace(
                go.Choropleth(
                    geojson=self.geojson,
                    locations=list(top_codes),
                    z=[0] * len(top_codes),
                    featureidkey="properties.adm1_code",
                    showscale=False,
                    marker_line_color="#ffab00",
                    marker_line_width=2.5,
                    hoverinfo="skip",
                    name="Top districts",
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
            projection=dict(type="mercator"),
        )

        fig.update_layout(
            title=dict(text=title, font=dict(size=22), x=0.05, xanchor="left"),
            margin=dict(l=20, r=20, t=70, b=20),
            showlegend=False,
        )

        fig = apply_theme(fig, theme)
        # Transparent background for maps
        fig.update_layout(
            paper_bgcolor=fig.layout.paper_bgcolor,
            plot_bgcolor="rgba(0,0,0,0)",
            geo=dict(bgcolor="rgba(0,0,0,0)"),
        )

        return fig

    def ranking_map(
        self,
        data: list[dict[str, Any]],
        name_column: str,
        value_column: str,
        title: str = "",
        theme: str = "dark",
        diverging: bool = True,
    ) -> go.Figure:
        """Create a diverging choropleth showing above/below average.

        Districts above average appear in red tones, below average in blue tones.
        """
        df = pd.DataFrame(data)
        df["_code"] = df[name_column].apply(self.resolve_name)
        df_valid = df.dropna(subset=["_code"])

        if df_valid.empty:
            return go.Figure()

        mean_val = df_valid[value_column].mean()
        colorscale = _RED_BLUE_DIVERGING if diverging else _HEAT_RED

        fig = go.Figure(
            go.Choropleth(
                geojson=self.geojson,
                locations=df_valid["_code"].tolist(),
                z=df_valid[value_column].tolist(),
                featureidkey="properties.adm1_code",
                colorscale=colorscale,
                zmin=float(df_valid[value_column].min()),
                zmax=float(df_valid[value_column].max()),
                marker_line_color="rgba(255,255,255,0.4)",
                marker_line_width=0.5,
                colorbar=dict(
                    title=dict(text=value_column, font=dict(size=13)),
                    thickness=15,
                    len=0.8,
                    x=0.85,
                ),
                hovertemplate=(
                    "<b>%{properties.name}</b><br>"
                    f"{value_column}: %{{z:,.0f}}<br>"
                    f"vs prosečno ({mean_val:,.0f}): %{{customdata[0]:+.1%}}<extra></extra>"
                ),
                customdata=df_valid.apply(
                    lambda r: [((r[value_column] - mean_val) / mean_val) if mean_val != 0 else 0], axis=1
                ).tolist(),
                name="",
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
            projection=dict(type="mercator"),
        )

        fig.update_layout(
            title=dict(text=title, font=dict(size=22), x=0.05, xanchor="left"),
            margin=dict(l=20, r=20, t=70, b=20),
            showlegend=False,
        )

        fig = apply_theme(fig, theme)
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            geo=dict(bgcolor="rgba(0,0,0,0)"),
        )

        return fig
