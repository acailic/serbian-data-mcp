"""Deterministic offline tests for viz/themes.py.

Covers the layout-dict builders, template wrappers, apply_theme dispatch,
polish_for_export, add_annotation, and add_highlight_zone — all pure-plotly
operations read back via go.Figure layout/annotation/shape attribute reads.
No network, no file, no export_dir coupling.
"""

import plotly.graph_objects as go

from serbian_data_mcp.viz.themes import (
    PROFESSIONAL_COLORS,
    PROFESSIONAL_PAPER,
    SEMANTIC_COLORS,
    _dark_layout_dict,
    _infographic_layout_dict,
    _light_layout_dict,
    _professional_layout_dict,
    add_annotation,
    add_highlight_zone,
    apply_theme,
    dark_template,
    infographic_template,
    light_template,
    polish_for_export,
    professional_template,
)


# ── layout-dict builders ────────────────────────────────────────────────────


def test_dark_layout_dict_shape_and_colorway():
    layout = _dark_layout_dict()
    assert layout["paper_bgcolor"] == "#1a1a2e"
    assert layout["plot_bgcolor"] == "#16213e"
    assert layout["font"]["color"] == "#e0e0e0"
    # colorway wired to semantic palette
    assert layout["colorway"] is SEMANTIC_COLORS
    # margins present
    assert layout["margin"] == {"l": 80, "r": 40, "t": 80, "b": 80}


def test_light_layout_dict_shape_and_colorway():
    layout = _light_layout_dict()
    assert layout["paper_bgcolor"] == "#ffffff"
    assert layout["plot_bgcolor"] == "#f8f9fa"
    assert layout["font"]["color"] == "#37474f"
    assert layout["colorway"] is SEMANTIC_COLORS
    # light hoverlabel has white bg, dark text
    assert layout["hoverlabel"]["bgcolor"] == "#ffffff"
    assert layout["hoverlabel"]["font"]["color"] == "#1a1a2e"


def test_infographic_layout_dict_shape():
    layout = _infographic_layout_dict()
    # infographic is dark-bg, large-font, centered title
    assert layout["paper_bgcolor"] == "#1a1a2e"
    assert layout["font"]["size"] == 16
    assert layout["title"]["x"] == 0.5
    assert layout["title"]["xanchor"] == "center"
    # xaxis hides grid (minimal chrome), yaxis keeps grid
    assert layout["xaxis"]["showgrid"] is False
    assert layout["yaxis"]["showgrid"] is True
    # larger margins than dark/light
    assert layout["margin"] == {"l": 100, "r": 60, "t": 100, "b": 100}


def test_professional_layout_dict_shape_and_colorway():
    layout = _professional_layout_dict()
    # FT/Economist salmon paper, same tone for plot area (no split bg)
    assert layout["paper_bgcolor"] == PROFESSIONAL_PAPER
    assert layout["plot_bgcolor"] == PROFESSIONAL_PAPER
    assert PROFESSIONAL_PAPER == "#fff1e5"
    # colorway is the colorblind-safe Okabe-Ito palette, NOT the flag palette
    assert layout["colorway"] is PROFESSIONAL_COLORS
    assert layout["colorway"] is not SEMANTIC_COLORS
    assert layout["colorway"][0] == "#0072b2"
    # title is left-aligned editorial style with a serif headline font
    assert layout["title"]["x"] == 0.0
    assert layout["title"]["xanchor"] == "left"
    assert "Georgia" in layout["title"]["font"]["family"]
    # body font stays sans for legibility
    assert "Inter" in layout["font"]["family"]
    # Tufte-style: solid x baseline, faint y grid only
    assert layout["xaxis"]["linecolor"] == "#1c1c1c"
    assert layout["xaxis"]["showline"] is True
    assert layout["yaxis"]["gridcolor"] == "#e8dcd0"
    assert layout["yaxis"]["showline"] is False
    # legend is borderless (transparent) — minimal chrome
    assert layout["legend"]["borderwidth"] == 0


def test_professional_is_distinct_from_light():
    prof = _professional_layout_dict()
    light = _light_layout_dict()
    # professional salmon paper vs light white/gray — genuinely different register
    assert prof["paper_bgcolor"] != light["paper_bgcolor"]
    assert prof["plot_bgcolor"] != light["plot_bgcolor"]
    # different palette object
    assert prof["colorway"] is not light["colorway"]
    # professional title is serif + left, light title is sans + left-ish but
    # different family
    assert prof["title"]["font"]["family"] != light["title"]["font"]["family"]


def test_three_layouts_are_distinct_deep_copies():
    a = _dark_layout_dict()
    b = _dark_layout_dict()
    # mutating one does not affect the other
    a["paper_bgcolor"] = "MUTATED"
    assert b["paper_bgcolor"] == "#1a1a2e"


# ── template wrappers (deepcopy) ────────────────────────────────────────────


def test_dark_template_returns_deepcopy_of_dark_layout():
    tmpl = dark_template()
    assert tmpl["paper_bgcolor"] == "#1a1a2e"
    # deepcopy: mutating returned dict does not corrupt future calls
    tmpl["font"]["color"] = "MUTATED"
    fresh = dark_template()
    assert fresh["font"]["color"] == "#e0e0e0"


def test_light_template_returns_deepcopy_of_light_layout():
    tmpl = light_template()
    assert tmpl["paper_bgcolor"] == "#ffffff"
    tmpl["font"]["color"] = "MUTATED"
    assert light_template()["font"]["color"] == "#37474f"


def test_infographic_template_returns_deepcopy_of_infographic_layout():
    tmpl = infographic_template()
    assert tmpl["paper_bgcolor"] == "#1a1a2e"
    assert tmpl["title"]["xanchor"] == "center"
    tmpl["title"]["x"] = -1
    assert infographic_template()["title"]["x"] == 0.5


def test_professional_template_returns_deepcopy_of_professional_layout():
    tmpl = professional_template()
    assert tmpl["paper_bgcolor"] == PROFESSIONAL_PAPER
    # deepcopy preserves palette values (not identity — deepcopy makes a new list)
    assert tmpl["colorway"] == PROFESSIONAL_COLORS
    assert tmpl["colorway"] is not SEMANTIC_COLORS
    # deepcopy: mutating returned dict does not corrupt future calls
    tmpl["paper_bgcolor"] = "MUTATED"
    assert professional_template()["paper_bgcolor"] == PROFESSIONAL_PAPER


# ── apply_theme ─────────────────────────────────────────────────────────────


def _fig_with_traces() -> go.Figure:
    """Figure with a marker-bearing Scatter so trace-polish loop fires."""
    return go.Figure(
        data=[
            go.Scatter(x=[1, 2, 3], y=[4, 5, 6], mode="markers", name="a"),
            go.Bar(x=[1, 2], y=[3, 4], name="b"),
        ]
    )


def test_apply_theme_dark_sets_layout_and_marker_line():
    fig = _fig_with_traces()
    out = apply_theme(fig, "dark")
    assert out is fig  # mutates and returns same figure
    assert fig.layout.paper_bgcolor == "#1a1a2e"
    # every marker-bearing trace gets a zero-width line
    assert fig.data[0].marker.line.width == 0
    # bar trace has no marker attribute by default → skipped, no error
    # NOTE: trace_updates["marker"]["opacity"] = 0.9 is set for dark theme but the
    # polish loop only applies {"line": ...}, so opacity never reaches the trace —
    # inert dead code (see test_apply_theme_opacity_is_inert_dead_code).
    assert fig.data[0].marker.opacity is None


def test_apply_theme_light_keeps_no_marker_opacity():
    fig = _fig_with_traces()
    apply_theme(fig, "light")
    assert fig.layout.paper_bgcolor == "#ffffff"
    assert fig.data[0].marker.line.width == 0
    # opacity only added on dark theme
    assert fig.data[0].marker.opacity is None


def test_apply_theme_infographic():
    fig = _fig_with_traces()
    apply_theme(fig, "infographic")
    assert fig.layout.paper_bgcolor == "#1a1a2e"
    # infographic centered title
    assert fig.layout.title.xanchor == "center"


def test_apply_theme_professional():
    fig = _fig_with_traces()
    out = apply_theme(fig, "professional")
    assert out is fig
    assert fig.layout.paper_bgcolor == PROFESSIONAL_PAPER
    assert fig.layout.plot_bgcolor == PROFESSIONAL_PAPER
    # Okabe-Ito palette reaches the figure layout
    assert fig.layout.colorway[0] == "#0072b2"
    # serif title font propagated
    assert "Georgia" in fig.layout.title.font.family
    # marker-polish loop still runs on professional (zero-width marker line)
    assert fig.data[0].marker.line.width == 0


def test_apply_theme_unknown_theme_falls_back_to_dark():
    """Unknown theme name → _dark_layout_dict fallback (line 239)."""
    fig = _fig_with_traces()
    apply_theme(fig, "does-not-exist")
    assert fig.layout.paper_bgcolor == "#1a1a2e"
    # fallback picks _dark_layout_dict; opacity stays None (inert dead code, see above)
    assert fig.data[0].marker.opacity is None


def test_apply_theme_default_arg_is_dark():
    fig = _fig_with_traces()
    apply_theme(fig)  # no theme arg → default 'dark'
    assert fig.layout.paper_bgcolor == "#1a1a2e"


def test_apply_theme_opacity_is_inert_dead_code():
    """Line 249 sets trace_updates['marker']['opacity']=0.9 for dark, but the
    polish loop (lines 251-253) only applies {'line': ...} — opacity is never
    propagated to the trace. Lock the actual (inert) behavior so a future fix
    that wires opacity through changes this assertion deliberately."""
    fig = _fig_with_traces()
    apply_theme(fig, "dark")
    assert fig.data[0].marker.opacity is None


def test_apply_theme_trace_without_marker_is_safe():
    """A trace lacking .marker (e.g. go.Heatmap) must not crash the polish loop."""
    fig = go.Figure(data=[go.Heatmap(z=[[1, 2], [3, 4]])])
    apply_theme(fig, "dark")
    assert fig.layout.paper_bgcolor == "#1a1a2e"


# ── polish_for_export ───────────────────────────────────────────────────────


def test_polish_for_export_title_override():
    fig = go.Figure(data=[go.Scatter(x=[1], y=[1])])
    polish_for_export(fig, title="My Title")
    assert fig.layout.title.text == "My Title"
    assert fig.layout.title.xanchor == "left"


def test_polish_for_export_subtitle_adds_annotation():
    fig = go.Figure(data=[go.Scatter(x=[1], y=[1])])
    polish_for_export(fig, subtitle="A subtitle")
    anns = list(fig.layout.annotations)
    sub = [a for a in anns if a.text == "A subtitle"]
    assert len(sub) == 1
    assert sub[0].font.color == "#90a4ae"
    # subtitle uses paper coords, no arrow
    assert sub[0].xref == "paper"
    assert sub[0].yref == "paper"
    assert sub[0].showarrow is False


def test_polish_for_export_source_default_and_custom():
    # default source
    fig1 = go.Figure(data=[go.Scatter(x=[1], y=[1])])
    polish_for_export(fig1)
    src1 = [a for a in fig1.layout.annotations if "serbian-data-mcp" in (a.text or "")]
    assert len(src1) == 1
    assert "data.gov.rs" in src1[0].text

    # custom source
    fig2 = go.Figure(data=[go.Scatter(x=[1], y=[1])])
    polish_for_export(fig2, source="RZS")
    src2 = [a for a in fig2.layout.annotations if a.text == "RZS"]
    assert len(src2) == 1


def test_polish_for_export_source_annotation_coords():
    fig = go.Figure(data=[go.Scatter(x=[1], y=[1])])
    polish_for_export(fig)
    src = next(a for a in fig.layout.annotations if "serbian-data-mcp" in a.text)
    assert src.x == 1
    assert src.y == -0.06
    assert src.xanchor == "right"
    assert src.showarrow is False


def test_polish_for_export_enforces_min_height():
    # no height set → bumped to 500
    fig = go.Figure(data=[go.Scatter(x=[1], y=[1])])
    polish_for_export(fig)
    assert fig.layout.height == 500

    # height below 400 → bumped to 500
    fig2 = go.Figure(data=[go.Scatter(x=[1], y=[1])])
    fig2.update_layout(height=300)
    polish_for_export(fig2)
    assert fig2.layout.height == 500

    # height >= 400 → preserved
    fig3 = go.Figure(data=[go.Scatter(x=[1], y=[1])])
    fig3.update_layout(height=600)
    polish_for_export(fig3)
    assert fig3.layout.height == 600


def test_polish_for_export_sets_autosize_width_none():
    fig = go.Figure(data=[go.Scatter(x=[1], y=[1])])
    polish_for_export(fig)
    assert fig.layout.autosize is True
    assert fig.layout.width is None


def test_polish_for_export_returns_same_figure():
    fig = go.Figure(data=[go.Scatter(x=[1], y=[1])])
    out = polish_for_export(fig, title="X", subtitle="Y", source="Z")
    assert out is fig
    # 2 annotations: subtitle + source
    assert len(list(fig.layout.annotations)) == 2


# ── add_annotation ──────────────────────────────────────────────────────────


def test_add_annotation_adds_callout():
    fig = go.Figure(data=[go.Scatter(x=[1, 2], y=[1, 2])])
    out = add_annotation(fig, text="Peak", x=2, y=2)
    assert out is fig
    ann = fig.layout.annotations[-1]
    assert ann.text == "Peak"
    assert ann.x == 2
    assert ann.y == 2
    assert ann.arrowhead == 2
    assert ann.arrowcolor == "#ffab00"
    assert ann.bgcolor == "rgba(26,26,46,0.85)"
    assert ann.font.color == "#ffffff"
    assert ann.font.size == 14
    assert ann.showarrow is True


def test_add_annotation_custom_args():
    fig = go.Figure(data=[go.Scatter(x=[1, 2], y=[1, 2])])
    add_annotation(
        fig,
        text="Note",
        x=1,
        y=1,
        arrow_color="#1565c0",
        font_size=18,
        show_arrow=False,
        bgcolor="#ffffff",
    )
    ann = fig.layout.annotations[-1]
    assert ann.arrowcolor == "#1565c0"
    assert ann.font.size == 18
    assert ann.showarrow is False
    assert ann.bgcolor == "#ffffff"


# ── add_highlight_zone ──────────────────────────────────────────────────────


def test_add_highlight_zone_no_annotation():
    fig = go.Figure(data=[go.Scatter(x=[1, 2, 3, 4], y=[1, 2, 3, 4])])
    out = add_highlight_zone(fig, x_start=2, x_end=3)
    assert out is fig
    shapes = list(fig.layout.shapes)
    assert len(shapes) == 1
    rect = shapes[0]
    assert rect.x0 == 2
    assert rect.x1 == 3
    assert rect.fillcolor == "rgba(198, 40, 40, 0.1)"
    assert rect.layer == "below"
    # no annotation_text → no annotation emitted for the rect
    assert fig.layout.annotations == () or all(getattr(a, "text", None) != "zone" for a in fig.layout.annotations)


def test_add_highlight_zone_with_annotation_and_custom_color():
    fig = go.Figure(data=[go.Scatter(x=[1, 2, 3, 4], y=[1, 2, 3, 4])])
    add_highlight_zone(
        fig,
        x_start=1,
        x_end=2,
        fill_color="rgba(21,101,192,0.2)",
        annotation_text="Kriza",
    )
    # vrect with annotation lands a shape + an annotation
    shapes = list(fig.layout.shapes)
    assert len(shapes) == 1
    assert shapes[0].fillcolor == "rgba(21,101,192,0.2)"
    ann_texts = [a.text for a in fig.layout.annotations]
    assert "Kriza" in ann_texts
