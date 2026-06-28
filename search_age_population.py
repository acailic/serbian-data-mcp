#!/usr/bin/env python3
"""Search for age population datasets using API client directly."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from serbian_data_mcp.api.client import UDataClient


async def main():
    """Search for age population datasets and show sample data."""
    print("🔍 Searching for age population datasets on data.gov.rs")
    print("=" * 60)

    async with UDataClient() as client:
        # Search for age-related datasets
        result = await client.search_datasets(query="age population demographics", page_size=20)

        print(f"\nFound {result.total} datasets\n")

        if result.datasets:
            for i, dataset in enumerate(result.datasets[:8], 1):
                print(f"{i}. {dataset.title or 'Untitled'}")
                print(f"   ID: {dataset.id}")
                print(f"   Organization: {dataset.organization or 'N/A'}")

                if dataset.description:
                    desc = dataset.description[:150] + "..." if len(dataset.description) > 150 else dataset.description
                    print(f"   Description: {desc}")

                # Show available resources
                if dataset.resources:
                    print(f"   Resources ({len(dataset.resources)}):")
                    for r in dataset.resources[:3]:
                        print(f"     - {r.title or r.format or 'N/A'} ({r.format or 'N/A'})")
                        if r.format == "csv" or r.format == "json":
                            print("       ⚡ Downloadable for analysis")

                print()

        if result.total > 8:
            print(f"... and {result.total - 8} more datasets")
        else:
            print("Try alternative searches:")
            for term in ["population", "demographics", "stanovnistvo"]:
                r = await client.search_datasets(query=term, page_size=1)
                print(f"  • '{term}': {r.total} datasets")


if __name__ == "__main__":
    asyncio.run(main())
