"""Offline deterministic tests for viz/data_tables.py (data_table_html + data_table_css).

These functions are pure string builders (no plotly, no network), so coverage
is achieved with substring assertions on the returned HTML/CSS.
"""

from __future__ import annotations

from serbian_data_mcp.viz.data_tables import data_table_css, data_table_html


# -- data_table_html ----------------------------------------------------------


def test_empty_data_returns_no_data_message() -> None:
    """Empty input list returns the localized 'Nema podataka' placeholder."""
    out = data_table_html([])
    assert out == "<p style='color: #b0bec5;'>Nema podataka</p>"


def test_columns_auto_detected_from_first_row() -> None:
    """When columns=None, all keys of the first row become headers in order."""
    out = data_table_html([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
    assert "<th>a</th>" in out
    assert "<th>b</th>" in out
    # header order preserved
    assert out.index("<th>a</th>") < out.index("<th>b</th>")


def test_columns_explicit_subset() -> None:
    """Explicit columns list restricts displayed columns to that subset."""
    out = data_table_html([{"a": 1, "b": 2, "c": 3}], columns=["a", "c"])
    assert "<th>a</th>" in out
    assert "<th>c</th>" in out
    assert "<th>b</th>" not in out


def test_max_rows_slicing_and_overflow_note() -> None:
    """Rows beyond max_rows are dropped and a localized overflow note appears."""
    data = [{"x": i} for i in range(10)]
    out = data_table_html(data, max_rows=3)
    # overflow note references shown vs total counts in Serbian
    assert "Prikazano 3 od 10 redova" in out
    # only 3 <tr> body rows present
    assert out.count("<tr class=") == 3


def test_no_overflow_note_when_within_limit() -> None:
    """No overflow note when data length fits within max_rows."""
    out = data_table_html([{"x": 1}, {"x": 2}], max_rows=50)
    assert "Prikazano" not in out


def test_highlight_column_max_default() -> None:
    """highlight_column highlights the row with the MAX value by default."""
    out = data_table_html(
        [{"v": 1}, {"v": 9}, {"v": 5}],
        highlight_column="v",
    )
    # row index 1 (value 9) must be the highlight-row
    assert "<tr class='highlight-row'>" in out
    assert out.index("highlight-row") > out.index("<tbody>")


def test_highlight_column_min_when_highlight_max_false() -> None:
    """highlight_max=False highlights the row with the MIN value."""
    out = data_table_html(
        [{"v": 1}, {"v": 9}, {"v": 5}],
        highlight_column="v",
        highlight_max=False,
    )
    assert "<tr class='highlight-row'>" in out


def test_highlight_column_not_in_columns_skips_highlight() -> None:
    """A highlight_column absent from columns produces no highlight-row."""
    out = data_table_html([{"v": 1}, {"v": 2}], highlight_column="missing")
    assert "highlight-row" not in out


def test_highlight_column_skips_non_numeric_values() -> None:
    """Non-numeric highlight values are skipped; numeric max still highlighted."""
    out = data_table_html(
        [{"v": "n/a"}, {"v": 7}, {"v": 3}],
        highlight_column="v",
    )
    assert "<tr class='highlight-row'>" in out


def test_highlight_column_all_non_numeric_no_highlight() -> None:
    """If no highlight value parses as numeric, no row is highlighted."""
    out = data_table_html([{"v": "x"}, {"v": "y"}], highlight_column="v")
    assert "highlight-row" not in out


def test_alt_row_class_on_odd_index() -> None:
    """Rows at odd indices get the 'alt-row' class (zebra striping)."""
    out = data_table_html([{"x": 1}, {"x": 2}, {"x": 3}])
    assert "<tr class='alt-row'>" in out


def test_rank_column_adds_rank_header_and_cells() -> None:
    """rank_column prepends a '#' header and per-row rank cells (1-indexed)."""
    out = data_table_html(
        [{"name": "a"}, {"name": "b"}],
        rank_column="name",
    )
    assert "<th>#</th>" in out
    assert "<td class='rank-cell'>1</td>" in out
    assert "<td class='rank-cell'>2</td>" in out


def test_format_columns_pct_number_currency() -> None:
    """format_columns maps pct/number/currency to the expected formatted strings.

    Formatting is class-agnostic (the number-cell class is only applied to the
    highlight column), so anchor assertions on the value, not the class.
    """
    data = [{"p": 0.255, "n": 1234.0, "c": 9.5}]
    out = data_table_html(
        data,
        format_columns={"p": "pct", "n": "number", "c": "currency"},
    )
    assert ">25.5%<" in out
    assert ">1,234<" in out
    assert ">€9.50<" in out


def test_format_columns_non_numeric_falls_back_to_str() -> None:
    """A pct/number/currency format on a non-numeric value falls back to str(val)."""
    out = data_table_html(
        [{"p": "n/a"}],
        format_columns={"p": "pct"},
    )
    assert ">n/a<" in out


def test_unformatted_value_str_coerced() -> None:
    """Values without a format entry are coerced via str(); class is '' absent highlight."""
    out = data_table_html([{"x": 42, "y": True}])
    assert "<td class=''>42</td>" in out
    assert "<td class=''>True</td>" in out


def test_number_cell_class_only_on_highlight_column() -> None:
    """number-cell class is applied exclusively to the highlight_column's cells."""
    out = data_table_html(
        [{"v": 1, "name": "a"}],
        highlight_column="v",
    )
    assert "<td class='number-cell'>1</td>" in out
    assert "<td class='number-cell'>a</td>" not in out


def test_title_and_caption_rendered() -> None:
    """title and caption appear in their respective slots."""
    out = data_table_html([{"x": 1}], title="My Title", caption="note")
    assert "<h3 class='table-title'>My Title</h3>" in out
    assert "<p class='table-caption'>note</p>" in out


def test_missing_value_for_column_renders_blank() -> None:
    """A row missing a declared column renders an empty cell."""
    out = data_table_html([{"a": 1, "b": 2}, {"a": 3}], columns=["a", "b"])
    # second row's b cell should be empty
    assert "<td class=''></td>" in out


# -- data_table_css -----------------------------------------------------------


def test_data_table_css_returns_key_classes() -> None:
    """data_table_css returns CSS containing the component's core classes."""
    css = data_table_css()
    assert isinstance(css, str)
    for cls in (".data-table-container", ".table-title", ".data-table", ".highlight-row", ".alt-row", ".rank-cell"):
        assert cls in css
    # print media rule present
    assert "@media print" in css
