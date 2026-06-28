"""Offline tests for tools/export.py MCP tools.

Covers the 4 tools that shipped with no/transport-only coverage:
  - export_visualization (format gate + html/json + exception→ToolError)
  - export_data (empty/format gates + csv/json/xlsx + openpyxl-missing + generic error)
  - export_chart_pdf (RuntimeError→kaleido + generic error + success via module-attr patch)
  - generate_embed (success envelope + exception→ToolError)

export_to_datawrapper is covered in test_ported_tools.py.

No network. config.export_dir is redirected to a tmp dir via sandbox_export_dir.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import pytest
from fastmcp.exceptions import ToolError

from serbian_data_mcp.config import config
from serbian_data_mcp.tools import export as export_mod


# --------------------------------------------------------------------------- #
# Helpers / fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def sandbox_export_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect config.export_dir to a tmp dir (export_dir is a class property)."""
    monkeypatch.setattr(type(config), "export_dir", property(lambda self: tmp_path))
    return tmp_path


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _figure_dict() -> dict[str, Any]:
    """Minimal valid plotly figure dict (the on-the-wire MCP input shape)."""
    fig = go.Figure(data=[go.Bar(x=["a", "b"], y=[1, 2])])
    return fig.to_dict()


# --------------------------------------------------------------------------- #
# export_visualization
# --------------------------------------------------------------------------- #


def test_export_visualization_unsupported_format_raises(sandbox_export_dir: Path) -> None:
    with pytest.raises(ToolError, match="Unsupported format 'png'"):
        _run(export_mod.export_visualization(_figure_dict(), format="png"))


def test_export_visualization_html_writes_file_and_envelope(sandbox_export_dir: Path) -> None:
    result = _run(export_mod.export_visualization(_figure_dict(), format="html", filename="graf"))
    assert result["format"] == "html"
    assert result["filename"] == "graf"
    # export_visualization passes filename verbatim (no extension appended) to export_html,
    # so the on-disk filepath is the bare filename in export_dir — locks actual behavior.
    assert result["filepath"].endswith("graf")
    assert Path(result["filepath"]).exists()
    text = Path(result["filepath"]).read_text(encoding="utf-8")
    assert "Plotly.newPlot" in text


def test_export_visualization_json_writes_file_and_envelope(sandbox_export_dir: Path) -> None:
    result = _run(export_mod.export_visualization(_figure_dict(), format="json", filename="data"))
    assert result["format"] == "json"
    assert result["filename"] == "data"
    assert result["filepath"].endswith("data")
    payload = json.loads(Path(result["filepath"]).read_text(encoding="utf-8"))
    assert payload["data"][0]["type"] == "bar"


def test_export_visualization_exception_wrapped_as_tool_error(
    monkeypatch: pytest.MonkeyPatch, sandbox_export_dir: Path
) -> None:
    async def _boom(*_args: Any, **_kwargs: Any) -> str:
        raise RuntimeError("viz layer blew up")

    monkeypatch.setattr(export_mod, "export_html", _boom)
    with pytest.raises(ToolError, match="Export failed: viz layer blew up"):
        _run(export_mod.export_visualization(_figure_dict(), format="html"))


# --------------------------------------------------------------------------- #
# export_data
# --------------------------------------------------------------------------- #


def test_export_data_empty_raises(sandbox_export_dir: Path) -> None:
    with pytest.raises(ToolError, match="No data to export"):
        _run(export_mod.export_data([], filename="x"))


def test_export_data_unsupported_format_raises(sandbox_export_dir: Path) -> None:
    with pytest.raises(ToolError, match="Unsupported format 'parquet'"):
        _run(export_mod.export_data([{"a": 1}], format="parquet"))


def test_export_data_csv_writes_file_and_envelope(sandbox_export_dir: Path) -> None:
    rows = [{"grad": "BG", "stanovnici": 1378}, {"grad": "NS", "stanovnici": 250}]
    result = _run(export_mod.export_data(rows, filename="gradovi", format="csv"))
    assert result["format"] == "csv"
    assert result["rows"] == 2
    assert result["columns"] == ["grad", "stanovnici"]
    assert result["filename"] == "gradovi.csv"
    text = Path(result["filepath"]).read_text(encoding="utf-8-sig")
    assert "grad,stanovnici" in text
    assert "BG,1378" in text


def test_export_data_json_writes_file_and_envelope(sandbox_export_dir: Path) -> None:
    rows = [{"a": 1}, {"a": 2}]
    result = _run(export_mod.export_data(rows, filename="pod", format="json"))
    assert result["format"] == "json"
    assert result["rows"] == 2
    assert result["filename"] == "pod.json"
    payload = json.loads(Path(result["filepath"]).read_text(encoding="utf-8"))
    assert payload == rows


def test_export_data_xlsx_writes_file_and_envelope(sandbox_export_dir: Path) -> None:
    rows = [{"a": 1}, {"a": 2}]
    result = _run(export_mod.export_data(rows, filename="xl", format="xlsx"))
    assert result["format"] == "xlsx"
    assert result["filename"] == "xl.xlsx"
    # openpyxl is installed → real .xlsx file written (zip magic bytes PK)
    assert Path(result["filepath"]).read_bytes()[:2] == b"PK"


def test_export_data_xlsx_missing_openpyxl_wrapped(monkeypatch: pytest.MonkeyPatch, sandbox_export_dir: Path) -> None:
    """If openpyxl import fails inside df.to_excel, the tool surfaces a clear ToolError."""
    import pandas as pd

    def _raise_import_error(*_args: Any, **_kwargs: Any) -> None:
        raise ImportError("openpyxl")

    monkeypatch.setattr(pd.DataFrame, "to_excel", _raise_import_error)
    with pytest.raises(ToolError, match="XLSX export requires openpyxl"):
        _run(export_mod.export_data([{"a": 1}], filename="noxlsx", format="xlsx"))


def test_export_data_generic_exception_wrapped(monkeypatch: pytest.MonkeyPatch, sandbox_export_dir: Path) -> None:
    import pandas as pd

    def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(pd.DataFrame, "to_csv", _boom)
    with pytest.raises(ToolError, match="Export failed: disk full"):
        _run(export_mod.export_data([{"a": 1}], filename="fail", format="csv"))


# --------------------------------------------------------------------------- #
# export_chart_pdf
# --------------------------------------------------------------------------- #


def test_export_chart_pdf_runtime_error_wraps_with_kaleido_hint(
    monkeypatch: pytest.MonkeyPatch, sandbox_export_dir: Path
) -> None:
    """export_pdf raising RuntimeError (kaleido unavailable) → ToolError with install hint."""

    async def _boom(*_args: Any, **_kwargs: Any) -> str:
        raise RuntimeError("PDF export requires kaleido")

    monkeypatch.setattr(export_mod, "export_pdf", _boom)
    with pytest.raises(ToolError, match="PDF export failed.*Install kaleido"):
        _run(export_mod.export_chart_pdf(_figure_dict(), filename="doc"))


def test_export_chart_pdf_kaleido_missing_natural_hits_generic_path(
    sandbox_export_dir: Path,
) -> None:
    """Real plotly raises ValueError (not RuntimeError) when kaleido is absent, so the
    tool's generic `except Exception` arm fires — distinct from the RuntimeError arm."""
    with pytest.raises(ToolError, match="PDF export failed"):
        _run(export_mod.export_chart_pdf(_figure_dict(), filename="doc"))


def test_export_chart_pdf_success(monkeypatch: pytest.MonkeyPatch, sandbox_export_dir: Path) -> None:
    async def _ok(*_args: Any, filename: str, width: int, height: int) -> str:
        assert (filename, width, height) == ("izvestaj", 1200, 700)
        return str(sandbox_export_dir / f"{filename}.pdf")

    monkeypatch.setattr(export_mod, "export_pdf", _ok)
    result = _run(export_mod.export_chart_pdf(_figure_dict(), filename="izvestaj"))
    assert result == {
        "filepath": str(sandbox_export_dir / "izvestaj.pdf"),
        "format": "pdf",
        "width": 1200,
        "height": 700,
    }


def test_export_chart_pdf_generic_exception_wrapped(monkeypatch: pytest.MonkeyPatch, sandbox_export_dir: Path) -> None:
    async def _boom(*_args: Any, **_kwargs: Any) -> str:
        raise ValueError("bad figure")

    monkeypatch.setattr(export_mod, "export_pdf", _boom)
    with pytest.raises(ToolError, match="PDF export failed: bad figure"):
        _run(export_mod.export_chart_pdf(_figure_dict(), filename="doc"))


def test_export_chart_pdf_custom_dimensions_passthrough(
    monkeypatch: pytest.MonkeyPatch, sandbox_export_dir: Path
) -> None:
    captured: dict[str, Any] = {}

    async def _ok(*_args: Any, filename: str, width: int, height: int) -> str:
        captured.update(filename=filename, width=width, height=height)
        return str(sandbox_export_dir / f"{filename}.pdf")

    monkeypatch.setattr(export_mod, "export_pdf", _ok)
    _run(export_mod.export_chart_pdf(_figure_dict(), filename="big", width=1920, height=1080))
    assert captured == {"filename": "big", "width": 1920, "height": 1080}


# --------------------------------------------------------------------------- #
# generate_embed
# --------------------------------------------------------------------------- #


def test_generate_embed_success_envelope(sandbox_export_dir: Path) -> None:
    result = _run(generate_embed_result(_figure_dict()))
    assert set(result) == {"iframe_code", "width", "height", "note"}
    assert "<iframe" in result["iframe_code"]
    assert result["width"] == 700
    assert result["height"] == 450
    assert "Paste the iframe_code" in result["note"]


def test_generate_embed_custom_dimensions_and_title(sandbox_export_dir: Path) -> None:
    result = _run(export_mod.generate_embed(_figure_dict(), width=800, height=600, title="Stanovništvo"))
    assert result["width"] == 800 and result["height"] == 600
    assert 'width="800"' in result["iframe_code"]
    assert 'height="600"' in result["iframe_code"]
    assert 'title="Stanovništvo"' in result["iframe_code"]


def test_generate_embed_exception_wrapped(monkeypatch: pytest.MonkeyPatch, sandbox_export_dir: Path) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("embed renderer failed")

    monkeypatch.setattr(export_mod, "generate_embed_code", _boom)
    with pytest.raises(ToolError, match="Embed generation failed: embed renderer failed"):
        _run(export_mod.generate_embed(_figure_dict()))


# Helper kept at bottom so the success test reads cleanly against the envelope shape.
def generate_embed_result(figure: dict[str, Any]) -> Any:
    return export_mod.generate_embed(figure)
