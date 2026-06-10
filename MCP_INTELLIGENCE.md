# Serbian Data MCP - Server Intelligence Enhancements

## Current State

The MCP server is a thin wrapper around the data.gov.rs API with no intelligence about the data catalog.

## Required Intelligence Features

### 1. Dataset Catalog Cache
- **Maintain indexed catalog** of all datasets at startup
- **Store**: Dataset ID, title, description, organization, resource formats, tags
- **Enable**: Fast semantic search without hitting API rate limits
- **Update**: Periodically refresh (daily/weekly)

### 2. Semantic Understanding
- **Dataset categorization**: Auto-tag datasets by topic (population, finance, environment, health)
- **Keyword extraction**: Identify key terms in descriptions
- **Smart matching**: Map user queries "age data" → datasets tagged "demographics", "census", "population by age"

### 3. Intelligent Suggestions
- **When exact match fails**: Suggest semantically related datasets
- **Explain reasoning**: "No age data found, but these 5 datasets contain population information..."
- **Provide alternatives**: "You might be interested in Statistical Office datasets"

### 4. Format Awareness
- **Track download availability**: Which datasets have CSV/JSON vs just metadata
- **Prioritize**: Suggest datasets with downloadable data over metadata-only
- **Preview capabilities**: Show sample data when available

### 5. Query Enhancement
- **Query expansion**: "age population" → search ["age", "population", "demographics", "stanovništvo", "popis"]
- **Language awareness**: Search in both Serbian and English
- **Fuzzy matching**: Handle typos, synonyms

## Implementation Strategy

### Phase 1: Catalog Builder
```python
class DatasetCatalog:
    """Maintain indexed catalog of all datasets."""
    
    async def build_catalog(self):
        """Fetch and index all datasets at startup."""
        # Fetch all datasets (paginated)
        # Extract: ID, title, description, org, formats, tags
        # Store in searchable structure
        # Save to JSON cache file
        
    async def search_semantic(self, query: str) -> List[Dataset]:
        """Search using semantic understanding."""
        # Query expansion
        # Keyword matching
        # Relevance scoring
        # Return ranked results
```

### Phase 2: Enhanced MCP Tools
```python
@mcp.tool()
async def intelligent_search(
    query: str,
    suggest_alternatives: bool = True
) -> dict[str, Any]:
    """Search with intelligence and fallback suggestions."""
    
    # 1. Expand query (synonyms, translations)
    # 2. Search catalog (not live API)
    # 3. If no results, suggest alternatives
    # 4. Rank by relevance
    # 5. Return with explanations
```

### Phase 3: Dataset Preview
```python
@mcp.tool()
async def preview_dataset(dataset_id: str) -> dict[str, Any]:
    """Show dataset info with data preview."""
    
    # Get metadata
    # Try to download first 10 rows
    # Show column names and sample values
    # Let user understand data structure
```

## Benefits

**For users:**
- Ask natural questions without knowing exact dataset names
- Get intelligent suggestions when exact matches fail
- Understand what data exists before downloading
- Get faster responses (no rate limits on cached catalog)

**For server:**
- Reduced API calls (rate limits avoided)
- Better user experience
- More adoption due to intelligence

## Priority

1. **HIGH**: Catalog builder (enables all other features)
2. **HIGH**: Query expansion (language awareness)
3. **MEDIUM**: Alternative suggestions
4. **MEDIUM**: Dataset preview
5. **LOW**: Automatic categorization

## Example Usage

**Before (current):**
```
User: "age population data"
MCP: "0 results" (dead end)
```

**After (enhanced):**
```
User: "age population data"
MCP: "No exact match found, but I found 3 relevant datasets:
  1. 'Popis stanovništva' (Population census) - CSV format, downloadable
  2. 'Demografska po starosti' (Age structure) - XLS format, downloadable
  3. 'Stanovništvo po opštinama' (Population by regions) - JSON format

Would you like me to download and show sample data from any of these?"
```

This makes the MCP genuinely useful instead of just being an API wrapper.
