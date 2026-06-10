# Serbian Data MCP - Intelligent Server Specification

**Phase 0 Output: Requirements & Architecture**
**Date:** 2025-01-10
**Status:** Ready for Planning

---

## Executive Summary

Transform the Serbian Data MCP server from a thin API wrapper into an intelligent discovery engine that understands available data, guides users to relevant datasets, and provides semantic search capabilities across 3,430+ datasets from 180+ organizations.

---

## 1. Business Goals

### Problem Statement
The current MCP server provides raw API access to data.gov.rs with no intelligence about:
- What datasets actually exist (users must know exact names)
- Semantic relationships between datasets (no understanding of topics)
- Alternative suggestions when exact matches fail
- Language awareness (Serbian/English dataset discovery)

### Success Criteria
1. Users can ask natural questions ("age population data") without knowing exact dataset names
2. Server provides intelligent suggestions when exact matches fail
3. Fast responses without hitting API rate limits (cached catalog)
4. Bilingual awareness (Serbian/English keywords)

---

## 2. Functional Requirements

### FR1: Dataset Catalog Cache
**Priority:** HIGH

**Requirements:**
- Fetch and index all 3,430+ datasets at server startup
- Store: dataset ID, title, description, organization, resource formats, tags
- Enable fast semantic search without API calls
- Periodic refresh (daily/weekly configurable)
- Persist to disk for fast server restart

**Acceptance Criteria:**
- Catalog builds in <60 seconds on first run
- Subsequent startups load catalog in <5 seconds from cache
- Cache invalidation when datasets are added/modified

### FR2: Semantic Search
**Priority:** HIGH

**Requirements:**
- Query expansion: "age population" → ["age", "population", "demographics", "stanovništvo", "popis"]
- Keyword matching on title, description, tags
- Relevance scoring algorithm
- Language awareness (Serbian/English)

**Acceptance Criteria:**
- Returns relevant datasets for natural language queries
- Handles typos and synonyms
- Bilingual keyword matching

### FR3: Alternative Suggestions
**Priority:** MEDIUM

**Requirements:**
- When no exact match: suggest semantically related datasets
- Explain reasoning: "No age data found, but these 5 datasets contain population information..."
- Provide alternatives with relevance scores

**Acceptance Criteria:**
- Never returns empty results without suggestions
- Suggestions are actually relevant to user intent
- Clear explanations of why datasets were suggested

### FR4: Dataset Preview
**Priority:** MEDIUM

**Requirements:**
- Show dataset metadata
- Preview first 10 rows when downloadable (CSV/JSON)
- Display column names and sample values
- Help users understand data structure before downloading

**Acceptance Criteria:**
- Preview loads in <3 seconds
- Shows clear data structure overview
- Gracefully handles non-downloadable datasets

### FR5: Query Enhancement
**Priority:** HIGH

**Requirements:**
- Query expansion with synonyms
- Fuzzy matching for typos
- Language translation (Serbian ↔ English)
- Format awareness (prioritize CSV/JSON over metadata-only)

**Acceptance Criteria:**
- Handles typos in user queries
- Works in both Serbian and English
- Prioritizes downloadable datasets

---

## 3. Technical Architecture

### Module Structure

```
src/serbian_data_mcp/
├── catalog/
│   ├── __init__.py
│   ├── cache.py          # DatasetCatalog class
│   ├── search.py         # SemanticSearchEngine
│   ├── suggestions.py    # AlternativeSuggestions
│   └── preview.py        # DatasetPreview
├── intelligence/
│   ├── __init__.py
│   ├── query_expander.py # Query expansion
│   ├── relevance.py      # Scoring algorithms
│   └── multilingual.py   # Serbian/English keywords
└── data/
    └── cache.json        # Persisted catalog cache
```

### Data Models

```python
# Catalog models
@dataclass
class CachedDataset:
    id: str
    title: str
    description: str
    organization: str
    formats: list[str]
    tags: list[str]
    created_at: str
    modified_at: str
    resource_count: int
    has_downloadable: bool

@dataclass
class SearchResult:
    dataset: CachedDataset
    relevance_score: float
    matched_keywords: list[str]
    match_reason: str

@dataclass
class Suggestion:
    datasets: list[SearchResult]
    explanation: str
    total_alternatives: int
```

### API Contracts

**New MCP Tools:**

```python
@mcp.tool()
async def intelligent_search(
    query: str,
    suggest_alternatives: bool = True,
    max_results: int = 10
) -> dict[str, Any]:
    """Search datasets with semantic understanding and fallback suggestions."""

@mcp.tool()
async def preview_dataset(
    dataset_id: str
) -> dict[str, Any]:
    """Show dataset info with data preview (first 10 rows)."""

@mcp.tool()
async def refresh_catalog(
    force: bool = False
) -> dict[str, Any]:
    """Refresh dataset catalog cache."""
```

### Caching Strategy

**Storage Format:** JSON (human-readable, easy debugging)
```json
{
  "version": "1.0",
  "built_at": "2025-01-10T12:00:00Z",
  "total_datasets": 3430,
  "datasets": [...]
}
```

**Refresh Policy:**
- Server startup: check cache age
- If cache >24 hours old: refresh in background
- Manual refresh via `refresh_catalog()` tool
- Force refresh with `force=True` parameter

**Cache Location:**
```
~/.serbian-data-mcp/cache/catalog.json
```

### Search Algorithms

**Query Expansion:**
1. Tokenize input query
2. Expand with synonyms (age → [age, years, staros])
3. Translate to Serbian (population → stanovništvo)
4. Add related terms (demographics → census, registry, statistics)

**Keyword Matching:**
```python
def calculate_relevance(dataset: CachedDataset, query_terms: list[str]) -> float:
    score = 0.0
    
    # Title match (highest weight)
    if any(term in dataset.title.lower() for term in query_terms):
        score += 0.5
        
    # Description match
    if any(term in dataset.description.lower() for term in query_terms):
        score += 0.3
        
    # Tags match
    if any(term in dataset.tags for term in query_terms):
        score += 0.2
        
    return score
```

**Fuzzy Matching:**
- Use Levenshtein distance for typos
- Threshold: 2 characters for short words, 3 for long words

**Language Awareness:**
- Parallel Serbian/English dictionaries
- Auto-detect query language
- Search in both languages

---

## 4. Non-Functional Requirements

### Performance
- Catalog build: <60 seconds (3,430 datasets via API pagination)
- Search queries: <500ms from cached catalog
- Dataset preview: <3 seconds (if downloadable)

### Scalability
- Handle 3,430+ datasets
- Support concurrent search requests
- Efficient memory usage (<100MB for catalog)

### Maintainability
- Clear module separation
- Comprehensive tests (unit + integration)
- Type hints throughout
- Documentation for all algorithms

### Availability
- Server startup succeeds even if catalog building fails
- Graceful degradation to API-only mode if cache unavailable
- Background refresh without blocking server

---

## 5. Technical Constraints

### Environment
- Python 3.11+
- FastMCP 3.4.2 (latest API)
- Async/await patterns only
- Pydantic V2 for data validation

### External Dependencies
- data.gov.rs API (rate limits apply)
- No external ML/NLP services (keep lightweight)

### Compatibility
- Must work with existing MCP tools
- No breaking changes to current API
- SSE transport mode (port 8001)

---

## 6. Implementation Phases

### Phase 1: Catalog Builder (Foundation)
- DatasetCatalog class
- API pagination to fetch all datasets
- JSON cache persistence
- Refresh logic

### Phase 2: Semantic Search
- QueryExpander module
- SearchEngine with relevance scoring
- Language awareness
- Fuzzy matching

### Phase 3: Enhanced MCP Tools
- intelligent_search tool
- preview_dataset tool
- Alternative suggestions

### Phase 4: Testing & Validation
- Unit tests for all modules
- Integration tests with real API
- Performance benchmarks
- End-to-end validation

---

## 7. Success Validation

### Functional Tests
```python
# Test semantic understanding
assert await intelligent_search("age data") returns population datasets
assert await intelligent_search("stanovništvo") returns same as "population"

# Test alternative suggestions
result = await intelligent_search("nonexistent term")
assert result["suggestions"] > 0
assert result["explanation"] is not None

# Test dataset preview
preview = await preview_dataset(dataset_id)
assert preview["sample_data"] or preview["error"] is clear
```

### Performance Tests
```python
# Catalog build
assert time_to_build_catalog() < 60 seconds

# Search speed
assert time_to_search() < 500ms

# Memory usage
assert catalog_memory_footprint() < 100MB
```

### Integration Tests
```bash
# Start server
./start_server.sh

# Connect via MCP client
# Test: intelligent_search("population by age")
# Verify: Returns relevant datasets with explanations
```

---

## 8. Risk Mitigation

### API Rate Limits
**Risk:** data.gov.rs may rate limit during catalog build
**Mitigation:**
- Exponential backoff in pagination
- Progress checkpointing (resume if interrupted)
- Background refresh without blocking

### Cache Invalidation
**Risk:** Stale cache if datasets change
**Mitigation:**
- Daily refresh by default
- Manual refresh available
- Check dataset `modified_at` timestamps

### False Positives
**Risk:** Irrelevant suggestions due to keyword matching
**Mitigation:**
- Minimum relevance threshold (0.3)
- Relevance scoring tuning
- User feedback loop (future)

---

## 9. Open Questions

1. **Exact synonym lists:** Need comprehensive Serbian↔English term dictionary
2. **Relevance tuning:** May need adjustment based on real usage
3. **Cache location:** Should it be configurable? Currently `~/.serbian-data-mcp/`

---

## 10. Next Steps

**Phase 1 (Planning):** Create implementation plan with task breakdown

**Phase 2 (Execution):** Build modules in priority order:
1. DatasetCatalog (enables everything else)
2. QueryExpander (language awareness)
3. SearchEngine (semantic search)
4. AlternativeSuggestions (fallback)
5. Enhanced MCP tools (user-facing)

**Phase 3 (QA):** Comprehensive testing

**Phase 4 (Validation):** Multi-perspective review

---

**Specification approved by:** Autopilot Phase 0
**Ready for Phase 1:** Architect creates implementation plan
