"""Analysis and profiling tools.

Contracts:
  - data_profile(data) → column names, types, stats, samples
  - extract_data_insights(data) → surprising findings with severity
  - compute_metrics(data) → YoY, per-capita, growth rates, index values
"""

from __future__ import annotations

from typing import Any, Optional

from fastmcp.exceptions import ToolError

from .. import mcp
from ..viz.insights import extract_insights, generate_narrative, compute_derived_metrics
from . import _helpers as h


@mcp.tool()
async def data_profile(data: list[dict[str, Any]], sample_size: int = 5) -> dict[str, Any]:
    """Understand data structure BEFORE creating charts or transforming.

    Returns column names, types, unique counts, null counts, sample values.
    For numeric columns: min, max, mean, median.

    ALWAYS use after get_resource_data() and before create_chart() to choose correct columns.

    Returns: {columns: [{name, dtype, non_null, null_count, unique, sample_values, min?, max?, mean?, median?}],
              total_rows, total_columns, memory_usage}

    Args:
        data: Row dicts from get_resource_data()
        sample_size: Sample values per column (default 5)
    """
    if not data:
        raise ToolError("Empty dataset — pass data from get_resource_data()")

    import numpy as np
    import pandas as pd

    df = pd.DataFrame(data)
    columns = []
    for col in df.columns:
        col_info: dict[str, Any] = {
            "name": col,
            "dtype": str(df[col].dtype),
            "non_null": int(df[col].count()),
            "null_count": int(df[col].isna().sum()),
            "unique": int(df[col].nunique()),
            "sample_values": df[col].dropna().head(sample_size).tolist(),
        }
        if df[col].dtype in ("int64", "float64"):
            col_info["min"] = float(df[col].min()) if pd.notna(df[col].min()) else None
            col_info["max"] = float(df[col].max()) if pd.notna(df[col].max()) else None
            col_info["mean"] = float(df[col].mean()) if pd.notna(df[col].mean()) else None
            col_info["median"] = float(df[col].median()) if pd.notna(df[col].median()) else None
        columns.append(col_info)

    return {
        "columns": columns,
        "total_rows": len(data),
        "total_columns": len(df.columns),
        "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB",
    }


@mcp.tool()
async def extract_data_insights(
    data: list[dict[str, Any]],
    time_column: Optional[str] = None,
    entity_column: Optional[str] = None,
    max_insights: int = 10,
) -> dict[str, Any]:
    """Extract surprising findings from data: extremes, trends, outliers, inequality.

    Each insight has severity (critical/high/medium/low), headline, and narrative.
    Sorted by severity. Use AFTER data_profile() to identify time/entity columns.

    Returns: {insights: [...], total_found, headline, severity_summary}

    Args:
        data: Row dicts from get_resource_data()
        time_column: Column with years/dates for temporal analysis
        entity_column: Column with entity names (cities, districts)
        max_insights: Max insights (default 10)
    """
    try:
        insights = extract_insights(data, time_column=time_column, entity_column=entity_column)
        top = insights[:max_insights]
        return {
            "insights": top,
            "total_found": len(insights),
            "headline": top[0].get("headline", "") if top else "",
            "severity_summary": {
                sev: sum(1 for i in top if i.get("severity") == sev) for sev in ("critical", "high", "medium", "low")
            },
        }
    except Exception as e:
        raise ToolError(f"Insight extraction failed: {e}") from e


@mcp.tool()
async def generate_data_narrative(
    data: list[dict[str, Any]],
    title: str = "",
    time_column: Optional[str] = None,
    entity_column: Optional[str] = None,
    max_insights: int = 5,
) -> dict[str, Any]:
    """Generate a data story: headline, big number, narrative text.

    Returns: {title, headline, big_number, big_label, insights, summary}

    Args:
        data: Row dicts from get_resource_data()
        title: Story topic
        time_column: Optional time column
        entity_column: Optional entity column
        max_insights: Max insights in narrative
    """
    try:
        return generate_narrative(
            data,
            title=title,
            time_column=time_column,
            entity_column=entity_column,
            max_insights=max_insights,
        )
    except Exception as e:
        raise ToolError(f"Narrative generation failed: {e}") from e


@mcp.tool()
async def compute_metrics(
    data: list[dict[str, Any]],
    time_column: Optional[str] = None,
    entity_column: Optional[str] = None,
    population_column: Optional[str] = None,
) -> dict[str, Any]:
    """Compute derived metrics: YoY changes, per-capita, growth rates, index (base=100).

    Returns: {yoy_changes, per_capita, growth_rates, index_values, derived_data}

    Args:
        data: Row dicts
        time_column: Temporal column for YoY/growth
        entity_column: Entity names for per-entity breakdown
        population_column: Population counts for per-capita
    """
    try:
        return compute_derived_metrics(
            data,
            time_column=time_column,
            entity_column=entity_column,
            population_column=population_column,
        )
    except Exception as e:
        raise ToolError(f"Metric computation failed: {e}") from e


@mcp.tool()
async def forecast_data(
    data: list[dict[str, Any]],
    time_column: str,
    value_column: str,
    periods_ahead: int = 5,
    method: str = "linear",
) -> dict[str, Any]:
    """Forecast future values using regression. 'At this rate, X by 2030.'

    Returns: {forecast_data, growth_rate, projection_note, r_squared, historical_data, trend_line}

    Args:
        data: Row dicts with time series
        time_column: Time ordering column
        value_column: Column to forecast
        periods_ahead: Future periods to predict
        method: 'linear' or 'exponential'
    """
    from ..viz.forecast import forecast_linear

    try:
        return forecast_linear(
            data,
            time_column=time_column,
            value_column=value_column,
            periods_ahead=periods_ahead,
            method=method,
        )
    except Exception as e:
        raise ToolError(f"Forecast failed: {e}") from e


@mcp.tool()
async def benchmark_data(
    data: list[dict[str, Any]],
    value_column: str,
    entity_column: str,
    benchmarks: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    """Compare against benchmarks (EU average, regional, custom).

    Returns: {statistical_benchmarks, best_performer, worst_performer, comparisons, insights}

    Args:
        data: Row dicts
        value_column: Numeric column to benchmark
        entity_column: Entity names
        benchmarks: {benchmark_name: value}, e.g. {"EU average": 50000}
    """
    from ..viz.forecast import benchmark_comparison

    try:
        return benchmark_comparison(
            data,
            value_column=value_column,
            entity_column=entity_column,
            benchmarks=benchmarks,
        )
    except Exception as e:
        raise ToolError(f"Benchmark failed: {e}") from e


@mcp.tool()
async def compare_cross_dataset(
    data_a: list[dict[str, Any]],
    data_b: list[dict[str, Any]],
    value_column_a: str,
    value_column_b: str,
    entity_column_a: Optional[str] = None,
    entity_column_b: Optional[str] = None,
    label_a: str = "Dataset A",
    label_b: str = "Dataset B",
) -> dict[str, Any]:
    """Extract insights by comparing two related datasets.

    Finds correlations, divergences, and rank disagreements.
    Ideal for: 'population vs air quality' analyses.

    Returns: {summary_a, summary_b, correlation, insights}

    Args:
        data_a: First dataset
        data_b: Second dataset
        value_column_a: Numeric column in first dataset
        value_column_b: Numeric column in second dataset
        entity_column_a: Entity column in first dataset
        entity_column_b: Entity column in second dataset
        label_a: Label for first dataset
        label_b: Label for second dataset
    """
    from ..viz.forecast import cross_dataset_insights

    try:
        return cross_dataset_insights(
            data_a,
            data_b,
            value_column_a=value_column_a,
            value_column_b=value_column_b,
            entity_column_a=entity_column_a,
            entity_column_b=entity_column_b,
            label_a=label_a,
            label_b=label_b,
        )
    except Exception as e:
        raise ToolError(f"Cross-dataset comparison failed: {e}") from e
