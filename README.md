# Serbian Data MCP Server

MCP server for accessing Serbian open data portal (data.gov.rs) with built-in visualization capabilities.

## Features

- 🔍 Search 3,400+ datasets from Serbian government
- 📊 Create 6 types of charts (line, bar, pie, scatter, histogram, box)
- 📥 Download data in JSON, CSV, XML, XLSX formats
- 🎨 Export visualizations as HTML/PNG/JSON
- 🇷🇸 Full Serbian language support (UTF-8)
- 🚀 Built-in rate limiting and caching
- 📖 Comprehensive documentation with 24+ examples
- 🛠️ Data transformation tools (filter, group, aggregate, sort, select)

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Run the interactive setup wizard
./setup.sh
```

This will automatically:
- ✅ Check your Python installation
- ✅ Create configuration with sensible defaults
- ✅ Install all dependencies
- ✅ Set up necessary directories
- ✅ Test the installation

### Option 2: Manual Setup

```bash
# Clone repository
git clone https://github.com/acailic/serbian-data-mcp
cd serbian-data-mcp

# Install with uv
uv sync

# Or with pip
pip install -e .

# Create configuration
cp config.example.json config.json
```

## 📖 Configuration

### Interactive Configuration Wizard

```bash
python configure.py
```

The wizard guides you through:
- API settings (URL, rate limiting, timeout)
- Directory preferences (cache, exports)
- Validation with helpful error messages
- Automatic directory creation

### Manual Configuration

Edit `config.json` (created from `config.example.json`):

```json
{
  "api_base": "https://data.gov.rs",
  "rate_limit": 1.0,
  "timeout": 30,
  "cache_dir": ".cache",
  "export_dir": "exports"
}
```

## 🧪 Testing

### Test API Connection

```bash
./test_connection.sh
```

This validates:
- Connectivity to data.gov.rs
- API response format
- Available dataset count

### Run Examples

```bash
python example_usage.py
```

Demonstrates:
- Dataset search
- Data retrieval
- Visualization creation
- Export functionality

## 📚 Documentation

**📖 Complete Documentation Available in [docs/](docs/)**

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get started in 5 minutes
- **[Usage Examples](docs/EXAMPLES.md)** - 24+ real-world examples and use cases
- **[API Reference](docs/API_REFERENCE.md)** - Complete tool documentation with parameters
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Contributing Guide](docs/CONTRIBUTING.md)** - Developer contribution guidelines
- **[docs/README.md](docs/README.md)** - Documentation navigation and index

**Additional Resources:**
- **[DEV_GUIDE.md](DEV_GUIDE.md)** - Comprehensive developer guide
- **Examples** - Check `example_usage.py` for usage patterns
- **Error Handling** - Helpful error messages for common issues

## 🚀 Usage

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

## Development

### Setup Development Environment

```bash
# Install dependencies
make install

# Or manually
uv sync --dev
```

### Running Tests

```bash
# Run all tests with coverage
make test

# Quick tests (no coverage)
make test-quick

# Only unit tests
make test-unit

# Only integration tests
make test-integration
```

### Code Quality Checks

```bash
# Run all quality checks (lint, format, type-check, security)
make check

# Quick checks (lint + format only)
make check-quick

# Individual checks
make lint      # Ruff linting
make format    # Format code with ruff
make type-check # Type checking with pyright
make security  # Security checks with bandit
```

### Available Make Commands

```bash
make help      # Show all available commands
make install   # Install dependencies
make test      # Run tests with coverage
make check     # Run all quality checks
make clean     # Clean up generated files
make dev       # Setup development environment
make all       # Install, test, and check
```

## Testing Infrastructure

The project includes comprehensive testing infrastructure:

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Coverage Reports**: HTML and terminal coverage output
- **Type Checking**: 100% type coverage with pyright
- **Code Quality**: Automated linting and formatting with ruff
- **Security Checks**: Bandit security scanning

### CI/CD Pipeline

GitHub Actions workflows automatically run:

1. **Test Suite** (`.github/workflows/test.yml`)
   - Tests on Python 3.11, 3.12, 3.13
   - Coverage reporting to Codecov

2. **Code Quality** (`.github/workflows/code-quality.yml`)
   - Type checking with pyright
   - Linting with ruff
   - Formatting checks
   - Security scanning with bandit

## Project Structure

```
serbian-data-mcp/
├── src/serbian_data_mcp/
│   ├── api/              # API client and models
│   ├── data/             # Data parsing and transformation
│   ├── viz/              # Visualization tools
│   └── config.py         # Configuration management
├── tests/                # Comprehensive test suite
├── .github/workflows/    # CI/CD configuration
├── pyproject.toml        # Project configuration
└── Makefile              # Development commands
```

## Quality Standards

- **Type Coverage**: 100% (strict pyright checking)
- **Test Coverage**: Comprehensive with coverage reporting
- **Code Style**: Automated formatting with ruff (120 char line length)
- **Security**: Automated security scanning
- **CI/CD**: Automated testing on multiple Python versions

## License

MIT License - see LICENSE file
