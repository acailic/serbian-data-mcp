# API Reference - Serbian Data MCP

Complete reference for all MCP tools, parameters, and responses.

## Table of Contents

1. [Search Tools](#search-tools)
2. [Data Retrieval Tools](#data-retrieval-tools)
3. [Visualization Tools](#visualization-tools)
4. [Data Transformation Tools](#data-transformation-tools)
5. [Export Tools](#export-tools)
6. [Utility Tools](#utility-tools)

## Search Tools

### search_datasets

Search for datasets on the Serbian data portal.

**Parameters:**
- `query` (string, optional): Search query string. Default: ""
- `format` (string, optional): Filter by file format. Options: "json", "csv", "xml", "xlsx". Default: null
- `organization` (string, optional): Filter by organization ID. Default: null
- `page_size` (integer, optional): Number of results per page. Default: 10, Max: 100
- `page` (integer, optional): Page number (1-indexed). Default: 1

**Returns:**
```json
{
  "datasets": [
    {
      "id": "dataset-id",
      "title": "Dataset Title",
      "description": "Dataset description",
      "organization": {
        "id": "org-id",
        "name": "Organization Name"
      },
      "resources": [...],
      "tags": ["tag1", "tag2"],
      "created_at": "2023-01-01T00:00:00",
      "modified_at": "2023-12-31T23:59:59",
      "frequency": "annual",
      "license": "CC-BY-4.0"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 10
}
```

**Example:**
```python
# Search for population datasets
result = await mcp.call_tool("search_datasets", {
  "query": "population",
  "format": "json",
  "page_size": 20
})
```

### suggest_datasets

Get autocomplete suggestions for dataset search.

**Parameters:**
- `query` (string, required): Partial search query
- `format` (string, optional): Filter by file format. Default: null
- `size` (integer, optional): Number of suggestions. Default: 10

**Returns:**
```json
{
  "results": [
    "Population by municipality 2023",
    "Population census 2022",
    "Population projections 2030"
  ]
}
```

**Example:**
```python
# Get suggestions for "pop"
suggestions = await mcp.call_tool("suggest_datasets", {
  "query": "pop",
  "size": 10
})
```

### list_organizations

List all organizations that publish datasets.

**Parameters:**
- `page_size` (integer, optional): Number of results per page. Default: 50
- `page` (integer, optional): Page number (1-indexed). Default: 1

**Returns:**
```json
{
  "organizations": [
    {
      "id": "org-id",
      "name": "Organization Name",
      "description": "Organization description",
      "url": "https://organization.gov.rs",
      "logo": "https://data.gov.rs/logo.png"
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 50
}
```

**Example:**
```python
# Get first 50 organizations
orgs = await mcp.call_tool("list_organizations", {
  "page_size": 50
})
```

## Data Retrieval Tools

### get_dataset

Get complete details for a specific dataset.

**Parameters:**
- `dataset_id` (string, required): Dataset identifier

**Returns:**
```json
{
  "id": "dataset-id",
  "title": "Complete Dataset Title",
  "description": "Full dataset description",
  "organization": {
    "id": "org-id",
    "name": "Organization Name",
    "description": "Org description",
    "url": "https://organization.gov.rs"
  },
  "resources": [
    {
      "id": "resource-id",
      "title": "Data file title",
      "description": "Resource description",
      "format": "csv",
      "url": "https://data.gov.rs/resource.csv",
      "created_at": "2023-01-01T00:00:00",
      "size": 1024000,
      "mime_type": "text/csv",
      "checksum": "md5-hash"
    }
  ],
  "tags": ["demography", "population"],
  "created_at": "2023-01-01T00:00:00",
  "modified_at": "2023-12-31T23:59:59",
  "frequency": "annual",
  "temporal_coverage": "2020-2023",
  "spatial_coverage": "Serbia",
  "license": "CC-BY-4.0"
}
```

**Example:**
```python
# Get complete dataset details
dataset = await mcp.call_tool("get_dataset", {
  "dataset_id": "population-2023"
})
```

### get_resource_data

Download and parse resource data.

**Parameters:**
- `resource_id` (string, required): Resource identifier

**Returns:**
- For JSON: Parsed dictionary or list
- For CSV: DataFrame structure with rows and columns
- For Excel: DataFrame structure with sheet data
- For XML: Raw XML text

**Example (CSV):**
```json
{
  "data": [
    {
      "year": 2020,
      "population": 6890000,
      "growth_rate": 0.5
    },
    {
      "year": 2021,
      "population": 6930000,
      "growth_rate": 0.6
    }
  ],
  "columns": ["year", "population", "growth_rate"],
  "rows": 2
}
```

**Example (JSON):**
```json
{
  "total_population": 7000000,
  "urban": 4500000,
  "rural": 2500000,
  "by_region": {
    "belgrade": 1700000,
    "vojvodina": 2000000
  }
}
```

**Example:**
```python
# Download CSV data
data = await mcp.call_tool("get_resource_data", {
  "resource_id": "population-csv-2023"
})
```

## Visualization Tools

### create_visualization

Create interactive charts from data.

**Parameters:**
- `data` (array/object, required): Data to visualize
- `chart_type` (string, required): Chart type. Options: "line", "bar", "pie", "scatter", "histogram", "box"
- `x_column` (string, optional): Column name for X axis (required for most charts)
- `y_column` (string, optional): Column name for Y axis (required for most charts)
- `values_column` (string, optional): Column for pie chart values
- `names_column` (string, optional): Column for pie chart labels
- `color_column` (string, optional): Column for color grouping
- `size_column` (string, optional): Column for size grouping (scatter plots)
- `title` (string, optional): Chart title
- `orientation` (string, optional): Bar chart orientation. Options: "v", "h". Default: "v"
- `bins` (integer, optional): Number of bins for histogram. Default: auto

**Returns:**
```json
{
  "figure": {
    "data": [...],
    "layout": {...}
  },
  "type": "plotly",
  "interactive": true
}
```

**Chart Types:**

1. **Line Chart** - Time series, trends
```python
chart = await mcp.call_tool("create_visualization", {
  "data": data,
  "chart_type": "line",
  "x_column": "year",
  "y_column": "population",
  "title": "Population Trends"
})
```

2. **Bar Chart** - Comparisons, rankings
```python
chart = await mcp.call_tool("create_visualization", {
  "data": data,
  "chart_type": "bar",
  "x_column": "region",
  "y_column": "gdp",
  "title": "Regional GDP",
  "orientation": "v"
})
```

3. **Pie Chart** - Distributions, proportions
```python
chart = await mcp.call_tool("create_visualization", {
  "data": data,
  "chart_type": "pie",
  "values_column": "amount",
  "names_column": "category",
  "title": "Budget Distribution"
})
```

4. **Scatter Plot** - Correlations, relationships
```python
chart = await mcp.call_tool("create_visualization", {
  "data": data,
  "chart_type": "scatter",
  "x_column": "education",
  "y_column": "income",
  "color_column": "region",
  "title": "Education vs Income"
})
```

5. **Histogram** - Distributions
```python
chart = await mcp.call_tool("create_visualization", {
  "data": data,
  "chart_type": "histogram",
  "column": "age",
  "title": "Age Distribution",
  "bins": 20
})
```

6. **Box Plot** - Statistical comparison
```python
chart = await mcp.call_tool("create_visualization", {
  "data": data,
  "chart_type": "box",
  "x_column": "sector",
  "y_column": "salary",
  "title": "Salary Distribution by Sector"
})
```

## Data Transformation Tools

### filter_data

Filter data based on criteria.

**Parameters:**
- `data` (array/object, required): Data to filter
- `filters` (object, required): Filter criteria

**Filter Operators:**
- Direct value: `{"column": "value"}`
- Comparison: `{"column": {">=": 10, "<=": 20}}`
- List matching: `{"column": ["value1", "value2"]}`
- In operator: `{"column": {"in": ["a", "b"]}}`

**Example:**
```python
# Filter for years 2020-2023
filtered = await mcp.call_tool("filter_data", {
  "data": data,
  "filters": {
    "year": {">=": 2020, "<=": 2023}
  }
})

# Filter by category
filtered = await mcp.call_tool("filter_data", {
  "data": data,
  "filters": {
    "category": ["education", "health"]
  }
})
```

### group_data

Group data by columns.

**Parameters:**
- `data` (array/object, required): Data to group
- `group_by` (string/array, required): Column name(s) to group by
- `aggregations` (object, optional): Aggregation functions per column

**Aggregation Functions:**
- "sum", "mean", "median", "min", "max", "count", "std", "var"

**Example:**
```python
# Group by region and calculate totals
grouped = await mcp.call_tool("group_data", {
  "data": data,
  "group_by": "region",
  "aggregations": {
    "population": "sum",
    "gdp": "mean"
  }
})
```

### aggregate_data

Aggregate a single column.

**Parameters:**
- `data` (array/object, required): Data to aggregate
- `column` (string, required): Column name to aggregate
- `function` (string, required): Aggregation function

**Functions:**
- "sum", "mean", "median", "min", "max", "count", "std", "var"

**Example:**
```python
# Calculate total population
total = await mcp.call_tool("aggregate_data", {
  "data": data,
  "column": "population",
  "function": "sum"
})
```

### sort_data

Sort data by columns.

**Parameters:**
- `data` (array/object, required): Data to sort
- `by` (string/array, required): Column name(s) to sort by
- `ascending` (boolean, optional): Sort order. Default: true

**Example:**
```python
# Sort by GDP descending
sorted_data = await mcp.call_tool("sort_data", {
  "data": data,
  "by": ["gdp", "population"],
  "ascending": false
})
```

### select_columns

Select specific columns from data.

**Parameters:**
- `data` (array/object, required): Data to process
- `columns` (array, required): Column names to select

**Example:**
```python
# Select only year and population columns
selected = await mcp.call_tool("select_columns", {
  "data": data,
  "columns": ["year", "population", "growth_rate"]
})
```

## Export Tools

### export_visualization

Export visualization to file.

**Parameters:**
- `figure` (object, required): Plotly Figure object
- `format` (string, required): Export format. Options: "html", "png", "json"
- `filename` (string, required): Output filename
- `output_dir` (string, optional): Output directory. Default: from config
- `scale` (number, optional): Scale factor for PNG. Default: 1.0

**Returns:**
```json
{
  "filepath": "/path/to/exports/chart.html",
  "format": "html",
  "size": 45000
}
```

**Example (HTML):**
```python
# Export as interactive HTML
result = await mcp.call_tool("export_visualization", {
  "figure": chart,
  "format": "html",
  "filename": "population-trends.html"
})
```

**Example (PNG):**
```python
# Export as high-resolution image
result = await mcp.call_tool("export_visualization", {
  "figure": chart,
  "format": "png",
  "filename": "population-trends.png",
  "scale": 2.0
})
```

**Example (JSON):**
```python
# Export chart data as JSON
result = await mcp.call_tool("export_visualization", {
  "figure": chart,
  "format": "json",
  "filename": "population-trends.json"
})
```

## Utility Tools

### get_config

Get current configuration settings.

**Returns:**
```json
{
  "api_base": "https://data.gov.rs",
  "rate_limit": 1.0,
  "timeout": 30,
  "cache_dir": ".cache",
  "export_dir": "exports"
}
```

### health_check

Check MCP server and API connectivity.

**Returns:**
```json
{
  "status": "healthy",
  "api_reachable": true,
  "version": "0.1.0",
  "timestamp": "2023-12-31T23:59:59"
}
```

## Error Responses

All tools follow standard error response format:

```json
{
  "error": true,
  "message": "Error description",
  "code": "ERROR_CODE",
  "details": {...}
}
```

**Common Error Codes:**
- `DATASET_NOT_FOUND`: Dataset ID does not exist
- `RESOURCE_NOT_FOUND`: Resource ID does not exist
- `INVALID_FORMAT`: Unsupported file format
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `API_ERROR`: API request failed
- `PARSE_ERROR`: Failed to parse data
- `VISUALIZATION_ERROR`: Chart creation failed

## Rate Limiting

The MCP server includes built-in rate limiting:

- **Default**: 1 request per second
- **Configurable**: Set `rate_limit` in config.json
- **Automatic**: Requests are automatically delayed

## Data Format Support

### Supported Formats

1. **JSON** - Structured data, API responses
2. **CSV** - Spreadsheet data, UTF-8 and Latin1 encoding
3. **Excel** - XLSX files, multi-sheet support
4. **XML** - Structured markup (raw text)

### Encoding Support

- UTF-8 (with and without BOM)
- Latin1 (ISO-8859-1)
- Fallback with error replacement

## Response Objects

### Dataset Object

```typescript
{
  id: string,
  title: string,
  description?: string,
  organization?: {
    id: string,
    name: string,
    description?: string,
    url?: string,
    logo?: string
  },
  resources: Array<{
    id: string,
    title: string,
    description?: string,
    format?: string,
    url?: string,
    created_at?: string,
    size?: number,
    mime_type?: string,
    checksum?: string
  }>,
  tags: string[],
  created_at?: string,
  modified_at?: string,
  frequency?: string,
  temporal_coverage?: string,
  spatial_coverage?: string,
  license?: string
}
```

### SearchResult Object

```typescript
{
  datasets: Dataset[],
  total: number,
  page: number,
  page_size: number,
  total_pages: number,
  has_next: boolean,
  has_previous: boolean
}
```

## Best Practices

1. **Start with search** - Find relevant datasets first
2. **Get dataset details** - Understand structure before downloading
3. **Filter early** - Reduce data size during retrieval
4. **Use appropriate formats** - JSON for APIs, CSV for data analysis
5. **Export results** - Save visualizations for reuse
6. **Handle errors** - Check error responses and retry if needed

## Next Steps

- Try [Examples](EXAMPLES.md) for common use cases
- See [Troubleshooting](TROUBLESHOOTING.md) for common issues
- Return to [Quick Start](QUICKSTART.md) for setup help
