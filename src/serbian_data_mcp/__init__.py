"""Serbian Data MCP Server

MCP server for accessing Serbian open data portal (data.gov.rs).
"""

__version__ = "0.1.0"

__all__ = ["mcp", "main", "__version__"]

from fastmcp import FastMCP

mcp = FastMCP("serbian-data")

# Import tools, resources, and prompts to register them on the MCP server
from . import tools  # noqa: F401, E402


def main():
    """Entry point for the MCP server."""
    mcp.run()
