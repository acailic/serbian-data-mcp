"""Deterministic offline tests for viz/insights.py.

Covers the 3 public functions (extract_insights, generate_narrative,
compute_derived_metrics) and the 4 pure helpers (_safe_float, _pct_change,
_format_number, _format_pct) — all pure pandas/numpy, no network/file IO.
"""

from __future__ import annotations

import math

import pytest

from serbian_data_mcp.viz.insights import (
    _format_number,
    _format_pct,
    _pct_change,
    _safe_float,
    compute_derived_metrics,
    extract_insights,
    generate_narrative,
)

# ── _safe_float ──────────────────────────────────────────────────────────


class TestSafeFloat:
    def test_plain_number(self) -> None:
        assert _safe_float(3.14) == 3.14

    def test_numeric_string(self) -> None:
        assert _safe_float("2.5") == 2.5

    def test_integer(self) -> None:
        assert _safe_float(7) == 7.0

    def test_infinity_returns_none(self) -> None:
        assert _safe_float(float("inf")) is None

    def test_nan_returns_none(self) -> None:
        assert _safe_float(float("nan")) is None

    def test_non_numeric_string_returns_none(self) -> None:
        assert _safe_float("abc") is None

    def test_none_returns_none(self) -> None:
        assert _safe_float(None) is None


# ── _pct_change ──────────────────────────────────────────────────────────


class TestPctChange:
    def test_normal_increase(self) -> None:
        assert _pct_change(100, 150) == 50.0

    def test_normal_decrease(self) -> None:
        assert _pct_change(200, 100) == -50.0

    def test_negative_base(self) -> None:
        # ((0 - (-100)) / abs(-100)) * 100 = 100
        assert _pct_change(-100, 0) == 100.0

    def test_zero_base_positive_new_is_inf(self) -> None:
        assert math.isinf(_pct_change(0, 5))

    def test_zero_base_zero_new_is_zero(self) -> None:
        assert _pct_change(0, 0) == 0.0

    def test_zero_base_negative_new_is_zero(self) -> None:
        # new > 0 is False, so the else branch returns 0.0
        assert _pct_change(0, -5) == 0.0


# ── _format_number ───────────────────────────────────────────────────────


class TestFormatNumber:
    def test_millions(self) -> None:
        assert _format_number(1_500_000) == "1.5M"

    def test_thousands(self) -> None:
        assert _format_number(2_500) == "2.5K"

    def test_small(self) -> None:
        assert _format_number(42.5) == "42.5"

    def test_negative_millions(self) -> None:
        assert _format_number(-1_500_000) == "-1.5M"

    def test_suffix_applied(self) -> None:
        assert _format_number(1_500_000, suffix="€") == "1.5M€"


# ── _format_pct ──────────────────────────────────────────────────────────


class TestFormatPct:
    def test_positive_has_plus(self) -> None:
        assert _format_pct(5.0) == "+5.0%"

    def test_negative_no_plus(self) -> None:
        assert _format_pct(-5.0) == "-5.0%"

    def test_zero_no_plus(self) -> None:
        assert _format_pct(0.0) == "0.0%"


# ── extract_insights ─────────────────────────────────────────────────────


class TestExtractInsights:
    def test_empty_data_returns_empty(self) -> None:
        assert extract_insights([]) == []

    def test_no_numeric_columns_returns_empty(self) -> None:
        data = [{"city": "BG"}, {"city": "NS"}]
        assert extract_insights(data) == []

    def test_explicit_numeric_columns_override_auto(self) -> None:
        data = [{"city": "BG", "pop": 100}, {"city": "NS", "pop": 50}]
        # Passing numeric_columns=["pop"] with no entity → still produces
        # extreme_max / extreme_min insights.
        out = extract_insights(data, numeric_columns=["pop"])
        types = {i["type"] for i in out}
        assert "extreme_max" in types
        assert "extreme_min" in types

    def test_extreme_max_min_with_entity(self) -> None:
        data = [
            {"city": "BG", "pop": 100},
            {"city": "NS", "pop": 50},
            {"city": "NI", "pop": 75},
        ]
        out = extract_insights(data, entity_column="city")
        by_type = {i["type"]: i for i in out}
        mx = by_type["extreme_max"]
        mn = by_type["extreme_min"]
        assert mx["value"] == 100
        assert mx["entity"] == "BG"
        assert mx["column"] == "pop"
        assert mn["value"] == 50
        assert mn["entity"] == "NS"
        # max 100 not > mean*2 (75*2=150) → medium
        assert mx["severity"] == "medium"
        # min 50 not < mean*0.5 (37.5) → medium
        assert mn["severity"] == "medium"

    def test_extreme_high_severity_when_above_2x_mean(self) -> None:
        data = [
            {"city": "A", "v": 10},
            {"city": "B", "v": 10},
            {"city": "C", "v": 100},
        ]
        out = extract_insights(data, entity_column="city")
        mx = next(i for i in out if i["type"] == "extreme_max")
        assert mx["value"] == 100
        assert mx["severity"] == "high"  # 100 > mean(40)*2=80

    def test_temporal_change_critical_severity(self) -> None:
        data = [
            {"year": 2020, "v": 100},
            {"year": 2021, "v": 200},
        ]
        out = extract_insights(data, time_column="year")
        temporal = next(i for i in out if i["type"] == "temporal_change")
        assert temporal["severity"] == "critical"  # pct 100 > 50
        assert temporal["pct_change"] == pytest.approx(100.0)
        assert temporal["first_time"] == "2020"
        assert temporal["last_time"] == "2021"
        assert "increased" in temporal["detail"]

    @pytest.mark.parametrize(
        ("first", "last", "expected"),
        [
            (100, 160, "critical"),  # 60% > 50
            (100, 130, "high"),  # 30% > 20
            (100, 115, "medium"),  # 15% > 10
            (100, 108, "low"),  # 8% <= 10
        ],
    )
    def test_temporal_severity_tiers(self, first: int, last: int, expected: str) -> None:
        data = [
            {"year": 2020, "v": first},
            {"year": 2021, "v": last},
        ]
        out = extract_insights(data, time_column="year")
        temporal = next(i for i in out if i["type"] == "temporal_change")
        assert temporal["severity"] == expected

    def test_temporal_decrease_direction(self) -> None:
        data = [
            {"year": 2020, "v": 200},
            {"year": 2021, "v": 50},
        ]
        out = extract_insights(data, time_column="year")
        temporal = next(i for i in out if i["type"] == "temporal_change")
        assert temporal["pct_change"] < 0
        assert "decreased" in temporal["detail"]

    def test_temporal_entity_detail(self) -> None:
        data = [
            {"year": 2020, "city": "BG", "v": 100},
            {"year": 2020, "city": "NS", "v": 50},
            {"year": 2021, "city": "BG", "v": 300},
            {"year": 2021, "city": "NS", "v": 55},
        ]
        out = extract_insights(data, time_column="year", entity_column="city")
        temporal = next(i for i in out if i["type"] == "temporal_change")
        # BG had the biggest change (100→300, +200%) so it appears in detail
        assert "Biggest change: BG" in temporal["detail"]

    def test_ranking_insight(self) -> None:
        data = [
            {"city": "A", "v": 10},
            {"city": "B", "v": 30},
            {"city": "C", "v": 20},
        ]
        out = extract_insights(data, entity_column="city")
        ranking = next(i for i in out if i["type"] == "ranking")
        assert ranking["column"] == "v"
        assert "B" in ranking["headline"]  # leader
        assert ranking["ranking"]["A"] == pytest.approx(10.0)
        assert ranking["ranking"]["B"] == pytest.approx(30.0)
        assert ranking["severity"] == "medium"

    def test_inequality_fires_when_cv_high(self) -> None:
        data = [{"v": v} for v in [1, 2, 100]]
        out = extract_insights(data)
        ineq = next((i for i in out if i["type"] == "inequality"), None)
        assert ineq is not None
        assert ineq["column"] == "v"
        assert "coefficient_of_variation" in ineq

    def test_inequality_skipped_when_cv_low(self) -> None:
        # uniform-ish values → cv near 0
        data = [{"v": v} for v in [100, 101, 100, 101]]
        out = extract_insights(data)
        assert not any(i["type"] == "inequality" for i in out)

    def test_outlier_detection(self) -> None:
        # 20 baseline points + 1 extreme outlier past 3σ
        data = [{"v": 10}] * 20 + [{"v": 500}]
        out = extract_insights(data)
        outlier = next((i for i in out if i["type"] == "outlier"), None)
        assert outlier is not None
        assert outlier["outlier_count"] >= 1
        assert "mean" in outlier
        assert "threshold" in outlier

    def test_outlier_skipped_with_too_few_rows(self) -> None:
        # < 5 rows → no outlier analysis
        data = [{"v": 10}, {"v": 10}, {"v": 1000}]
        out = extract_insights(data)
        assert not any(i["type"] == "outlier" for i in out)

    def test_results_sorted_by_severity(self) -> None:
        data = [
            {"year": 2020, "v": 100},
            {"year": 2021, "v": 500},  # critical temporal change
        ]
        out = extract_insights(data, time_column="year")
        severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        ranks = [severity_rank[i["severity"]] for i in out]
        assert ranks == sorted(ranks)

    def test_empty_column_values_skipped(self) -> None:
        # all-NaN column yields no extremes
        data = [{"city": "A", "v": math.nan}, {"city": "B", "v": math.nan}]
        out = extract_insights(data, numeric_columns=["v"])
        assert out == []


# ── generate_narrative ───────────────────────────────────────────────────


class TestGenerateNarrative:
    def test_empty_data_envelope(self) -> None:
        out = generate_narrative([])
        assert out["headline"] == "No data available"
        assert out["insights"] == []
        assert out["big_number"] is None
        assert out["big_label"] is None
        assert out["title"] == ""

    def test_title_echoed(self) -> None:
        out = generate_narrative([], title="My Story")
        assert out["title"] == "My Story"

    def test_headline_from_top_insight(self) -> None:
        data = [{"city": "A", "v": 10}, {"city": "B", "v": 1000}]
        out = generate_narrative(data, entity_column="city")
        assert out["headline"]
        assert out["insights"]  # non-empty

    def test_big_number_from_temporal_change(self) -> None:
        data = [
            {"year": 2020, "v": 100},
            {"year": 2021, "v": 300},
        ]
        out = generate_narrative(data, time_column="year")
        # temporal_change insight drives big_number = pct_change
        assert out["big_number"] == pytest.approx(200.0)
        assert out["big_label"]

    def test_big_number_fallback_to_total(self) -> None:
        # No time column → big_number falls back to column total
        data = [{"v": 100}, {"v": 200}, {"v": 300}]
        out = generate_narrative(data)
        assert out["big_number"] == pytest.approx(600.0)
        assert out["big_label"] == "Total v"

    def test_summary_includes_record_count(self) -> None:
        data = [{"city": "A", "v": 10}, {"city": "B", "v": 20}]
        out = generate_narrative(data, entity_column="city")
        assert "2 records" in out["summary"]
        assert "2 city categories" in out["summary"]

    def test_max_insights_respected(self) -> None:
        # Multiple numeric columns → many insights; cap at max_insights
        data = [
            {"year": 2020, "a": 100, "b": 50},
            {"year": 2021, "a": 300, "b": 10},
        ]
        out = generate_narrative(data, time_column="year", max_insights=2)
        assert len(out["insights"]) <= 2


# ── compute_derived_metrics ──────────────────────────────────────────────


class TestComputeDerivedMetrics:
    def test_empty_data_envelope(self) -> None:
        out = compute_derived_metrics([])
        assert out["yoy_changes"] == {}
        assert out["per_capita"] == {}
        assert out["growth_rates"] == {}
        assert out["index_values"] == {}
        assert out["derived_data"] == []

    def test_derived_data_always_present(self) -> None:
        data = [{"v": 1}, {"v": 2}]
        out = compute_derived_metrics(data)
        assert out["derived_data"] == data

    def test_yoy_changes(self) -> None:
        data = [
            {"year": 2020, "v": 100},
            {"year": 2021, "v": 150},
            {"year": 2022, "v": 180},
        ]
        out = compute_derived_metrics(data, time_column="year")
        yoy = out["yoy_changes"]["v"]
        assert yoy["2020→2021"] == pytest.approx(50.0)
        assert yoy["2021→2022"] == pytest.approx(20.0)

    def test_yoy_skips_zero_base(self) -> None:
        data = [
            {"year": 2020, "v": 0},
            {"year": 2021, "v": 100},
        ]
        out = compute_derived_metrics(data, time_column="year")
        # prev_sum==0 → no change recorded
        assert out["yoy_changes"]["v"] == {}

    def test_per_capita(self) -> None:
        data = [
            {"city": "A", "v": 100, "pop": 10},
            {"city": "B", "v": 200, "pop": 20},
        ]
        out = compute_derived_metrics(data, entity_column="city", population_column="pop")
        pc = out["per_capita"]["v"]
        # both entities have v_per_capita == 10
        assert len(pc) == 2
        for row in pc:
            assert row["v_per_capita"] == pytest.approx(10.0)

    def test_growth_rates(self) -> None:
        data = [
            {"year": 2020, "v": 100},
            {"year": 2021, "v": 121},
            {"year": 2022, "v": 121},
        ]
        out = compute_derived_metrics(data, time_column="year")
        gr = out["growth_rates"]["v"]
        assert gr["start_value"] == pytest.approx(100.0)
        assert gr["end_value"] == pytest.approx(121.0)
        assert gr["n_periods"] == 2
        assert gr["total_change_pct"] == pytest.approx(21.0)

    def test_growth_rates_skipped_when_first_zero(self) -> None:
        data = [
            {"year": 2020, "v": 0},
            {"year": 2021, "v": 100},
        ]
        out = compute_derived_metrics(data, time_column="year")
        assert "v" not in out["growth_rates"]

    def test_index_values_base_100(self) -> None:
        data = [
            {"year": 2020, "v": 100},
            {"year": 2021, "v": 150},
            {"year": 2022, "v": 200},
        ]
        out = compute_derived_metrics(data, time_column="year")
        idx = out["index_values"]["v"]
        assert idx["2020"] == pytest.approx(100.0)
        assert idx["2021"] == pytest.approx(150.0)
        assert idx["2022"] == pytest.approx(200.0)

    def test_exclude_columns_not_metric_targets(self) -> None:
        data = [
            {"year": 2020, "pop": 1000, "v": 50},
            {"year": 2021, "pop": 1100, "v": 60},
        ]
        out = compute_derived_metrics(data, time_column="year", population_column="pop")
        # 'pop' is excluded as a metric target (it's the population column)
        assert "v" in out["yoy_changes"]
        assert "pop" not in out["yoy_changes"]
