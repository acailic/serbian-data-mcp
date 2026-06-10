# Stage 3: Visualization & Data Export Review

**Status**: ✅ COMPLETE
**Tier**: MEDIUM

## Findings

### [FINDING:V1] Safe Chart Implementation

**Severity**: NONE
**Confidence**: HIGH

**Assessment**: The `ChartBuilder` class uses Plotly Express and Graph Objects, which are safe for generating visualizations. No XSS or injection vulnerabilities found.

**Safety Features**:
- Plotly handles data sanitization automatically
- No arbitrary code execution
- Output is JSON-based plot data, not executable JavaScript

**Location**: `src/serbian_data_mcp/viz/charts.py`

---

### [FINDING:V2] No Path Traversal Risks in Charts

**Severity**: NONE
**Confidence**: HIGH

**Assessment**: Chart methods only accept column names and data from the DataFrame, not file paths or URLs. No path traversal vectors.

---

### [FINDING:V3] Exporters Path Traversal Risk

**Severity**: MEDIUM
**Confidence**: HIGH

**Issue**: Export functions use user-provided `filename` without validation, allowing path traversal attacks.

**Location**: `src/serbian_data_mcp/viz/exporters.py:26, 50, 70`

**Evidence**:
```python
filepath = output_dir / filename  # No validation of filename
fig.write_html(filepath, include_plotlyjs="cdn")
```

**Attack Vectors**:
- `filename = "../../etc/passwd"` - write outside export directory
- `filename = "../../../malicious.html"` - write to arbitrary locations
- `filename = ".hidden"` - create hidden files

**Impact**: Arbitrary file write within filesystem constraints.

**Fix Required**:
1. Sanitize filename: extract basename only
2. Validate no path separators in filename
3. Add file extension whitelist

---

### [FINDING:V4] No File Size Limits

**Severity**: LOW
**Confidence**: MEDIUM

**Issue**: No limits on export file sizes or chart complexity.

**Impact**: Large datasets could create:
- Huge HTML/JSON exports (memory/disk exhaustion)
- Long-running PNG exports (DoS)

**Recommendation**: Add size limits and timeout handling for exports.

---

### [FINDING:V5] HTML Export Safety

**Severity**: LOW
**Confidence**: HIGH

**Assessment**: HTML exports use Plotly CDN (`include_plotlyjs="cdn"`), which is safe.

**Note**: Plotly HTML is self-contained and doesn't execute arbitrary JavaScript from user data.

---

## Overall Assessment

**Visualization Safety**: 7/10
- Plotly usage is safe and appropriate
- No injection vulnerabilities in chart building
- **CRITICAL**: Path traversal in exporters must be fixed

**Recommendations**:
1. **URGENT**: Fix path traversal in all export functions
2. Add input validation for chart parameters
3. Implement size limits for datasets to prevent memory issues
4. Document max dataset sizes for each chart type
