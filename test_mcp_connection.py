#!/usr/bin/env python3
"""Connect to Serbian Data MCP Server via SSE and search for age population data."""

import asyncio
import json

from mcp_python import ClientSession
from mcp_python.client.sse import SseClientTransport


async def main():
    """Connect to MCP server and search for age population data."""
    # Connect to SSE server
    transport = SseClientTransport(url="http://localhost:8001/sse")

    print("🔗 Connecting to Serbian Data MCP Server...")
    print("Server: http://localhost:8001/sse")
    print()

    async with ClientSession(transport) as session:
        # Initialize connection
        await session.initialize()

        print("✅ Connected!")
        print("\n📊 Available Tools:")

        # List available tools
        tools = await session.list_tools()
        for tool in tools.tools[:5]:
            print(f"  • {tool.name}: {tool.description[:60]}...")

        print(f"\n... and {len(tools.tools) - 5} more tools")
        print("\n" + "=" * 60)
        print("🔍 Searching for age population datasets...")
        print("=" * 60)

        # Search for age population datasets
        result = await session.call_tool("search_datasets", {"query": "age population", "page_size": 10})

        data = json.loads(result.content[0].text)

        print(f"\nFound {data.get('total', 0)} datasets\n")

        if data.get("datasets"):
            for i, dataset in enumerate(data["datasets"][:5], 1):
                print(f"{i}. {dataset.get('title', 'Untitled')}")
                print(f"   ID: {dataset.get('id')}")
                print(f"   Organization: {dataset.get('organization', {}).get('name', 'N/A')}")
                desc = dataset.get("description", "")
                if desc:
                    short_desc = desc[:100] + "..." if len(desc) > 100 else desc
                    print(f"   Description: {short_desc}")
                print()
        else:
            print("No datasets found")

        # Try alternative search
        print("\n" + "-" * 60)
        print("Alternative: 'population' datasets")
        print("-" * 60 + "\n")

        result = await session.call_tool("search_datasets", {"query": "population", "page_size": 5})

        data = json.loads(result.content[0].text)
        print(f"Found {data.get('total', 0)} population datasets\n")

        if data.get("datasets"):
            for i, dataset in enumerate(data["datasets"][:3], 1):
                print(f"{i}. {dataset.get('title', 'Untitled')}")
                print(f"   Resources: {len(dataset.get('resources', []))}")


if __name__ == "__main__":
    asyncio.run(main())
