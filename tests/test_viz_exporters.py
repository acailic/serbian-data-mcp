"""Offline tests for viz/exporters.py.

Covers _validate_filename (every guard), export_html / export_png / export_json /
export_pdf (async file exporters), generate_embed_code (sync, in-memory base64), and
fig_to_dict.

Pure file/string operations — no network. PNG/PDF kaleido fallback is exercised
via a fake fig that controls write_image per-engine, so no kaleido install needed.
config.export_dir is redirected to a tmp dir (sandbox_export_dir fixture) for the
output_dir=None branches.
"""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path

import plotly.graph_objects as go
import pytest

from serbian_data_mcp.config import config
from serbian_data_mcp.viz import exporters as exp


# --------------------------------------------------------------------------- #
# Helpers / fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def sandbox_export_dir(monkeypatch, tmp_path):
    """Redirect config.export_dir to a tmp dir (export_dir is a class property)."""
    monkeypatch.setattr(type(config), "export_dir", property(lambda self: tmp_path))
    return tmp_path


def _real_fig(title: str | None = "Izveštaj") -> go.Figure:
    fig = go.Figure(data=[go.Bar(x=["a", "b"], y=[1, 2])])
    if title is not None:
        fig.update_layout(title={"text": title})
    return fig


class _ImgFig:
    """Fake fig controlling write_image per-engine + recording write_html.

    fail_engines: set of engine names whose write_image call should raise.
    to_json payload is configurable so export paths that read it stay deterministic.
    """

    def __init__(self, *, fail_engines: set[str] | None = None, to_json_data: str = "{}") -> None:
        self._fail = fail_engines or set()
        self._to_json = to_json_data
        self.image_calls: list[tuple[str, str]] = []
        self.html_calls: list[str] = []

    def write_image(self, path, **kwargs) -> None:  # type: ignore[no-untyped-def]
        engine = kwargs.get("engine", "")
        self.image_calls.append((str(path), engine))
        if engine in self._fail:
            raise RuntimeError(f"{engine} not available")

    def write_html(self, path, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.html_calls.append(str(path))
        Path(path).write_text("<html></html>", encoding="utf-8")

    def to_json(self) -> str:
        return self._to_json


def _run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------- #
# _validate_filename
# --------------------------------------------------------------------------- #


def test_validate_filename_empty_raises() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        exp._validate_filename("")


def test_validate_filename_slash_rejected() -> None:
    with pytest.raises(ValueError, match="Path traversal"):
        exp._validate_filename("a/b.png")


def test_validate_filename_backslash_rejected() -> None:
    with pytest.raises(ValueError, match="Path traversal"):
        exp._validate_filename("a\\b.png")


def test_validate_filename_drive_colon_rejected() -> None:
    with pytest.raises(ValueError, match="Path traversal"):
        exp._validate_filename("C:secret.png")


def test_validate_filename_dotdot_rejected() -> None:
    # ".." without a slash: the slash guard (line 154) would catch "../x" first,
    # so feed a slash-free input to reach the dedicated ".." guard at line 158.
    with pytest.raises(ValueError, match="Path traversal"):
        exp._validate_filename("file..traversal.png")


@pytest.mark.parametrize("char", ["~", "$", "|", ";", "&", "<", ">", "*", "?", "[", "]", "!", "`"])
def test_validate_filename_suspicious_chars_rejected(char: str) -> None:
    with pytest.raises(ValueError, match="Suspicious character"):
        exp._validate_filename(f"name{char}.png")


def test_validate_filename_dot_invalid_after_sanitization() -> None:
    with pytest.raises(ValueError, match="Invalid filename"):
        exp._validate_filename(".")


def test_validate_filename_valid_passes_through() -> None:
    assert exp._validate_filename("chart_2024.html") == "chart_2024.html"


# --------------------------------------------------------------------------- #
# export_html
# --------------------------------------------------------------------------- #


def test_export_html_writes_styled_page_and_returns_path(tmp_path: Path) -> None:
    fig = _real_fig("Stanovništvo")
    out = _run(exp.export_html(fig, "stanica.html", output_dir=tmp_path, title="Stanovništvo"))

    assert out == str(tmp_path / "stanica.html")
    text = Path(out).read_text(encoding="utf-8")
    assert "Stanovništvo" in text
    assert "cdn.plot.ly" in text  # plotly_cdn wired
    assert "Plotly.newPlot('chart'" in text  # render_js emitted
    assert "Source: data.gov.rs" in text  # default source
    assert "🇷🇸 data.gov.rs" in text  # badge header


def test_export_html_title_extracted_from_fig_layout(tmp_path: Path) -> None:
    fig = _real_fig("Sa Fig-a")  # no explicit title arg → pulled from fig.layout.title
    out = _run(exp.export_html(fig, "x.html", output_dir=tmp_path))
    text = Path(out).read_text(encoding="utf-8")
    assert "Sa Fig-a" in text


def test_export_html_no_title_falls_back_to_default(tmp_path: Path) -> None:
    fig = _real_fig(title=None)  # fig has no title, no title arg
    out = _run(exp.export_html(fig, "y.html", output_dir=tmp_path))
    text = Path(out).read_text(encoding="utf-8")
    assert "Serbian Data Visualization" in text


def test_export_html_custom_source(tmp_path: Path) -> None:
    fig = _real_fig()
    out = _run(exp.export_html(fig, "z.html", output_dir=tmp_path, source="Izvor: RZS"))
    assert "Izvor: RZS" in Path(out).read_text(encoding="utf-8")


def test_export_html_output_dir_none_uses_config_export_dir(sandbox_export_dir: Path) -> None:
    fig = _real_fig()
    out = _run(exp.export_html(fig, "cfg.html"))  # output_dir=None → config.export_dir
    assert out == str(sandbox_export_dir / "cfg.html")
    assert Path(out).exists()


def test_export_html_invalid_filename_raises(tmp_path: Path) -> None:
    fig = _real_fig()
    with pytest.raises(ValueError, match="Path traversal"):
        _run(exp.export_html(fig, "../escape.html", output_dir=tmp_path))


def test_export_html_creates_missing_output_dir(tmp_path: Path) -> None:
    fig = _real_fig()
    target = tmp_path / "nested" / "deep"
    out = _run(exp.export_html(fig, "deep.html", output_dir=target))
    assert Path(out).exists()
    assert target.is_dir()


# --------------------------------------------------------------------------- #
# export_png
# --------------------------------------------------------------------------- #


def test_export_png_kaleido_success(tmp_path: Path) -> None:
    fig = _ImgFig(fail_engines={"orca"})  # kaleido works
    out = _run(exp.export_png(fig, "ok.png", output_dir=tmp_path))
    assert out == str(tmp_path / "ok.png")
    engines = [engine for _, engine in fig.image_calls]
    assert engines == ["kaleido"]  # orca arm never tried


def test_export_png_orca_fallback(tmp_path: Path) -> None:
    fig = _ImgFig(fail_engines={"kaleido"})  # kaleido fails → orca succeeds
    out = _run(exp.export_png(fig, "fb.png", output_dir=tmp_path))
    assert out == str(tmp_path / "fb.png")
    engines = [engine for _, engine in fig.image_calls]
    assert engines == ["kaleido", "orca"]


def test_export_png_both_fail_writes_html_and_raises(tmp_path: Path) -> None:
    fig = _ImgFig(fail_engines={"kaleido", "orca"})
    with pytest.raises(RuntimeError, match="PNG export requires kaleido"):
        _run(exp.export_png(fig, "fail.png", output_dir=tmp_path))
    assert fig.html_calls == [str(tmp_path / "fail.html")]


def test_export_png_invalid_filename_raises(tmp_path: Path) -> None:
    fig = _ImgFig()
    with pytest.raises(ValueError, match="cannot be empty"):
        _run(exp.export_png(fig, "", output_dir=tmp_path))


# --------------------------------------------------------------------------- #
# export_json
# --------------------------------------------------------------------------- #


def test_export_json_writes_fig_json(tmp_path: Path) -> None:
    fig = _real_fig()
    out = _run(exp.export_json(fig, "data.json", output_dir=tmp_path))
    assert out == str(tmp_path / "data.json")
    payload = json.loads(Path(out).read_text(encoding="utf-8"))
    assert payload["data"][0]["type"] == "bar"


def test_export_json_creates_missing_output_dir(tmp_path: Path) -> None:
    fig = _real_fig()
    target = tmp_path / "out"
    out = _run(exp.export_json(fig, "d.json", output_dir=target))
    assert target.is_dir()
    assert Path(out).exists()


# --------------------------------------------------------------------------- #
# export_pdf
# --------------------------------------------------------------------------- #


def test_export_pdf_kaleido_success(tmp_path: Path) -> None:
    fig = _ImgFig()  # kaleido works
    out = _run(exp.export_pdf(fig, "doc.pdf", output_dir=tmp_path))
    assert out == str(tmp_path / "doc.pdf")
    assert [e for _, e in fig.image_calls] == ["kaleido"]


def test_export_pdf_kaleido_failure_raises_runtime_error(tmp_path: Path) -> None:
    fig = _ImgFig(fail_engines={"kaleido"})
    with pytest.raises(RuntimeError, match="PDF export requires kaleido"):
        _run(exp.export_pdf(fig, "bad.pdf", output_dir=tmp_path))


# --------------------------------------------------------------------------- #
# generate_embed_code
# --------------------------------------------------------------------------- #


def test_generate_embed_code_returns_full_dict() -> None:
    fig = _real_fig()
    result = exp.generate_embed_code(fig)
    assert set(result) == {"iframe_code", "html_snippet", "data_url", "width", "height"}
    assert result["width"] == 700 and result["height"] == 450
    assert "<iframe" in result["iframe_code"]
    assert "data:text/html;base64," in result["data_url"]
    # html_snippet is full standalone HTML from plotly
    assert "<html" in result["html_snippet"].lower()


def test_generate_embed_code_custom_dimensions_and_title() -> None:
    fig = _real_fig()
    result = exp.generate_embed_code(fig, width=800, height=600, title="Moj Grafikon")
    assert result["width"] == 800 and result["height"] == 600
    assert 'width="800"' in result["iframe_code"]
    assert 'height="600"' in result["iframe_code"]
    assert 'title="Moj Grafikon"' in result["iframe_code"]


def test_generate_embed_code_data_url_round_trips() -> None:
    fig = _real_fig()
    result = exp.generate_embed_code(fig)
    # base64 data url decodes back to html_snippet content
    encoded = result["data_url"].split("base64,", 1)[1]
    decoded = base64.b64decode(encoded).decode("utf-8")
    assert decoded == result["html_snippet"]


# --------------------------------------------------------------------------- #
# fig_to_dict
# --------------------------------------------------------------------------- #


def test_fig_to_dict_returns_parsed_dict() -> None:
    fig = _real_fig()
    result = exp.fig_to_dict(fig)
    assert isinstance(result, dict)
    assert result["data"][0]["type"] == "bar"
