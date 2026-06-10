## Handoff: Phase 1 (Planning) → Phase 2 (Execution)

**Date:** 2025-01-10
**Transition:** Planning → Implementation

---

### Decided

**Architecture:**
- Module structure: `catalog/` for cache/search/suggestions, `intelligence/` for query expansion
- Data models: `CachedDataset`, `SearchResult`, `Suggestion` dataclasses
- Storage: JSON cache at `~/.serbian-data-mcp/cache/catalog.json`
- Refresh policy: 24-hour auto-refresh, manual via `refresh_catalog()` tool

**Implementation Strategy:**
- Sequential foundation: Task 1 (structure) → Task 2 (DatasetCatalog)
- Parallel after foundation: Tasks 3-5 (search modules) can run concurrently
- TDD approach: Write tests alongside implementation (Task 8)

**API Contracts:**
- `intelligent_search(query, suggest_alternatives=True, max_results=10)`
- `preview_dataset(dataset_id)`
- `refresh_catalog(force=False)`

**Search Algorithm:**
- Relevance scoring: title (0.5) + description (0.3) + tags (0.2)
- Query expansion: synonyms + Serbian↔English translations
- Fuzzy matching: Levenshtein distance (threshold: 2-3 chars)

---

### Rejected

**Rejected: Machine Learning / NLP libraries**
- **Reason:** Keep lightweight, no external ML dependencies
- **Alternative:** Simple synonym-based expansion, keyword matching

**Rejected: Redis caching**
- **Reason:** Overkill for single-server use case
- **Alternative:** JSON file cache (simpler, human-readable)

**Rejected: Real-time API search**
- **Reason:** Rate limits, slow responses
- **Alternative:** Search cached catalog only

---

### Risks

**API Rate Limits (MEDIUM):**
- Catalog build may hit data.gov.rs rate limits
- **Mitigation:** Exponential backoff (1s, 2s, 4s, 8s), progress checkpointing

**Poor Relevance Scoring (MEDIUM):**
- Search may return irrelevant datasets
- **Mitigation:** 0.3 minimum score threshold, manual tuning based on testing

**Cache Corruption (LOW):**
- Invalid cache could crash server
- **Mitigation:** JSON validation on load, fallback to API-only mode

---

### Files Created

**Phase 0:**
- `.omc/autopilot/spec.md` - Requirements & architecture specification

**Phase 1:**
- `.omc/plans/autopilot-impl.md` - Detailed implementation plan with 10 tasks
- `.omc/handoffs/phase1-phase2.md` - This handoff document

---

### Remaining for Phase 2

**Implementation Tasks (10 total):**
1. Create catalog module structure (30 min)
2. Implement DatasetCatalog class (60 min)
3. Implement SearchEngine module (90 min)
4. Implement QueryExpansion (60 min)
5. Implement AlternativeSuggestions (45 min)
6. Implement DatasetPreview (60 min)
7. Implement Enhanced MCP tools (60 min)
8. Add unit tests (90 min)
9. Add integration tests (60 min)
10. Performance validation (30 min)

**Total Effort:** ~5-6 hours with parallelization

**Execution Strategy:**
- Use Ralph mode for persistence and retry logic
- Spawn Ultrawork agents for parallel implementation
- Start with sequential foundation (Tasks 1-2)
- Parallelize independent work (Tasks 3-6, 8-9)

---

### Key Files to Modify

**New Files to Create:**
- `src/serbian_data_mcp/catalog/__init__.py`
- `src/serbian_data_mcp/catalog/cache.py`
- `src/serbian_data_mcp/catalog/search.py`
- `src/serbian_data_mcp/catalog/suggestions.py`
- `src/serbian_data_mcp/catalog/preview.py`
- `src/serbian_data_mcp/catalog/models.py`
- `src/serbian_data_mcp/intelligence/__init__.py`
- `src/serbian_data_mcp/intelligence/query_expander.py`
- `tests/test_catalog.py`
- `tests/test_search.py`
- `tests/test_intelligence.py`
- `tests/test_suggestions.py`
- `tests/test_integration_catalog.py`

**Files to Modify:**
- `src/serbian_data_mcp/tools.py` - Add new MCP tools

---

### Quality Gates

**Before Moving to Phase 3 (QA):**
- [ ] All 10 implementation tasks completed
- [ ] Unit tests pass (pytest tests/test_*.py)
- [ ] Integration tests pass (requires network)
- [ ] Code has type hints throughout
- [ ] No breaking changes to existing MCP tools

**Before Moving to Phase 4 (Validation):**
- [ ] Performance benchmarks pass (catalog build <60s, search <500ms)
- [ ] Memory footprint <100MB
- [ ] Server starts successfully in SSE mode

---

### Contact

**Plan created by:** Autopilot Phase 1 (Architect)
**Questions:** Review `.omc/plans/autopilot-impl.md` for full task breakdown
**Next:** Phase 2 execution begins with Ralph + Ultrawork agents

---

**End of Handoff**
