"""Offline unit tests for tools/analysis.py — the data_profiling MCP tool surface.

Covers ``data_profile`` which shipped with zero direct test coverage. It is pure
pandas (no network, no catalog/client dependency), so the tests are fully
deterministic and assert the exact profiling contract: column dtypes, null
counts, unique counts, sample sizing, and numeric-only min/max/mean/median.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp.exceptions import ToolError

from serbian_data_mcp.tools import analysis as analysis_mod
from serbian_data_mcp.tools.analysis import (
    benchmark_data,
    compare_cross_dataset,
    compute_metrics,
    data_profile,
    extract_data_insights,
    forecast_data,
    generate_data_narrative,
)
from serbian_data_mcp.viz import forecast as forecast_mod


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


# ---------------------------------------------------------------------------
# Wrapper tools (extract_data_insights / generate_data_narrative / compute_metrics
# / forecast_data / benchmark_data / compare_cross_dataset)
#
# These 6 tools are thin wrappers over viz.insights / viz.forecast functions.
# The wrapper contract worth locking: (a) kwargs pass through to the viz fn,
# (b) viz exceptions are wrapped in ToolError with a descriptive prefix, and
# (c) for extract_data_insights the post-processing envelope (max_insights
# clamping + severity_summary counting) is computed from the raw insight list.
# The viz functions themselves are exercised elsewhere; here we stand them up
# with capturing fakes so the wrapper layer is deterministic and offline.
# ---------------------------------------------------------------------------


class _Fake:
    """Configurable stand-in for a viz function: captures calls, returns preset or raises."""

    def __init__(self, return_value: Any = None, exc: Exception | None = None) -> None:
        self.return_value = return_value
        self.exc = exc
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append({"args": args, "kwargs": kwargs})
        if self.exc is not None:
            raise self.exc
        return self.return_value


# --- extract_data_insights ------------------------------------------------


@pytest.mark.asyncio
async def test_extract_data_insights_envelope_and_clamp(monkeypatch: pytest.MonkeyPatch) -> None:
    """max_insights slices the list; severity_summary counts only the kept slice."""
    raw = [
        {"headline": "A", "severity": "critical"},
        {"headline": "B", "severity": "high"},
        {"headline": "C", "severity": "low"},
    ]
    fake = _Fake(return_value=raw)
    monkeypatch.setattr(analysis_mod, "extract_insights", fake)

    result = await extract_data_insights([{"x": 1}], time_column="year", entity_column="city", max_insights=2)

    assert result["total_found"] == 3  # counts the full raw list, not the clamped slice
    assert len(result["insights"]) == 2  # clamped to max_insights
    assert result["headline"] == "A"  # headline is top[0]
    assert result["severity_summary"] == {"critical": 1, "high": 1, "medium": 0, "low": 0}
    # Kwargs pass through verbatim.
    assert fake.calls[0]["kwargs"] == {"time_column": "year", "entity_column": "city"}


@pytest.mark.asyncio
async def test_extract_data_insights_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(analysis_mod, "extract_insights", _Fake(return_value=[]))
    result = await extract_data_insights([{"x": 1}])
    assert result["insights"] == []
    assert result["total_found"] == 0
    assert result["headline"] == ""  # no top[0] → empty string, not an IndexError


@pytest.mark.asyncio
async def test_extract_data_insights_wraps_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(analysis_mod, "extract_insights", _Fake(exc=ValueError("boom")))
    with pytest.raises(ToolError, match="Insight extraction failed"):
        await extract_data_insights([{"x": 1}])


# --- generate_data_narrative ---------------------------------------------


@pytest.mark.asyncio
async def test_generate_data_narrative_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    narrative = {"title": "T", "headline": "H", "big_number": "42", "summary": "s"}
    fake = _Fake(return_value=narrative)
    monkeypatch.setattr(analysis_mod, "generate_narrative", fake)

    result = await generate_data_narrative([{"x": 1}], title="T", time_column="year", max_insights=5)

    assert result is narrative  # wrapper returns the viz dict untouched
    assert fake.calls[0]["kwargs"] == {
        "title": "T",
        "time_column": "year",
        "entity_column": None,
        "max_insights": 5,
    }


@pytest.mark.asyncio
async def test_generate_data_narrative_wraps_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(analysis_mod, "generate_narrative", _Fake(exc=RuntimeError("nope")))
    with pytest.raises(ToolError, match="Narrative generation failed"):
        await generate_data_narrative([{"x": 1}])


# --- compute_metrics -----------------------------------------------------


@pytest.mark.asyncio
async def test_compute_metrics_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    metrics = {"yoy_changes": {}, "per_capita": {}, "growth_rates": {}, "index_values": {}, "derived_data": []}
    fake = _Fake(return_value=metrics)
    monkeypatch.setattr(analysis_mod, "compute_derived_metrics", fake)

    result = await compute_metrics(
        [{"x": 1}],
        time_column="year",
        entity_column="city",
        population_column="pop",
    )

    assert result is metrics
    assert fake.calls[0]["kwargs"] == {
        "time_column": "year",
        "entity_column": "city",
        "population_column": "pop",
    }


@pytest.mark.asyncio
async def test_compute_metrics_wraps_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(analysis_mod, "compute_derived_metrics", _Fake(exc=KeyError("missing")))
    with pytest.raises(ToolError, match="Metric computation failed"):
        await compute_metrics([{"x": 1}])


# --- forecast_data (viz func imported inside the body) -------------------


@pytest.mark.asyncio
async def test_forecast_data_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    out = {"forecast_data": [], "growth_rate": 0.1, "r_squared": 0.9}
    fake = _Fake(return_value=out)
    monkeypatch.setattr(forecast_mod, "forecast_linear", fake)

    result = await forecast_data(
        [{"year": 2020, "v": 1}],
        time_column="year",
        value_column="v",
        periods_ahead=7,
        method="exponential",
    )

    assert result is out
    assert fake.calls[0]["kwargs"] == {
        "time_column": "year",
        "value_column": "v",
        "periods_ahead": 7,
        "method": "exponential",
    }


@pytest.mark.asyncio
async def test_forecast_data_wraps_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(forecast_mod, "forecast_linear", _Fake(exc=ValueError("bad")))
    with pytest.raises(ToolError, match="Forecast failed"):
        await forecast_data([{"year": 2020, "v": 1}], time_column="year", value_column="v")


# --- benchmark_data ------------------------------------------------------


@pytest.mark.asyncio
async def test_benchmark_data_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    out = {"comparisons": [], "best_performer": {}, "worst_performer": {}, "insights": []}
    fake = _Fake(return_value=out)
    monkeypatch.setattr(forecast_mod, "benchmark_comparison", fake)

    benchmarks = {"EU average": 50000.0}
    result = await benchmark_data(
        [{"city": "BG", "gdp": 60000}],
        value_column="gdp",
        entity_column="city",
        benchmarks=benchmarks,
    )

    assert result is out
    assert fake.calls[0]["kwargs"] == {
        "value_column": "gdp",
        "entity_column": "city",
        "benchmarks": benchmarks,
    }


@pytest.mark.asyncio
async def test_benchmark_data_wraps_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(forecast_mod, "benchmark_comparison", _Fake(exc=ValueError("bad")))
    with pytest.raises(ToolError, match="Benchmark failed"):
        await benchmark_data([{"city": "BG", "gdp": 1}], value_column="gdp", entity_column="city")


# --- compare_cross_dataset ----------------------------------------------


@pytest.mark.asyncio
async def test_compare_cross_dataset_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    out = {"summary_a": {}, "summary_b": {}, "correlation": 0.5, "insights": []}
    fake = _Fake(return_value=out)
    monkeypatch.setattr(forecast_mod, "cross_dataset_insights", fake)

    result = await compare_cross_dataset(
        [{"city": "BG", "pop": 100}],
        [{"city": "BG", "aqi": 50}],
        value_column_a="pop",
        value_column_b="aqi",
        label_a="Population",
        label_b="Air",
    )

    assert result is out
    assert fake.calls[0]["kwargs"] == {
        "value_column_a": "pop",
        "value_column_b": "aqi",
        "entity_column_a": None,
        "entity_column_b": None,
        "label_a": "Population",
        "label_b": "Air",
    }


@pytest.mark.asyncio
async def test_compare_cross_dataset_wraps_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(forecast_mod, "cross_dataset_insights", _Fake(exc=ValueError("bad")))
    with pytest.raises(ToolError, match="Cross-dataset comparison failed"):
        await compare_cross_dataset(
            [{"city": "BG", "pop": 1}],
            [{"city": "BG", "aqi": 1}],
            value_column_a="pop",
            value_column_b="aqi",
        )
