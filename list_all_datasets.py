#!/usr/bin/env python3
"""List all available datasets from Serbian data portal API."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from serbian_data_mcp.api.client import UDataClient


async def main():
    """Fetch and categorize all datasets."""
    print("📊 Serbian Data Portal - All Datasets")
    print("=" * 70)
    print()

    async with UDataClient() as client:
        # Get total count first
        first_page = await client.search_datasets(page_size=1)
        total = first_page.total

        print(f"Total datasets: {total}\n")
        print("Fetching all datasets (this may take a moment)...")
        print()

        # Fetch all datasets (100 at a time)
        all_datasets = []
        page = 1
        page_size = 100

        while len(all_datasets) < total:
            result = await client.search_datasets(page_size=page_size, page=page)

            if not result.datasets:
                break

            all_datasets.extend(result.datasets)
            print(f"Fetched {len(all_datasets)}/{total} datasets...")
            page += 1

        print(f"\n✅ Retrieved {len(all_datasets)} datasets\n")
        print("=" * 70)

        # Categorize by organization
        by_org = {}
        for ds in all_datasets:
            org_name = ds.organization or "Unknown"
            if org_name not in by_org:
                by_org[org_name] = []
            by_org[org_name].append(ds)

        # Show by organization
        print(f"\nDatasets by Organization ({len(by_org)} organizations):\n")

        # Sort organizations by dataset count
        sorted_orgs = sorted(by_org.items(), key=lambda x: len(x[1]), reverse=True)

        for org_name, datasets in sorted_orgs[:20]:
            print(f"\n📁 {org_name}")
            print(f"   Datasets: {len(datasets)}")

            # Show first few datasets
            for i, ds in enumerate(datasets[:3], 1):
                print(f"   {i}. {ds.title or 'Untitled'}")
                if ds.description:
                    desc = ds.description[:80] + "..." if len(ds.description) > 80 else ds.description
                    print(f"      {desc}")

            if len(datasets) > 3:
                print(f"   ... and {len(datasets) - 3} more")

        print("\n" + "=" * 70)
        print("\nData formats available:")
        formats = set()
        for ds in all_datasets:
            for r in ds.resources:
                if r.format:
                    formats.add(r.format)

        for fmt in sorted(formats):
            count = sum(1 for ds in all_datasets for r in ds.resources if r.format == fmt)
            print(f"  • {fmt}: {count} resources")


if __name__ == "__main__":
    asyncio.run(main())
