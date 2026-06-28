"""Offline unit tests for tools/analysis.py — the data_profiling MCP tool surface.

Covers ``data_profile`` which shipped with zero direct test coverage. It is pure
pandas (no network, no catalog/client dependency), so the tests are fully
deterministic and assert the exact profiling contract: column dtypes, null
counts, unique counts, sample sizing, and numeric-only min/max/mean/median.
"""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from serbian_data_mcp.tools.analysis import data_profile


# ---------------------------------------------------------------------------
# data_profile
# ---------------------------------------------------------------------------


def _col(profile: dict, name: str) -> dict:
    """Pull a single column info dict out of a data_profile result."""
    return next(c for c in profile["columns"] if c["name"] == name)


@pytest.mark.asyncio
async def test_data_profile_empty_raises_tool_error() -> None:
    """Empty dataset must surface a ToolError, not a pandas edge-case result."""
    with pytest.raises(ToolError, match="Empty dataset"):
        await data_profile([])


@pytest.mark.asyncio
async def test_data_profile_numeric_column_reports_stats() -> None:
    data = [
        {"city": "BG", "pop": 210},
        {"city": "NS", "pop": 80},
        {"city": "NI", "pop": 100},
    ]
    profile = await data_profile(data)

    pop = _col(profile, "pop")
    assert pop["min"] == 80.0
    assert pop["max"] == 210.0
    assert pop["mean"] == pytest.approx(130.0)
    assert pop["median"] == pytest.approx(100.0)
    assert pop["non_null"] == 3
    assert pop["null_count"] == 0
    assert pop["unique"] == 3


@pytest.mark.asyncio
async def test_data_profile_text_column_omits_numeric_stats() -> None:
    data = [{"city": "BG"}, {"city": "NS"}, {"city": "BG"}]
    profile = await data_profile(data)

    city = _col(profile, "city")
    # Non-numeric dtype → no min/max/mean/median keys emitted.
    for key in ("min", "max", "mean", "median"):
        assert key not in city
    assert city["unique"] == 2
    assert city["null_count"] == 0


@pytest.mark.asyncio
async def test_data_profile_null_counts() -> None:
    data = [
        {"city": "BG", "pop": 210},
        {"city": "NS", "pop": None},
        {"city": "BG", "pop": 80},
    ]
    profile = await data_profile(data)

    pop = _col(profile, "pop")
    assert pop["non_null"] == 2
    assert pop["null_count"] == 1
    # Sample values skip the null row.
    assert None not in pop["sample_values"]


@pytest.mark.asyncio
async def test_data_profile_sample_size_honored() -> None:
    data = [{"city": f"c{i}", "pop": i} for i in range(10)]
    profile = await data_profile(data, sample_size=3)

    city = _col(profile, "city")
    assert len(city["sample_values"]) == 3
    assert city["sample_values"] == ["c0", "c1", "c2"]


@pytest.mark.asyncio
async def test_data_profile_top_level_shape() -> None:
    data = [{"city": "BG", "pop": 210, "year": 2020}]
    profile = await data_profile(data)

    assert profile["total_rows"] == 1
    assert profile["total_columns"] == 3
    assert isinstance(profile["memory_usage"], str)
    assert profile["memory_usage"].endswith(" KB")
    assert len(profile["columns"]) == 3
    # Every column info carries the base keys regardless of dtype.
    for col in profile["columns"]:
        assert {"name", "dtype", "non_null", "null_count", "unique", "sample_values"} <= set(col)


@pytest.mark.asyncio
async def test_data_profile_dtype_reporting() -> None:
    data = [{"city": "BG", "pop": 210, "year": 2020}]
    profile = await data_profile(data)

    assert _col(profile, "city")["dtype"] == "str"
    assert _col(profile, "pop")["dtype"] == "int64"
    assert _col(profile, "year")["dtype"] == "int64"
