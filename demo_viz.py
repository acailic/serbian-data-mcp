#!/usr/bin/env python3
"""Demo: Create all chart types with sample data."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from serbian_data_mcp.viz.charts import ChartBuilder
from serbian_data_mcp.viz.exporters import export_html, export_png

# Sample data for demonstrations
datasets = {
    "population": [
        {"year": 2018, "population": 7000000, "region": "Central"},
        {"year": 2019, "population": 7050000, "region": "Central"},
        {"year": 2020, "population": 6870000, "region": "Central"},
        {"year": 2021, "population": 6900000, "region": "Central"},
        {"year": 2022, "population": 6920000, "region": "Central"},
    ],
    "regions": [
        {"region": "Beograd", "gdp": 50, "population": 1700000},
        {"region": "Vojvodina", "gdp": 25, "population": 2000000},
        {"region": "Šumadija", "gdp": 12, "population": 1800000},
        {"region": "Južna", "gdp": 8, "population": 1200000},
        {"region": "Zapadna", "gdp": 5, "population": 800000},
    ],
    "categories": [
        {"category": "Agriculture", "value": 15},
        {"category": "Industry", "value": 30},
        {"category": "Services", "value": 45},
        {"category": "Technology", "value": 10},
    ]
}

async def demo_all_charts():
    """Create all chart types."""
    print("📊 Creating Visualization Demos")
    print("=" * 50)

    # 1. Line Chart
    print("\n1. Line Chart (Population Trend)")
    builder = ChartBuilder(datasets["population"])
    chart = builder.line_chart("year", "population", "Serbian Population Trend")
    await export_html(chart, "demo_line.html")
    print("   ✅ Saved: exports/demo_line.html")

    # 2. Bar Chart (Vertical)
    print("\n2. Bar Chart (Regional GDP)")
    builder = ChartBuilder(datasets["regions"])
    chart = builder.bar_chart("region", "gdp", "Regional GDP Distribution")
    await export_html(chart, "demo_bar.html")
    print("   ✅ Saved: exports/demo_bar.html")

    # 3. Bar Chart (Horizontal)
    print("\n3. Bar Chart (Horizontal - Population)")
    chart = builder.bar_chart("region", "population", "Regional Population", orientation="h")
    await export_html(chart, "demo_bar_h.html")
    print("   ✅ Saved: exports/demo_bar_h.html")

    # 4. Pie Chart
    print("\n4. Pie Chart (Economic Sectors)")
    builder = ChartBuilder(datasets["categories"])
    chart = builder.pie_chart("value", "category", "Economic Sector Distribution")
    await export_html(chart, "demo_pie.html")
    print("   ✅ Saved: exports/demo_pie.html")

    # 5. Scatter Plot
    print("\n5. Scatter Plot (GDP vs Population)")
    builder = ChartBuilder(datasets["regions"])
    chart = builder.scatter_plot("population", "gdp", "Regional GDP vs Population", size_column="gdp")
    await export_html(chart, "demo_scatter.html")
    print("   ✅ Saved: exports/demo_scatter.html")

    # 6. Histogram
    print("\n6. Histogram (GDP Distribution)")
    chart = builder.histogram("gdp", "GDP Distribution", bins=5)
    await export_html(chart, "demo_histogram.html")
    print("   ✅ Saved: exports/demo_histogram.html")

    # 7. Box Plot
    print("\n7. Box Plot (Population by Region)")
    chart = builder.box_plot("population", "region", "Population Distribution by Region")
    await export_html(chart, "demo_box.html")
    print("   ✅ Saved: exports/demo_box.html")

    print("\n" + "=" * 50)
    print("✅ All visualizations created!")
    print("\nOpen in browser:")
    for i, name in enumerate([
        "demo_line.html",
        "demo_bar.html",
        "demo_bar_h.html",
        "demo_pie.html",
        "demo_scatter.html",
        "demo_histogram.html",
        "demo_box.html"
    ], 1):
        print(f"  {i}. exports/{name}")

if __name__ == "__main__":
    asyncio.run(demo_all_charts())
