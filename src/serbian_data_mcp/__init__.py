"""Serbian Data MCP Server

MCP server for accessing Serbian open data portal (data.gov.rs).
"""

__version__ = "0.1.0"

from fastmcp import FastMCP

mcp = FastMCP("serbian-data")

from .api import client, models
from .viz import charts, exporters
from .data import parsers, transformers


def main():
    """Entry point for the MCP server."""
    mcp.run()
