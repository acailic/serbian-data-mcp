#!/usr/bin/env python3
"""Search all datasets from Statistical Office (РЗС)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from serbian_data_mcp.api.client import UDataClient

async def main():
    """Browse Statistical Office datasets by organization name."""
    print("🏢 Browsing Републички завод за статистику (РЗС) datasets")
    print("=" * 60)

    async with UDataClient() as client:
        # Get organizations to find РЗС
        orgs = await client.list_organizations(page_size=100)
        rzs_org = None
        for org in orgs:
            if "РЗС" in (org.name or "") or "statistic" in (org.name or "").lower():
                rzs_org = org
                print(f"Found: {org.name} (ID: {org.id})")
                break

        if not rzs_org:
            print("❌ Statistical Office not found in organization list")
            print("\nShowing all organizations:")
            for org in orgs[:10]:
                print(f"  • {org.name} (ID: {org.id})")
            return

        # Search datasets by this organization
        print(f"\n📊 Searching datasets from {rzs_org.name}...\n")
        result = await client.search_datasets(
            organization=rzs_org.id,
            page_size=50
        )

        print(f"Found {result.total} datasets\n")

        if result.datasets:
            # Look for anything with population/demographic keywords
            keywords = ["stanovni", "population", "staros", "age", "demograf", "popis", "broj"]

            for i, ds in enumerate(result.datasets[:20], 1):
                title_lower = (ds.title or "").lower()
                desc_lower = (ds.description or "").lower()
                combined = title_lower + " " + desc_lower

                matches = [kw for kw in keywords if kw in combined]

                if matches or i <= 10:  # Show first 10 regardless
                    print(f"{i}. {ds.title or 'Untitled'}")
                    print(f"   ID: {ds.id}")
                    if matches:
                        print(f"   🔍 Keywords: {', '.join(matches)}")
                    if ds.resources:
                        formats = {r.format for r in ds.resources if r.format}
                        print(f"   Formats: {', '.join(formats)}")
                    print()
        else:
            print("No datasets found")

if __name__ == "__main__":
    asyncio.run(main())
