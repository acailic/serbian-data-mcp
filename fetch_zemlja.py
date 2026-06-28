#!/usr/bin/env python3
"""Fetch and examine the 'Земља' dataset from Statistical Office."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from serbian_data_mcp.api.client import UDataClient

async def main():
    """Fetch 'Земља' dataset to examine contents."""
    print("📊 Fetching dataset: Земља (Land)")
    print("=" * 60)

    async with UDataClient() as client:
        # Search for the dataset first to get ID
        result = await client.search_datasets(
            query="Земља",
            page_size=5
        )

        if result.datasets and result.datasets[0]:
            dataset_id = result.datasets[0].id
            print(f"Found dataset: {result.datasets[0].title}")
            print(f"ID: {dataset_id}")
            print()

            # Get full dataset details
            dataset = await client.get_dataset(dataset_id)
            if dataset:
                print(f"Title: {dataset.title or 'N/A'}")
                print(f"Description: {dataset.description or 'N/A'}")
                print(f"Organization: {dataset.organization or 'N/A'}")
                print(f"Created: {dataset.created_at or 'N/A'}")
                print()

                print(f"Resources ({len(dataset.resources)}):")
                for i, resource in enumerate(dataset.resources, 1):
                    print(f"\n{i}. {resource.title or 'N/A'}")
                    print(f"   ID: {resource.id}")
                    print(f"   Format: {resource.format or 'N/A'}")
                    if resource.url:
                        print(f"   URL: {resource.url[:80]}...")

                    # Try to fetch data if CSV/JSON
                    if resource.format in ['csv', 'json', 'xlsx']:
                        print("\n   ⚡ Attempting to download...")
                        try:
                            data = await client.get_resource_data(resource.id)
                            print("   ✅ Data fetched successfully")

                            # Show first few rows
                            if hasattr(data, 'head'):
                                print("\n   First 5 rows:")
                                print(data.head().to_string(index=False))
                            elif isinstance(data, dict):
                                print(f"\n   Data keys: {list(data.keys())}")
                            elif isinstance(data, list) and len(data) > 0:
                                print(f"\n   First item keys: {list(data[0].keys())}")
                        except Exception as e:
                            print(f"   ❌ Failed to download: {str(e)[:100]}")
                print()

if __name__ == "__main__":
    asyncio.run(main())
