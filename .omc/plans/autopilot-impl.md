# Implementation Plan: Intelligent Serbian Data MCP Server

**Phase 1 Output: Implementation Plan**
**Created:** 2025-01-10
**Status:** Ready for Execution

---

## Overview

Transform the Serbian Data MCP server from a thin API wrapper into an intelligent discovery engine through catalog caching, semantic search, and alternative suggestions.

**Total Estimated Effort:** 4-6 hours
**Critical Path:** Catalog Builder → Search Engine → Enhanced Tools

---

## Task Breakdown

### Task 1: Create Catalog Module Structure
**Priority:** HIGH (BLOCKS ALL OTHER TASKS)
**Estimated:** 30 minutes
**Dependencies:** None

**Steps:**
1. Create `src/serbian_data_mcp/catalog/` directory
2. Create module files:
   - `__init__.py` (exports)
   - `cache.py` (DatasetCatalog class)
   - `models.py` (CachedDataset, SearchResult dataclasses)
   - `exceptions.py` (Catalog-specific exceptions)
3. Add type hints throughout

**Verification:**
```python
from serbian_data_mcp.catalog import DatasetCatalog, CachedDataset
# Should import without errors
```

---

### Task 2: Implement DatasetCatalog Class
**Priority:** HIGH
**Estimated:** 60 minutes
**Dependencies:** Task 1

**Steps:**
1. `DatasetCatalog.__init__()`:
   - Set cache path: `~/.serbian-data-mcp/cache/catalog.json`
   - Initialize empty dataset index

2. `DatasetCatalog.build_catalog()`:
   - Fetch all datasets via API pagination (100 per page)
   - Extract: ID, title, description, organization, formats, tags
   - Implement exponential backoff for API rate limits
   - Save to JSON cache with metadata (version, built_at, total)

3. `DatasetCatalog.load_cache()`:
   - Load from JSON if exists and <24 hours old
   - Return False if cache missing/expired

4. `DatasetCatalog.refresh()`:
   - Check dataset `modified_at` timestamps
   - Only update changed datasets (incremental refresh)

**Implementation Details:**
```python
class DatasetCatalog:
    def __init__(self, cache_path: Path | None = None):
        self.cache_path = cache_path or Path.home() / ".serbian-data-mcp" / "cache" / "catalog.json"
        self.datasets: dict[str, CachedDataset] = {}
        
    async def initialize(self) -> None:
        """Load cache or build catalog."""
        if not await self._load_cache():
            await self.build_catalog()
            
    async def build_catalog(self) -> None:
        """Fetch all datasets from API and index them."""
        # API pagination with exponential backoff
        # Save to JSON cache
        
    async def _load_cache(self) -> bool:
        """Load from cache if fresh."""
        # Check file exists and age <24h
        # Load JSON into self.datasets
```

**Verification:**
- Unit test: `test_catalog_build()` - builds catalog with mock API
- Integration test: `test_catalog_persistence()` - saves/loads from JSON

---

### Task 3: Implement Search Engine Module
**Priority:** HIGH
**Estimated:** 90 minutes
**Dependencies:** Task 2

**Steps:**
1. Create `src/serbian_data_mcp/catalog/search.py`

2. `SearchEngine.search()`:
   - Tokenize query into terms
   - Calculate relevance score for each dataset
   - Sort by score descending
   - Return top N results

3. Relevance scoring algorithm:
   ```python
   def calculate_relevance(dataset: CachedDataset, terms: list[str]) -> float:
       score = 0.0
       
       # Title match: highest weight (0.5)
       title_lower = dataset.title.lower()
       if any(term in title_lower for term in terms):
           score += 0.5
           
       # Description match: medium weight (0.3)
       desc_lower = dataset.description.lower()
       if any(term in desc_lower for term in terms):
           score += 0.3
           
       # Tags match: lower weight (0.2)
       if any(term in dataset.tags for term in terms):
           score += 0.2
           
       return score
   ```

4. Add fuzzy matching for typos:
   - Use Levenshtein distance
   - Threshold: 2 chars for short words (<5), 3 for long words

**Verification:**
- Unit test: `test_search_relevance()` - scores correct datasets higher
- Unit test: `test_search_fuzzy()` - handles typos

---

### Task 4: Implement Query Expansion
**Priority:** HIGH
**Estimated:** 60 minutes
**Dependencies:** Task 3

**Steps:**
1. Create `src/serbian_data_mcp/intelligence/` directory
2. Create `query_expander.py`

3. Build synonym dictionary:
   ```python
   SYNONYMS = {
       "age": ["age", "years", "staros", "godine"],
       "population": ["population", "stanovništvo", "ljudi", "broj stanovnika"],
       "demographics": ["demographics", "demografija", "popis", "census"]
   }
   ```

4. `QueryExpander.expand()`:
   - Tokenize input query
   - Replace terms with synonym sets
   - Add translations (Serbian ↔ English)
   - Remove duplicates
   - Return expanded term list

5. Language detection:
   - Simple heuristic: if any Serbian character (č, ć, ž, š, đ) → assume Serbian
   - Default: search in both languages

**Verification:**
- Unit test: `test_expansion_basic()` - "age" → ["age", "years", "staros", "godine"]
- Unit test: `test_expansion_translations()` - "stanovništvo" → includes "population"

---

### Task 5: Implement Alternative Suggestions
**Priority:** MEDIUM
**Estimated:** 45 minutes
**Dependencies:** Task 3, Task 4

**Steps:**
1. Create `src/serbian_data_mcp/catalog/suggestions.py`

2. `AlternativeSuggestionEngine.suggest()`:
   - When search returns 0 results:
     - Find datasets with partial keyword matches
     - Find datasets with semantic topic overlap
     - Return top 5 with explanations

3. Explanation generation:
   ```python
   def explain_suggestion(query: str, datasets: list[SearchResult]) -> str:
       if not datasets:
           return "No matching datasets found."
       
       # Analyze what keywords matched
       matched_keywords = set()
       for ds in datasets:
           matched_keywords.update(ds.matched_keywords)
       
       return f"No exact match for '{query}', but found {len(datasets)} datasets " \
              f"related to: {', '.join(sorted(matched_keywords))}"
   ```

**Verification:**
- Unit test: `test_suggestions_empty_search()` - returns alternatives when no results
- Unit test: `test_suggestion_explanation()` - generates clear explanations

---

### Task 6: Implement Dataset Preview
**Priority:** MEDIUM
**Estimated:** 60 minutes
**Dependencies:** Task 2

**Steps:**
1. Create `src/serbian_data_mcp/catalog/preview.py`

2. `DatasetPreview.preview()`:
   - Get dataset metadata from catalog
   - Find first CSV/JSON resource
   - Download first 10 rows
   - Return column names + sample data

3. Handle non-downloadable datasets:
   - Check resource formats
   - If no CSV/JSON: return metadata-only preview

**Implementation Details:**
```python
async def preview_dataset(dataset_id: str) -> dict[str, Any]:
    dataset = catalog.get(dataset_id)
    if not dataset:
        raise DatasetNotFound(dataset_id)
    
    # Find downloadable resource
    csv_resource = next(
        (r for r in dataset.resources if r.format == "csv"),
        None
    )
    
    if not csv_resource:
        return {"metadata": dataset, "sample": None, "reason": "No downloadable data"}
    
    # Download first 10 rows
    data = await client.get_resource_data(csv_resource.id, nrows=10)
    return {
        "metadata": dataset,
        "sample": data.head(10).to_dict(),
        "columns": list(data.columns)
    }
```

**Verification:**
- Integration test: `test_preview_csv()` - shows sample data
- Integration test: `test_preview_metadata_only()` - handles non-downloadable

---

### Task 7: Implement Enhanced MCP Tools
**Priority:** HIGH
**Estimated:** 60 minutes
**Dependencies:** Task 2, Task 3, Task 4, Task 5, Task 6

**Steps:**
1. Modify `src/serbian_data_mcp/tools.py`

2. Add `intelligent_search` tool:
   ```python
   @mcp.tool()
   async def intelligent_search(
       query: str,
       suggest_alternatives: bool = True,
       max_results: int = 10
   ) -> dict[str, Any]:
       """Search datasets with semantic understanding and fallback suggestions."""
       # 1. Initialize catalog (loads cache)
       # 2. Expand query with synonyms/translations
       # 3. Search catalog
       # 4. If no results and suggest_alternatives: find alternatives
       # 5. Return results with explanations
   ```

3. Add `preview_dataset` tool:
   ```python
   @mcp.tool()
   async def preview_dataset(dataset_id: str) -> dict[str, Any]:
       """Show dataset info with data preview (first 10 rows)."""
   ```

4. Add `refresh_catalog` tool:
   ```python
   @mcp.tool()
   async def refresh_catalog(force: bool = False) -> dict[str, Any]:
       """Refresh dataset catalog cache."""
   ```

**Verification:**
- Integration test: `test_intelligent_search()` - finds relevant datasets
- Integration test: `test_preview_tool()` - shows dataset preview

---

### Task 8: Add Unit Tests
**Priority:** MEDIUM
**Estimated:** 90 minutes
**Dependencies:** All implementation tasks

**Steps:**
1. Create `tests/test_catalog.py`:
   - `test_catalog_build()` - mock API pagination
   - `test_catalog_persistence()` - save/load JSON
   - `test_catalog_refresh()` - incremental updates

2. Create `tests/test_search.py`:
   - `test_search_relevance()` - scoring algorithm
   - `test_search_fuzzy()` - typo handling
   - `test_empty_results()` - returns empty list

3. Create `tests/test_intelligence.py`:
   - `test_query_expansion()` - synonym translation
   - `test_language_detection()` - Serbian/English

4. Create `tests/test_suggestions.py`:
   - `test_suggestions_generation()` - alternatives for empty search
   - `test_explanation_format()` - clear explanations

**Verification:**
```bash
pytest tests/test_catalog.py -v
pytest tests/test_search.py -v
pytest tests/test_intelligence.py -v
pytest tests/test_suggestions.py -v
# All tests pass
```

---

### Task 9: Add Integration Tests
**Priority:** MEDIUM
**Estimated:** 60 minutes
**Dependencies:** Task 8

**Steps:**
1. Create `tests/test_integration_catalog.py`:
   - Build real catalog from data.gov.rs
   - Verify 3,430+ datasets indexed
   - Test cache persistence

2. Create `tests/test_integration_search.py`:
   - Real queries: "age population", "stanovništvo", "budget"
   - Verify results are relevant
   - Test bilingual search

3. Create `tests/test_integration_tools.py`:
   - Test `intelligent_search` MCP tool
   - Test `preview_dataset` MCP tool
   - Test `refresh_catalog` MCP tool

**Verification:**
```bash
pytest tests/test_integration_*.py -v
# All integration tests pass (requires network)
```

---

### Task 10: Performance Validation
**Priority:** MEDIUM
**Estimated:** 30 minutes
**Dependencies:** Task 9

**Steps:**
1. Benchmark catalog build:
   ```python
   import time
   start = time.time()
   await catalog.build_catalog()
   duration = time.time() - start
   assert duration < 60, f"Catalog build took {duration}s (limit: 60s)"
   ```

2. Benchmark search speed:
   ```python
   start = time.time()
   results = await search_engine.search("population")
   duration = time.time() - start
   assert duration < 0.5, f"Search took {duration}s (limit: 0.5s)"
   ```

3. Memory footprint:
   ```python
   import tracemalloc
   tracemalloc.start()
   # Load catalog
   current, peak = tracemalloc.get_traced_memory()
   assert peak < 100_000_000  # 100MB
   ```

**Verification:**
- All benchmarks pass
- Document actual performance numbers

---

## Task Dependencies

```
Task 1 (Module Structure)
    ↓
Task 2 (DatasetCatalog) ← Task 6 (Preview) ┐
    ↓                                      │
Task 3 (SearchEngine) ← Task 4 (Expander) │
    ↓                                      │
Task 5 (Suggestions)                       │
    ↓                                      │
Task 7 (MCP Tools) ←────────────────────────┘
    ↓
Task 8 (Unit Tests)
    ↓
Task 9 (Integration Tests)
    ↓
Task 10 (Performance)
```

**Parallel Opportunities:**
- Tasks 2, 3, 4 can start after Task 1
- Tasks 5, 6 can run in parallel
- Task 8 can run alongside implementation (TDD)

---

## Risk Mitigation

### Risk 1: API Rate Limits During Catalog Build
**Impact:** Catalog build fails or takes too long
**Probability:** MEDIUM
**Mitigation:**
- Exponential backoff in pagination (1s, 2s, 4s, 8s)
- Progress checkpointing (save every 500 datasets)
- Resume capability if interrupted

### Risk 2: Cache Corruption
**Impact:** Server fails to load cached catalog
**Probability:** LOW
**Mitigation:**
- JSON schema validation on load
- Fallback to API-only mode if cache invalid
- Clear error messages for users

### Risk 3: Poor Relevance Scoring
**Impact:** Search returns irrelevant datasets
**Probability:** MEDIUM
**Mitigation:**
- Relevance threshold (0.3 minimum score)
- User feedback loop (future enhancement)
- Manual tuning based on testing

---

## Success Criteria

### Functional
- ✅ Catalog builds in <60 seconds
- ✅ Search returns <500ms from cache
- ✅ Bilingual queries work (Serbian/English)
- ✅ Alternative suggestions appear for empty results
- ✅ Dataset preview shows sample data

### Quality
- ✅ All tests pass (unit + integration)
- ✅ Code has type hints throughout
- ✅ No breaking changes to existing MCP tools
- ✅ Memory footprint <100MB

### Integration
- ✅ Server starts successfully
- ✅ `intelligent_search` tool works from MCP client
- ✅ SSE transport mode works (port 8001)

---

## Estimated Timeline

**Sequential:** ~9 hours (sum of all tasks)
**Parallel:** ~5-6 hours (independent tasks run concurrently)

### Breakdown
- Tasks 1-2 (Foundation): 90 min
- Tasks 3-5 (Search): 195 min → 120 min parallel
- Tasks 6-7 (Tools): 120 min
- Tasks 8-10 (Testing): 180 min → 90 min parallel with implementation

**Fastest Path:** 4-5 hours with aggressive parallelization

---

## Open Questions

1. **Synonym dictionary scope:** How extensive should the Serbian↔English dictionary be?
   - **Recommendation:** Start with 50 common terms, expand based on usage

2. **Cache refresh frequency:** Is daily refresh appropriate?
   - **Recommendation:** Start with 24h, make configurable

3. **Relevance threshold tuning:** What's the right minimum score?
   - **Recommendation:** Start with 0.3, adjust based on testing

---

## Next Steps

**Phase 2 (Execution):**
- Spawn executor agents for parallel implementation
- Begin with Tasks 1-2 (foundation) unblocked
- Run Tasks 3-5 in parallel after foundation ready
- Implement TDD: tests alongside code

**Phase 3 (QA):**
- Run all tests
- Fix failures in cycles
- Validate performance benchmarks

**Phase 4 (Validation):**
- Architect review: functional completeness
- Security review: SSRF, path traversal
- Code review: quality, style, maintainability

---

**Plan approved by:** Autopilot Phase 1
**Ready for Phase 2:** Execution begins
