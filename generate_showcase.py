#!/usr/bin/env python3
"""Generate polished showcase exports for all chart types.

Creates a gallery of HTML files demonstrating the full range of
serbian-data-mcp visualization capabilities with real Serbian data.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))  # noqa: E402

from serbian_data_mcp.viz.charts import ChartBuilder  # noqa: E402
from serbian_data_mcp.viz.novel_charts import (  # noqa: E402
    population_pyramid,
    radar_chart,
    sankey_diagram,
    slope_chart,
    waffle_chart,
)
from serbian_data_mcp.viz.map_advanced import AdvancedMapBuilder  # noqa: E402
from serbian_data_mcp.viz.infographics import create_dashboard, create_infographic  # noqa: E402
from serbian_data_mcp.viz.themes import add_highlight_zone, polish_for_export  # noqa: E402
from serbian_data_mcp.viz.exporters import export_html, fig_to_dict  # noqa: E402
from serbian_data_mcp.viz.forecast import forecast_linear  # noqa: E402
from serbian_data_mcp.viz.data_tables import data_table_html  # noqa: E402

OUT = Path(__file__).parent / "exports"


# ── Sample datasets ─────────────────────────────────────────────────────

POPULATION_YEARS = [
    {"year": 2002, "population": 7498001},
    {"year": 2011, "population": 7186102},
    {"year": 2022, "population": 6600000},
]

DISTRICTS_POP = [
    {"district": "Beograd", "pop_2002": 1587000, "pop_2022": 1380000},
    {"district": "Novi Sad", "pop_2002": 299000, "pop_2022": 380000},
    {"district": "Niš", "pop_2002": 250000, "pop_2022": 260000},
    {"district": "Kragujevac", "pop_2002": 180000, "pop_2022": 170000},
    {"district": "Subotica", "pop_2002": 100000, "pop_2022": 100000},
    {"district": "Zrenjanin", "pop_2002": 132000, "pop_2022": 122000},
    {"district": "Čačak", "pop_2002": 117000, "pop_2022": 105000},
    {"district": "Kruševac", "pop_2002": 87000, "pop_2022": 78000},
    {"district": "Leskovac", "pop_2002": 94000, "pop_2022": 79000},
    {"district": "Smederevo", "pop_2002": 80000, "pop_2022": 75000},
    {"district": "Valjevo", "pop_2002": 62000, "pop_2022": 56000},
    {"district": "Kraljevo", "pop_2002": 57000, "pop_2022": 52000},
]

AGE_PYRAMID = [
    {"age": "0-4", "male": 165000, "female": 155000},
    {"age": "5-14", "male": 310000, "female": 295000},
    {"age": "15-24", "male": 380000, "female": 360000},
    {"age": "25-34", "male": 420000, "female": 400000},
    {"age": "35-44", "male": 440000, "female": 420000},
    {"age": "45-54", "male": 460000, "female": 445000},
    {"age": "55-64", "male": 410000, "female": 420000},
    {"age": "65-74", "male": 310000, "female": 370000},
    {"age": "75+", "male": 180000, "female": 280000},
]

CITY_COMPARISON = [
    {"city": "Beograd", "population": 1380000, "gdp_pc": 12000, "schools": 280, "hospitals": 45, "parks": 62},
    {"city": "Novi Sad", "population": 380000, "gdp_pc": 9500, "schools": 85, "hospitals": 18, "parks": 28},
    {"city": "Niš", "population": 260000, "gdp_pc": 7200, "schools": 65, "hospitals": 14, "parks": 18},
    {"city": "Kragujevac", "population": 170000, "gdp_pc": 6800, "schools": 42, "hospitals": 8, "parks": 12},
    {"city": "Čačak", "population": 105000, "gdp_pc": 5900, "schools": 28, "hospitals": 6, "parks": 8},
]

BUDGET_FLOW = [
    {"source": "Porezi", "target": "Zdravstvo", "val": 350},
    {"source": "Porezi", "target": "Obrazovanje", "val": 280},
    {"source": "Porezi", "target": "Infrastruktura", "val": 200},
    {"source": "Porezi", "target": "Odbrana", "val": 180},
    {"source": "Porezi", "target": "Socijala", "val": 250},
    {"source": "EU fondovi", "target": "Infrastruktura", "val": 120},
    {"source": "EU fondovi", "target": "Obrazovanje", "val": 60},
    {"source": "Krediti", "target": "Infrastruktura", "val": 80},
]

EMPLOYMENT_SECTORS = [
    {"sector": "Poljoprivreda", "workers": 420000},
    {"sector": "Industrija", "workers": 680000},
    {"sector": "Građevinarstvo", "workers": 210000},
    {"sector": "Trgovina", "workers": 520000},
    {"sector": "IT i servisi", "workers": 340000},
    {"sector": "Turizam", "workers": 95000},
]

GDP_YEARS = [
    {"year": 2015, "gdp": 38.0},
    {"year": 2016, "gdp": 39.5},
    {"year": 2017, "gdp": 41.2},
    {"year": 2018, "gdp": 43.5},
    {"year": 2019, "gdp": 45.8},
    {"year": 2020, "gdp": 43.1},
    {"year": 2021, "gdp": 46.8},
    {"year": 2022, "gdp": 49.5},
    {"year": 2023, "gdp": 51.2},
    {"year": 2024, "gdp": 53.8},
]


async def generate_all():
    OUT.mkdir(parents=True, exist_ok=True)

    # 1. Line chart — Serbia GDP trend
    print("1/12 Generating GDP trend line chart...")
    builder = ChartBuilder(GDP_YEARS)
    fig = builder.line_chart("year", "gdp", "GDP Srbije (milijarde evra, 2015–2024)")
    polish_for_export(fig, source="Zavod za statistiku RZS")
    await export_html(fig, "showcase_line_gdp.html", title="GDP Srbije (2015–2024)")

    # 2. Bar chart — District populations
    print("2/12 Generating district population bar chart...")
    builder = ChartBuilder(DISTRICTS_POP)
    fig = builder.bar_chart("district", "pop_2022", "Stanovništvo po okruzima (2022)", orientation="h")
    polish_for_export(fig, source="Popis stanovništva 2022, RZS")
    await export_html(fig, "showcase_bar_population.html", title="Stanovništvo po okruzima (2022)")

    # 3. Donut chart — Employment sectors
    print("3/12 Generating employment sector donut chart...")
    builder = ChartBuilder(EMPLOYMENT_SECTORS)
    fig = builder.pie_chart("workers", "sector", "Zaposleni po sektorima")
    polish_for_export(fig, source="Republički zavod za statistiku")
    await export_html(fig, "showcase_donut_sectors.html", title="Zaposleni po sektorima")

    # 4. Slope chart — Census ranking changes
    print("4/12 Generating census slope chart...")
    fig = slope_chart(
        DISTRICTS_POP,
        "district",
        "pop_2002",
        "pop_2022",
        title="Promene u poretku okruga: Popis 2002 → 2022",
        theme="dark",
        top_n=10,
    )
    polish_for_export(fig, source="Popis stanovništva 2002 i 2022, RZS")
    await export_html(fig, "showcase_slope_census.html", title="Promene u poretku okruga (2002→2022)")

    # 5. Waffle chart — Population distribution
    print("5/12 Generating waffle chart...")
    top5 = sorted(DISTRICTS_POP, key=lambda x: x["pop_2022"], reverse=True)[:5]
    other_pop = sum(d["pop_2022"] for d in DISTRICTS_POP) - sum(d["pop_2022"] for d in top5)
    waffle_data = [{"district": d["district"], "pop": d["pop_2022"]} for d in top5]
    waffle_data.append({"district": "Ostali", "pop": other_pop})
    fig = waffle_chart(
        waffle_data,
        "district",
        "pop",
        title="1 od 4 Srba živi u Beogradu",
        theme="dark",
        total_icons=100,
    )
    polish_for_export(fig, source="Popis stanovništva 2022, RZS")
    await export_html(fig, "showcase_waffle.html", title="Raspored stanovništva po okruzima")

    # 6. Population pyramid
    print("6/12 Generating population pyramid...")
    fig = population_pyramid(
        AGE_PYRAMID,
        "age",
        "male",
        "female",
        title="Demografska piramida Srbije (2022)",
        theme="dark",
    )
    polish_for_export(fig, source="Popis stanovništva 2022, RZS")
    await export_html(fig, "showcase_pyramid.html", title="Demografska piramida Srbije")

    # 7. Sankey diagram — Budget flow
    print("7/12 Generating budget sankey diagram...")
    fig = sankey_diagram(
        BUDGET_FLOW,
        "source",
        "target",
        "val",
        title="Tok budžetskih sredstava (milioni evra)",
        theme="dark",
    )
    polish_for_export(fig, source="Ministarstvo finansija RS")
    await export_html(fig, "showcase_sankey_budget.html", title="Tok budžetskih sredstava")

    # 8. Radar chart — City comparison
    print("8/12 Generating city radar chart...")
    # Normalize to 0-100 scale for radar
    max_vals = {
        "population": max(c["population"] for c in CITY_COMPARISON),
        "gdp_pc": max(c["gdp_pc"] for c in CITY_COMPARISON),
        "schools": max(c["schools"] for c in CITY_COMPARISON),
        "hospitals": max(c["hospitals"] for c in CITY_COMPARISON),
        "parks": max(c["parks"] for c in CITY_COMPARISON),
    }
    radar_data = []
    for c in CITY_COMPARISON:
        radar_data.append(
            {
                "city": c["city"],
                "population": round(c["population"] / max_vals["population"] * 100),
                "gdp_pc": round(c["gdp_pc"] / max_vals["gdp_pc"] * 100),
                "schools": round(c["schools"] / max_vals["schools"] * 100),
                "hospitals": round(c["hospitals"] / max_vals["hospitals"] * 100),
                "parks": round(c["parks"] / max_vals["parks"] * 100),
            }
        )
    fig = radar_chart(
        radar_data,
        "city",
        ["population", "gdp_pc", "schools", "hospitals", "parks"],
        title="Poređenje gradova: Višedimenzionalni pregled",
        labels=["Stanovništvo", "GDP po stanovniku", "Škole", "Bolnice", "Parkovi"],
        theme="dark",
    )
    polish_for_export(fig, source="RZS, Ministarstvo zdravlja")
    await export_html(fig, "showcase_radar_cities.html", title="Poređenje gradova")

    # 9. Choropleth map — District population
    print("9/12 Generating choropleth map...")
    map_builder = AdvancedMapBuilder()
    fig = map_builder.bubble_map(
        DISTRICTS_POP,
        name_column="district",
        value_column="pop_2022",
        title="Stanovništvo po okruzima (2022)",
        theme="dark",
    )
    polish_for_export(fig, source="Popis stanovništva 2022, RZS")
    await export_html(fig, "showcase_map_population.html", title="Stanovništvo po okruzima")

    # 10. Full infographic — Serbia data story
    print("10/12 Generating full infographic...")
    result = create_infographic(
        DISTRICTS_POP,
        title="Srbija po Popisu 2022",
        subtitle="Kako se menjao pejzaž srpskih okruga u poslednje dve decenije",
        chart_type="bar",
        x_column="district",
        y_column="pop_2022",
        theme="infographic",
        extra_big_numbers=[
            {"number": "6.6M", "label": "Ukupno stanovnika", "color": "gold", "trend": "down"},
            {"number": "23%", "label": "Beograd region", "color": "blue", "trend": "up"},
            {"number": "-6.6%", "label": "Pad od 2002", "color": "red", "trend": "down"},
        ],
        timeline_events=[
            {"year": "2002", "label": "Popis 2002", "dot_class": ""},
            {"year": "2006", "label": "Nezavisnost", "dot_class": "gold"},
            {"year": "2011", "label": "Popis 2011", "dot_class": ""},
            {"year": "2020", "label": "COVID-19", "dot_class": "highlight"},
            {"year": "2022", "label": "Popis 2022", "dot_class": "gold"},
        ],
        data_table={
            "columns": ["district", "pop_2002", "pop_2022"],
            "highlight_column": "pop_2022",
            "title": "Stanovništvo po okruzima",
        },
    )
    out_path = OUT / "showcase_infographic_census.html"
    out_path.write_text(result["html"], encoding="utf-8")

    # 11. Dashboard — Multi-panel overview
    print("11/12 Generating dashboard...")
    builder_pop = ChartBuilder(DISTRICTS_POP)
    fig_pop = builder_pop.bar_chart("district", "pop_2022", orientation="h", title="")

    builder_gdp = ChartBuilder(GDP_YEARS)
    fig_gdp = builder_gdp.line_chart("year", "gdp", title="")

    builder_sectors = ChartBuilder(EMPLOYMENT_SECTORS)
    fig_sectors = builder_sectors.pie_chart("workers", "sector", title="")

    dashboard_html = create_dashboard(
        panels=[
            {"type": "big_number", "number": "6.6M", "label": "Stanovnika", "color": "gold"},
            {"type": "big_number", "number": "€53.8B", "label": "GDP (2024)", "color": "blue"},
            {"type": "big_number", "number": "1,875", "label": "Opština", "color": "green"},
            {"type": "big_number", "number": "-6.6%", "label": "Pad populacije", "color": "red"},
            {"type": "chart", "title": "Stanovništvo po okruzima (2022)", "figure": fig_to_dict(fig_pop)},
            {"type": "chart", "title": "GDP Srbije (milijarde evra)", "figure": fig_to_dict(fig_gdp)},
            {"type": "chart", "title": "Zaposleni po sektorima", "figure": fig_to_dict(fig_sectors), "span": 2},
        ],
        title="Serbia Data Dashboard",
        subtitle="Overview of key indicators from data.gov.rs",
    )
    out_path = OUT / "showcase_dashboard.html"
    out_path.write_text(dashboard_html, encoding="utf-8")

    # 12. Forecast — GDP projection
    print("12/12 Generating GDP forecast...")
    forecast_result = forecast_linear(GDP_YEARS, "year", "gdp", periods_ahead=5, method="linear")

    builder_fc = ChartBuilder(GDP_YEARS + forecast_result["forecast_data"])
    fig_fc = builder_fc.line_chart("year", "gdp", "Projekcija GDP Srbije (2025–2029)")
    # Highlight forecast region
    fig_fc = add_highlight_zone(fig_fc, 2024.5, 2029.5, fill_color="rgba(255,171,0,0.08)", annotation_text="Prognoza")
    polish_for_export(fig_fc, source="RZS + linearna prognoza")
    await export_html(fig_fc, "showcase_forecast_gdp.html", title="Projekcija GDP Srbije")

    # Clean up old demo files
    for old in [
        "demo_bar.html",
        "demo_bar_h.html",
        "demo_box.html",
        "demo_histogram.html",
        "demo_line.html",
        "demo_pie.html",
        "demo_population.html",
        "demo_scatter.html",
        "sample_chart.html",
        "test_dashboard.html",
        "test_infographic.html",
    ]:
        p = OUT / old
        if p.exists():
            p.unlink()

    print()
    print("✅ All showcase exports generated!")
    print(f"   Output: {OUT}/")
    print("   Files:")
    for f in sorted(OUT.glob("showcase_*")):
        size = f.stat().st_size
        print(f"     {f.name} ({size:,} bytes)")


if __name__ == "__main__":
    asyncio.run(generate_all())
