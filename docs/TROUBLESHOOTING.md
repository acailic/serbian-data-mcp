# Troubleshooting Guide - Serbian Data MCP

Common issues and solutions for Serbian Data MCP server.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Configuration Issues](#configuration-issues)
3. [MCP Connection Issues](#mcp-connection-issues)
4. [Data Access Issues](#data-access-issues)
5. [Visualization Issues](#visualization-issues)
6. [Performance Issues](#performance-issues)
7. [Error Messages](#error-messages)

## Installation Issues

### Issue: Python version too old

**Error:**
```
ERROR: This package requires Python 3.11 or higher
```

**Solution:**
```bash
# Check your Python version
python --version

# Install Python 3.11+ from python.org
# Or use pyenv:
pyenv install 3.11
pyenv global 3.11
```

### Issue: uv command not found

**Error:**
```
bash: uv: command not found
```

**Solution:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use pip instead
pip install -e .
```

### Issue: Dependencies installation fails

**Error:**
```
ERROR: Could not find a version that satisfies the requirement fastmcp
```

**Solution:**
```bash
# Update pip
pip install --upgrade pip

# Install dependencies manually
pip install fastmcp plotly pandas httpx requests pydantic openpyxl

# Or use uv (recommended)
uv pip install fastmcp plotly pandas httpx requests pydantic openpyxl
```

### Issue: Permission denied during installation

**Error:**
```
ERROR: Permission denied
```

**Solution:**
```bash
# Use user installation
pip install --user -e .

# Or use virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
pip install -e .
```

## Configuration Issues

### Issue: config.json not found

**Error:**
```
Config file not found: config.json
```

**Solution:**
```bash
# Copy example config
cp config.example.json config.json

# Or create manually
cat > config.json << EOF
{
  "api_base": "https://data.gov.rs",
  "rate_limit": 1.0,
  "timeout": 30,
  "cache_dir": ".cache",
  "export_dir": "exports"
}
EOF
```

### Issue: Invalid JSON in config.json

**Error:**
```
JSON decode error in config.json
```

**Solution:**
```bash
# Validate your JSON
cat config.json | python -m json.tool

# Fix syntax errors (missing commas, trailing commas, etc.)
# Ensure proper JSON format
```

### Issue: Cache directory permission denied

**Error:**
```
Permission denied: .cache
```

**Solution:**
```bash
# Create cache directory with proper permissions
mkdir -p .cache
chmod 755 .cache

# Or change cache location in config.json
# "cache_dir": "/tmp/serbian-data-cache"
```

### Issue: Export directory doesn't exist

**Error:**
```
Export directory not found: exports
```

**Solution:**
```bash
# Create export directory
mkdir -p exports

# The server will create it automatically,
# but you can pre-create it if needed
```

## MCP Connection Issues

### Issue: Claude Desktop can't connect to MCP

**Error:**
```
Failed to connect to MCP server: serbian-data
```

**Solutions:**

1. **Check path in config:**
```json
{
  "mcpServers": {
    "serbian-data": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/serbian-data-mcp",  // Use absolute path
        "run",
        "python",
        "-m",
        "serbian_data_mcp"
      ]
    }
  }
}
```

2. **Try alternative config:**
```json
{
  "mcpServers": {
    "serbian-data": {
      "command": "python",
      "args": ["-m", "serbian_data_mcp"],
      "cwd": "/ABSOLUTE/PATH/TO/serbian-data-mcp"
    }
  }
}
```

3. **Restart Claude Desktop:**
   - Completely close Claude Desktop
   - Wait 10 seconds
   - Restart Claude Desktop

### Issue: MCP server crashes immediately

**Error:**
```
MCP server exited with code 1
```

**Solution:**
```bash
# Test server manually
cd /path/to/serbian-data-mcp
python -m serbian_data_mcp

# Check for errors in output
# Common issues:
# - Missing dependencies
# - Python version too old
# - Import errors
```

### Issue: Tools not showing in Claude

**Problem:** MCP connects but tools don't appear

**Solution:**
```bash
# Verify server is running
python -m serbian_data_mcp

# Check Claude Desktop logs
# macOS: ~/Library/Logs/Claude/
# Windows: %APPDATA%\Claude\logs\
# Linux: ~/.config/Claude/logs/

# Restart Claude Desktop completely
```

## Data Access Issues

### Issue: Dataset not found

**Error:**
```
Dataset not found: xyz-123
```

**Solution:**
```python
# Search for correct dataset ID
search_datasets("dataset name")

# Get exact ID from search results
# Use the ID returned by search, not title
```

### Issue: Resource download fails

**Error:**
```
Failed to download resource: abc-456
```

**Solutions:**

1. **Check resource exists:**
```python
# Get dataset details first
dataset = get_dataset("dataset-id")
# Verify resource ID in dataset.resources
```

2. **Check network connection:**
```bash
# Test API access
curl https://data.gov.rs/api/1/datasets/

# Check for proxy/firewall issues
```

3. **Resource might be temporarily unavailable:**
```python
# Try again later
# Some resources are temporarily offline
```

### Issue: Format not supported

**Error:**
```
Unsupported format: xyz
```

**Solution:**
```python
# Check supported formats
# Supported: json, csv, xlsx, xls, xml

# Use format filtering in search
search_datasets("population", format="csv")

# Or try different resource
dataset = get_dataset("dataset-id")
# Find resource with supported format
```

### Issue: CSV parsing fails

**Error:**
```
CSV parsing error: invalid encoding
```

**Solution:**
```python
# The parser tries multiple encodings automatically
# UTF-8 with BOM
# Latin1 (ISO-8859-1)
# UTF-8 with error replacement

# If still failing, the file might be corrupted
# Try downloading directly from portal
```

### Issue: Rate limiting errors

**Error:**
```
Rate limit exceeded: too many requests
```

**Solution:**
```json
// Increase rate_limit in config.json
{
  "rate_limit": 2.0  // 2 seconds between requests
}
```

## Visualization Issues

### Issue: Chart creation fails

**Error:**
```
Visualization error: invalid data format
```

**Solutions:**

1. **Check data structure:**
```python
# Data must be array of objects or have proper structure
# Verify column names exist
data = get_resource_data("resource-id")
# Check actual column names in data
```

2. **Verify required parameters:**
```python
# Line/Bar/Scatter charts need x_column and y_column
# Pie charts need values_column and names_column
# Histogram needs column parameter

create_visualization(
  data=data,
  chart_type="line",
  x_column="year",        // Required
  y_column="population"   // Required
)
```

3. **Check data types:**
```python
# Numeric columns for Y-axis
# Valid column names
# Non-empty data

# Filter invalid data first
filter_data(data, {"population": {">": 0}})
```

### Issue: PNG export fails

**Error:**
```
PNG export failed: kaleido not installed
```

**Solution:**
```bash
# Install kaleido for image export
pip install kaleido

# Or use HTML export instead
export_visualization(figure, format="html", filename="chart.html")
```

### Issue: Chart looks wrong

**Problem:** Chart creates but doesn't look right

**Solutions:**

1. **Check data types:**
```python
# Ensure numeric columns are actually numeric
# String columns for categories
# Date columns for time series

# Transform data if needed
```

2. **Try different chart type:**
```python
# Some data works better with different charts
# Time series → line chart
# Categories → bar/pie chart
# Distribution → histogram/box plot
```

3. **Adjust chart parameters:**
```python
# Add title, adjust orientation
# Use color grouping for clarity
create_visualization(
  data=data,
  chart_type="bar",
  x_column="category",
  y_column="value",
  title="Clear Chart Title",
  orientation="h"  // Try horizontal
)
```

## Performance Issues

### Issue: Slow search results

**Problem:** Searches take too long

**Solutions:**

1. **Use specific queries:**
```python
# Narrow searches with filters
search_datasets(
  query="population",
  format="csv",        // Filter by format
  organization="org-id" // Filter by organization
)
```

2. **Reduce page size:**
```python
// Get fewer results initially
search_datasets("query", page_size=10)
```

3. **Use autocomplete:**
```python
// Get suggestions faster
suggest_datasets("pop")
```

### Issue: Large datasets slow to process

**Problem:** Big files take long to download/parse

**Solutions:**

1. **Filter data early:**
```python
// Filter during download if possible
// Or filter immediately after
filter_data(data, {"year": 2023})
```

2. **Select specific columns:**
```python
// Reduce data size
select_columns(data, ["year", "population"])
```

3. **Use appropriate format:**
```python
// JSON is usually faster to parse than CSV
// Choose JSON when available
search_datasets("query", format="json")
```

### Issue: Memory usage high

**Problem:** Server uses too much memory

**Solutions:**

1. **Process data in chunks:**
```python
// Work with smaller subsets
filter_data(data, {"region": "belgrade"})

// Process one region at a time
```

2. **Clear cache:**
```bash
// Remove cached files
rm -rf .cache/*

// Or change cache location
// "cache_dir": "/tmp/cache"
```

3. **Restart server:**
```bash
// Restart Claude Desktop
// Clears all cached data
```

## Error Messages

### Common error codes and meanings

**DATASET_NOT_FOUND**
- Dataset ID doesn't exist or was deleted
- Search for correct ID

**RESOURCE_NOT_FOUND**
- Resource ID doesn't exist
- Check dataset details for valid resources

**INVALID_FORMAT**
- File format not supported
- Try JSON, CSV, XLSX, or XML

**RATE_LIMIT_EXCEEDED**
- Too many requests to API
- Increase rate_limit in config

**API_ERROR**
- API request failed
- Check network connection
- Try again later

**PARSE_ERROR**
- Failed to parse data
- File might be corrupted
- Try different format

**VISUALIZATION_ERROR**
- Chart creation failed
- Check data structure
- Verify required parameters

## Getting Help

### Checklist for Issues

Before seeking help, check:

1. ✅ Python 3.11+ installed
2. ✅ All dependencies installed
3. ✅ config.json exists and is valid
4. ✅ MCP server connects in Claude Desktop
5. ✅ Network connection working
6. ✅ API accessible (https://data.gov.rs)
7. ✅ Sufficient disk space for cache/exports
8. ✅ Proper file permissions

### Debug Mode

Enable debug output:

```bash
# Run server with verbose output
python -m serbian_data_mcp --verbose

# Or check Claude Desktop logs
# Look for MCP server output
```

### Report Issues

If problems persist:

1. Document the error
2. Include steps to reproduce
3. Share relevant config (remove sensitive data)
4. Include Python version and OS
5. Check [Examples](EXAMPLES.md) for similar use cases

### Community Resources

- GitHub Issues: Report bugs and request features
- Documentation: Check [API Reference](API_REFERENCE.md)
- Examples: See [Examples](EXAMPLES.md) for patterns

## Proactive Maintenance

### Regular Tasks

1. **Clean cache:**
```bash
# Remove old cached files
rm -rf .cache/*
```

2. **Clean exports:**
```bash
# Remove old exported files
rm -rf exports/*
```

3. **Update dependencies:**
```bash
# Keep packages current
uv sync --upgrade
# or
pip install --upgrade -e .
```

4. **Check for updates:**
```bash
# Pull latest changes
git pull origin main
```

## Next Steps

- Return to [Quick Start](QUICKSTART.md) for setup
- Check [Examples](EXAMPLES.md) for usage patterns
- See [API Reference](API_REFERENCE.md) for tool details
