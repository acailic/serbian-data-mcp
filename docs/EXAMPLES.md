# Usage Examples - Serbian Data MCP

Real-world examples of using Serbian Data MCP for data analysis and visualization.

## Table of Contents

1. [Basic Search Examples](#basic-search-examples)
2. [Data Retrieval Examples](#data-retrieval-examples)
3. [Visualization Examples](#visualization-examples)
4. [Advanced Analysis Examples](#advanced-analysis-examples)
5. [Integration Examples](#integration-examples)
6. [Smithery Installation Examples](#smithery-installation-examples)

## Basic Search Examples

### Example 1: Search for Population Data

**Prompt:**
```
Search for datasets about population with JSON format
```

**What happens:**
- MCP searches data.gov.rs for "population"
- Filters results to JSON format
- Returns top 10 matching datasets

**Use for:** Demographic research, population studies

### Example 2: Find Economic Datasets

**Prompt:**
```
Find datasets about economy from the statistical office
```

**What happens:**
- Searches for "economy" datasets
- Filters by organization (statistical office)
- Returns structured dataset information

**Use for:** Economic analysis, financial research

### Example 3: Browse by Organization

**Prompt:**
```
List all organizations that publish data
```

**What happens:**
- Returns list of all data providers
- Shows organization IDs and names
- Useful for filtering searches

**Use for:** Discovering data sources

### Example 4: Search with Autocomplete

**Prompt:**
```
Suggest datasets starting with "budžet"
```

**What happens:**
- Returns autocomplete suggestions
- Shows matching dataset titles
- Helps find specific datasets

**Use for:** Finding specific datasets by name

## Data Retrieval Examples

### Example 5: Get Complete Dataset Details

**Prompt:**
```
Get complete details for dataset ID population-2023
```

**What happens:**
- Retrieves full dataset metadata
- Shows all available resources
- Includes tags, descriptions, dates

**Use for:** Understanding dataset structure

### Example 6: Download JSON Data

**Prompt:**
```
Download the JSON data from resource ID 12345
```

**What happens:**
- Fetches JSON data from portal
- Parses and structures the data
- Returns ready-to-use data

**Use for:** API integration, data processing

### Example 7: Download CSV Data

**Prompt:**
```
Download the CSV file from budget-2024 dataset
```

**What happens:**
- Downloads CSV file
- Handles encoding (UTF-8, Latin1)
- Returns as structured DataFrame

**Use for:** Spreadsheet analysis, data import

### Example 8: Download Excel Data

**Prompt:**
```
Download the Excel file from economic-indicators dataset
```

**What happens:**
- Downloads XLSX file
- Parses all sheets
- Returns structured data

**Use for:** Financial reports, multi-sheet data

## Visualization Examples

### Example 9: Create Line Chart

**Prompt:**
```
Find population data by year and create a line chart showing trends from 2010 to 2023
```

**What happens:**
- Searches for population datasets
- Downloads time-series data
- Creates line chart with years on X-axis
- Plots population on Y-axis

**Result:** Interactive HTML chart showing population trends

**Use for:** Time-series analysis, trend visualization

### Example 10: Create Bar Chart

**Prompt:**
```
Find regional GDP data and create a bar chart comparing regions
```

**What happens:**
- Searches for GDP datasets
- Filters by region
- Creates horizontal bar chart
- Compares values across regions

**Result:** Interactive bar chart comparing regional GDP

**Use for:** Regional comparisons, ranking

### Example 11: Create Pie Chart

**Prompt:**
```
Find budget allocation data and create a pie chart showing spending categories
```

**What happens:**
- Downloads budget data
- Groups by category
- Creates pie chart with percentages
- Shows spending distribution

**Result:** Pie chart showing budget breakdown

**Use for:** Budget analysis, expenditure breakdown

### Example 12: Create Scatter Plot

**Prompt:**
```
Find education vs employment data and create a scatter plot
```

**What happens:**
- Downloads relevant dataset
- Plots education on X-axis
- Plots employment on Y-axis
- Shows correlation

**Result:** Scatter plot revealing relationships

**Use for:** Correlation analysis, pattern detection

### Example 13: Create Histogram

**Prompt:**
```
Find income distribution data and create a histogram
```

**What happens:**
- Downloads income data
- Creates frequency distribution
- Shows income ranges
- Identifies patterns

**Result:** Histogram showing income distribution

**Use for:** Distribution analysis, demographic studies

### Example 14: Create Box Plot

**Prompt:**
```
Find salary data by sector and create a box plot
```

**What happens:**
- Downloads salary data
- Groups by sector
- Creates box plots for each group
- Shows outliers and quartiles

**Result:** Box plot comparing salary distributions

**Use for:** Comparative analysis, outlier detection

### Example 15: Create Choropleth Map (Regions Shaded by Value)

**Prompt:**
```
Find GDP per country data for the Balkans and create a choropleth map shading each country by GDP, focused on Europe
```

**What happens:**
- Downloads country-level GDP data
- Maps country names to geographic regions (`locationmode` defaults to "country names")
- Shades each region by its GDP value on a base map (coastlines + landmass)
- Color ramp (Viridis) encodes magnitude; colorbar on the side

**Result:** Interactive choropleth — whole countries filled by metric, answering "which regions rank highest/lowest?"

**Use for:** Spatial comparison of an aggregate statistic (GDP, population density, turnout, pollution by region). Distinct from `scatter_geo` (individual points) and `line_geo` (routes).

### Example 16: Create Geographic Line Chart (Routes/Trajectories)

**Prompt:**
```
Find transport corridor data with lat/lon waypoints and create a line_geo chart showing connected routes through Serbia, one color per corridor
```

**What happens:**
- Downloads waypoint data (latitude/longitude per row)
- Joins consecutive waypoints into connected line paths on a base map
- `color_column` splits the data into one separate path per group (multiple routes)
- `scope` focuses the base map (e.g. "europe")

**Result:** Interactive map with connected route lines — flight/shipping routes, migration corridors, storm tracks, supply-chain arcs

**Use for:** Routes, trajectories, flows on a map. Distinct from `scatter_geo` (discrete points, no connecting line) and `choropleth` (whole regions shaded).

## Advanced Analysis Examples

### Example 17: Filter and Aggregate Data

**Prompt:**
```
Download trade data, filter for exports in 2023, and calculate total by country
```

**What happens:**
- Downloads trade dataset
- Filters for year 2023, exports only
- Groups by country
- Aggregates totals
- Returns summary data

**Use for:** Trade analysis, export statistics

### Example 18: Time Series Analysis

**Prompt:**
```
Find monthly unemployment data, filter for last 5 years, and create a line chart
```

**What happens:**
- Downloads unemployment data
- Filters date range
- Creates time-series visualization
- Shows trends over time

**Use for:** Economic monitoring, trend analysis

### Example 19: Multi-Dataset Comparison

**Prompt:**
```
Find population datasets for Belgrade, Novi Sad, and Niš and compare their growth
```

**What happens:**
- Searches for city population data
- Downloads multiple datasets
- Merges and compares data
- Creates comparative chart

**Use for:** Urban studies, city comparisons

### Example 20: Custom Aggregation

**Prompt:**
```
Download budget data, group by ministry, and calculate average spending over 5 years
```

**What happens:**
- Downloads budget data
- Groups by ministry
- Calculates average spending
- Returns aggregated results

**Use for:** Budget analysis, spending trends

## Integration Examples

### Example 21: Export Visualization

**Prompt:**
```
Create a population trend chart and export it as HTML
```

**What happens:**
- Creates visualization
- Exports as interactive HTML
- Saves to exports directory
- Returns file path

**Use for:** Reports, presentations, web publishing

### Example 22: Export as PNG

**Prompt:**
```
Create a regional GDP chart and export as high-resolution PNG
```

**What happens:**
- Creates visualization
- Exports as PNG image
- Uses high resolution
- Returns file path

**Use for:** Publications, printing, documents

**Note:** Requires kaleido package (`pip install kaleido`)

### Example 23: Export Chart Data

**Prompt:**
```
Create a visualization and export the chart data as JSON
```

**What happens:**
- Creates visualization
- Exports as JSON
- Preserves chart structure
- Returns file path

**Use for:** Custom processing, API integration

### Example 24: Chained Analysis

**Prompt:**
```
Search for inflation data, download the latest CSV, create a line chart, and export as HTML
```

**What happens:**
- Searches datasets
- Downloads data
- Creates visualization
- Exports file
- Returns complete result

**Use for:** Automated workflows, reporting

### Example 25: Data Transformation

**Prompt:**
```
Download economic data, filter for years 2020-2023, sort by GDP, and select top 10 countries
```

**What happens:**
- Downloads dataset
- Applies date filter
- Sorts by GDP column
- Selects top 10
- Returns processed data

**Use for:** Data cleaning, ranking reports

### Example 26: Statistical Analysis

**Prompt:**
```
Download temperature data, calculate mean, median, and standard deviation by month
```

**What happens:**
- Downloads weather data
- Groups by month
- Calculates statistics
- Returns summary table

**Use for:** Climate analysis, weather reports

## Smithery Installation Examples

### Example 27: Install via Smithery CLI (Claude Desktop)

[Smithery](https://smithery.ai) is a registry and CLI for managing MCP server connections. It automatically configures your AI client — no manual config file editing needed.

```bash
# Install the Smithery CLI (requires Node.js 20+)
npm install -g smithery@latest

# Authenticate with Smithery
smithery auth login

# Add Serbian Data MCP to Claude Desktop
smithery mcp add acailic/serbian-data-mcp --client claude
```

**What happens:**
- Smithery downloads and configures the MCP server
- Claude Desktop config is updated automatically
- Server runs via `uvx --from serbian-data-mcp serbian-data-mcp`

**Use for:** One-command setup for Claude Desktop users

### Example 28: Install via Smithery (Cursor)

```bash
# Add to Cursor
smithery mcp add acailic/serbian-data-mcp --client cursor

# Restart Cursor for changes to take effect
```

**Use for:** One-command setup for Cursor users

### Example 29: Install via Smithery (Remote Connection)

If you prefer a fully managed remote connection instead of running the server locally:

```bash
# Connect as a remote Smithery connection
smithery mcp add acailic/serbian-data-mcp --id serbian-data

# Verify the connection
smithery mcp list

# List available tools
smithery tool list serbian-data
```

**What happens:**
- Smithery hosts the MCP connection remotely
- No local Python installation needed
- Works with any MCP-compatible client

**Use for:** Users who want zero local dependencies

### Example 30: Use Smithery CLI to Call Tools Directly

You can also call MCP tools directly from the command line via Smithery:

```bash
# Search for datasets
smithery tool call serbian-data search_datasets '{"query": "population", "page_size": 5}'

# Get dataset details
smithery tool call serbian-data get_dataset '{"dataset_id": "population-2023"}'

# Create a visualization
smithery tool call serbian-data create_visualization '{"chart_type": "line", "title": "Population Trends"}'
```

**Use for:** Scripting, automation, testing without an AI client

### Example 31: Remove Smithery Connection

```bash
# Remove from Claude Desktop
smithery mcp remove acailic/serbian-data-mcp --client claude

# Remove a remote connection
smithery mcp remove serbian-data
```

**Use for:** Cleanup and switching between installation methods

## Real-World Use Cases

### Government & Policy

**Budget Analysis:**
```
Download the national budget, group by category, and create a pie chart showing spending distribution
```

**Policy Evaluation:**
```
Find education spending data over time and create a line chart showing trends
```

### Business & Economy

**Market Research:**
```
Search for consumer price index data and create a visualization showing inflation trends
```

**Industry Analysis:**
```
Download production data by sector and create a bar chart comparing industries
```

### Academic & Research

**Demographic Studies:**
```
Find census data, create population pyramid charts for different regions
```

**Economic Research:**
```
Download GDP data, analyze growth rates, and visualize trends
```

### Journalism & Media

**Data Journalism:**
```
Find government spending data, create visualizations for investigative reports
```

**Public Information:**
```
Download air quality data and create accessible visualizations for public
```

## Tips for Best Results

1. **Be Specific** - Use exact search terms for better results
2. **Filter by Format** - Specify JSON/CSV/XLSX when you know the format
3. **Start Simple** - Begin with basic searches before complex analysis
4. **Export Results** - Save visualizations for reuse and sharing
5. **Check Data Quality** - Verify dataset dates and completeness

## Common Patterns

### Time Series Pattern
```
Find [metric] data, create line chart showing [time_period] trends
```

### Comparison Pattern
```
Find [category] data and create bar chart comparing [items]
```

### Distribution Pattern
```
Find [metric] data and create pie chart showing [categories]
```

### Analysis Pattern
```
Download [dataset], filter for [conditions], and calculate [aggregation]
```

## Next Steps

- See [API Reference](API_REFERENCE.md) for all available tools
- Check [Troubleshooting](TROUBLESHOOTING.md) for common issues
- Return to [Quick Start](QUICKSTART.md) for setup help
