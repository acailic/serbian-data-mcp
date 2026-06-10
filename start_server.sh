#!/bin/bash
# Start Serbian Data MCP Server in SSE mode

echo "🚀 Starting Serbian Data MCP Server (SSE mode)"
echo "=============================================="
echo ""

# Set environment variables for SSE mode
export FASTMCP_HOST="localhost"
export FASTMCP_PORT="8001"
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

echo "Server will start on: http://localhost:8001"
echo "Press Ctrl+C to stop"
echo ""

# Start the server with SSE transport using uv run
uv run python -c "
import os
os.environ['FASTMCP_HOST'] = 'localhost'
os.environ['FASTMCP_PORT'] = '8001'

from serbian_data_mcp import mcp
mcp.run(transport='sse')
"
