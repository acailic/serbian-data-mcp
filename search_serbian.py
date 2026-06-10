#!/usr/bin/env python3
"""Search for population data using Serbian language terms."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from serbian_data_mcp.api.client import UDataClient

async def main():
    """Search using Serbian terms."""
    print("🔍 Pretraga podataka o stanovništvu (Search population data)")
    print("=" * 60)

    async with UDataClient() as client:
        # Try Serbian search terms
        searches = [
            "stanovništvo",  # population
            "broj stanovnika",  # number of inhabitants
            "starosno",  # age
            "demografija",  # demographics
            "popis",  # census
            "age",  # English fallback
        ]

        for term in searches:
            result = await client.search_datasets(query=term, page_size=5)
            if result.total > 0:
                print(f"\n📊 '{term}': {result.total} datasets found\n")
                for ds in result.datasets[:3]:
                    print(f"  • {ds.title or 'Untitled'}")
                    print(f"    ID: {ds.id}")
                    if ds.description:
                        desc = ds.description[:100] + "..." if len(ds.description) > 100 else ds.description
                        print(f"    {desc}")
                    print()
                break
        else:
            print("\n❌ No population datasets found")
            print("Try browsing all datasets:")

            # List recent datasets
            result = await client.search_datasets(page_size=10)
            print(f"\nRecent datasets ({result.total} total):\n")
            for ds in result.datasets[:8]:
                print(f"  • {ds.title or 'Untitled'}")
                print(f"    {ds.organization or 'N/A'}")

if __name__ == "__main__":
    asyncio.run(main())
