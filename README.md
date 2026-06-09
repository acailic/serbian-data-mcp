# Serbian Data MCP Server

MCP server for accessing Serbian open data portal (data.gov.rs) with built-in visualization capabilities.

## Features

- 🔍 Search 3,400+ datasets from Serbian government
- 📊 Create charts from open data (line, bar, pie, scatter)
- 📥 Download data in JSON, CSV, XML, XLSX formats
- 🎨 Export visualizations as HTML/PNG/JSON
- 🇷🇸 Full Serbian language support (UTF-8)

## Installation

```bash
# Clone repository
git clone https://github.com/acailic/serbian-data-mcp
cd serbian-data-mcp

# Install with uv
uv sync

# Or with pip
pip install -e .
```

## Configuration

Copy `config.example.json` to `config.json`:

```bash
cp config.example.json config.json
```

## Usage

### Run MCP Server

```bash
# Direct
python -m serbian_data_mcp

# Via script
serbian-data-mcp
```

### Claude Desktop Configuration

Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "serbian-data": {
      "command": "uv",
      "args": ["--directory", "/path/to/serbian-data-mcp", "run", "python", "-m", "serbian_data_mcp"]
    }
  }
}
```

### Available Tools

- `search_datasets` - Search datasets with filters
- `get_dataset` - Get complete dataset details
- `get_resource_data` - Download and parse resource data
- `create_visualization` - Create charts from data
- `list_organizations` - Browse data providers
- `suggest_datasets` - Autocomplete for search

## Examples

```python
# Search datasets
datasets = await mcp.call_tool("search_datasets", {
    "query": "population",
    "format": "json",
    "page_size": 10
})

# Create visualization
chart = await mcp.call_tool("create_visualization", {
    "data": data,
    "chart_type": "line",
    "title": "Population Trends",
    "x_column": "year",
    "y_column": "population",
    "export_format": "html"
})
```

## License

MIT License - see LICENSE file
