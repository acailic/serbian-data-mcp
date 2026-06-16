"""MCP protocol tests for Serbian Data MCP Server.

Exercises the full MCP capability surface via in-process transport:
  • Server discovery  (list_tools, list_resources, list_prompts)
  • Search tools      (search_datasets, suggest_datasets, list_organizations)
  • Data retrieval     (get_dataset)
  • Visualization      (create_chart, export_visualization)
  • Data transforms   (transform_data, filter_data_tool)
  • Utilities         (health_check)
  • Resources         (read serbian-data://server-info)
  • Prompts           (render each prompt template)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.client import FastMCPTransport

from serbian_data_mcp import mcp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def mcp_client():
    """Yield an MCP Client connected to the server in-process."""
    transport = FastMCPTransport(mcp)
    async with Client(transport) as client:
        yield client


@pytest.fixture
def sample_data() -> list[dict[str, Any]]:
    """Reusable sample dataset for tool calls."""
    return [
        {"region": "Beograd", "year": 2020, "population": 1700000, "gdp": 25000},
        {"region": "Vojvodina", "year": 2020, "population": 2000000, "gdp": 18000},
        {"region": "Beograd", "year": 2021, "population": 1720000, "gdp": 26000},
        {"region": "Vojvodina", "year": 2021, "population": 2010000, "gdp": 18500},
        {"region": "Sumadija", "year": 2021, "population": 1900000, "gdp": 16000},
        {"region": "Beograd", "year": 2022, "population": 1740000, "gdp": 27500},
    ]


@pytest.fixture
def pie_data() -> list[dict[str, Any]]:
    """Data suitable for pie charts."""
    return [
        {"sector": "Technology", "share": 35},
        {"sector": "Agriculture", "share": 20},
        {"sector": "Services", "share": 30},
        {"sector": "Manufacturing", "share": 15},
    ]


# ===========================================================================
# 1. Server Discovery Tests
# ===========================================================================


class TestServerDiscovery:
    """Verify the MCP client can discover tools, resources, and prompts."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_all_registered(self, mcp_client):
        tools = await mcp_client.list_tools()
        names = {t.name for t in tools}
        assert len(names) >= 14, f"Expected >=14 tools, got {len(names)}: {names}"
        # Spot-check critical tools
        for name in ("search_datasets", "create_chart", "filter_data_tool", "health_check"):
            assert name in names, f"Tool '{name}' missing"

    @pytest.mark.asyncio
    async def test_list_tools_have_descriptions(self, mcp_client):
        tools = await mcp_client.list_tools()
        for tool in tools:
            assert tool.description, f"Tool '{tool.name}' has no description"

    @pytest.mark.asyncio
    async def test_list_resources(self, mcp_client):
        resources = await mcp_client.list_resources()
        uris = {str(r.uri) for r in resources}
        assert "serbian-data://server-info" in uris

    @pytest.mark.asyncio
    async def test_list_prompts(self, mcp_client):
        prompts = await mcp_client.list_prompts()
        names = {p.name for p in prompts}
        assert len(names) >= 3
        for name in ("search_prompt", "visualize_prompt", "data_journalism_prompt"):
            assert name in names, f"Prompt '{name}' missing"

    @pytest.mark.asyncio
    async def test_server_info_resource(self, mcp_client):
        result = await mcp_client.read_resource("serbian-data://server-info")
        assert isinstance(result, list) and len(result) > 0
        text = result[0].text if hasattr(result[0], "text") else str(result[0])
        data = json.loads(text)
        assert data["name"] == "serbian-data"
        assert "version" in data
        assert "supported_formats" in data
        assert "chart_types" in data

    @pytest.mark.asyncio
    async def test_guide_resource(self, mcp_client):
        result = await mcp_client.read_resource("serbian-data://guide")
        assert isinstance(result, list) and len(result) > 0
        text = result[0].text if hasattr(result[0], "text") else str(result[0])
        data = json.loads(text)
        assert "workflow" in data
        assert "tips" in data


# ===========================================================================
# 2. Search Tools Tests
# ===========================================================================


class TestSearchTools:
    """Verify search-related MCP tools work."""

    @pytest.mark.asyncio
    async def test_search_datasets_empty_query(self, mcp_client):
        result = await mcp_client.call_tool("search_datasets", {"query": "", "page_size": 3})
        data = _parse_result(result)
        assert "datasets" in data
        assert "total" in data
        assert isinstance(data["datasets"], list)

    @pytest.mark.asyncio
    async def test_search_datasets_with_query(self, mcp_client):
        result = await mcp_client.call_tool("search_datasets", {"query": "statistika", "page_size": 2})
        data = _parse_result(result)
        assert isinstance(data["datasets"], list)
        assert data["page_size"] == 2

    @pytest.mark.asyncio
    async def test_search_datasets_pagination(self, mcp_client):
        result = await mcp_client.call_tool("search_datasets", {"query": "", "page": 2, "page_size": 5})
        data = _parse_result(result)
        assert data["page"] == 2

    @pytest.mark.asyncio
    async def test_suggest_datasets(self, mcp_client):
        result = await mcp_client.call_tool("suggest_datasets", {"query": "pop", "size": 5})
        data = _parse_result(result)
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    @pytest.mark.asyncio
    async def test_list_organizations(self, mcp_client):
        result = await mcp_client.call_tool("list_organizations", {"page_size": 5})
        data = _parse_result(result)
        assert "organizations" in data
        assert isinstance(data["organizations"], list)


# ===========================================================================
# 3. Data Retrieval Tests
# ===========================================================================


class TestDataRetrieval:
    """Verify data retrieval MCP tools work."""

    @pytest.mark.asyncio
    async def test_get_dataset_not_found(self, mcp_client):
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="Dataset.*not found"):
            await mcp_client.call_tool("get_dataset", {"dataset_id": "nonexistent-id-12345"})


# ===========================================================================
# 4. Visualization Tests
# ===========================================================================


class TestVisualization:
    """Verify chart creation and export through MCP protocol."""

    @pytest.mark.asyncio
    async def test_create_line_chart(self, mcp_client, sample_data):
        result = await mcp_client.call_tool(
            "create_chart",
            {
                "data": sample_data,
                "chart_type": "line",
                "x_column": "year",
                "y_column": "population",
                "title": "Population by Year",
            },
        )
        data = _parse_result(result)
        assert data["type"] == "plotly"
        assert data["interactive"] is True
        assert "figure" in data
        assert data["chart_type"] == "line"

    @pytest.mark.asyncio
    async def test_create_bar_chart(self, mcp_client, sample_data):
        result = await mcp_client.call_tool(
            "create_chart",
            {
                "data": sample_data,
                "chart_type": "bar",
                "x_column": "region",
                "y_column": "gdp",
                "title": "GDP by Region",
            },
        )
        data = _parse_result(result)
        assert data["chart_type"] == "bar"
        assert "figure" in data

    @pytest.mark.asyncio
    async def test_create_pie_chart(self, mcp_client, pie_data):
        result = await mcp_client.call_tool(
            "create_chart",
            {
                "data": pie_data,
                "chart_type": "pie",
                "values_column": "share",
                "names_column": "sector",
                "title": "Sector Distribution",
            },
        )
        data = _parse_result(result)
        assert data["chart_type"] == "pie"

    @pytest.mark.asyncio
    async def test_create_scatter_plot(self, mcp_client, sample_data):
        result = await mcp_client.call_tool(
            "create_chart",
            {
                "data": sample_data,
                "chart_type": "scatter",
                "x_column": "population",
                "y_column": "gdp",
                "title": "Population vs GDP",
            },
        )
        data = _parse_result(result)
        assert data["chart_type"] == "scatter"

    @pytest.mark.asyncio
    async def test_create_histogram(self, mcp_client, sample_data):
        result = await mcp_client.call_tool(
            "create_chart",
            {
                "data": sample_data,
                "chart_type": "histogram",
                "x_column": "population",
                "title": "Population Distribution",
                "bins": 5,
            },
        )
        data = _parse_result(result)
        assert data["chart_type"] == "histogram"

    @pytest.mark.asyncio
    async def test_create_box_plot(self, mcp_client, sample_data):
        result = await mcp_client.call_tool(
            "create_chart",
            {
                "data": sample_data,
                "chart_type": "box",
                "x_column": "region",
                "y_column": "population",
                "title": "Population by Region",
            },
        )
        data = _parse_result(result)
        assert data["chart_type"] == "box"

    @pytest.mark.asyncio
    async def test_create_invalid_chart_type(self, mcp_client, sample_data):
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="Unsupported chart type"):
            await mcp_client.call_tool(
                "create_chart",
                {
                    "data": sample_data,
                    "chart_type": "radar",
                    "x_column": "year",
                    "y_column": "population",
                },
            )

    @pytest.mark.asyncio
    async def test_export_visualization_json(self, mcp_client, sample_data, tmp_path):
        # Create a chart first
        chart_result = await mcp_client.call_tool(
            "create_chart",
            {
                "data": sample_data,
                "chart_type": "line",
                "x_column": "year",
                "y_column": "population",
                "title": "Export Test",
            },
        )
        chart_data = _parse_result(chart_result)
        figure = chart_data["figure"]

        # Export as JSON
        export_result = await mcp_client.call_tool(
            "export_visualization",
            {
                "figure": figure,
                "format": "json",
                "filename": "test-export",
            },
        )
        data = _parse_result(export_result)
        assert data["format"] == "json"
        assert Path(data["filepath"]).exists()


# ===========================================================================
# 5. Data Transformation Tests
# ===========================================================================


class TestDataTransformations:
    """Verify data transformation tools through MCP protocol."""

    @pytest.mark.asyncio
    async def test_filter_data_tool(self, mcp_client, sample_data):
        result = await mcp_client.call_tool(
            "filter_data_tool",
            {
                "data": sample_data,
                "filters": {"region": "Beograd"},
            },
        )
        data = _parse_result(result)
        assert data["rows"] == 3
        for row in data["data"]:
            assert row["region"] == "Beograd"

    @pytest.mark.asyncio
    async def test_transform_data_sort(self, mcp_client, sample_data):
        result = await mcp_client.call_tool(
            "transform_data",
            {
                "data": sample_data,
                "operation": "sort",
                "column": "population",
                "ascending": True,
            },
        )
        data = _parse_result(result)
        values = [r["population"] for r in data["data"]]
        assert values == sorted(values)

    @pytest.mark.asyncio
    async def test_transform_data_sort_descending(self, mcp_client, sample_data):
        result = await mcp_client.call_tool(
            "transform_data",
            {
                "data": sample_data,
                "operation": "sort",
                "column": "gdp",
                "ascending": False,
            },
        )
        data = _parse_result(result)
        values = [r["gdp"] for r in data["data"]]
        assert values == sorted(values, reverse=True)

    @pytest.mark.asyncio
    async def test_transform_data_group(self, mcp_client, sample_data):
        result = await mcp_client.call_tool(
            "transform_data",
            {
                "data": sample_data,
                "operation": "group",
                "group_by": "region",
            },
        )
        data = _parse_result(result)
        assert "data" in data
        assert data["rows"] > 0

    @pytest.mark.asyncio
    async def test_transform_data_aggregate(self, mcp_client, sample_data):
        result = await mcp_client.call_tool(
            "transform_data",
            {
                "data": sample_data,
                "operation": "aggregate",
                "column": "population",
                "function": "sum",
            },
        )
        data = _parse_result(result)
        assert data["function"] == "sum"
        assert data["value"] > 0

    @pytest.mark.asyncio
    async def test_transform_data_select(self, mcp_client, sample_data):
        result = await mcp_client.call_tool(
            "transform_data",
            {
                "data": sample_data,
                "operation": "select",
                "columns": ["region", "population"],
            },
        )
        data = _parse_result(result)
        assert data["rows"] == len(sample_data)
        for row in data["data"]:
            assert "region" in row
            assert "population" in row
            assert "gdp" not in row

    @pytest.mark.asyncio
    async def test_transform_data_invalid_operation(self, mcp_client, sample_data):
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="Unknown operation"):
            await mcp_client.call_tool(
                "transform_data",
                {
                    "data": sample_data,
                    "operation": "explode",
                },
            )


# ===========================================================================
# 6. Utility Tools Tests
# ===========================================================================


class TestUtilityTools:
    """Verify health-check tools."""

    @pytest.mark.asyncio
    async def test_health_check(self, mcp_client):
        result = await mcp_client.call_tool("health_check", {})
        data = _parse_result(result)
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data


# ===========================================================================
# 7. Prompt Rendering Tests
# ===========================================================================


class TestPromptRendering:
    """Verify prompt templates render correctly."""

    @pytest.mark.asyncio
    async def test_search_prompt(self, mcp_client):
        result = await mcp_client.get_prompt("search_prompt", {"query": "education"})
        assert len(result.messages) >= 1
        text = result.messages[0].content.text
        assert "education" in text

    @pytest.mark.asyncio
    async def test_visualize_prompt(self, mcp_client):
        result = await mcp_client.get_prompt("visualize_prompt", {"description": "GDP trend"})
        assert len(result.messages) >= 1
        text = result.messages[0].content.text
        assert "GDP trend" in text

    @pytest.mark.asyncio
    async def test_data_journalism_prompt(self, mcp_client):
        result = await mcp_client.get_prompt("data_journalism_prompt", {"topic": "air quality"})
        assert len(result.messages) >= 1
        text = result.messages[0].content.text
        assert "air quality" in text


# ===========================================================================
# 8. End-to-end Pipeline Test
# ===========================================================================


class TestEndToEndPipeline:
    """Test a full MCP workflow: data → transform → visualize → export."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self, mcp_client, tmp_path):
        data = [
            {"city": "Beograd", "year": 2020, "population": 1700},
            {"city": "Novi Sad", "year": 2020, "population": 350},
            {"city": "Beograd", "year": 2021, "population": 1720},
            {"city": "Novi Sad", "year": 2021, "population": 355},
            {"city": "Nis", "year": 2021, "population": 250},
        ]

        # Step 1: Filter
        filter_result = await mcp_client.call_tool(
            "filter_data_tool",
            {
                "data": data,
                "filters": {"year": 2021},
            },
        )
        filtered = _parse_result(filter_result)
        assert filtered["rows"] == 3

        # Step 2: Sort
        sort_result = await mcp_client.call_tool(
            "transform_data",
            {
                "data": filtered["data"],
                "operation": "sort",
                "column": "population",
                "ascending": False,
            },
        )
        sorted_data = _parse_result(sort_result)
        assert sorted_data["data"][0]["population"] >= sorted_data["data"][-1]["population"]

        # Step 3: Visualize
        viz_result = await mcp_client.call_tool(
            "create_chart",
            {
                "data": sorted_data["data"],
                "chart_type": "bar",
                "x_column": "city",
                "y_column": "population",
                "title": "City Population 2021",
            },
        )
        viz_data = _parse_result(viz_result)
        assert viz_data["chart_type"] == "bar"

        # Step 4: Export
        export_result = await mcp_client.call_tool(
            "export_visualization",
            {
                "figure": viz_data["figure"],
                "format": "json",
                "filename": "pipeline-test",
            },
        )
        export_data = _parse_result(export_result)
        assert Path(export_data["filepath"]).exists()


# ===========================================================================
# Helpers
# ===========================================================================


def _parse_result(result: Any) -> dict[str, Any]:
    """Extract text content from an MCP CallToolResult."""
    for content in result.content:
        if hasattr(content, "text"):
            return json.loads(content.text)
    if hasattr(result, "content") and result.content:
        text = result.content[0].text if hasattr(result.content[0], "text") else str(result.content[0])
        return json.loads(text)
    raise ValueError(f"Could not parse MCP result: {result}")
