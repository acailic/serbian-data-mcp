#!/usr/bin/env python3
"""Browse Statistical Office datasets for population data."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from serbian_data_mcp.api.client import UDataClient


async def main():
    """Browse Statistical Office (РЗС) datasets."""
    print("🏢 Републички завод за статистику (Statistical Office)")
    print("=" * 60)

    async with UDataClient() as client:
        # Search for datasets from Statistical Office
        result = await client.search_datasets(
            organization="5fbf76d87de2727637f02829",  # РЗС ID
            page_size=20,
        )

        print(f"\nFound {result.total} datasets from Statistical Office\n")

        # Look for population-related datasets
        pop_datasets = []
        for ds in result.datasets:
            title_lower = (ds.title or "").lower()
            if any(
                term in title_lower
                for term in ["stanovništvo", "population", "popis", "broj", "starosno", "age", "demograf"]
            ):
                pop_datasets.append(ds)

        print(f"📊 Population-related: {len(pop_datasets)} datasets\n")

        if pop_datasets:
            for i, ds in enumerate(pop_datasets[:10], 1):
                print(f"{i}. {ds.title or 'Untitled'}")
                print(f"   ID: {ds.id}")
                if ds.description:
                    desc = ds.description[:150] + "..." if len(ds.description) > 150 else ds.description
                    print(f"   {desc}")
                if ds.resources:
                    print(
                        f"   Resources: {len(ds.resources)} ({', '.join({r.format for r in ds.resources if r.format})})"
                    )
                print()
        else:
            # Show first 10 datasets
            print("Recent datasets from Statistical Office:\n")
            for i, ds in enumerate(result.datasets[:10], 1):
                print(f"{i}. {ds.title or 'Untitled'}")
                if ds.resources:
                    print(f"   Resources: {len(ds.resources)}")
                print()


if __name__ == "__main__":
    asyncio.run(main())
