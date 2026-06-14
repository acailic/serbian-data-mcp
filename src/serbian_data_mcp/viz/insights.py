"""Auto-narrative generation and insight extraction from datasets.

Scans data for statistically interesting patterns, extremes, trends,
and generates human-readable "shocking" insights that make data
interesting to regular people.
"""

import logging
from typing import Any

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def _safe_float(value: Any) -> float | None:
    """Convert value to float, returning None on failure."""
    try:
        v = float(value)
        if np.isfinite(v):
            return v
        return None
    except (ValueError, TypeError):
        return None


def _pct_change(old: float, new: float) -> float:
    """Calculate percentage change from old to new."""
    if old == 0:
        return float("inf") if new > 0 else 0.0
    return ((new - old) / abs(old)) * 100


def _format_number(value: float, suffix: str = "") -> str:
    """Format a number for human-readable display."""
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.1f}M{suffix}"
    if abs(value) >= 1_000:
        return f"{value / 1_000:,.1f}K{suffix}"
    return f"{value:,.1f}{suffix}"


def _format_pct(value: float) -> str:
    """Format a percentage value."""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def extract_insights(
    data: list[dict[str, Any]],
    time_column: str | None = None,
    numeric_columns: list[str] | None = None,
    entity_column: str | None = None,
) -> list[dict[str, Any]]:
    """Extract the most interesting/shocking insights from a dataset.

    Analyzes data for:
    - Biggest absolute and percentage changes
    - Extremes (max/min values with entity context)
    - Rankings (top/bottom N)
    - Alarming thresholds exceeded
    - Accelerating or decelerating trends

    Args:
        data: List of row dicts
        time_column: Optional column with temporal data (years, dates)
        numeric_columns: Columns to analyze (auto-detected if None)
        entity_column: Optional column with entity names (cities, ministries)
        context: Optional context string for narrative (e.g., "Serbia", "2024")

    Returns:
        List of insight dicts with 'type', 'headline', 'detail', 'severity', 'columns'
    """
    if not data:
        return []

    df = pd.DataFrame(data)

    # Auto-detect numeric columns if not provided
    if numeric_columns is None:
        exclude_cols = {c for c in (time_column, entity_column) if c and c in df.columns}
        numeric_columns = [
            col for col in df.columns if df[col].dtype in ("int64", "float64") and col not in exclude_cols
        ]

    if not numeric_columns:
        return []

    insights: list[dict[str, Any]] = []

    # ── 1. Extreme values (max/min with entity context) ──────────────────
    for col in numeric_columns:
        values = df[col].dropna()
        if len(values) == 0:
            continue

        max_val = values.max()
        min_val = values.min()
        mean_val = values.mean()

        max_row = df.loc[df[col].idxmax()]
        min_row = df.loc[df[col].idxmin()]

        entity_label = entity_column or "entry"

        # Max insight
        max_entity = str(max_row.get(entity_label, "")) if entity_column in df.columns else ""
        insight = {
            "type": "extreme_max",
            "headline": f"Maximum {_format_number(max_val)} — {max_entity}"
            if max_entity
            else f"Maximum value: {_format_number(max_val)}",
            "detail": f"The highest {col} value is {_format_number(max_val)}, which is {_format_pct(_pct_change(mean_val, max_val))} above the average of {_format_number(mean_val)}.",
            "severity": "high" if max_val > mean_val * 2 else "medium",
            "value": max_val,
            "column": col,
            "entity": max_entity,
        }
        insights.append(insight)

        # Min insight
        min_entity = str(min_row.get(entity_label, "")) if entity_column in df.columns else ""
        insight = {
            "type": "extreme_min",
            "headline": f"Minimum {_format_number(min_val)} — {min_entity}"
            if min_entity
            else f"Minimum value: {_format_number(min_val)}",
            "detail": f"The lowest {col} value is {_format_number(min_val)}, which is {_format_pct(_pct_change(mean_val, min_val))} below the average of {_format_number(mean_val)}.",
            "severity": "high" if min_val < mean_val * 0.5 else "medium",
            "value": min_val,
            "column": col,
            "entity": min_entity,
        }
        insights.append(insight)

    # ── 2. Biggest changes over time ───────────────────────────────────
    if time_column and len(df) > 1:
        time_sorted = df.sort_values(time_column)
        time_values = time_sorted[time_column].dropna().unique()

        if len(time_values) >= 2:
            first_time = time_values[0]
            last_time = time_values[-1]

            first_period = time_sorted[time_sorted[time_column] == first_time]
            last_period = time_sorted[time_sorted[time_column] == last_time]

            for col in numeric_columns:
                first_val = first_period[col].sum() if len(first_period) > 1 else first_period[col].iloc[0]
                last_val = last_period[col].sum() if len(last_period) > 1 else last_period[col].iloc[0]

                first_val = _safe_float(first_val)
                last_val = _safe_float(last_val)
                if first_val is None or last_val is None or first_val == 0:
                    continue

                pct = _pct_change(first_val, last_val)
                abs_change = last_val - first_val

                # Determine severity
                if abs(pct) > 50:
                    severity = "critical"
                elif abs(pct) > 20:
                    severity = "high"
                elif abs(pct) > 10:
                    severity = "medium"
                else:
                    severity = "low"

                # Find entity with biggest change if entity column exists
                entity_detail = ""
                if entity_column and entity_column in df.columns:
                    # Per-entity change
                    entity_changes = []
                    for entity in df[entity_column].dropna().unique():
                        e_first = first_period[first_period[entity_column] == entity]
                        e_last = last_period[last_period[entity_column] == entity]
                        if len(e_first) > 0 and len(e_last) > 0:
                            ef = _safe_float(e_first[col].iloc[0])
                            el = _safe_float(e_last[col].iloc[0])
                            if ef is not None and el is not None and ef != 0:
                                entity_changes.append((entity, _pct_change(ef, el), ef, el))

                    if entity_changes:
                        entity_changes.sort(key=lambda x: abs(x[1]), reverse=True)
                        top_entity = entity_changes[0]
                        entity_detail = f" Biggest change: {top_entity[0]} ({_format_pct(top_entity[1])})."

                direction = "increased" if pct > 0 else "decreased"
                insight = {
                    "type": "temporal_change",
                    "headline": f"{col.title()} {_format_pct(abs(pct))} {direction}",
                    "detail": f"From {_format_number(first_val)} ({first_time}) to {_format_number(last_val)} ({last_time}) — a {_format_number(abs(abs_change))} {direction}.{entity_detail}",
                    "severity": severity,
                    "pct_change": pct,
                    "abs_change": abs_change,
                    "column": col,
                    "first_time": str(first_time),
                    "last_time": str(last_time),
                }
                insights.append(insight)

    # ── 3. Rankings (top/bottom N) ──────────────────────────────────────
    if entity_column and entity_column in df.columns:
        for col in numeric_columns:
            # Sum across time periods per entity if time column exists
            if time_column:
                agg = df.groupby(entity_column)[col].sum()
            else:
                agg = df.groupby(entity_column)[col].first()

            top5 = agg.nlargest(5)
            bottom5 = agg.nsmallest(5)

            top_entities = ", ".join([f"{name} ({_format_number(val)})" for name, val in top5.items()])
            bottom_entities = ", ".join([f"{name} ({_format_number(val)})" for name, val in bottom5.items()])

            insight = {
                "type": "ranking",
                "headline": f"Top 5 in {col}: {top_entities.split(',')[0]} leads",
                "detail": f"Highest: {top_entities}. Lowest: {bottom_entities}.",
                "severity": "medium",
                "column": col,
                "ranking": {str(k): float(v) for k, v in agg.sort_values(ascending=False).items()},
            }
            insights.append(insight)

    # ── 4. Variance / inequality analysis ───────────────────────────────
    for col in numeric_columns:
        values = df[col].dropna()
        if len(values) < 3:
            continue

        std_val = values.std()
        mean_val = values.mean()
        cv = std_val / mean_val if mean_val != 0 else 0  # coefficient of variation

        if cv > 1.0:
            insight = {
                "type": "inequality",
                "headline": f"Huge inequality in {col} — {_format_number(values.max())}× spread",
                "detail": f"Values range from {_format_number(values.min())} to {_format_number(values.max())}. "
                f"The highest value is {_format_number(values.max() / values.min())}× the lowest. "
                f"Coefficient of variation: {cv:.1f} (high inequality).",
                "severity": "high" if cv > 2.0 else "medium",
                "column": col,
                "coefficient_of_variation": round(cv, 2),
            }
            insights.append(insight)

    # ── 5. Threshold alerts ─────────────────────────────────────────────
    # Auto-detect "alarming" values (values > 3σ from mean)
    for col in numeric_columns:
        values = df[col].dropna()
        if len(values) < 5:
            continue

        mean_val = values.mean()
        std_val = values.std()
        if std_val == 0:
            continue

        outliers = df[abs(df[col] - mean_val) > 3 * std_val]
        if len(outliers) > 0:
            entity_names = []
            for _, row in outliers.iterrows():
                if entity_column and entity_column in row.index:
                    entity_names.append(f"{row[entity_column]} ({_format_number(row[col])})")
                else:
                    entity_names.append(_format_number(row[col]))

            insight = {
                "type": "outlier",
                "headline": f"⚠️ {len(outliers)} extreme outlier(s) in {col}",
                "detail": f"These values are more than 3 standard deviations from the mean: {', '.join(entity_names[:5])}.",
                "severity": "high",
                "column": col,
                "outlier_count": len(outliers),
                "mean": mean_val,
                "threshold": mean_val + 3 * std_val,
            }
            insights.append(insight)

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    insights.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 3))

    return insights


def generate_narrative(
    data: list[dict[str, Any]],
    title: str = "",
    time_column: str | None = None,
    entity_column: str | None = None,
    max_insights: int = 5,
) -> dict[str, Any]:
    """Generate a complete data narrative with headline, insights, and summary.

    Combines insight extraction with narrative text generation for
    creating compelling data stories that are interesting to regular people.

    Args:
        data: List of row dicts
        title: Dataset/story title
        time_column: Optional time column
        entity_column: Optional entity column
        max_insights: Maximum number of insights to include

    Returns:
        Dict with 'title', 'headline', 'insights', 'summary', 'big_number', 'big_label'
    """
    if not data:
        return {
            "title": title,
            "headline": "No data available",
            "insights": [],
            "summary": "",
            "big_number": None,
            "big_label": None,
        }

    df = pd.DataFrame(data)
    numeric_columns = [col for col in df.columns if df[col].dtype in ("int64", "float64")]

    insights = extract_insights(data, time_column=time_column, entity_column=entity_column)
    top_insights = insights[:max_insights]

    # Generate headline from most severe insight
    headline = ""
    if top_insights:
        best = top_insights[0]
        headline = best["headline"]

    # Find "big number" — the most dramatic single value
    big_number = None
    big_label = None

    if numeric_columns:
        # Check for temporal change as the most dramatic big number
        for insight in insights:
            if insight["type"] == "temporal_change":
                big_number = insight.get("pct_change")
                big_label = insight["headline"]
                break

        # Fall back to total or max
        if big_number is None:
            for col in numeric_columns:
                total = df[col].sum()
                if total > 0:
                    big_number = total
                    big_label = f"Total {col}"
                    break

    # Generate summary text
    summary_parts = []
    if top_insights:
        summary_parts.append(top_insights[0]["detail"])
    if len(top_insights) > 1:
        summary_parts.append(f"Also notable: {top_insights[1]['headline']}.")

    if len(df) > 0:
        rows_info = f"Analysis based on {len(df)} records"
        if numeric_columns:
            rows_info += f" across {len(numeric_columns)} metrics"
        if entity_column and entity_column in df.columns:
            n_entities = df[entity_column].nunique()
            rows_info += f" from {n_entities} {entity_column.replace('_', ' ')} categories"
        summary_parts.append(rows_info + ".")

    return {
        "title": title,
        "headline": headline,
        "insights": top_insights,
        "summary": " ".join(summary_parts),
        "big_number": big_number,
        "big_label": big_label,
        "total_insights_found": len(insights),
    }


def compute_derived_metrics(
    data: list[dict[str, Any]],
    time_column: str | None = None,
    entity_column: str | None = None,
    population_column: str | None = None,
) -> dict[str, Any]:
    """Compute derived metrics for deeper analysis.

    Calculates:
    - Year-over-year percentage changes
    - Per-capita values (if population_column provided)
    - Growth rates (compound annual / linear)
    - Index values (base period = 100)

    Args:
        data: List of row dicts
        time_column: Optional time column for temporal analysis
        entity_column: Optional entity column for per-entity analysis
        population_column: Optional column with population for per-capita calculations

    Returns:
        Dict with 'yoy_changes', 'per_capita', 'growth_rates', 'index_values', 'derived_data'
    """
    if not data:
        return {"yoy_changes": {}, "per_capita": {}, "growth_rates": {}, "index_values": {}, "derived_data": []}

    df = pd.DataFrame(data)
    numeric_columns = [col for col in df.columns if df[col].dtype in ("int64", "float64")]
    # Exclude time/entity/population columns from metric computation targets
    exclude_cols = {c for c in (time_column, entity_column, population_column) if c and c in df.columns}
    metric_columns = [c for c in numeric_columns if c not in exclude_cols]

    result: dict[str, Any] = {
        "yoy_changes": {},
        "per_capita": {},
        "growth_rates": {},
        "index_values": {},
        "derived_data": df.to_dict(orient="records"),
    }

    # ── Year-over-year changes ──────────────────────────────────────────
    if time_column and time_column in df.columns:
        time_sorted = df.sort_values(time_column)
        time_values = time_sorted[time_column].dropna().unique()

        if len(time_values) >= 2:
            for col in metric_columns:
                changes = {}
                for i in range(1, len(time_values)):
                    prev = time_values[i - 1]
                    curr = time_values[i]
                    prev_data = time_sorted[time_sorted[time_column] == prev]
                    curr_data = time_sorted[time_sorted[time_column] == curr]

                    prev_sum = prev_data[col].sum()
                    curr_sum = curr_data[col].sum()

                    if prev_sum != 0:
                        changes[f"{prev}→{curr}"] = round(_pct_change(prev_sum, curr_sum), 2)
                result["yoy_changes"][col] = changes

    # ── Per-capita calculations ─────────────────────────────────────────
    if population_column and population_column in df.columns:
        for col in metric_columns:
            df[f"{col}_per_capita"] = df[col] / df[population_column].replace(0, float("nan"))
            per_capita_data = (
                df[[entity_column, f"{col}_per_capita"]].dropna()
                if entity_column and entity_column in df.columns
                else df[[f"{col}_per_capita"]].dropna()
            )
            result["per_capita"][col] = per_capita_data.to_dict(orient="records")

        result["derived_data"] = df.to_dict(orient="records")

    # ── Growth rates ─────────────────────────────────────────────────────
    if time_column and time_column in df.columns:
        time_sorted = df.sort_values(time_column)
        time_values = time_sorted[time_column].dropna().unique()

        if len(time_values) >= 2:
            for col in metric_columns:
                first_val = time_sorted[time_sorted[time_column] == time_values[0]][col].sum()
                last_val = time_sorted[time_sorted[time_column] == time_values[-1]][col].sum()

                if first_val > 0:
                    n_periods = len(time_values) - 1
                    cagr = (last_val / first_val) ** (1 / n_periods) - 1
                    linear_rate = (last_val - first_val) / n_periods / first_val

                    result["growth_rates"][col] = {
                        "compound_annual": round(cagr * 100, 2),
                        "linear_per_period": round(linear_rate * 100, 2),
                        "total_change_pct": round(_pct_change(first_val, last_val), 2),
                        "n_periods": n_periods,
                        "start_value": float(first_val),
                        "end_value": float(last_val),
                    }

    # ── Index values (base = 100) ───────────────────────────────────────
    if time_column and time_column in df.columns:
        for col in metric_columns:
            time_agg = df.groupby(time_column)[col].sum().sort_index()
            if len(time_agg) > 0 and time_agg.iloc[0] != 0:
                index_values = (time_agg / time_agg.iloc[0] * 100).round(2)
                result["index_values"][col] = {str(k): float(v) for k, v in index_values.items()}

    return result
