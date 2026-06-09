# Serbian Data MCP Server - Developer Guide

## 🚀 Quick Start

We've made it incredibly easy to get started with the Serbian Data MCP Server. Choose your preferred method:

### Method 1: Automated Setup (Recommended)

```bash
# Run the interactive setup wizard
./setup.sh
```

This one command will:
- ✅ Check your Python installation
- ✅ Create configuration file with defaults
- ✅ Install all dependencies
- ✅ Create necessary directories
- ✅ Test the installation
- ✅ Provide you with next steps

### Method 2: Manual Setup

```bash
# 1. Install dependencies
uv sync  # or: pip install -e .

# 2. Create configuration
cp config.example.json config.json

# 3. Test connection
./test_connection.sh
```

## 🔧 Configuration

### Interactive Configuration Wizard

```bash
python configure.py
```

The wizard will guide you through:
- API base URL
- Rate limiting settings
- Request timeout
- Directory preferences

### Manual Configuration

Edit `config.json`:

```json
{
  "api_base": "https://data.gov.rs",
  "rate_limit": 1.0,
  "timeout": 30,
  "cache_dir": ".cache",
  "export_dir": "exports"
}
```

#### Configuration Options

- **api_base**: Base URL for the Serbian data portal API
- **rate_limit**: Seconds between API requests (1.0 = 1 second)
- **timeout**: Request timeout in seconds (30 = 30 seconds)
- **cache_dir**: Directory for caching API responses
- **export_dir**: Directory for exported visualizations and data

## 🧪 Testing

### Test API Connection

```bash
./test_connection.sh
```

This will:
- Test connectivity to data.gov.rs
- Verify API response format
- Report total available datasets
- Provide quick troubleshooting tips

### Run Example Usage

```bash
python example_usage.py
```

This demonstrates:
- Searching for datasets
- Getting dataset details
- Listing organizations
- Getting search suggestions
- Creating visualizations

## 📚 Usage Examples

### Basic API Usage

```python
import asyncio
from serbian_data_mcp.api.client import UDataClient

async def main():
    async with UDataClient() as client:
        # Search for datasets
        result = await client.search_datasets(query="population")

        for dataset in result.datasets:
            print(f"{dataset.title} - {dataset.id}")

asyncio.run(main())
```

### Download Data

```python
async with UDataClient() as client:
    # Get dataset details
    dataset = await client.get_dataset("dataset-id")

    # Download and parse resource data
    for resource in dataset.resources:
        data = await client.get_resource_data(resource.id)
        print(data)
```

### Create Visualizations

```python
from serbian_data_mcp.viz.charts import create_chart
from serbian_data_mcp.viz.exporters import export_chart

# Create a line chart
chart = create_chart(
    data={"year": [2018, 2019, 2020], "population": [7000000, 7050000, 6870000]},
    chart_type="line",
    title="Population Trends",
    x_column="year",
    y_column="population"
)

# Export to HTML
export_chart(chart, "population_chart.html", format="html")
```

## ❌ Error Handling

The server provides helpful error messages for common issues:

### Connection Errors

```
❌ Cannot connect to https://data.gov.rs
   Please check your internet connection
```

### Dataset Not Found

```
❌ Dataset not found: invalid-id
   Check the dataset ID or search for available datasets
```

### Configuration Errors

```
❌ Configuration error: api_base
   Invalid URL format
   💡 Suggestion: URL must start with http:// or https://
```

### Rate Limiting

```
❌ Rate limit exceeded (1.0s between requests)
   Please wait 0.5 seconds before trying again
```

## 🛠️ Troubleshooting

### Installation Issues

**Problem**: `ModuleNotFoundError: No module named 'serbian_data_mcp'`

**Solution**: 
```bash
# Make sure you're in the project directory
cd serbian-data-mcp

# Reinstall dependencies
uv sync  # or: pip install -e .
```

### Connection Problems

**Problem**: Cannot connect to data.gov.rs

**Solutions**:
1. Check internet connectivity
2. Verify `api_base` in config.json
3. Try the test connection script: `./test_connection.sh`
4. Check if the service is temporarily down

### Configuration Validation

**Problem**: Invalid configuration settings

**Solution**:
```bash
# Run the configuration wizard
python configure.py

# Or manually validate
python -c "from serbian_data_mcp.config_validation import load_and_validate_config; print(load_and_validate_config(Path('config.json')))"
```

### Timeout Errors

**Problem**: Requests timing out

**Solutions**:
1. Increase `timeout` in config.json
2. Check your internet speed
3. Try during off-peak hours

## 📁 Project Structure

```
serbian-data-mcp/
├── src/serbian_data_mcp/
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Entry point
│   ├── config.py            # Configuration management
│   ├── config_validation.py # Pydantic validation models
│   ├── exceptions.py        # Custom exception classes
│   ├── api/                 # API client and models
│   │   ├── client.py        # UData API client
│   │   └── models.py        # Data models
│   ├── viz/                 # Visualization tools
│   │   ├── charts.py        # Chart creation
│   │   └── exporters.py     # Export functionality
│   └── data/                # Data processing
│       ├── parsers.py       # File format parsers
│       └── transformers.py   # Data transformers
├── tests/                   # Test files
├── setup.sh                 # Automated setup script
├── configure.py             # Interactive configuration wizard
├── test_connection.sh       # Connection testing
├── example_usage.py         # Usage examples
└── config.json             # Your configuration (create this)
```

## 🎯 Next Steps

1. **Test the connection**: `./test_connection.sh`
2. **Run examples**: `python example_usage.py`
3. **Explore the API**: Browse available datasets
4. **Create visualizations**: Export charts from data
5. **Integrate with Claude**: Add to Claude Desktop config

## 🤝 Contributing

We welcome contributions! Areas of interest:
- Additional data format parsers
- More visualization types
- Performance optimizations
- Documentation improvements
- Bug fixes and enhancements

## 📄 License

MIT License - see LICENSE file for details

## 🇷🇸 About

This MCP server provides access to the Serbian government's open data portal (data.gov.rs), making it easy to query, download, and visualize Serbian public data.

Built with ❤️ for the Serbian open data community.
