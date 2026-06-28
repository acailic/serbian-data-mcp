#!/usr/bin/env python3
"""Example usage of Serbian Data MCP Server.

This script demonstrates how to use the Serbian Data API client
to search for datasets, download data, and create visualizations.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent / "src"))

from serbian_data_mcp.api.client import UDataClient
from serbian_data_mcp.viz.charts import ChartBuilder
from serbian_data_mcp.viz.exporters import export_html


async def example_search_datasets():
    """Example: Search for datasets."""
    print("🔍 Example 1: Searching for datasets")
    print("=" * 50)

    async with UDataClient() as client:
        # Search for population-related datasets
        result = await client.search_datasets(query="population", page_size=5)

        print(f"Found {result.total} datasets matching 'population'")
        print(f"\nShowing {len(result.datasets)} results:")

        for i, dataset in enumerate(result.datasets, 1):
            print(f"\n{i}. {dataset.title or 'Untitled'}")
            print(f"   ID: {dataset.id}")
            print(f"   Organization: {dataset.organization}")
            if dataset.description:
                desc = dataset.description[:100] + "..." if len(dataset.description) > 100 else dataset.description
                print(f"   Description: {desc}")

    print("\n" + "✅" * 25 + "\n")


async def example_get_dataset():
    """Example: Get complete dataset details."""
    print("📊 Example 2: Getting dataset details")
    print("=" * 50)

    async with UDataClient() as client:
        # First search to get a dataset ID
        result = await client.search_datasets(query="statistika", page_size=1)

        if result.datasets:
            dataset_id = result.datasets[0].id
            print(f"Fetching details for dataset: {dataset_id}")

            dataset = await client.get_dataset(dataset_id)

            if dataset:
                print(f"\nTitle: {dataset.title or 'N/A'}")
                print(f"Description: {dataset.description or 'N/A'}")
                print(f"Organization: {dataset.organization or 'N/A'}")
                print(f"Created: {dataset.created or 'N/A'}")
                print(f"\nResources ({len(dataset.resources)}):")

                for i, resource in enumerate(dataset.resources, 1):
                    print(f"  {i}. {resource.title or resource.format or 'N/A'}")
                    print(f"     Format: {resource.format or 'N/A'}")
                    if resource.url:
                        print(f"     URL: {resource.url[:60]}...")
        else:
            print("No datasets found")

    print("\n" + "✅" * 25 + "\n")


async def example_list_organizations():
    """Example: List data provider organizations."""
    print("🏢 Example 3: Listing organizations")
    print("=" * 50)

    async with UDataClient() as client:
        organizations = await client.list_organizations(page_size=10)

        print(f"\nFound {len(organizations)} organizations:\n")

        for i, org in enumerate(organizations, 1):
            print(f"{i}. {org.name or 'Unnamed Organization'}")
            if org.description:
                desc = org.description[:80] + "..." if len(org.description) > 80 else org.description
                print(f"   {desc}")

    print("\n" + "✅" * 25 + "\n")


async def example_suggestions():
    """Example: Get search suggestions."""
    print("💡 Example 4: Getting search suggestions")
    print("=" * 50)

    async with UDataClient() as client:
        # Get suggestions for a partial query
        suggestions = await client.suggest_datasets("pop", size=8)

        print("\nSuggestions for 'pop':\n")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")

    print("\n" + "✅" * 25 + "\n")


async def example_visualization():
    """Example: Create a simple visualization."""
    print("📈 Example 5: Creating a visualization")
    print("=" * 50)

    # Sample data for demonstration
    data = {"year": [2018, 2019, 2020, 2021, 2022], "population": [7000000, 7050000, 6870000, 6900000, 6920000]}

    print("\nCreating a line chart from sample data...")
    print("Year vs Population")

    try:
        # Create chart using ChartBuilder
        builder = ChartBuilder(data)
        chart = builder.line_chart(x_column="year", y_column="population", title="Serbian Population Trend (Sample)")

        # Export to HTML
        output_path = "sample_chart.html"

        # Export using async function
        result = await export_html(chart, output_path)
        print(f"Chart exported to: {result}")

        print(f"\n✅ Chart saved to: {output_path}")
        print("   Open it in your browser to view the interactive chart")

    except Exception as e:
        print(f"\n⚠️  Visualization failed: {e}")
        print("   This is expected if dependencies are missing")

    print("\n" + "✅" * 25 + "\n")


async def main():
    """Run all examples."""
    print("🇷🇸 Serbian Data MCP Server - Usage Examples")
    print("=" * 50)
    print()

    try:
        # Run examples
        await example_search_datasets()
        await example_get_dataset()
        await example_list_organizations()
        await example_suggestions()
        await example_visualization()

        print("🎉 All examples completed!")
        print()
        print("Next steps:")
        print("  • Try your own searches with the API client")
        print("  • Export visualizations in different formats")
        print("  • Integrate with Claude Desktop for AI-powered queries")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("   Make sure you have internet connectivity")
        print("   and the server is properly configured.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
