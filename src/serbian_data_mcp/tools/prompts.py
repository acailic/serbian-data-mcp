"""MCP prompts for common workflows."""

from .. import mcp


@mcp.prompt()
def search_prompt(query: str = "population") -> str:
    """Prompt for searching datasets."""
    return (
        f"Search data.gov.rs for '{query}'.\n"
        f"1. search_datasets(query='{query}') → find datasets\n"
        f"2. get_dataset(id, detail_level='metadata') → full details\n"
        f"3. Report top 5 with descriptions, formats, and available resources"
    )


@mcp.prompt()
def visualize_prompt(description: str = "Create a chart") -> str:
    """Prompt for visualization workflow."""
    return (
        f"{description}\n"
        f"Workflow: search_datasets → get_resource_data → data_profile → "
        f"transform_data (if needed) → create_chart → export_visualization"
    )


@mcp.prompt()
def data_journalism_prompt(topic: str = "Serbian economy") -> str:
    """Prompt for data journalism exploration."""
    return (
        f"Data journalism: {topic}\n"
        f"1. search_datasets(query) → find data\n"
        f"2. get_resource_data(resource_id) → download\n"
        f"3. data_profile(data) → understand structure\n"
        f"4. extract_data_insights(data) → find surprising findings\n"
        f"5. create_chart(data, ...) → visualize\n"
        f"6. build_infographic(data, ...) → create shareable story"
    )
