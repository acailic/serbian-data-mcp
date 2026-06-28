#!/usr/bin/env python3
"""MCP Client Showcase – Demonstrates all MCP capabilities of the Serbian Data Server.

This script connects to the Serbian Data MCP Server in-process and exercises
every MCP capability: tools, resources, and prompts.  It serves as both a
living example and a quick smoke-test.

Usage:
    python example_mcp_client.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

# Ensure the source package is importable
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastmcp import Client
from fastmcp.client import FastMCPTransport
from serbian_data_mcp import mcp


# ---------- pretty-printing helpers ----------

BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def header(text: str, icon: str = "🔧") -> None:
    print(f"\n{BOLD}{CYAN}{'=' * 60}{RESET}")
    print(f"{BOLD}{CYAN}{icon}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 60}{RESET}\n")


def step(n: int, text: str) -> None:
    print(f"{BOLD}{YELLOW}[Step {n}]{RESET} {text}")


def ok(text: str) -> None:
    print(f"  {GREEN}✓{RESET} {text}")


def info(text: str) -> None:
    print(f"  {DIM}{text}{RESET}")


def show_json(data: Any, max_lines: int = 20) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    lines = text.splitlines()
    if len(lines) > max_lines:
        for line in lines[: max_lines - 1]:
            print(f"    {line}")
        print(f"    {DIM}... ({len(lines) - max_lines + 1} more lines){RESET}")
    else:
        for line in lines:
            print(f"    {line}")


def parse_result(result: Any) -> dict[str, Any]:
    for content in result.content:
        if hasattr(content, "text"):
            return json.loads(content.text)
    raise ValueError(f"Cannot parse MCP result: {result}")


# ---------- showcase sections ----------


async def discover_server(client: Client) -> None:
    """Showcase 1: Server discovery – tools, resources, prompts."""
    header("Server Discovery", "🔍")

    # Tools
    step(1, "Listing all available MCP tools …")
    tools = await client.list_tools()
    ok(f"Found {len(tools)} tools")
    for tool in tools:
        print(f"    {CYAN}{tool.name:<30}{RESET} {DIM}{tool.description[:70]}{RESET}")

    # Resources
    step(2, "Listing all available MCP resources …")
    resources = await client.list_resources()
    ok(f"Found {len(resources)} resources")
    for r in resources:
        print(f"    {CYAN}{r.uri}{RESET}")

    # Prompts
    step(3, "Listing all available MCP prompts …")
    prompts = await client.list_prompts()
    ok(f"Found {len(prompts)} prompts")
    for p in prompts:
        desc = p.description or ""
        print(f"    {CYAN}{p.name:<30}{RESET} {DIM}{desc[:70]}{RESET}")


async def read_resources(client: Client) -> None:
    """Showcase 2: Reading MCP resources."""
    header("Reading Resources", "📄")

    step(1, "Reading serbian-data://server-info …")
    contents = await client.read_resource("serbian-data://server-info")
    info_text = contents[0].text if hasattr(contents[0], "text") else str(contents[0])
    data = json.loads(info_text)
    ok("Server metadata retrieved")
    show_json(data)


async def render_prompts(client: Client) -> None:
    """Showcase 3: Rendering MCP prompts."""
    header("Prompt Templates", "💬")

    examples = [
        ("search_prompt", {"query": "obrazovanje"}, "Search for education datasets"),
        ("explore_dataset_prompt", {"dataset_id": "demo-123"}, "Explore a specific dataset"),
        ("visualize_prompt", {"description": "GDP trend chart"}, "Create a GDP visualization"),
    ]

    for i, (name, args, desc) in enumerate(examples, 1):
        step(i, f"Rendering prompt '{name}' ({desc}) …")
        result = await client.get_prompt(name, args)
        for msg in result.messages:
            text = msg.content.text if hasattr(msg.content, "text") else str(msg.content)
            print(f"    {DIM}{text[:200]}{RESET}")
        ok(f"Prompt rendered with {len(result.messages)} message(s)")


async def search_and_retrieve(client: Client) -> None:
    """Showcase 4: Search tools – search, suggest, list organizations."""
    header("Search & Data Retrieval", "🔎")

    step(1, "Searching datasets (query='statistika', page_size=3) …")
    result = await client.call_tool("search_datasets", {"query": "statistika", "page_size": 3})
    data = parse_result(result)
    ok(f"Found {data['total']} total datasets, showing {len(data['datasets'])}")
    for ds in data["datasets"]:
        print(f"    {CYAN}{ds.get('title', 'N/A')[:60]}{RESET}")
        print(f"    {DIM}  ID: {ds['id']}  Tags: {ds.get('tags', [])[:3]}{RESET}")

    step(2, "Getting search suggestions (query='pop') …")
    result = await client.call_tool("suggest_datasets", {"query": "pop", "size": 5})
    data = parse_result(result)
    ok(f"Got {data['count']} suggestions")
    for s in data["suggestions"][:5]:
        print(f"    • {s}")

    step(3, "Listing organizations (page_size=5) …")
    result = await client.call_tool("list_organizations", {"page_size": 5})
    data = parse_result(result)
    ok(f"Got {data['count']} organizations")
    for org in data["organizations"]:
        print(f"    • {CYAN}{org.get('name', 'N/A')}{RESET}")


async def transform_data(client: Client) -> None:
    """Showcase 5: Data transformation pipeline."""
    header("Data Transformation Pipeline", "⚙️")

    sample = [
        {"region": "Beograd", "year": 2021, "population": 1720, "gdp": 26000},
        {"region": "Novi Sad", "year": 2021, "population": 355, "gdp": 18500},
        {"region": "Nis", "year": 2021, "population": 250, "gdp": 16000},
        {"region": "Beograd", "year": 2022, "population": 1740, "gdp": 27500},
        {"region": "Novi Sad", "year": 2022, "population": 360, "gdp": 19000},
    ]

    step(1, "Filtering: year == 2022 …")
    result = await client.call_tool(
        "filter_data_tool",
        {
            "data": sample,
            "filters": {"year": 2022},
        },
    )
    data = parse_result(result)
    ok(f"Filtered to {data['rows']} rows")
    show_json(data)

    step(2, "Sorting by GDP descending …")
    result = await client.call_tool(
        "sort_data_tool",
        {
            "data": data["data"],
            "by": "gdp",
            "ascending": False,
        },
    )
    data = parse_result(result)
    ok("Sorted")
    show_json(data)

    step(3, "Aggregating: sum of population …")
    result = await client.call_tool(
        "aggregate_data_tool",
        {
            "data": data["data"],
            "column": "population",
            "function": "sum",
        },
    )
    data = parse_result(result)
    ok(f"Total population (in thousands): {data['value']}")

    step(4, "Selecting columns: region, gdp …")
    result = await client.call_tool(
        "select_columns_tool",
        {
            "data": sample,
            "columns": ["region", "gdp"],
        },
    )
    data = parse_result(result)
    ok(f"Selected {len(data.get('columns', []))} columns")
    show_json(data)


async def visualize(client: Client) -> None:
    """Showcase 6: Visualization – create charts and export."""
    header("Visualization & Export", "📊")

    sample = [
        {"city": "Beograd", "pop": 1740, "gdp": 27500},
        {"city": "Novi Sad", "pop": 360, "gdp": 19000},
        {"city": "Nis", "pop": 250, "gdp": 16000},
        {"city": "Kragujevac", "pop": 180, "gdp": 14000},
    ]

    chart_types = [
        ("bar", {"x_column": "city", "y_column": "pop", "title": "Population by City"}),
        ("pie", {"values_column": "gdp", "names_column": "city", "title": "GDP Share"}),
        ("scatter", {"x_column": "pop", "y_column": "gdp", "title": "Population vs GDP"}),
    ]

    last_figure = None
    for i, (ctype, params) in enumerate(chart_types, 1):
        step(i, f"Creating {ctype} chart: {params.get('title', '')} …")
        args = {"data": sample, "chart_type": ctype, **params}
        result = await client.call_tool("create_visualization", args)
        data = parse_result(result)
        ok(f"Chart created (type={data['chart_type']}, interactive={data['interactive']})")
        info(f"Figure has {len(data['figure'].get('data', []))} trace(s)")
        last_figure = data["figure"]

    if last_figure:
        step(4, "Exporting chart to JSON …")
        result = await client.call_tool(
            "export_visualization",
            {
                "figure": last_figure,
                "format": "json",
                "filename": "showcase-chart",
            },
        )
        data = parse_result(result)
        ok(f"Exported to {data['filepath']}")


async def utilities(client: Client) -> None:
    """Showcase 7: Utility tools – config and health."""
    header("Utilities", "🛠️")

    step(1, "Getting server configuration …")
    result = await client.call_tool("get_config_tool", {})
    data = parse_result(result)
    ok("Configuration retrieved")
    show_json(data)

    step(2, "Health check …")
    result = await client.call_tool("health_check", {})
    data = parse_result(result)
    ok(f"Status: {data['status']}, API reachable: {data['api_reachable']}")
    show_json(data)


# ---------- main ----------


async def main() -> None:
    print(f"\n{BOLD}🇷🇸  Serbian Data MCP Server – Client Showcase{RESET}")
    print(f"{DIM}{'─' * 60}{RESET}")
    start = time.perf_counter()

    transport = FastMCPTransport(mcp)
    async with Client(transport) as client:
        await discover_server(client)
        await read_resources(client)
        await render_prompts(client)
        await search_and_retrieve(client)
        await transform_data(client)
        await visualize(client)
        await utilities(client)

    elapsed = time.perf_counter() - start
    print(f"\n{BOLD}{GREEN}{'=' * 60}{RESET}")
    print(f"{BOLD}{GREEN}✅  All showcases completed in {elapsed:.2f}s{RESET}")
    print(f"{BOLD}{GREEN}{'=' * 60}{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
