"""Offline unit tests for ``viz/animations.py`` — the real animated-chart builders.

The tool wrappers in ``tools/animations.py`` fake these three functions at the
module-attribute seam (see ``test_animations_tools.py``), so the viz-layer code
shipped at ~10% coverage. All three builders are pure plotly (``apply_theme``
only mutates the figure layout; no file/network/export_dir coupling), so tests
read ``fig.data`` / ``fig.frames`` / ``fig.layout`` directly — fully
deterministic, no sandbox or fixtures.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from serbian_data_mcp.viz.animations import (
    animated_bars_evolution,
    animated_comparison,
    animated_timeline,
)

# 3 times → len(times)//2 == 1, so frames 0,1 are bar phase and frame 2 is the
# line phase that builds one Scatter per category with full history.
_TIMELINE_DATA: list[dict[str, Any]] = [
    {"time": 2020, "cat": "A", "val": 10},
    {"time": 2021, "cat": "A", "val": 15},
    {"time": 2022, "cat": "A", "val": 20},
    {"time": 2020, "cat": "B", "val": 5},
    {"time": 2021, "cat": "B", "val": 8},
    {"time": 2022, "cat": "B", "val": 12},
]


# --------------------------------------------------------------------------- #
# animated_timeline
# --------------------------------------------------------------------------- #
class TestAnimatedTimeline:
    def test_returns_figure_with_one_frame_per_time(self) -> None:
        fig = animated_timeline(_TIMELINE_DATA, "time", "cat", "val")
        assert isinstance(fig, go.Figure)
        assert len(fig.frames) == 3

    def test_frame_name_is_str_time(self) -> None:
        fig = animated_timeline(_TIMELINE_DATA, "time", "cat", "val")
        assert [f.name for f in fig.frames] == ["2020", "2021", "2022"]

    def test_bar_phase_frames_hold_bar_trace(self) -> None:
        fig = animated_timeline(_TIMELINE_DATA, "time", "cat", "val")
        # i=0 and i=1 are <= len(times)//2 → bar phase
        assert isinstance(fig.frames[0].data[0], go.Bar)
        assert isinstance(fig.frames[1].data[0], go.Bar)

    def test_line_phase_frame_holds_one_scatter_per_category(self) -> None:
        fig = animated_timeline(_TIMELINE_DATA, "time", "cat", "val")
        line_frame = fig.frames[2]
        assert all(isinstance(t, go.Scatter) for t in line_frame.data)
        assert [t.name for t in line_frame.data] == ["A", "B"]

    def test_line_phase_scatter_carries_full_history(self) -> None:
        fig = animated_timeline(_TIMELINE_DATA, "time", "cat", "val")
        cat_a = fig.frames[2].data[0]
        assert list(cat_a.x) == [2020, 2021, 2022]
        assert list(cat_a.y) == [10, 15, 20]

    def test_line_phase_empty_traces_falls_back_to_bar(self) -> None:
        # Each category appears at a single distinct time → in the line phase
        # no category has >1 row, so the Scatter list is empty and the fallback
        # Bar (subset at time t) is used.
        single_row_data = [
            {"time": 2020, "cat": "A", "val": 10},
            {"time": 2021, "cat": "B", "val": 20},
            {"time": 2022, "cat": "C", "val": 30},
        ]
        fig = animated_timeline(single_row_data, "time", "cat", "val")
        assert isinstance(fig.frames[2].data[0], go.Bar)

    def test_initial_data_is_bar_for_first_time(self) -> None:
        fig = animated_timeline(_TIMELINE_DATA, "time", "cat", "val")
        assert isinstance(fig.data[0], go.Bar)
        assert set(fig.data[0].x.tolist()) == {"A", "B"}

    def test_slider_has_one_step_per_time_with_period_prefix(self) -> None:
        fig = animated_timeline(_TIMELINE_DATA, "time", "cat", "val")
        slider = fig.layout.sliders[0]
        assert slider.currentvalue.prefix == "Period: "
        assert [s.label for s in slider.steps] == ["2020", "2021", "2022"]

    def test_updatemenus_has_play_pause_buttons(self) -> None:
        fig = animated_timeline(_TIMELINE_DATA, "time", "cat", "val")
        labels = [b.label for b in fig.layout.updatemenus[0].buttons]
        assert labels == ["▶ Pokreni", "⏸ Pauza"]

    def test_frame_and_transition_duration_propagate_to_slider(self) -> None:
        fig = animated_timeline(_TIMELINE_DATA, "time", "cat", "val", frame_duration=900, transition_duration=450)
        slider = fig.layout.sliders[0]
        assert slider.transition.duration == 450
        first_step_args = slider.steps[0].args
        assert first_step_args[1]["frame"]["duration"] == 900

    def test_title_and_yaxis_set(self) -> None:
        fig = animated_timeline(_TIMELINE_DATA, "time", "cat", "val", title="Rast")
        assert fig.layout.title.text == "Rast"
        assert fig.layout.yaxis.title.text == "val"


# --------------------------------------------------------------------------- #
# animated_bars_evolution
# --------------------------------------------------------------------------- #
class TestAnimatedBarsEvolution:
    def test_returns_figure_with_one_frame_per_time(self) -> None:
        fig = animated_bars_evolution(_TIMELINE_DATA, "time", "cat", "val")
        assert isinstance(fig, go.Figure)
        assert len(fig.frames) == 3

    def test_bars_sorted_ascending_by_value_per_frame(self) -> None:
        fig = animated_bars_evolution(_TIMELINE_DATA, "time", "cat", "val")
        # Frame at t=2020: A=10, B=5 → ascending order is [B, A]
        f0 = fig.frames[0].data[0]
        assert list(f0.x) == ["B", "A"]
        assert list(f0.y) == [5, 10]

    def test_text_labels_formatted_with_thousands(self) -> None:
        big = [
            {"time": 2020, "cat": "A", "val": 1500},
            {"time": 2020, "cat": "B", "val": 2500},
        ]
        fig = animated_bars_evolution(big, "time", "cat", "val")
        assert list(fig.frames[0].data[0].text) == ["1,500", "2,500"]
        assert fig.frames[0].data[0].textposition == "outside"

    def test_blues_colorscale_applied(self) -> None:
        fig = animated_bars_evolution(_TIMELINE_DATA, "time", "cat", "val")
        bar = fig.frames[0].data[0]
        assert bar.marker.colorscale is not None

    def test_barmode_relative(self) -> None:
        fig = animated_bars_evolution(_TIMELINE_DATA, "time", "cat", "val")
        assert fig.layout.barmode == "relative"

    def test_slider_period_prefix_and_step_count(self) -> None:
        fig = animated_bars_evolution(_TIMELINE_DATA, "time", "cat", "val")
        slider = fig.layout.sliders[0]
        assert slider.currentvalue.prefix == "Period: "
        assert len(slider.steps) == 3

    def test_updatemenus_has_play_pause_buttons(self) -> None:
        fig = animated_bars_evolution(_TIMELINE_DATA, "time", "cat", "val")
        labels = [b.label for b in fig.layout.updatemenus[0].buttons]
        assert labels == ["▶ Pokreni", "⏸ Pauza"]

    def test_frame_duration_propagates_to_slider_step(self) -> None:
        fig = animated_bars_evolution(_TIMELINE_DATA, "time", "cat", "val", frame_duration=700)
        step = fig.layout.sliders[0].steps[0]
        assert step.args[1]["frame"]["duration"] == 700

    def test_initial_data_is_bar_for_first_time_sorted(self) -> None:
        fig = animated_bars_evolution(_TIMELINE_DATA, "time", "cat", "val")
        assert isinstance(fig.data[0], go.Bar)
        assert list(fig.data[0].x) == ["B", "A"]


# --------------------------------------------------------------------------- #
# animated_comparison
# --------------------------------------------------------------------------- #
class TestAnimatedComparison:
    def _datasets(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "2021": [{"cat": "A", "val": 10}, {"cat": "B", "val": 5}],
            "2022": [{"cat": "A", "val": 20}, {"cat": "B", "val": 30}],
        }

    def test_returns_figure_with_one_frame_per_dataset(self) -> None:
        fig = animated_comparison(self._datasets(), "cat", "val")
        assert isinstance(fig, go.Figure)
        assert len(fig.frames) == 2

    def test_frame_name_is_dataset_label(self) -> None:
        fig = animated_comparison(self._datasets(), "cat", "val")
        assert [f.name for f in fig.frames] == ["2021", "2022"]

    def test_default_color_palette_applied(self) -> None:
        fig = animated_comparison(self._datasets(), "cat", "val")
        assert fig.frames[0].data[0].marker.color == "#1565c0"
        assert fig.frames[1].data[0].marker.color == "#c62828"

    def test_custom_colors_override_palette(self) -> None:
        fig = animated_comparison(self._datasets(), "cat", "val", colors=["#ffffff", "#000000"])
        assert fig.frames[0].data[0].marker.color == "#ffffff"
        assert fig.frames[1].data[0].marker.color == "#000000"

    def test_color_cycles_when_more_datasets_than_colors(self) -> None:
        datasets = {
            "a": [{"cat": "A", "val": 1}],
            "b": [{"cat": "A", "val": 2}],
            "c": [{"cat": "A", "val": 3}],
        }
        fig = animated_comparison(datasets, "cat", "val", colors=["#111", "#222"])
        # i=2 → 2 % 2 == 0 → first color reused
        assert fig.frames[2].data[0].marker.color == "#111"

    def test_bars_sorted_ascending_per_frame(self) -> None:
        fig = animated_comparison(self._datasets(), "cat", "val")
        # 2021 frame: A=10, B=5 → ascending [B, A]
        assert list(fig.frames[0].data[0].x) == ["B", "A"]

    def test_text_labels_formatted(self) -> None:
        fig = animated_comparison(self._datasets(), "cat", "val")
        assert list(fig.frames[0].data[0].text) == ["5", "10"]

    def test_hovertemplate_contains_label(self) -> None:
        fig = animated_comparison(self._datasets(), "cat", "val")
        assert "<b>2021</b>" in fig.frames[0].data[0].hovertemplate

    def test_slider_podaci_prefix(self) -> None:
        fig = animated_comparison(self._datasets(), "cat", "val")
        assert fig.layout.sliders[0].currentvalue.prefix == "Podaci: "

    def test_initial_data_is_first_dataset_bar(self) -> None:
        fig = animated_comparison(self._datasets(), "cat", "val")
        assert isinstance(fig.data[0], go.Bar)
        assert fig.data[0].name == "2021"
