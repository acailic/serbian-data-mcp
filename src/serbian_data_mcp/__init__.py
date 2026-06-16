"""Serbian Data MCP Server

MCP server for accessing Serbian open data portal (data.gov.rs).
"""

__version__ = "0.2.0"

__all__ = ["mcp", "main", "__version__"]

from fastmcp import FastMCP

mcp = FastMCP("serbian-data")

# Register all MCP tools, resources, and prompts via modular tool packages
from . import tools  # noqa: F401, E402


def main():
    """Entry point for the MCP server."""
    mcp.run()
