"""Data table component for dashboards and infographics.

Generates a styled, responsive HTML table from tabular data with
conditional formatting, ranking indicators, and sparkline columns.
"""

from __future__ import annotations

import contextlib
from typing import Any, Optional


def data_table_html(
    data: list[dict[str, Any]],
    columns: Optional[list[str]] = None,
    highlight_column: Optional[str] = None,
    highlight_max: bool = True,
    max_rows: int = 50,
    rank_column: Optional[str] = None,
    format_columns: Optional[dict[str, str]] = None,
    title: str = "",
    caption: str = "",
) -> str:
    """Generate a styled HTML data table.

    Creates a responsive, scrollable table with conditional formatting
    for dashboards and reports. Supports ranking indicators and value formatting.

    Args:
        data: List of row dicts
        columns: Columns to include (auto-detected if None)
        highlight_column: Column to highlight (max or min value gets accent)
        highlight_max: If True, highlight max; if False, highlight min
        max_rows: Maximum rows to display
        rank_column: Column to use for ranking display
        format_columns: Dict of column→format ('number', 'pct', 'currency')
        title: Table title
        caption: Table caption text

    Returns:
        HTML string for the table
    """
    if not data:
        return "<p style='color: #b0bec5;'>Nema podataka</p>"

    if columns is None:
        columns = list(data[0].keys())

    rows = data[:max_rows]

    # Find highlight value
    highlight_val = None
    highlight_idx = -1
    if highlight_column and highlight_column in columns:
        numeric_vals = []
        for r in rows:
            try:
                numeric_vals.append((float(r[highlight_column]), r))
            except (ValueError, TypeError, KeyError):
                continue
        if numeric_vals:
            if highlight_max:
                highlight_val, highlight_row = max(numeric_vals, key=lambda x: x[0])
            else:
                highlight_val, highlight_row = min(numeric_vals, key=lambda x: x[0])
            highlight_idx = rows.index(highlight_row)

    # Build table HTML
    header_cells = "".join(f"<th>{c}</th>" for c in columns)
    if rank_column:
        header_cells = f"<th>#</th>{header_cells}"

    body_rows = ""
    for i, row in enumerate(rows):
        is_highlight = i == highlight_idx
        row_class = "highlight-row" if is_highlight else ("" if i % 2 == 0 else "alt-row")

        prefix = ""
        if rank_column and rank_column in row:
            try:
                prefix = f"<td class='rank-cell'>{i + 1}</td>"
            except (ValueError, TypeError):
                prefix = "<td class='rank-cell'>-</td>"

        cells = ""
        for col in columns:
            val = row.get(col, "")
            fmt = (format_columns or {}).get(col)

            if fmt == "pct":
                with contextlib.suppress((ValueError, TypeError)):
                    val = f"{float(val):.1%}"
            elif fmt == "number":
                with contextlib.suppress((ValueError, TypeError)):
                    val = f"{float(val):,.0f}"
            elif fmt == "currency":
                with contextlib.suppress((ValueError, TypeError)):
                    val = f"€{float(val):,.2f}"
            else:
                val = str(val)

            cell_class = "number-cell" if col == highlight_column else ""
            cells += f"<td class='{cell_class}'>{val}</td>"

        body_rows += f"<tr class='{row_class}'>{prefix}{cells}</tr>"

    title_html = f"<h3 class='table-title'>{title}</h3>" if title else ""
    caption_html = f"<p class='table-caption'>{caption}</p>" if caption else ""
    overflow_note = (
        f"<p class='table-note'>Prikazano {len(rows)} od {len(data)} redova</p>" if len(data) > max_rows else ""
    )

    return f"""
    <div class="data-table-container">
        {title_html}
        <div class="table-scroll">
            <table class="data-table">
                <thead><tr>{header_cells}</tr></thead>
                <tbody>{body_rows}</tbody>
            </table>
        </div>
        {overflow_note}
        {caption_html}
    </div>"""


def data_table_css() -> str:
    """CSS styles for the data table component.

    Include this in the <style> section of any HTML page that uses data_table_html().
    """
    return """
    .data-table-container {
        background: var(--bg-card, rgba(22, 33, 62, 0.9));
        border: 1px solid var(--border, rgba(255,255,255,0.08));
        border-radius: 16px;
        padding: 32px;
        margin-bottom: 32px;
    }
    .table-title {
        font-size: 1.4rem;
        font-weight: 700;
        margin-bottom: 16px;
        color: var(--accent-gold, #ffab00);
    }
    .table-scroll {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    .data-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }
    .data-table thead th {
        background: rgba(255,255,255,0.05);
        padding: 12px 16px;
        text-align: left;
        font-weight: 700;
        color: var(--text-secondary, #b0bec5);
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
        border-bottom: 2px solid var(--border, rgba(255,255,255,0.08));
        white-space: nowrap;
    }
    .data-table tbody td {
        padding: 10px 16px;
        border-bottom: 1px solid var(--border, rgba(255,255,255,0.05));
        color: var(--text-primary, #ffffff);
    }
    .data-table tbody tr:hover {
        background: rgba(255,255,255,0.03);
    }
    .data-table tbody tr.alt-row {
        background: rgba(255,255,255,0.02);
    }
    .data-table tbody tr.highlight-row {
        background: rgba(255,171,0,0.08);
    }
    .data-table tbody tr.highlight-row td {
        color: var(--accent-gold, #ffab00);
        font-weight: 600;
    }
    .data-table .rank-cell {
        font-weight: 700;
        color: var(--text-secondary, #b0bec5);
        text-align: center;
        width: 40px;
    }
    .data-table .number-cell {
        text-align: right;
        font-variant-numeric: tabular-nums;
    }
    .table-caption {
        font-size: 0.85rem;
        color: var(--text-secondary, #b0bec5);
        margin-top: 12px;
        font-style: italic;
    }
    .table-note {
        font-size: 0.8rem;
        color: var(--text-secondary, #b0bec5);
        margin-top: 8px;
        opacity: 0.7;
    }
    @media print {
        .data-table-container { break-inside: avoid; }
        .table-scroll { overflow-x: visible; }
    }
    """
