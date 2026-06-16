#!/bin/bash
# Start the Serbian Data MCP Web Demo (local dev)
#
# Prerequisites:
#   1. Get a free Gemini API key: https://aistudio.google.com/apikey
#   2. export GEMINI_API_KEY=your-key
#
# Usage:
#   ./web_demo/start.sh
#   open http://localhost:5000

set -e
cd "$(dirname "$0")/.."

if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  GEMINI_API_KEY not set!"
    echo "   Get a free key at: https://aistudio.google.com/apikey"
    echo "   Then run: export GEMINI_API_KEY=your-key"
    echo ""
    echo "   Starting anyway (health check only, no AI responses)..."
else
    echo "✅ Gemini API key configured"
fi

echo "🚀 Starting Serbian Data MCP Web Demo"
echo "   URL: http://localhost:${PORT:-5000}"
echo ""

export PORT="${PORT:-5000}"
uv run python web_demo/app.py
