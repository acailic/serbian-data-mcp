#!/bin/bash
# Serbian Data MCP Server Setup Script
# This script helps you get the server running quickly

set -e  # Exit on error

echo "🇷🇸 Serbian Data MCP Server - Setup"
echo "=================================="
echo ""

# Check Python version
echo "📋 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "   Please install Python 3.11 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "   ✅ Found Python $PYTHON_VERSION"

# Check if uv is available
if command -v uv &> /dev/null; then
    echo "   ✅ uv package manager found"
    INSTALL_METHOD="uv"
else
    echo "   ℹ️  uv not found, will use pip"
    INSTALL_METHOD="pip"
fi

# Create configuration if it doesn't exist
echo ""
echo "📝 Setting up configuration..."
if [ ! -f "config.json" ]; then
    if [ -f "config.example.json" ]; then
        cp config.example.json config.json
        echo "   ✅ Created config.json from example"
    else
        echo "   ⚠️  config.example.json not found, using defaults"
        cat > config.json << EOF
{
  "api_base": "https://data.gov.rs",
  "rate_limit": 1.0,
  "timeout": 30,
  "cache_dir": ".cache",
  "export_dir": "exports"
}
EOF
        echo "   ✅ Created config.json with defaults"
    fi
else
    echo "   ℹ️  config.json already exists"
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
if [ "$INSTALL_METHOD" = "uv" ]; then
    uv sync
    echo "   ✅ Dependencies installed with uv"
else
    pip install -e .
    echo "   ✅ Dependencies installed with pip"
fi

# Create necessary directories
echo ""
echo "📁 Creating necessary directories..."
mkdir -p .cache exports
echo "   ✅ Created .cache and exports directories"

# Test installation
echo ""
echo "🧪 Testing installation..."
if python3 -c "import serbian_data_mcp" 2>/dev/null; then
    echo "   ✅ serbian_data_mcp module imports successfully"
else
    echo "   ❌ Error: Failed to import serbian_data_mcp"
    exit 1
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Test the connection: ./test_connection.sh"
echo "  2. Run the server: python -m serbian_data_mcp"
echo "  3. Try examples: python example_usage.py"
echo ""
echo "For Claude Desktop integration, add to your config:"
echo '  {"mcpServers": {"serbian-data": {"command": "uv", "args": ["--directory", "'$(pwd)'", "run", "python", "-m", "serbian_data_mcp"]}}}'
