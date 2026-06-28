"""Forecasting, benchmarking, and cross-dataset analysis tools.

Provides simple statistical projections, EU/regional comparisons,
and multi-dataset insight extraction for deeper Serbian data analysis.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def forecast_linear(
    data: list[dict[str, Any]],
    time_column: str,
    value_column: str,
    periods_ahead: int = 5,
    method: str = "linear",
) -> dict[str, Any]:
    """Forecast future values using simple regression.

    Projects a metric forward by N periods using linear or exponential
    regression. Useful for "at this rate, Serbia will have X by 2030"
    type insights.

    Args:
        data: List of row dicts with time series data
        time_column: Column with temporal ordering (years, dates)
        value_column: Column with numeric values to forecast
        periods_ahead: Number of future periods to predict
        method: 'linear' or 'exponential'

    Returns:
        Dict with 'historical_data', 'forecast_data', 'trend_line',
             'growth_rate', 'projection_note', 'r_squared'
    """
    if not data:
        return {"error": "No data provided"}

    if periods_ahead < 1:
        return {"error": "periods_ahead must be at least 1"}

    df = pd.DataFrame(data)
    df = df.sort_values(time_column)

    # Try to extract numeric time values
    try:
        df["_t"] = pd.to_numeric(df[time_column])
    except (ValueError, TypeError):
        df["_t"] = range(len(df))

    y = pd.to_numeric(df[value_column], errors="coerce")
    x = df["_t"]

    valid = y.notna() & x.notna()
    x_clean = x[valid].values.astype(float)
    y_clean = y[valid].values.astype(float)

    if len(x_clean) < 2:
        return {"error": "Need at least 2 data points for forecasting"}

    # Linear regression
    coeffs = np.polyfit(x_clean, y_clean, 1)
    slope, intercept = coeffs

    # Calculate R²
    y_pred = np.polyval(coeffs, x_clean)
    ss_res = np.sum((y_clean - y_pred) ** 2)
    ss_tot = np.sum((y_clean - y_clean.mean()) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

    # Calculate growth rate
    if len(y_clean) >= 2:
        avg_growth_rate = ((y_clean[-1] / y_clean[0]) ** (1 / (len(y_clean) - 1)) - 1) * 100
    else:
        avg_growth_rate = 0

    # Generate forecast
    last_t = x_clean[-1]
    step = x_clean[1] - x_clean[0] if len(x_clean) > 1 else 1
    forecast_times = [last_t + step * (i + 1) for i in range(periods_ahead)]

    if method == "exponential" and y_clean[-1] > 0:
        # Exponential fit: y = a * e^(bx)
        log_y = np.log(np.maximum(y_clean, 1e-10))
        exp_coeffs = np.polyfit(x_clean, log_y, 1)
        forecast_values = np.exp(np.polyval(exp_coeffs, forecast_times))
        # Also compute exponential historical trend
        trend_values = np.exp(np.polyval(exp_coeffs, x_clean))
    else:
        forecast_values = np.polyval(coeffs, forecast_times)
        trend_values = y_pred

    # Build projection note
    last_val = y_clean[-1]
    first_forecast = forecast_values[0] if len(forecast_values) > 0 else last_val
    last_forecast = forecast_values[-1] if len(forecast_values) > 0 else first_forecast
    direction = "rasti" if slope > 0 else "padati"

    projection_note = (
        f"Na osnovu linearnog trenda, {value_column} će nastaviti da se {direction}. "
        f"Projekcija za {forecast_times[-1]:.0f}: {last_forecast:,.0f} "
        f"(od trenutnog {last_val:,.0f}). "
        f"Prosečna godišnja stopa rasta: {avg_growth_rate:+.2f}%."
    )

    return {
        "historical_data": df[[time_column, value_column]].to_dict(orient="records"),
        "forecast_data": [
            {time_column: t, value_column: round(float(v), 2), "_forecast": True}
            for t, v in zip(forecast_times, forecast_values, strict=True)
        ],
        "trend_line": [
            {time_column: t, "_trend": round(float(v), 2)} for t, v in zip(x_clean, trend_values, strict=True)
        ],
        "slope": round(float(slope), 4),
        "intercept": round(float(intercept), 2),
        "growth_rate": round(float(avg_growth_rate), 2),
        "r_squared": round(float(r_squared), 4),
        "projection_note": projection_note,
        "method": method,
        "periods_ahead": periods_ahead,
    }


def benchmark_comparison(
    data: list[dict[str, Any]],
    value_column: str,
    entity_column: str,
    benchmarks: Optional[dict[str, float]] = None,
    benchmark_labels: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Compare Serbian data against benchmark values (EU average, regional).

    Computes how each entity compares to reference values, generating
    insights about above/below benchmark performance.

    Args:
        data: List of row dicts
        value_column: Numeric column to benchmark
        entity_column: Entity names (districts, cities)
        benchmarks: Dict of benchmark_name → value (e.g., {'EU average': 50000})
        benchmark_labels: Dict of benchmark_name → display label

    Returns:
        Dict with 'comparisons', 'above_benchmark', 'below_benchmark',
             'insights', 'best_performer', 'worst_performer'
    """
    if not data:
        return {"error": "No data provided"}

    df = pd.DataFrame(data)
    values = pd.to_numeric(df[value_column], errors="coerce")

    if values.isna().all():
        return {"error": f"No numeric values in {value_column}"}

    mean_val = values.mean()
    median_val = values.median()
    std_val = values.std()

    results = {
        "statistical_benchmarks": {
            "mean": round(float(mean_val), 2),
            "median": round(float(median_val), 2),
            "std_dev": round(float(std_val), 2),
            "min": round(float(values.min()), 2),
            "max": round(float(values.max()), 2),
        },
        "comparisons": [],
        "above_benchmark": [],
        "below_benchmark": [],
        "insights": [],
    }

    # Statistical comparisons
    best_idx = values.idxmax()
    worst_idx = values.idxmin()
    results["best_performer"] = {
        "entity": str(df.loc[best_idx, entity_column]) if entity_column in df.columns else "",
        "value": round(float(values.max()), 2),
        "vs_mean": round(float((values.max() - mean_val) / mean_val * 100), 2) if mean_val != 0 else 0,
    }
    results["worst_performer"] = {
        "entity": str(df.loc[worst_idx, entity_column]) if entity_column in df.columns else "",
        "value": round(float(values.min()), 2),
        "vs_mean": round(float((values.min() - mean_val) / mean_val * 100), 2) if mean_val != 0 else 0,
    }

    # Custom benchmark comparisons
    if benchmarks:
        for name, bench_val in benchmarks.items():
            label = (benchmark_labels or {}).get(name, name)
            above = df[values >= bench_val]
            below = df[values < bench_val]

            comparison = {
                "benchmark_name": label,
                "benchmark_value": bench_val,
                "entities_above": len(above),
                "entities_below": len(below),
                "pct_above": round(len(above) / len(df) * 100, 1) if len(df) > 0 else 0,
                "best_vs_benchmark": round(float(values.max() - bench_val), 2),
                "worst_vs_benchmark": round(float(values.min() - bench_val), 2),
            }
            results["comparisons"].append(comparison)

            if entity_column in df.columns:
                above_entities = above[entity_column].tolist()[:5]
                below_entities = below[entity_column].tolist()[:5]
                results["above_benchmark"].append(
                    {
                        "benchmark": label,
                        "entities": above_entities,
                        "count": len(above),
                    }
                )
                results["below_benchmark"].append(
                    {
                        "benchmark": label,
                        "entities": below_entities,
                        "count": len(below),
                    }
                )

    # Generate insights
    if benchmarks:
        for name, bench_val in benchmarks.items():
            label = (benchmark_labels or {}).get(name, name)
            above_pct = len(df[values >= bench_val]) / len(df) * 100 if len(df) > 0 else 0

            if above_pct > 70:
                insight = f"Više od 70% entiteti su iznad {label} ({bench_val:,.0f})"
            elif above_pct < 30:
                insight = f"Manje od 30% entiteti dostižu {label} ({bench_val:,.0f})"
            else:
                insight = f"Približno polovina entiteti je iznad {label} ({bench_val:,.0f})"

            results["insights"].append(insight)

    # Variance insight
    cv = std_val / mean_val if mean_val != 0 else 0
    if cv > 0.5:
        results["insights"].append(
            f"Visoka nejednakost: koeficijent varijacije {cv:.1f} — "
            f"najbolji je {values.max():,.0f}, najgori {values.min():,.0f} "
            f"({values.max() / values.min():.1f}× razlika)."
        )

    return results


def cross_dataset_insights(
    data_a: list[dict[str, Any]],
    data_b: list[dict[str, Any]],
    value_column_a: str,
    value_column_b: str,
    entity_column_a: Optional[str] = None,
    entity_column_b: Optional[str] = None,
    label_a: str = "Skup A",
    label_b: str = "Skup B",
) -> dict[str, Any]:
    """Extract insights by comparing two related datasets.

    Finds correlations, divergences, and rank disagreements between
    two datasets. Useful for "population vs air quality", "GDP vs education",
    "budget planned vs executed" type analyses.

    Args:
        data_a: First dataset
        data_b: Second dataset
        value_column_a: Numeric column in first dataset
        value_column_b: Numeric column in second dataset
        entity_column_a: Entity column in first dataset (for entity-level comparison)
        entity_column_b: Entity column in second dataset
        label_a: Label for first dataset
        label_b: Label for second dataset

    Returns:
        Dict with 'summary_a', 'summary_b', 'correlation', 'insights'
    """
    df_a = pd.DataFrame(data_a)
    df_b = pd.DataFrame(data_b)

    vals_a = pd.to_numeric(df_a[value_column_a], errors="coerce").dropna()
    vals_b = pd.to_numeric(df_b[value_column_b], errors="coerce").dropna()

    result: dict[str, Any] = {
        "summary_a": {
            "label": label_a,
            "count": len(vals_a),
            "mean": round(float(vals_a.mean()), 2) if len(vals_a) > 0 else 0,
            "median": round(float(vals_a.median()), 2) if len(vals_a) > 0 else 0,
            "total": round(float(vals_a.sum()), 2),
        },
        "summary_b": {
            "label": label_b,
            "count": len(vals_b),
            "mean": round(float(vals_b.mean()), 2) if len(vals_b) > 0 else 0,
            "median": round(float(vals_b.median()), 2) if len(vals_b) > 0 else 0,
            "total": round(float(vals_b.sum()), 2),
        },
        "correlation": None,
        "insights": [],
    }

    # Overall comparison
    if len(vals_a) > 0 and len(vals_b) > 0:
        ratio = vals_a.mean() / vals_b.mean() if vals_b.mean() != 0 else 0
        result["overall_ratio"] = round(ratio, 3)
        result["difference"] = round(float(vals_a.mean() - vals_b.mean()), 2)
        result["pct_difference"] = (
            round(float((vals_a.mean() - vals_b.mean()) / vals_b.mean() * 100), 2) if vals_b.mean() != 0 else 0
        )

        result["insights"].append(
            f"{label_a} prosečno ({vals_a.mean():,.1f}) je {abs(result['pct_difference']):.1f}% "
            f"{'viši' if result['pct_difference'] > 0 else 'niži'} od {label_b} ({vals_b.mean():,.1f})."
        )

    # Entity-level correlation if both have entity columns
    if entity_column_a and entity_column_b and len(vals_a) > 2 and len(vals_b) > 2:
        merged = pd.merge(
            df_a[[entity_column_a, value_column_a]],
            df_b[[entity_column_b, value_column_b]],
            left_on=entity_column_a,
            right_on=entity_column_b,
            how="inner",
        )

        if len(merged) >= 3:
            x = pd.to_numeric(merged[value_column_a], errors="coerce")
            y = pd.to_numeric(merged[value_column_b], errors="coerce")
            valid = x.notna() & y.notna()

            if valid.sum() >= 3:
                corr = x[valid].corr(y[valid])
                result["correlation"] = round(float(corr), 4)

                if abs(corr) > 0.7:
                    direction = "pozitivna" if corr > 0 else "negativna"
                    strength = "jaka" if abs(corr) > 0.9 else "izražena"
                    result["insights"].append(
                        f"{strength.capitalize()} {direction} korelacija (r={corr:.2f}) "
                        f"između {value_column_a} i {value_column_b}."
                    )
                elif abs(corr) > 0.4:
                    direction = "pozitivna" if corr > 0 else "negativna"
                    result["insights"].append(
                        f"Umerena {direction} korelacija (r={corr:.2f}) između {value_column_a} i {value_column_b}."
                    )

                # Find biggest outliers (where the relationship breaks down)
                if valid.sum() > 5:
                    merged["_residual"] = abs(x[valid] * corr - y[valid])
                    top_outliers = merged.nlargest(3, "_residual")
                    outlier_names = top_outliers[entity_column_a].tolist()
                    result["insights"].append(
                        f"Najveća odstupanja od trenda: {', '.join(str(n) for n in outlier_names)}."
                    )

    return result
