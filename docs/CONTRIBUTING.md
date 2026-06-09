# Contributing Guide - Serbian Data MCP

How to contribute to Serbian Data MCP server development.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Code Structure](#code-structure)
4. [Testing](#testing)
5. [Documentation](#documentation)
6. [Pull Requests](#pull-requests)
7. [Coding Standards](#coding-standards)

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- uv (recommended) or pip
- Familiarity with MCP protocol
- Understanding of Serbian data portal structure

### Development Environment

```bash
# Clone repository
git clone https://github.com/acailic/serbian-data-mcp
cd serbian-data-mcp

# Install in development mode
uv sync --dev

# Or with pip
pip install -e ".[dev]"
```

### Verify Setup

```bash
# Run tests
pytest tests/

# Run server
python -m serbian_data_mcp

# Check health
curl https://data.gov.rs/api/1/datasets/
```

## Development Setup

### Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Linux/Mac)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
uv sync --dev
```

### Configuration

```bash
# Copy example config
cp config.example.json config.json

# Edit for development
nano config.json
```

Development config suggestions:
```json
{
  "api_base": "https://data.gov.rs",
  "rate_limit": 0.5,
  "timeout": 60,
  "cache_dir": ".cache",
  "export_dir": "test_exports"
}
```

## Code Structure

### Directory Layout

```
serbian-data-mcp/
├── src/
│   └── serbian_data_mcp/
│       ├── __init__.py          # Main MCP server
│       ├── __main__.py          # Entry point
│       ├── config.py            # Configuration management
│       ├── api/                 # API client layer
│       │   ├── __init__.py
│       │   ├── client.py        # UData API client
│       │   └── models.py        # Data models
│       ├── data/                # Data processing
│       │   ├── __init__.py
│       │   ├── parsers.py       # Format parsers
│       │   └── transformers.py  # Data transformations
│       └── viz/                 # Visualization
│           ├── __init__.py
│           ├── charts.py        # Chart builders
│           └── exporters.py     # Export utilities
├── tests/                       # Test suite
│   ├── test_api.py
│   ├── test_data.py
│   └── test_viz.py
├── docs/                        # Documentation
│   ├── QUICKSTART.md
│   ├── EXAMPLES.md
│   ├── API_REFERENCE.md
│   ├── TROUBLESHOOTING.md
│   └── CONTRIBUTING.md
├── config.example.json
├── pyproject.toml
├── README.md
└── LICENSE
```

### Core Components

**API Layer** (`api/`):
- `client.py`: HTTP requests to data.gov.rs
- `models.py`: Data model definitions

**Data Layer** (`data/`):
- `parsers.py`: Parse JSON, CSV, Excel, XML
- `transformers.py`: Filter, group, aggregate data

**Visualization Layer** (`viz/`):
- `charts.py`: Plotly chart builders
- `exporters.py`: Export to HTML, PNG, JSON

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=serbian_data_mcp tests/

# Verbose output
pytest -v tests/
```

### Test Structure

```python
# Example test structure
import pytest
from serbian_data_mcp.api.client import UDataClient

@pytest.mark.asyncio
async def test_search_datasets():
    """Test dataset search functionality."""
    client = UDataClient()
    result = await client.search_datasets("population")
    assert len(result.datasets) > 0
    assert result.total > 0
```

### Writing Tests

1. **Unit Tests**: Test individual functions
2. **Integration Tests**: Test API interactions
3. **Async Tests**: Use `@pytest.mark.asyncio`
4. **Mocking**: Mock HTTP requests for speed

### Test Guidelines

- Test both success and failure cases
- Use descriptive test names
- Mock external API calls
- Keep tests fast and isolated
- Test edge cases and error handling

## Documentation

### Updating Documentation

1. **Quick Start** (`QUICKSTART.md`): Installation and basic setup
2. **Examples** (`EXAMPLES.md`): Usage examples and use cases
3. **API Reference** (`API_REFERENCE.md`): Complete tool reference
4. **Troubleshooting** (`TROUBLESHOOTING.md`): Common issues and solutions
5. **Contributing** (`CONTRIBUTING.md`): This guide

### Documentation Style

- Use clear, concise language
- Include code examples
- Provide context for features
- Keep examples up to date
- Use consistent formatting

### Adding Examples

When adding new features:

1. Add example to `EXAMPLES.md`
2. Update `API_REFERENCE.md` with parameters
3. Include error cases in `TROUBLESHOOTING.md`

## Pull Requests

### Process

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Update documentation
6. Submit pull request

### Branch Naming

```
feature/add-new-chart-type
bug/fix-csv-parsing
docs/update-examples
refactor/improve-api-client
```

### Commit Messages

```
feat: Add scatter plot visualization
fix: Handle CSV files with BOM encoding
docs: Update troubleshooting section
refactor: Improve error handling in client
test: Add tests for data transformers
```

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type
- [ ] Feature
- [ ] Bug fix
- [ ] Documentation
- [ ] Refactoring
- [ ] Tests

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Documentation
- [ ] API reference updated
- [ ] Examples added
- [ ] README updated

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] No breaking changes (or documented)
- [ ] Documentation updated
```

## Coding Standards

### Python Style

- Follow PEP 8
- Use type hints
- Write docstrings
- Keep functions focused
- Use descriptive names

### Code Example

```python
from typing import Optional, List

async def search_datasets(
    query: str,
    format: Optional[str] = None,
    page_size: int = 10
) -> SearchResult:
    """Search for datasets on Serbian data portal.

    Args:
        query: Search query string
        format: Filter by file format
        page_size: Number of results per page

    Returns:
        SearchResult with matching datasets

    Raises:
        APIError: If search fails
    """
    client = UDataClient()
    return await client.search_datasets(query, format, page_size)
```

### Error Handling

```python
try:
    result = await api_request()
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        return None
    raise APIError(f"API request failed: {e}")
except httpx.RequestError as e:
    raise APIError(f"Network error: {e}")
```

### Type Hints

```python
from typing import Dict, List, Optional, Union

def process_data(
    data: Union[pd.DataFrame, List[Dict[str, Any]]],
    filters: Dict[str, Any]
) -> pd.DataFrame:
    """Process and filter data."""
    ...
```

### Docstrings

```python
def create_visualization(
    data: pd.DataFrame,
    chart_type: str
) -> go.Figure:
    """Create interactive visualization.

    Args:
        data: Data to visualize
        chart_type: Type of chart (line, bar, pie, etc.)

    Returns:
        Plotly Figure object

    Raises:
        ValueError: If chart_type is invalid
        VisualizationError: If chart creation fails
    """
    ...
```

## Adding New Features

### Checkpoints

1. **Planning**
   - Define feature scope
   - Identify dependencies
   - Consider breaking changes

2. **Implementation**
   - Write code with tests
   - Follow style guidelines
   - Handle errors properly

3. **Documentation**
   - Update API reference
   - Add usage examples
   - Document breaking changes

4. **Testing**
   - Unit tests for new code
   - Integration tests
   - Manual testing

5. **Review**
   - Self-review code
   - Check documentation
   - Verify tests pass

### Feature Example: Adding New Chart Type

1. **Update `viz/charts.py`**:
```python
def area_chart(
    self,
    x_column: str,
    y_column: str,
    title: str = ""
) -> go.Figure:
    """Create an area chart."""
    fig = px.area(
        self.data,
        x=x_column,
        y=y_column,
        title=title
    )
    return fig
```

2. **Add test**:
```python
@pytest.mark.asyncio
async def test_area_chart():
    """Test area chart creation."""
    data = pd.DataFrame({
        "year": [2020, 2021, 2022],
        "value": [10, 20, 30]
    })
    builder = ChartBuilder(data)
    fig = builder.area_chart("year", "value")
    assert fig is not None
```

3. **Update documentation**:
- Add to API reference
- Add example in EXAMPLES.md
- Update tool list in README

## Bug Fixes

### Bug Fix Process

1. **Reproduce the bug**
2. **Add failing test**
3. **Fix the code**
4. **Verify test passes**
5. **Check for side effects**
6. **Update documentation**

### Bug Fix Example

```python
# Before
async def parse_csv(content: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(content))

# After (handles BOM)
async def parse_csv(content: bytes) -> pd.DataFrame:
    try:
        return pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(io.BytesIO(content), encoding="latin1")
```

## Performance Optimization

### Guidelines

1. **Profile first**: Identify bottlenecks
2. **Measure impact**: Before and after optimization
3. **Consider trade-offs**: Speed vs readability
4. **Document changes**: Explain why optimization was needed

### Common Optimizations

- Async operations for I/O
- Caching expensive operations
- Lazy loading where appropriate
- Efficient data structures

## Release Process

### Version Bump

```bash
# Update version in __init__.py
__version__ = "0.2.0"

# Update pyproject.toml
version = "0.2.0"

# Commit changes
git commit -m "chore: Bump version to 0.2.0"
```

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped
- [ ] Tagged release
- [ ] GitHub release created

## Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Welcome newcomers
- Focus on what is best for the community

### Getting Help

- Check existing issues first
- Use descriptive titles
- Provide context and examples
- Be patient with responses

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to Serbian Data MCP! 🇷🇸

## Additional Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [data.gov.rs API](https://data.gov.rs/udata/doc/api/)
- [Plotly Documentation](https://plotly.com/python/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)

## Next Steps

- Set up development environment
- Explore the codebase
- Find good first issues
- Join discussions
- Submit your first PR!
