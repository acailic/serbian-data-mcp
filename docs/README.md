# Serbian Data MCP Documentation

Complete documentation for the Serbian Data MCP Server.

## Documentation Files

### [Quick Start Guide](QUICKSTART.md)
**5-minute setup guide** - Get up and running quickly
- Installation instructions
- Claude Desktop configuration
- Basic verification steps
- Common first tasks

**Start here if you're new to Serbian Data MCP**

### [Usage Examples](EXAMPLES.md)
**24 real-world examples** - Learn by doing
- Basic search examples
- Data retrieval patterns
- Visualization tutorials
- Advanced analysis workflows
- Integration examples

**Great for learning capabilities and common patterns**

### [API Reference](API_REFERENCE.md)
**Complete tool reference** - All parameters and responses
- Search tools (search_datasets, suggest_datasets, list_organizations)
- Data retrieval (get_dataset, get_resource_data)
- Visualization tools (create_visualization)
- Data transformation (filter, group, aggregate, sort, select)
- Export utilities (HTML, PNG, JSON)
- Error codes and responses

**Essential for detailed implementation**

### [Troubleshooting Guide](TROUBLESHOOTING.md)
**Common issues and solutions** - Solve problems fast
- Installation issues
- Configuration problems
- MCP connection troubles
- Data access errors
- Visualization issues
- Performance optimization

**First stop when something doesn't work**

### [Contributing Guide](CONTRIBUTING.md)
**Developer contributions** - Join the project
- Development setup
- Code structure overview
- Testing guidelines
- Documentation standards
- Pull request process

**For contributors and maintainers**

## Quick Navigation

### By Use Case

**Government & Policy Analysis**
- Budget analysis: See EXAMPLES.md Example 11
- Policy evaluation: See EXAMPLES.md Example 20
- Public information: See EXAMPLES.md Example 24

**Business & Economy**
- Market research: See EXAMPLES.md Example 19
- Industry analysis: See EXAMPLES.md Example 19
- Economic indicators: See API_REFERENCE.md - Data Retrieval

**Academic & Research**
- Demographic studies: See EXAMPLES.md Example 9
- Economic research: See EXAMPLES.md Example 19
- Data analysis: See EXAMPLES.md Example 15-18

**Journalism & Media**
- Data journalism: See EXAMPLES.md Example 24
- Visualizations: See EXAMPLES.md Example 10-14

### By Task

**Search & Discovery**
- Search datasets: API_REFERENCE.md - search_datasets
- Autocomplete: API_REFERENCE.md - suggest_datasets
- Browse organizations: API_REFERENCE.md - list_organizations

**Data Access**
- Get dataset details: API_REFERENCE.md - get_dataset
- Download data: API_REFERENCE.md - get_resource_data
- Format support: API_REFERENCE.md - Data Format Support

**Analysis & Processing**
- Filter data: API_REFERENCE.md - filter_data
- Group data: API_REFERENCE.md - group_data
- Aggregate: API_REFERENCE.md - aggregate_data
- Sort: API_REFERENCE.md - sort_data
- Select columns: API_REFERENCE.md - select_columns

**Visualization**
- Create charts: API_REFERENCE.md - create_visualization
- Export visualizations: API_REFERENCE.md - export_visualization
- Chart types: API_REFERENCE.md - Chart Types

## Learning Path

### Beginner (New to Serbian Data MCP)

1. Read [Quick Start Guide](QUICKSTART.md) - 5 minutes
2. Try basic search examples in [Examples](EXAMPLES.md) - 10 minutes
3. Create your first visualization - 10 minutes
4. Export and share your work - 5 minutes

**Total time: ~30 minutes**

### Intermediate (Familiar with basics)

1. Review complete [API Reference](API_REFERENCE.md) - 15 minutes
2. Try advanced analysis examples - 20 minutes
3. Learn data transformation tools - 15 minutes
4. Build custom workflow - 20 minutes

**Total time: ~70 minutes**

### Advanced (Ready to contribute)

1. Study [Contributing Guide](CONTRIBUTING.md) - 20 minutes
2. Set up development environment - 15 minutes
3. Review code structure - 20 minutes
4. Contribute improvements - Ongoing

**Total time: ~55 minutes + contribution time**

## Key Concepts

### MCP Server Integration

Serbian Data MCP integrates with Claude Desktop using the Model Context Protocol:

- **No API keys needed** - Uses public data portal
- **Automatic rate limiting** - Respects API limits
- **Caching included** - Speeds up repeated requests
- **Format support** - JSON, CSV, Excel, XML

### Data Portal (data.gov.rs)

Serbian government open data portal with:

- **3,400+ datasets** - Government open data
- **45+ organizations** - Data providers
- **Multiple formats** - JSON, CSV, XLSX, XML
- **Regular updates** - Current and historical data

### Visualization Capabilities

Interactive charts powered by Plotly:

- **Line charts** - Time series, trends
- **Bar charts** - Comparisons, rankings
- **Pie charts** - Distributions, proportions
- **Scatter plots** - Correlations, relationships
- **Histograms** - Distributions, frequencies
- **Box plots** - Statistical comparison

## Common Workflows

### Quick Data Lookup

```python
# 1. Search for dataset
search_datasets("population")

# 2. Get details
get_dataset("population-2023")

# 3. Download data
get_resource_data("resource-id")
```

### Analysis & Visualization

```python
# 1. Find and download data
data = get_resource_data("resource-id")

# 2. Transform if needed
filtered = filter_data(data, {"year": 2023})

# 3. Create visualization
chart = create_visualization(
  filtered,
  chart_type="bar",
  x_column="region",
  y_column="value"
)

# 4. Export
export_visualization(chart, format="html", filename="chart.html")
```

## Getting Help

### Documentation First

1. **Quick issues** - Check [Troubleshooting](TROUBLESHOOTING.md)
2. **Usage questions** - See [Examples](EXAMPLES.md)
3. **API details** - Review [API Reference](API_REFERENCE.md)
4. **Setup problems** - Follow [Quick Start](QUICKSTART.md)

### Community Resources

- **GitHub Issues** - Report bugs and request features
- **Pull Requests** - Contribute improvements
- **Documentation** - Help improve docs

### Debug Mode

Enable verbose output:

```bash
python -m serbian_data_mcp --verbose
```

## Best Practices

### Data Access

1. **Search first** - Find relevant datasets before downloading
2. **Use filters** - Reduce data size during retrieval
3. **Check formats** - Choose appropriate format for your use case
4. **Respect rate limits** - Built-in delays prevent API overload

### Visualization

1. **Know your data** - Understand structure before charting
2. **Choose right chart** - Match chart type to data and goal
3. **Add context** - Use titles and labels effectively
4. **Export results** - Save visualizations for reuse

### Development

1. **Follow guidelines** - See [Contributing Guide](CONTRIBUTING.md)
2. **Write tests** - Ensure code quality
3. **Document changes** - Keep docs up to date
4. **Be respectful** - Follow community guidelines

## Technical Specifications

### Requirements

- Python 3.11 or higher
- Claude Desktop (for MCP integration)
- Internet connection
- 50MB disk space (including cache)

### Dependencies

- fastmcp - MCP server framework
- plotly - Interactive visualizations
- pandas - Data processing
- httpx - Async HTTP client
- requests - Synchronous HTTP client
- pydantic - Data validation
- openpyxl - Excel file support

### Performance

- **Search**: < 2 seconds
- **Dataset details**: < 1 second
- **CSV download**: 2-10 seconds (file size dependent)
- **Visualization**: < 1 second
- **Export**: 1-5 seconds (format dependent)

## FAQ

### Is this free?

Yes! Serbian Data MCP is open source and accesses free public data.

### Do I need an API key?

No, the data.gov.rs portal is publicly accessible.

### What data is available?

3,400+ datasets across topics like population, economy, environment, and more.

### Can I use this commercially?

Yes, both the MCP server and the data are open source.

### How often is data updated?

Updates vary by dataset and organization. Check individual dataset metadata.

## Future Enhancements

Planned improvements:

- [ ] Additional chart types (heatmap, timeline)
- [ ] Data transformation pipeline builder
- [ ] Scheduled data updates
- [ ] Advanced filtering capabilities
- [ ] Multi-dataset joining
- [ ] Custom report templates

Suggestions welcome! Open an issue or pull request.

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- **data.gov.rs** - Serbian open data portal
- **UData** - Open data platform software
- **Plotly** - Interactive visualization library
- **FastMCP** - MCP server framework

---

**Ready to explore Serbian government data? Start with the [Quick Start Guide](QUICKSTART.md)!**

🇷🇸 **Serbian Data MCP** - Access 3,400+ government datasets with ease
