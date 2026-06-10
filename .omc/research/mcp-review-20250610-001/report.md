# Code Review Report: Serbian Data MCP Server

**Session ID**: mcp-review-20250610-001  
**Date**: 2025-06-10  
**Status**: ✅ COMPLETE  
**Review Type**: Comprehensive Security, Quality, & Best Practices

---

## Executive Summary

**Overall Assessment**: 7.5/10 - Good foundation with critical security issues requiring immediate attention.

**Key Findings**:
- ✅ **Strengths**: Strong test coverage, proper error handling, good API safety practices
- ⚠️ **Critical Issues**: Path traversal vulnerability in exporters, duplicate close() call bug
- 🔧 **Improvements Needed**: Config validation, security tooling integration, type hints

**Immediate Actions Required**:
1. Fix path traversal in export functions (SECURITY)
2. Remove duplicate close() call (BUG)
3. Add config validation (QUALITY)

---

## Methodology

### Research Stages

| Stage | Focus | Tier | Status |
|-------|-------|------|--------|
| MCP Architecture & Safety | Protocol compliance, security patterns | HIGH | ✅ Complete |
| Code Quality & Best Practices | Type hints, testing, documentation | MEDIUM | ✅ Complete |
| Visualization & Data Export | Chart generation, export safety | MEDIUM | ✅ Complete |
| API Integration & Data Handling | HTTP client, data validation | HIGH | ✅ Complete |

### Approach
- Parallel scientist agents analyzed independent code areas
- Cross-validated findings across stages
- Evidence collected with file locations and code snippets
- Risk levels assigned based on impact and exploitability

---

## Critical Findings

### 🔴 CRITICAL: Path Traversal in Export Functions

**Risk**: HIGH  
**Confidence**: HIGH  
**Location**: `src/serbian_data_mcp/viz/exporters.py`

**Issue**: All three export functions (`export_html`, `export_png`, `export_json`) accept user-provided `filename` without validation, allowing path traversal attacks.

**Evidence**:
```python
# Line 26, 50, 70 - No validation of filename parameter
filepath = output_dir / filename
fig.write_html(filepath, include_plotlyjs="cdn")
```

**Attack Vector**:
```python
# Malicious filename allows writing outside export directory
export_html(fig, "../../etc/malicious", output_dir)
# Creates file: /etc/malicious
```

**Impact**: Arbitrary file write within filesystem constraints

**Fix Required**:
```python
# Add filename sanitization
from pathlib import Path

def sanitize_filename(filename: str) -> str:
    """Extract safe basename from filename."""
    # Remove path separators
    clean_name = Path(filename).name
    # Add extension if missing
    if not clean_name.endswith(('.html', '.png', '.json')):
        clean_name += '.html'
    return clean_name

filepath = output_dir / sanitize_filename(filename)
```

---

### 🟠 HIGH: Duplicate close() Call Bug

**Risk**: MEDIUM (causes runtime errors)  
**Confidence**: HIGH  
**Location**: `src/serbian_data_mcp/api/client.py:232`

**Issue**: `__aexit__` method calls `await self.close()` twice, causing error on cleanup.

**Evidence**:
```python
async def __aexit__(self, exc_type, exc_val, exc_tb):
    await self.close()  # Line 231
    await self.close()  # Line 232 - DUPLICATE, will raise error
```

**Impact**: Async context manager cleanup fails, potentially masking real errors or causing resource leaks.

**Fix**: Remove line 232.

---

### 🟡 MEDIUM: Config Validation Issues

**Risk**: MEDIUM  
**Confidence**: HIGH  
**Location**: `src/serbian_data_mcp/config.py`

**Issues**:
1. **Silent failure** (lines 36-37): JSON decode errors ignored
2. **No path validation**: `cache_dir`/`export_dir` not validated
3. **No range validation**: `timeout` could be negative

**Evidence**:
```python
except (json.JSONDecodeError, IOError):
    pass  # Silent failure - confusing for users
```

**Impact**:
- Invalid config silently ignored
- Cache/export could write to arbitrary locations
- Invalid timeouts cause runtime errors

**Fix**: Use existing `config_validation.py` module, add proper error reporting.

---

## High-Priority Findings

### API Integration Safety

**SSRF Protection Needed** (MEDIUM Risk)
- Resource URLs not validated before fetching
- Add domain whitelist for trusted sources

**Retry Logic Missing** (LOW Risk)
- No retry for transient failures (5xx, timeouts)
- Currently only handles 429 rate limiting

---

## Positive Findings

### ✅ Strong Test Coverage
Comprehensive test suite covering API, data parsing, and visualization.

### ✅ Excellent HTTP Client Safety
- Timeout protection configured
- Rate limiting implemented  
- Custom exception hierarchy
- Proper async context management (except duplicate bug)

### ✅ Pydantic Schema Validation
All API responses validated through Pydantic models.

### ✅ Good Error Messages
Custom exceptions provide helpful context and suggestions.

---

## Visualization Quality Assessment

### Strengths
- ✅ Plotly usage is safe and appropriate
- ✅ No XSS/injection vulnerabilities in chart generation
- ✅ Good chart variety (line, bar, pie, scatter, histogram, box)

### Issues Found
- 🔴 **Path traversal** in all export functions
- ⚠️ No file size limits (DoS risk)
- ⚠️ No dataset size validation

### Recommendations
1. Add filename sanitization (URGENT)
2. Implement max dataset sizes per chart type
3. Add export size limits and timeouts

---

## Security Analysis

### MCP Protocol Compliance
✅ Proper FastMCP usage, no custom protocol vulnerabilities

### Dependency Security
✅ All dependencies are well-maintained:
- `httpx` - modern async HTTP client
- `pydantic` - validation framework
- `fastmcp` - minimal MCP implementation

### Security Tooling
⚠️ `bandit` included but not integrated into CI/CD

### Input Validation
⚠️ Missing validation in:
- Export filenames (CRITICAL)
- Resource URLs (MEDIUM)
- Configuration values (MEDIUM)

---

## Code Quality Metrics

| Metric | Score | Notes |
|--------|-------|-------|
| Type Hints | 7/10 | Good coverage, some `Any` types |
| Error Handling | 9/10 | Excellent custom exceptions |
| Test Coverage | 9/10 | Comprehensive test suite |
| Documentation | 8/10 | Good docstrings, clear APIs |
| Code Organization | 8/10 | Clean modular structure |

---

## Recommendations

### Immediate (Security)

1. **Fix Path Traversal** (exporters.py)
   ```python
   filename = Path(filename).name  # Remove path components
   if not filename.endswith(('.html', '.png', '.json')):
       raise ValueError("Invalid file extension")
   ```

2. **Fix Duplicate close()** (client.py:232)
   ```python
   # Remove the duplicate line
   ```

3. **Add URL Whitelist** (client.py:168)
   ```python
   ALLOWED_DOMAINS = {'data.gov.rs', 'dataset.gov.rs'}
   if not any(resource.url.startswith(d) for d in ALLOWED_DOMAINS):
       raise SecurityError("Untrusted resource domain")
   ```

### High Priority (Quality)

4. **Activate Config Validation**
   - Use existing `config_validation.py`
   - Report config errors to user
   - Validate paths are within project

5. **Add Security Linting**
   ```bash
   make security  # Run bandit
   ```

6. **Add Export Limits**
   - Max file size: 10MB
   - Max chart data: 100K rows
   - Export timeout: 30s

### Medium Priority (Enhancement)

7. **Improve Type Hints**
   - Replace `Any` with specific types
   - Add TypedDict for data structures

8. **Add Retry Logic**
   - Exponential backoff for 5xx errors
   - Retry network timeouts

9. **Document Security Model**
   - Intended deployment scenarios
   - Permission boundaries
   - Resource quotas

---

## Risk Summary

| Severity | Count | Issues |
|----------|-------|--------|
| 🔴 CRITICAL | 1 | Path traversal |
| 🟠 HIGH | 1 | Duplicate close() bug |
| 🟡 MEDIUM | 3 | Config validation, SSRF protection, missing retry logic |
| 🟢 LOW | 4 | Type hints, security tooling, documentation, file size limits |

**Total Issues Found**: 9  
**Critical Security Issues**: 1  
**High-Priority Bugs**: 1  
**Medium-Priority Improvements**: 3

---

## Verification Status

✅ Cross-validation complete - findings consistent across stages  
✅ No contradictions between research stages  
✅ Evidence quality verified  
✅ Risk assessments validated

---

## Appendix

### Files Analyzed

**Core MCP**:
- `src/serbian_data_mcp/__init__.py`
- `src/serbian_data_mcp/__main__.py`
- `src/serbian_data_mcp/config.py`
- `src/serbian_data_mcp/exceptions.py`

**API Layer**:
- `src/serbian_data_mcp/api/client.py`
- `src/serbian_data_mcp/api/models.py`

**Visualization**:
- `src/serbian_data_mcp/viz/charts.py`
- `src/serbian_data_mcp/viz/exporters.py`

**Tests**:
- `tests/test_api.py`
- `tests/test_data.py`
- `tests/test_viz.py`
- `tests/test_config.py`

**Configuration**:
- `pyproject.toml`
- `README.md`

### Session State

See `.omc/research/mcp-review-20250610-001/state.json` for complete research session data.

---

**Report Generated**: 2025-06-10  
**Research Method**: sciomc parallel scientist workflow  
**Confidence Level**: HIGH  
**Next Review Recommended**: After critical fixes applied
