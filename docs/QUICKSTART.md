# Quick Start Guide - Serbian Data MCP

Get up and running with Serbian Data MCP in 5 minutes.

## Prerequisites

- Python 3.11 or higher
- Claude Desktop (for MCP integration)
- Internet connection

## Installation (2 minutes)

### Option 1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/acailic/serbian-data-mcp
cd serbian-data-mcp

# Install dependencies (recommended: uv)
uv sync

# Or with pip
pip install -e .
```

### Option 2: Direct Installation

```bash
pip install serbian-data-mcp
```

### Option 3: Install via Smithery

[Smithery](https://smithery.ai) is a registry and CLI that makes it easy to discover and install MCP servers.

```bash
# Install the Smithery CLI (requires Node.js 20+)
npm install -g smithery@latest

# Add to Claude Desktop — automatically configures everything
smithery mcp add acailic/serbian-data-mcp --client claude

# Add to Cursor
smithery mcp add acailic/serbian-data-mcp --client cursor

# Or connect as a remote connection
smithery mcp add acailic/serbian-data-mcp --id serbian-data
```

Then restart your AI client. No manual config editing needed — Smithery handles it automatically.

## Configuration (1 minute)

Create your configuration file:

```bash
# Copy example config
cp config.example.json config.json

# Edit if needed (defaults work for most users)
nano config.json
```

Default configuration:
```json
{
  "api_base": "https://data.gov.rs",
  "rate_limit": 1.0,
  "timeout": 30,
  "cache_dir": ".cache",
  "export_dir": "exports"
}
```

## Claude Desktop Setup (2 minutes)

### 1. Locate Claude Desktop Config

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### 2. Add Serbian Data MCP

**If you installed via Smithery (Option 3 above):** Skip this step — Smithery already configured Claude Desktop for you.

**Otherwise**, add this to your `mcpServers` section:

```json
{
  "mcpServers": {
    "serbian-data": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/serbian-data-mcp",
        "run",
        "python",
        "-m",
        "serbian_data_mcp"
      ]
    }
  }
}
```

**Important:** Replace `/path/to/serbian-data-mcp` with your actual path.

**Alternative (without uv):**
```json
{
  "mcpServers": {
    "serbian-data": {
      "command": "python",
      "args": ["-m", "serbian_data_mcp"],
      "cwd": "/path/to/serbian-data-mcp"
    }
  }
}
```

### 3. Restart Claude Desktop

Completely close and restart Claude Desktop for changes to take effect.

## Verify Installation (30 seconds)

In Claude, try these prompts:

1. **Test basic search:**
   ```
   Search for datasets about population on the Serbian data portal
   ```

2. **Test visualization:**
   ```
   Find datasets about population and create a line chart showing trends
   ```

3. **Test data download:**
   ```
   Download the first CSV file from the population dataset
   ```

If these work, you're ready to go! 🎉

## Next Steps

- Explore [Examples](EXAMPLES.md) for common use cases
- Check [API Reference](API_REFERENCE.md) for all available tools
- Read [Troubleshooting](TROUBLESHOOTING.md) if you encounter issues

## Common First Tasks

### Find Datasets

```
Search for datasets about economy
```

### Get Dataset Details

```
Get details for dataset ID 12345
```

### Create Visualizations

```
Find data about unemployment and create a bar chart
```

### Download Data

```
Download the Excel file from dataset budget-2024
```

## Quick Tips

1. **Start broad** - Use general search terms first
2. **Filter by format** - Specify JSON, CSV, XLSX, or XML
3. **Use organizations** - Filter by specific government agencies
4. **Export charts** - Save visualizations as HTML for sharing
5. **Rate limiting** - Built-in delays prevent API overload

## Getting Help

If you run into issues:

1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review [Examples](EXAMPLES.md) for similar use cases
3. Consult [API Reference](API_REFERENCE.md) for parameter details

**You're now ready to explore 3,400+ Serbian government datasets!** 🇷🇸
