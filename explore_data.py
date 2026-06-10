#!/usr/bin/env python3
"""Explore available datasets to understand what's on the portal."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from serbian_data_mcp.api.client import UDataClient

async def main():
    """Explore datasets to find population data."""
    print("🔍 Exploring Serbian data portal (data.gov.rs)")
    print("=" * 60)

    async with UDataClient() as client:
        # Get organizations first
        print("\n📋 Organizations publishing data:\n")
        orgs = await client.list_organizations(page_size=10)
        for org in orgs[:10]:
            print(f"  • {org.name or 'Unnamed'}")
            if org.id:
                print(f"    ID: {org.id}")

        # Get recent datasets across all orgs
        print(f"\n📊 Recent datasets (across all organizations):\n")
        result = await client.search_datasets(page_size=20)

        for i, ds in enumerate(result.datasets[:15], 1):
            org_name = "Unknown"
            if ds.organization:
                org_name = ds.organization

            print(f"{i}. {ds.title or 'Untitled'}")
            print(f"   Organization: {org_name}")

            if ds.resources:
                formats = set(r.format for r in ds.resources if r.format)
                print(f"   Formats: {', '.join(formats)}")

            # Show description for context
            if ds.description and len(ds.description) < 200:
                print(f"   Description: {ds.description}")
            print()

        print(f"\nTotal datasets on portal: {result.total}")
        print(f"Datasets shown: {len(result.datasets)}")

if __name__ == "__main__":
    asyncio.run(main())
