#!/usr/bin/env python3
"""List sample datasets from Serbian data portal."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from serbian_data_mcp.api.client import UDataClient

async def main():
    """Fetch first 500 datasets and categorize them."""
    print("📊 Serbian Data Portal - Sample Datasets")
    print("=" * 70)
    print()

    async with UDataClient() as client:
        # Fetch first 500 datasets
        print("Fetching first 500 datasets...")
        print()

        all_datasets = []
        for page in range(1, 6):  # 5 pages × 100 = 500 datasets
            result = await client.search_datasets(page_size=100, page=page)
            if result.datasets:
                all_datasets.extend(result.datasets)
                print(f"Page {page}: {len(result.datasets)} datasets")

        print(f"\n✅ Retrieved {len(all_datasets)} datasets\n")
        print("=" * 70)

        # Categorize by organization
        by_org = {}
        formats = set()

        for ds in all_datasets:
            org_name = ds.organization.name if ds.organization else "Unknown"
            if org_name not in by_org:
                by_org[org_name] = []
            by_org[org_name].append(ds)

            # Collect formats
            for r in ds.resources:
                if r.format:
                    formats.add(r.format)

        # Show by organization (top 15 by count)
        print(f"\nDatasets by Organization ({len(by_org)} organizations):\n")

        sorted_orgs = sorted(by_org.items(), key=lambda x: len(x[1]), reverse=True)

        for org_name, datasets in sorted_orgs[:15]:
            print(f"\n📁 {org_name}")
            print(f"   Datasets: {len(datasets)}")

            # Show sample datasets
            for i, ds in enumerate(datasets[:2], 1):
                print(f"   {i}. {ds.title or 'Untitled'}")
                if ds.description:
                    desc = ds.description[:100] + "..." if len(ds.description) > 100 else ds.description
                    print(f"      {desc}")

        print(f"\n" + "=" * 70)
        print(f"\nAvailable data formats:\n")
        for fmt in sorted(formats):
            count = sum(1 for ds in all_datasets for r in ds.resources if r.format == fmt)
            print(f"  • {fmt}: {count} resources")

        print(f"\nTotal datasets on portal: {len(all_datasets)} shown (of ~3,430 total)")

if __name__ == "__main__":
    asyncio.run(main())
