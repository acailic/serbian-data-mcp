"""Deterministic offline tests for viz/forecast.py.

Covers the 3 public functions (forecast_linear, benchmark_comparison,
cross_dataset_insights) — all pure pandas/numpy, no network/file/plotly IO.
"""

from __future__ import annotations

import pandas as pd
import pytest

from serbian_data_mcp.viz.forecast import (
    benchmark_comparison,
    cross_dataset_insights,
    forecast_linear,
)


class TestForecastLinear:
    def test_empty_data_returns_error(self) -> None:
        assert forecast_linear([], "year", "val") == {"error": "No data provided"}

    def test_periods_ahead_below_one_returns_error(self) -> None:
        result = forecast_linear([{"year": 2020, "val": 10}], "year", "val", periods_ahead=0)
        assert result == {"error": "periods_ahead must be at least 1"}

    def test_fewer_than_two_points_returns_error(self) -> None:
        # Single row -> only 1 valid y point -> cannot fit a line.
        result = forecast_linear([{"year": 2020, "val": 10}], "year", "val")
        assert result == {"error": "Need at least 2 data points for forecasting"}

    def test_all_nan_values_returns_error(self) -> None:
        result = forecast_linear([{"year": 2020, "val": "x"}, {"year": 2021, "val": "y"}], "year", "val")
        assert result == {"error": "Need at least 2 data points for forecasting"}

    def test_linear_perfect_fit_envelope_and_keys(self) -> None:
        data = [
            {"year": 2020, "val": 10},
            {"year": 2021, "val": 20},
            {"year": 2022, "val": 30},
        ]
        result = forecast_linear(data, "year", "val", periods_ahead=2)
        assert set(result.keys()) == {
            "historical_data",
            "forecast_data",
            "trend_line",
            "slope",
            "intercept",
            "growth_rate",
            "r_squared",
            "projection_note",
            "method",
            "periods_ahead",
        }
        assert result["method"] == "linear"
        assert result["periods_ahead"] == 2
        assert result["slope"] == 10.0
        # x is the literal year (2020..2022), so intercept = -20190 (y at year 0).
        assert result["intercept"] == -20190.0
        assert result["r_squared"] == 1.0
        # growth_rate = ((30/10) ** (1/2) - 1) * 100
        assert result["growth_rate"] == pytest.approx(((30 / 10) ** 0.5 - 1) * 100, abs=0.01)
        assert len(result["forecast_data"]) == 2
        assert len(result["trend_line"]) == 3
        # forecast rows carry the _forecast marker
        assert all(row["_forecast"] for row in result["forecast_data"])

    def test_forecast_times_step_from_numeric_year(self) -> None:
        data = [{"year": y, "val": y} for y in (2020, 2021, 2022)]
        result = forecast_linear(data, "year", "val", periods_ahead=3)
        years = [row["year"] for row in result["forecast_data"]]
        assert years == [2023, 2024, 2025]

    def test_direction_padati_when_slope_negative(self) -> None:
        data = [
            {"year": 2020, "val": 30},
            {"year": 2021, "val": 20},
            {"year": 2022, "val": 10},
        ]
        result = forecast_linear(data, "year", "val")
        assert result["slope"] < 0
        assert "padati" in result["projection_note"]

    def test_direction_rasti_when_slope_positive(self) -> None:
        data = [
            {"year": 2020, "val": 10},
            {"year": 2021, "val": 20},
            {"year": 2022, "val": 30},
        ]
        result = forecast_linear(data, "year", "val")
        assert result["slope"] > 0
        assert "rasti" in result["projection_note"]

    def test_projection_note_format_and_growth_rate_sign(self) -> None:
        data = [
            {"year": 2020, "val": 100},
            {"year": 2021, "val": 200},
        ]
        result = forecast_linear(data, "year", "val", periods_ahead=4)
        note = result["projection_note"]
        assert "linearnog trenda" in note
        assert "Prosečna godišnja stopa rasta" in note
        assert "val" in note
        # growth_rate for 100->200 over 1 period = 100%
        assert result["growth_rate"] == pytest.approx(100.0, abs=0.01)

    def test_non_numeric_time_column_falls_back_to_index_range(self) -> None:
        # Non-numeric time strings force the range(len(df)) fallback (_t = 0,1,2).
        data = [
            {"label": "a", "val": 10},
            {"label": "b", "val": 20},
            {"label": "c", "val": 30},
        ]
        result = forecast_linear(data, "label", "val", periods_ahead=2)
        # step becomes 1 (range spacing), so forecast _t = 3, 4
        trend_ts = [row["label"] for row in result["trend_line"]]
        # Non-numeric time falls back to df["_t"] = range(len), and the trend
        # line echoes that numeric index under the time_column key (not labels).
        assert trend_ts == [0.0, 1.0, 2.0]
        assert result["r_squared"] == 1.0

    def test_exponential_method_branch(self) -> None:
        data = [
            {"year": 2020, "val": 10},
            {"year": 2021, "val": 20},
            {"year": 2022, "val": 40},
        ]
        result = forecast_linear(data, "year", "val", periods_ahead=3, method="exponential")
        assert result["method"] == "exponential"
        assert len(result["forecast_data"]) == 3
        # Exponential fit on doubling data forecasts > last value (40).
        assert result["forecast_data"][-1]["val"] > 40

    def test_exponential_ignored_when_last_value_non_positive(self) -> None:
        # y_clean[-1] <= 0 -> exponential falls back to the linear branch even
        # though method == 'exponential'. Using 0 (not a negative) avoids a
        # fractional-power-of-negative RuntimeWarning in the growth-rate term.
        data = [
            {"year": 2020, "val": 10},
            {"year": 2021, "val": 5},
            {"year": 2022, "val": 0},
        ]
        result = forecast_linear(data, "year", "val", method="exponential")
        # method label is preserved but the fit used the linear trend line.
        assert result["method"] == "exponential"
        assert result["slope"] < 0

    def test_constant_series_r_squared_zero(self) -> None:
        # ss_tot == 0 -> r_squared guard returns 0 instead of dividing by zero.
        data = [
            {"year": 2020, "val": 5},
            {"year": 2021, "val": 5},
            {"year": 2022, "val": 5},
        ]
        result = forecast_linear(data, "year", "val")
        assert result["r_squared"] == 0

    def test_growth_rate_zero_when_single_effective_point(self) -> None:
        # len(y_clean) >= 2 path is the norm; this guards the >= 2 gate stays
        # truthful by confirming normal data goes through the growth formula.
        data = [
            {"year": 2020, "val": 50},
            {"year": 2021, "val": 50},
        ]
        result = forecast_linear(data, "year", "val")
        # 50 -> 50 over 1 period => 0% growth
        assert result["growth_rate"] == pytest.approx(0.0, abs=0.01)

    def test_historical_data_echoes_input_columns(self) -> None:
        data = [
            {"year": 2020, "val": 10},
            {"year": 2021, "val": 20},
        ]
        result = forecast_linear(data, "year", "val")
        assert result["historical_data"] == data

    def test_unsorted_input_is_sorted_by_time(self) -> None:
        data = [
            {"year": 2022, "val": 30},
            {"year": 2020, "val": 10},
            {"year": 2021, "val": 20},
        ]
        result = forecast_linear(data, "year", "val")
        assert [row["year"] for row in result["historical_data"]] == [2020, 2021, 2022]


class TestBenchmarkComparison:
    def test_empty_data_returns_error(self) -> None:
        assert benchmark_comparison([], "val", "entity") == {"error": "No data provided"}

    def test_all_non_numeric_returns_error(self) -> None:
        result = benchmark_comparison([{"e": "a", "val": "x"}, {"e": "b", "val": "y"}], "val", "e")
        assert result == {"error": "No numeric values in val"}

    def test_statistical_benchmarks_without_custom_benchmarks(self) -> None:
        data = [{"e": "a", "val": 100}, {"e": "b", "val": 200}, {"e": "c", "val": 300}]
        result = benchmark_comparison(data, "val", "e")
        stats = result["statistical_benchmarks"]
        assert stats["mean"] == 200.0
        assert stats["median"] == 200.0
        assert stats["min"] == 100.0
        assert stats["max"] == 300.0
        assert result["comparisons"] == []
        assert result["above_benchmark"] == []
        assert result["below_benchmark"] == []
        assert result["insights"] == []
        assert result["best_performer"]["entity"] == "c"
        assert result["best_performer"]["value"] == 300.0
        assert result["best_performer"]["vs_mean"] == 50.0
        assert result["worst_performer"]["entity"] == "a"
        assert result["worst_performer"]["vs_mean"] == -50.0

    def test_mean_zero_guard_yields_zero_vs_mean(self) -> None:
        data = [{"e": "a", "val": 0}, {"e": "b", "val": 0}]
        result = benchmark_comparison(data, "val", "e")
        assert result["best_performer"]["vs_mean"] == 0
        assert result["worst_performer"]["vs_mean"] == 0

    def test_entity_column_absent_uses_empty_string(self) -> None:
        data = [{"val": 10}, {"val": 20}]
        result = benchmark_comparison(data, "val", "missing")
        assert result["best_performer"]["entity"] == ""
        assert result["worst_performer"]["entity"] == ""

    def test_benchmark_with_missing_entity_column_skips_above_below_lists(self) -> None:
        # benchmarks loop runs but entity_column not in df → comparisons computed,
        # above_benchmark/below_benchmark aggregation skipped (the 213->197 arm).
        data = [{"val": 100}, {"val": 50}]
        result = benchmark_comparison(data, "val", "missing", benchmarks={"eu": 60})
        assert result["comparisons"][0]["entities_above"] == 1
        assert result["comparisons"][0]["entities_below"] == 1
        assert result["above_benchmark"] == []
        assert result["below_benchmark"] == []

    def test_custom_benchmark_above_majority_insight(self) -> None:
        data = [{"e": f"e{i}", "val": v} for i, v in enumerate([100, 200, 300, 400, 500])]
        result = benchmark_comparison(data, "val", "e", benchmarks={"eu": 50})
        # All 5 above 50 -> >70% branch
        assert any("Više od 70%" in ins for ins in result["insights"])
        cmp_entry = result["comparisons"][0]
        assert cmp_entry["entities_above"] == 5
        assert cmp_entry["entities_below"] == 0
        assert cmp_entry["pct_above"] == 100.0
        assert result["above_benchmark"][0]["entities"] == ["e0", "e1", "e2", "e3", "e4"]
        assert result["below_benchmark"][0]["count"] == 0

    def test_custom_benchmark_below_minority_insight(self) -> None:
        data = [{"e": f"e{i}", "val": v} for i, v in enumerate([100, 200, 300, 400, 500])]
        result = benchmark_comparison(data, "val", "e", benchmarks={"eu": 450})
        # Only e4 (500) above -> 20% -> <30% branch
        assert any("Manje od 30%" in ins for ins in result["insights"])
        assert result["comparisons"][0]["entities_above"] == 1

    def test_custom_benchmark_middle_insight(self) -> None:
        data = [{"e": f"e{i}", "val": v} for i, v in enumerate([100, 200, 300, 400, 500])]
        result = benchmark_comparison(data, "val", "e", benchmarks={"eu": 250})
        # 300,400,500 above -> 60% -> middle branch
        assert any("Približno polovina" in ins for ins in result["insights"])

    def test_benchmark_labels_override_display_name(self) -> None:
        data = [{"e": "a", "val": 100}, {"e": "b", "val": 200}]
        result = benchmark_comparison(data, "val", "e", benchmarks={"eu": 50}, benchmark_labels={"eu": "EU Prosek"})
        assert result["comparisons"][0]["benchmark_name"] == "EU Prosek"
        assert result["above_benchmark"][0]["benchmark"] == "EU Prosek"

    def test_variance_insight_fires_on_high_cv(self) -> None:
        data = [{"e": "a", "val": 10}, {"e": "b", "val": 1000}]
        result = benchmark_comparison(data, "val", "e")
        assert any("Visoka nejednakost" in ins for ins in result["insights"])

    def test_variance_insight_absent_on_low_cv(self) -> None:
        data = [{"e": "a", "val": 100}, {"e": "b", "val": 101}]
        result = benchmark_comparison(data, "val", "e")
        assert not any("Visoka nejednakost" in ins for ins in result["insights"])

    def test_above_entities_capped_at_five(self) -> None:
        data = [{"e": f"e{i}", "val": 100} for i in range(8)]
        result = benchmark_comparison(data, "val", "e", benchmarks={"x": 50})
        assert len(result["above_benchmark"][0]["entities"]) == 5
        assert result["above_benchmark"][0]["count"] == 8

    def test_multiple_benchmarks_each_produce_comparisons_and_insights(self) -> None:
        data = [{"e": "a", "val": 100}, {"e": "b", "val": 200}]
        result = benchmark_comparison(data, "val", "e", benchmarks={"low": 50, "high": 150})
        assert len(result["comparisons"]) == 2
        assert len(result["above_benchmark"]) == 2
        assert len(result["below_benchmark"]) == 2
        # One insight per benchmark (plus a possible variance insight).
        names = {c["benchmark_name"] for c in result["comparisons"]}
        assert names == {"low", "high"}


class TestCrossDatasetInsights:
    def test_summaries_built_for_both_datasets(self) -> None:
        data_a = [{"r": "a", "val": 10}, {"r": "b", "val": 20}]
        data_b = [{"r": "a", "val2": 100}, {"r": "b", "val2": 200}]
        result = cross_dataset_insights(data_a, data_b, "val", "val2")
        assert result["summary_a"]["label"] == "Skup A"
        assert result["summary_b"]["label"] == "Skup B"
        assert result["summary_a"]["count"] == 2
        assert result["summary_a"]["mean"] == 15.0
        assert result["summary_a"]["median"] == 15.0
        assert result["summary_a"]["total"] == 30.0
        assert result["summary_b"]["mean"] == 150.0

    def test_custom_labels_appear_in_summary(self) -> None:
        data_a = [{"r": "a", "val": 1}]
        data_b = [{"r": "a", "val2": 2}]
        result = cross_dataset_insights(data_a, data_b, "val", "val2", label_a="BDP", label_b="Obrazovanje")
        assert result["summary_a"]["label"] == "BDP"
        assert result["summary_b"]["label"] == "Obrazovanje"

    def test_empty_values_yield_zero_mean_median(self) -> None:
        data_a = [{"r": "a", "val": "x"}]
        data_b = [{"r": "a", "val2": "y"}]
        result = cross_dataset_insights(data_a, data_b, "val", "val2")
        assert result["summary_a"]["mean"] == 0
        assert result["summary_a"]["median"] == 0
        assert result["summary_a"]["count"] == 0
        # No overall comparison when one side is empty
        assert "overall_ratio" not in result
        assert result["insights"] == []

    def test_overall_ratio_difference_and_pct_difference(self) -> None:
        data_a = [{"r": "a", "val": 150}, {"r": "b", "val": 150}]
        data_b = [{"r": "a", "val2": 100}, {"r": "b", "val2": 100}]
        result = cross_dataset_insights(data_a, data_b, "val", "val2")
        assert result["overall_ratio"] == 1.5
        assert result["difference"] == 50.0
        assert result["pct_difference"] == 50.0
        assert any("viši" in ins for ins in result["insights"])

    def test_pct_difference_negative_is_nizi(self) -> None:
        data_a = [{"r": "a", "val": 50}, {"r": "b", "val": 50}]
        data_b = [{"r": "a", "val2": 100}, {"r": "b", "val2": 100}]
        result = cross_dataset_insights(data_a, data_b, "val", "val2")
        assert result["pct_difference"] == -50.0
        assert any("niži" in ins for ins in result["insights"])

    def test_mean_zero_guard_on_dataset_b(self) -> None:
        data_a = [{"r": "a", "val": 50}, {"r": "b", "val": 50}]
        data_b = [{"r": "a", "val2": 0}, {"r": "b", "val2": 0}]
        result = cross_dataset_insights(data_a, data_b, "val", "val2")
        # vals_b.mean() == 0 -> ratio/difference paths guarded to 0
        assert result["overall_ratio"] == 0
        assert result["pct_difference"] == 0

    def test_strong_positive_correlation_insight(self) -> None:
        data_a = [{"r": f"r{i}", "val": i} for i in range(1, 7)]
        data_b = [{"r": f"r{i}", "val2": i * 2} for i in range(1, 7)]
        result = cross_dataset_insights(data_a, data_b, "val", "val2", "r", "r")
        assert result["correlation"] == 1.0
        assert any("Jaka pozitivna korelacija" in ins for ins in result["insights"])

    def test_strong_negative_correlation_insight(self) -> None:
        data_a = [{"r": f"r{i}", "val": i} for i in range(1, 7)]
        data_b = [{"r": f"r{i}", "val2": 7 - i} for i in range(1, 7)]
        result = cross_dataset_insights(data_a, data_b, "val", "val2", "r", "r")
        assert result["correlation"] == -1.0
        assert any("Jaka negativna korelacija" in ins for ins in result["insights"])

    def test_izrazena_tier_positive_correlation(self) -> None:
        # 0.7 < |r| <= 0.9 → strength "izražena" (not "jaka"). Self-validating:
        # compute expected corr inline so the data lands in the right tier by
        # construction rather than by a magic hand-picked number.
        xs = [1, 2, 3, 4, 5, 6, 7]
        ys = [2, 4, 3, 6, 5, 8, 7]
        expected = float(pd.Series(xs).corr(pd.Series(ys)))
        assert 0.7 < expected <= 0.9, expected
        data_a = [{"r": f"r{i}", "val": v} for i, v in enumerate(xs, start=1)]
        data_b = [{"r": f"r{i}", "val2": v} for i, v in enumerate(ys, start=1)]
        result = cross_dataset_insights(data_a, data_b, "val", "val2", "r", "r")
        assert result["correlation"] == round(expected, 4)
        assert any("Izražena pozitivna korelacija" in ins for ins in result["insights"])

    def test_izrazena_tier_negative_correlation(self) -> None:
        xs = [1, 2, 3, 4, 5, 6, 7]
        ys = [-v for v in [2, 4, 3, 6, 5, 8, 7]]
        expected = float(pd.Series(xs).corr(pd.Series(ys)))
        assert -0.9 <= expected < -0.7, expected
        data_a = [{"r": f"r{i}", "val": v} for i, v in enumerate(xs, start=1)]
        data_b = [{"r": f"r{i}", "val2": v} for i, v in enumerate(ys, start=1)]
        result = cross_dataset_insights(data_a, data_b, "val", "val2", "r", "r")
        assert result["correlation"] == round(expected, 4)
        assert any("Izražena negativna korelacija" in ins for ins in result["insights"])

    def test_moderate_correlation_insight(self) -> None:
        # x=[1..6], y=[1,5,2,6,3,7] -> pearson r ~= 0.655 (moderate branch)
        ys = [1, 5, 2, 6, 3, 7]
        data_a = [{"r": f"r{i}", "val": i} for i in range(1, 7)]
        data_b = [{"r": f"r{i}", "val2": ys[i - 1]} for i in range(1, 7)]
        result = cross_dataset_insights(data_a, data_b, "val", "val2", "r", "r")
        assert 0.4 < result["correlation"] <= 0.7
        assert any("Umerena pozitivna korelacija" in ins for ins in result["insights"])

    def test_weak_correlation_emits_no_correlation_insight(self) -> None:
        # x=[1..6], y=[3,1,6,2,5,4] -> pearson r ~= 0.371 (below 0.4 threshold)
        ys = [3, 1, 6, 2, 5, 4]
        data_a = [{"r": f"r{i}", "val": i} for i in range(1, 7)]
        data_b = [{"r": f"r{i}", "val2": ys[i - 1]} for i in range(1, 7)]
        result = cross_dataset_insights(data_a, data_b, "val", "val2", "r", "r")
        assert result["correlation"] <= 0.4
        assert not any("korelacija" in ins for ins in result["insights"])

    def test_outliers_reported_when_more_than_five_valid(self) -> None:
        data_a = [{"r": f"r{i}", "val": i} for i in range(1, 7)]
        data_b = [{"r": f"r{i}", "val2": i * 2} for i in range(1, 7)]
        result = cross_dataset_insights(data_a, data_b, "val", "val2", "r", "r")
        assert any("Najveća odstupanja" in ins for ins in result["insights"])

    def test_outliers_skipped_when_five_or_fewer_valid(self) -> None:
        # 4 overlapping entities -> correlation computed (valid>=3) but the
        # >5-valid outlier branch is skipped.
        data_a = [{"r": f"r{i}", "val": i} for i in range(1, 5)]
        data_b = [{"r": f"r{i}", "val2": i * 2} for i in range(1, 5)]
        result = cross_dataset_insights(data_a, data_b, "val", "val2", "r", "r")
        assert result["correlation"] == 1.0
        assert not any("Najveća odstupanja" in ins for ins in result["insights"])

    def test_no_entity_columns_skips_correlation(self) -> None:
        data_a = [{"val": i} for i in range(1, 7)]
        data_b = [{"val2": i * 2} for i in range(1, 7)]
        result = cross_dataset_insights(data_a, data_b, "val", "val2")
        assert result["correlation"] is None
        assert not any("korelacija" in ins for ins in result["insights"])

    def test_merged_below_three_skips_correlation(self) -> None:
        # Only 2 overlapping entities -> merged < 3 -> no correlation computed.
        data_a = [{"r": "a", "val": 1}, {"r": "b", "val": 2}]
        data_b = [{"r": "a", "val2": 2}, {"r": "b", "val2": 4}]
        result = cross_dataset_insights(data_a, data_b, "val", "val2", "r", "r")
        assert result["correlation"] is None

    def test_too_few_valid_pairs_skips_correlation(self) -> None:
        # 3 entities but one side has NaN for 2 of them -> <3 valid pairs.
        data_a = [
            {"r": "a", "val": 1},
            {"r": "b", "val": 2},
            {"r": "c", "val": 3},
        ]
        data_b = [
            {"r": "a", "val2": 2},
            {"r": "b", "val2": "x"},
            {"r": "c", "val2": "y"},
        ]
        result = cross_dataset_insights(data_a, data_b, "val", "val2", "r", "r")
        assert result["correlation"] is None

    def test_correlation_block_entered_but_merged_below_three(self) -> None:
        # Both sides have >2 numeric values (so the correlation block at line
        # 327 IS entered), but the entities don't overlap -> merged inner-join
        # yields 0 rows -> the len(merged) >= 3 gate (line 336) fails inside the
        # block, leaving correlation None. Distinct from test_merged_below_three
        # whose len(vals) <= 2 skips the block entirely before line 336.
        data_a = [{"r": f"a{i}", "val": i} for i in range(1, 4)]
        data_b = [{"r": f"b{i}", "val2": i} for i in range(1, 4)]
        result = cross_dataset_insights(data_a, data_b, "val", "val2", "r", "r")
        assert result["correlation"] is None
        assert not any("korelacija" in ins for ins in result["insights"])

    def test_correlation_block_entered_but_too_few_valid_pairs(self) -> None:
        # Both sides have >2 numeric values (block entered), merged has >=3 rows
        # (entities overlap), but only 2 rows are numeric on BOTH sides -> the
        # valid.sum() >= 3 gate (line 341) fails inside the block. Covers the
        # 341->367 partial branch that test_too_few_valid_pairs misses because
        # its vals_b drops to <=2 and skips the block before line 341.
        data_a = [
            {"r": "a", "val": 1},
            {"r": "b", "val": 2},
            {"r": "c", "val": 3},
            {"r": "d", "val": 4},
        ]
        data_b = [
            {"r": "a", "val2": 1},
            {"r": "b", "val2": 2},
            {"r": "c", "val2": "x"},
            {"r": "d", "val2": "y"},
            {"r": "e", "val2": 3},
        ]
        result = cross_dataset_insights(data_a, data_b, "val", "val2", "r", "r")
        assert result["correlation"] is None
        assert not any("korelacija" in ins for ins in result["insights"])
