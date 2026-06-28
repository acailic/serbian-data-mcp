"""Deterministic offline tests for viz/infographics.py.

Covers _build_html (chart-specs rendering), create_dashboard (multi-panel HTML
assembly), and create_infographic (big-number + chart + insight page builder).

All three are pure HTML-string builders with no network / file / export_dir
coupling: create_infographic patches insights.generate_narrative (imported
inside the function body) to control the narrative dict deterministically, and
uses the real ChartBuilder (offline go.Figure construction). Assertions are
plain substring reads against the returned HTML.
"""

import plotly.graph_objects as go

from serbian_data_mcp.viz import insights as insights_mod
from serbian_data_mcp.viz import infographics as infographics_mod
from serbian_data_mcp.viz.infographics import _build_html, create_dashboard, create_infographic


# ── fixtures & helpers ──────────────────────────────────────────────────────


def _data() -> list[dict]:
    return [
        {"godina": 2020, "vrednost": 100},
        {"godina": 2021, "vrednost": 150},
        {"godina": 2022, "vrednost": 200},
    ]


def _narrative(**overrides) -> dict:
    base = {
        "insights": [
            {"severity": "critical", "headline": "Veliki skok", "detail": "Detalj A"},
            {"severity": "medium", "headline": "Srednje", "detail": "Detalj B"},
        ],
        "big_number": None,
        "big_label": "Pop",
        "headline": "Headline tekst",
        "summary": "Ovo je sažetak.",
    }
    base.update(overrides)
    return base


def _patch_narrative(monkeypatch, **overrides) -> None:
    """Patch insights.generate_narrative (re-imported per call) with a fixed dict."""

    def _fake(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return _narrative(**overrides)

    monkeypatch.setattr(insights_mod, "generate_narrative", _fake)


# ── _build_html ─────────────────────────────────────────────────────────────


def test_build_html_no_chart_specs_omits_rendercall():
    html = _build_html("Naslov", "Podnaslov", "<p>telo</p>")
    assert "<!DOCTYPE html>" in html
    assert "Naslov" in html
    assert "Podnaslov" in html
    # The renderChart *definition* is always embedded; with no specs there is no call.
    assert "renderChart('" not in html


def test_build_html_with_chart_specs_emits_renderchart_js():
    html = _build_html(
        "Naslov",
        "Podnaslov",
        "<div id='c1'></div>",
        chart_specs=[("c1", {"data": [{"type": "bar"}], "layout": {}})],
    )
    assert "renderChart('c1'" in html
    assert '"type": "bar"' in html


# ── create_dashboard ────────────────────────────────────────────────────────


def test_dashboard_chart_panel_emits_renderchart_spec():
    fig = {"data": [{"type": "scatter"}], "layout": {}}
    html = create_dashboard(
        [{"type": "chart", "title": "Graf", "figure": fig}],
        title="Dash",
        subtitle="Sub",
    )
    assert "Dash" in html
    assert "Graf" in html
    assert 'id="panel-1"' in html
    assert "renderChart('panel-1'" in html


def test_dashboard_html_panel_emits_content():
    html = create_dashboard(
        [{"type": "html", "title": "Sekcija", "content": "<b>BOLD</b>"}],
    )
    assert "Sekcija" in html
    assert "<b>BOLD</b>" in html
    assert "renderChart('" not in html


def test_dashboard_big_number_panel():
    html = create_dashboard(
        [{"type": "big_number", "number": "6.9M", "label": "Pop", "color": "gold"}],
    )
    assert "big-number-grid" in html
    assert "6.9M" in html
    assert "Pop" in html
    assert "big-number-card gold" in html


def test_dashboard_span_two_panel():
    html = create_dashboard(
        [{"type": "html", "title": "Wide", "content": "x", "span": 2}],
    )
    assert "grid-column: span 2;" in html


def test_dashboard_chart_panel_without_figure_is_skipped():
    html = create_dashboard(
        [{"type": "chart", "title": "Bez figura"}],  # no figure key -> neither branch
    )
    assert "Bez figura" not in html
    assert "renderChart('" not in html
    assert "dashboard-grid" in html


def test_dashboard_empty_panels_still_assembles_body():
    html = create_dashboard([], title="Prazno")
    assert "dashboard-grid" in html
    assert "Prazno" in html
    assert "renderChart('" not in html


def test_dashboard_big_numbers_and_chart_split():
    html = create_dashboard(
        [
            {"type": "big_number", "number": "5", "label": "A"},
            {"type": "chart", "title": "C", "figure": {"data": [{"type": "bar"}]}},
        ],
    )
    assert "big-number-grid" in html
    assert "dashboard-grid" in html
    assert 'id="panel-1"' in html


# ── create_infographic — error + envelope ───────────────────────────────────


def test_infographic_empty_data_returns_error_envelope():
    result = create_infographic([])
    assert result["error"] == "No data provided"
    assert result["html"] == ""
    assert result["insights"] == []
    assert result["chart_figure"] is None
    assert result["metadata"] == {}


def test_infographic_basic_envelope_keys(monkeypatch):
    _patch_narrative(monkeypatch)
    result = create_infographic(_data(), title="Priča", x_column="godina", y_column="vrednost")
    assert set(result) == {"html", "insights", "chart_figure", "metadata"}
    assert "Priča" in result["html"]
    assert result["metadata"]["title"] == "Priča"
    assert result["metadata"]["total_rows"] == 3
    assert result["metadata"]["total_insights"] == 2
    assert result["chart_figure"]["data"]


# ── create_infographic — chart-type branches ────────────────────────────────


def test_infographic_bar_chart_injects_chart_section(monkeypatch):
    _patch_narrative(monkeypatch)
    result = create_infographic(_data(), x_column="godina", y_column="vrednost", chart_type="bar")
    assert result["chart_figure"]["data"][0]["type"] == "bar"
    assert 'id="main-chart"' in result["html"]
    assert "chart-section" in result["html"]


def test_infographic_pie_chart_uses_pie_kwargs(monkeypatch):
    _patch_narrative(monkeypatch)
    result = create_infographic(_data(), x_column="godina", y_column="vrednost", chart_type="pie")
    assert result["chart_figure"]["data"][0]["type"] == "pie"


def test_infographic_unknown_chart_type_falls_back_to_bar(monkeypatch):
    _patch_narrative(monkeypatch)
    result = create_infographic(_data(), x_column="godina", y_column="vrednost", chart_type="nonexistent")
    # ChartBuilder has no nonexistent_chart attr -> chart_fn None -> go.Bar fallback
    assert result["chart_figure"]["data"][0]["type"] == "bar"


def test_infographic_no_columns_yields_empty_figure(monkeypatch):
    _patch_narrative(monkeypatch)
    result = create_infographic(_data(), title="Bez grafika")
    assert result["chart_figure"]["data"] == []
    # No chart data -> no chart-section injection
    assert 'id="main-chart"' not in result["html"]


def test_infographic_annotations_added_to_figure(monkeypatch):
    _patch_narrative(monkeypatch)
    result = create_infographic(
        _data(),
        x_column="godina",
        y_column="vrednost",
        annotations=[{"text": "Beleška", "x": 2021, "y": 150}],
    )
    ann_texts = [a["text"] for a in result["chart_figure"]["layout"].get("annotations", [])]
    assert "Beleška" in ann_texts


# ── create_infographic — big-number color + display formatting ──────────────


def test_infographic_big_number_positive_int_is_gold(monkeypatch):
    _patch_narrative(monkeypatch, big_number=5)
    result = create_infographic(_data())
    assert "big-number-card gold" in result["html"]
    assert ">5<" in result["html"]


def test_infographic_big_number_negative_int_is_red(monkeypatch):
    _patch_narrative(monkeypatch, big_number=-3)
    result = create_infographic(_data())
    assert "big-number-card red" in result["html"]
    assert ">-3<" in result["html"]


def test_infographic_big_number_zero_is_blue(monkeypatch):
    _patch_narrative(monkeypatch, big_number=0)
    result = create_infographic(_data())
    assert "big-number-card blue" in result["html"]


def test_infographic_big_number_non_numeric_defaults_red(monkeypatch):
    _patch_narrative(monkeypatch, big_number="6.92M")
    result = create_infographic(_data())
    assert "big-number-card red" in result["html"]
    assert "6.92M" in result["html"]


def test_infographic_big_number_subunit_float_formats_as_percent(monkeypatch):
    _patch_narrative(monkeypatch, big_number=0.5)
    result = create_infographic(_data())
    assert "50.0%" in result["html"]


def test_infographic_big_number_millions_formats_with_m(monkeypatch):
    _patch_narrative(monkeypatch, big_number=2_500_000.0)
    result = create_infographic(_data())
    assert "2.5M" in result["html"]


def test_infographic_big_number_thousands_formats_with_k(monkeypatch):
    _patch_narrative(monkeypatch, big_number=5_000.0)
    result = create_infographic(_data())
    assert "5.0K" in result["html"]


def test_infographic_big_number_hundreds_plain_format(monkeypatch):
    # 100 < abs < 1000 -> the elif's else arm (f"{x:,.0f}"); no thousand separator
    # because the >=1000 arm captures everything that would render a comma.
    _patch_narrative(monkeypatch, big_number=250.0)
    result = create_infographic(_data())
    assert ">250<" in result["html"]


def test_infographic_big_number_float_between_one_and_hundred_skips_format(monkeypatch):
    # 1 <= abs <= 100 -> the `abs > 100` gate is False, number_display stays the raw float.
    _patch_narrative(monkeypatch, big_number=50.0)
    result = create_infographic(_data())
    assert ">50.0<" in result["html"]
    assert "big-number-card gold" in result["html"]


# ── create_infographic — extra big numbers + trends ─────────────────────────


def test_infographic_extra_big_numbers_trend_up_down_flat(monkeypatch):
    _patch_narrative(monkeypatch)
    result = create_infographic(
        _data(),
        extra_big_numbers=[
            {"number": "10", "label": "A", "color": "green", "trend": "up"},
            {"number": "20", "label": "B", "color": "red", "trend": "down"},
            {"number": "30", "label": "C", "color": "blue", "trend": "stable"},
        ],
    )
    assert "rast" in result["html"]  # trend-up
    assert "pad" in result["html"]  # trend-down
    assert "stabilno" in result["html"]  # trend-flat (else arm)


def test_infographic_big_number_uses_label_from_narrative(monkeypatch):
    _patch_narrative(monkeypatch, big_number=5, big_label="Pop Label")
    result = create_infographic(_data(), title="Naslov")
    assert "Pop Label" in result["html"]


# ── create_infographic — insights / summary / timeline / table ──────────────


def test_infographic_insights_html_with_severity_badges(monkeypatch):
    _patch_narrative(monkeypatch)
    result = create_infographic(_data())
    assert "Key Findings" in result["html"]
    assert "Veliki skok" in result["html"]
    assert "severity-badge critical" in result["html"]
    assert "severity-badge medium" in result["html"]


def test_infographic_insights_section_skipped_when_empty(monkeypatch):
    _patch_narrative(monkeypatch, insights=[])
    result = create_infographic(_data())
    assert "Key Findings" not in result["html"]
    assert result["metadata"]["total_insights"] == 0


def test_infographic_summary_html_rendered(monkeypatch):
    _patch_narrative(monkeypatch, summary="Sažetak priče.")
    result = create_infographic(_data())
    assert "Sažetak priče." in result["html"]


def test_infographic_summary_absent_when_not_set(monkeypatch):
    _patch_narrative(monkeypatch, summary="")
    result = create_infographic(_data())
    # summary_html empty string -> no extra section
    assert "Sažetak" not in result["html"]


def test_infographic_timeline_rendered_when_more_than_one_event(monkeypatch):
    _patch_narrative(monkeypatch)
    result = create_infographic(
        _data(),
        timeline_events=[
            {"year": "2020", "label": "A", "dot_class": "highlight"},
            {"year": "2021", "label": "B"},
        ],
    )
    # The runtime element (CSS rule is always embedded, so assert the actual div).
    assert 'class="timeline-ribbon"' in result["html"]
    assert "event-dot highlight" in result["html"]


def test_infographic_timeline_skipped_when_single_event(monkeypatch):
    _patch_narrative(monkeypatch)
    result = create_infographic(
        _data(),
        timeline_events=[{"year": "2020", "label": "Solo"}],
    )
    assert 'class="timeline-ribbon"' not in result["html"]


def test_infographic_data_table_rendered(monkeypatch):
    _patch_narrative(monkeypatch)
    result = create_infographic(
        _data(),
        data_table={"columns": ["godina", "vrednost"], "highlight_column": "vrednost", "title": "Tabela"},
    )
    assert "Tabela" in result["html"]
    assert "data-table" in result["html"]


def test_infographic_subtitle_falls_back_to_headline(monkeypatch):
    _patch_narrative(monkeypatch, headline="Headline tekst")
    result = create_infographic(_data(), subtitle="", x_column="godina", y_column="vrednost")
    assert "Headline tekst" in result["html"]


# ── module wiring sanity ────────────────────────────────────────────────────


def test_infographics_module_exports():
    assert infographics_mod.create_infographic is create_infographic
    assert infographics_mod.create_dashboard is create_dashboard
    assert callable(go.Figure)
