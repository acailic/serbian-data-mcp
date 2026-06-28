"""Tests for data parsing and transformation."""

import pytest
import pandas as pd
from serbian_data_mcp.data import parse_json, parse_csv, filter_data, group_data, aggregate_data


@pytest.mark.asyncio
async def test_parse_json():
    """Test JSON parsing."""
    content = b'{"name": "Test", "value": 123}'
    result = await parse_json(content)

    assert result["name"] == "Test"
    assert result["value"] == 123


@pytest.mark.asyncio
async def test_parse_json_array():
    """Test JSON array parsing."""
    content = b'[{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]'
    result = await parse_json(content)

    assert len(result) == 2
    assert result[0]["name"] == "A"


@pytest.mark.asyncio
async def test_parse_csv():
    """Test CSV parsing."""
    content = b"name,value\nTest,123\nAnother,456"
    df = await parse_csv(content)

    assert len(df) == 2
    assert "name" in df.columns
    assert "value" in df.columns
    assert df.iloc[0]["name"] == "Test"


@pytest.mark.asyncio
async def test_parse_csv_with_utf8_bom():
    """Test CSV parsing with UTF-8 BOM."""
    content = b"\xef\xbb\xbfname,value\nTest,123"
    df = await parse_csv(content)

    assert len(df) == 1
    assert df.columns[0] == "name"


def test_filter_data():
    """Test data filtering."""
    data = pd.DataFrame({"category": ["A", "B", "A", "C"], "value": [10, 20, 30, 40]})

    result = filter_data(data, {"category": "A"})

    assert len(result) == 2
    assert all(result["category"] == "A")


def test_filter_data_with_list():
    """Test filtering with list of values."""
    data = pd.DataFrame({"category": ["A", "B", "A", "C"], "value": [10, 20, 30, 40]})

    result = filter_data(data, {"category": ["A", "B"]})

    assert len(result) == 3


def test_filter_data_with_operators():
    """Test filtering with comparison operators."""
    data = pd.DataFrame({"value": [10, 20, 30, 40]})

    result = filter_data(data, {"value": {">": 15}})

    assert len(result) == 3
    assert all(result["value"] > 15)


def test_group_data():
    """Test data grouping."""
    data = pd.DataFrame({"category": ["A", "B", "A", "B"], "value": [10, 20, 30, 40]})

    result = group_data(data, "category")

    assert "category" in result.columns
    assert len(result) == 2


def test_aggregate_data():
    """Test data aggregation."""
    data = pd.DataFrame({"value": [10, 20, 30, 40]})

    result = aggregate_data(data, "value", "sum")

    assert result == 100


def test_aggregate_mean():
    """Test mean aggregation."""
    data = pd.DataFrame({"value": [10, 20, 30, 40]})

    result = aggregate_data(data, "value", "mean")

    assert result == 25.0


def test_filter_with_list_input():
    """Test filtering with list input."""
    data = [{"category": "A", "value": 10}, {"category": "B", "value": 20}, {"category": "A", "value": 30}]

    result = filter_data(data, {"category": "A"})

    assert len(result) == 2


# -- CSV parsing additional tests ----------------------------------------------


@pytest.mark.asyncio
async def test_parse_csv_latin1_fallback() -> None:
    """CSV with non-UTF-8 content should fallback to latin1."""
    content = b"name,city\r\nTest,\xe9\xe8"  # latin1 encoded e-acute, e-grave
    df = await parse_csv(content)
    assert len(df) == 1
    assert "name" in df.columns


@pytest.mark.asyncio
async def test_parse_csv_empty() -> None:
    """Empty CSV should produce empty DataFrame (header only)."""
    content = b"name,value\n"
    df = await parse_csv(content)
    assert len(df) == 0
    assert "name" in df.columns


# -- JSON parsing additional tests ---------------------------------------------


@pytest.mark.asyncio
async def test_parse_json_nested() -> None:
    """JSON with nested structure."""
    content = b'{"outer": {"inner": "value"}}'
    result = await parse_json(content)
    assert result["outer"]["inner"] == "value"


@pytest.mark.asyncio
async def test_parse_json_empty_object() -> None:
    """Empty JSON object."""
    content = b"{}"
    result = await parse_json(content)
    assert result == {}


@pytest.mark.asyncio
async def test_parse_json_empty_array() -> None:
    """Empty JSON array."""
    content = b"[]"
    result = await parse_json(content)
    assert result == []


@pytest.mark.asyncio
async def test_parse_json_invalid_raises() -> None:
    """Invalid JSON should raise an exception."""
    content = b"{invalid json}"
    with pytest.raises(Exception):
        await parse_json(content)


# -- Excel parsing (skip if openpyxl not installed) ------------------------------


@pytest.mark.asyncio
async def test_parse_excel_not_implemented() -> None:
    """Excel parsing should work when openpyxl is available, but we can't generate a real xlsx here."""
    from serbian_data_mcp.data.parsers import parse_excel as _parse_excel

    # Create a minimal invalid xlsx to test error handling
    content = b"not-a-real-xlsx"
    with pytest.raises(Exception):
        await _parse_excel(content)


# -- parse_resource dispatch ----------------------------------------------------


@pytest.mark.asyncio
async def test_parse_resource_xml_fallback() -> None:
    """XML format should return raw text."""
    from serbian_data_mcp.data.parsers import parse_resource

    content = b"<root><item>test</item></root>"
    mock_resp = type("obj", (), {"content": content})()
    result = await parse_resource(mock_resp, "xml")
    assert isinstance(result, str)
    assert "<root>" in result


@pytest.mark.asyncio
async def test_parse_resource_unknown_format_fallback() -> None:
    """Unknown format should attempt JSON parse then raw text fallback."""
    from serbian_data_mcp.data.parsers import parse_resource

    content = b"some plain text data"
    mock_resp = type("obj", (), {"content": content})()
    result = await parse_resource(mock_resp, "txt")
    assert isinstance(result, str)


# -- parse_resource typed-format dispatch (json/csv/xlsx) -----------------------


def _mock_resp(content: bytes) -> object:
    return type("obj", (), {"content": content})()


@pytest.mark.asyncio
async def test_parse_resource_dispatches_json() -> None:
    """parse_resource should dispatch format='json' to parse_json (line 28)."""
    from serbian_data_mcp.data.parsers import parse_resource

    result = await parse_resource(_mock_resp(b'{"k": "v"}'), "json")
    assert result == {"k": "v"}


@pytest.mark.asyncio
async def test_parse_resource_dispatches_csv() -> None:
    """parse_resource should dispatch format='csv' to parse_csv (line 30)."""
    from serbian_data_mcp.data.parsers import parse_resource

    df = await parse_resource(_mock_resp(b"name,value\nTest,123\n"), "csv")
    assert isinstance(df, pd.DataFrame)
    assert df.iloc[0]["name"] == "Test"


@pytest.mark.asyncio
async def test_parse_resource_dispatches_excel() -> None:
    """parse_resource should dispatch format='xlsx' (and aliases) to parse_excel (line 32)."""
    from serbian_data_mcp.data import parsers

    sentinel = pd.DataFrame([{"x": 1}])

    async def _fake_excel(_content: bytes) -> pd.DataFrame:
        return sentinel

    monkeypatch_target = parsers
    original = parsers.parse_excel
    monkeypatch_target.parse_excel = _fake_excel
    try:
        for fmt in ("xlsx", "xls", "excel"):
            result = await parsers.parse_resource(_mock_resp(b"placeholder"), fmt)
            assert result is sentinel
    finally:
        monkeypatch_target.parse_excel = original


# -- parse_csv double-failure fallback (latin1 also fails -> utf-8 replace) -----


@pytest.mark.asyncio
async def test_parse_csv_latin1_failure_falls_back_to_utf8_replace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When both utf-8-sig and latin1 reads raise, fall back to utf-8 errors=replace (lines 62-64)."""
    from serbian_data_mcp.data import parsers

    sentinel = pd.DataFrame([{"name": "recovered"}])
    calls: list[dict[str, object]] = []

    def _fake_read_csv(_buf: object, **kwargs: object) -> pd.DataFrame:
        calls.append(kwargs)
        encoding = kwargs.get("encoding")
        # First call (utf-8-sig) and second call (latin1) both raise; third returns sentinel.
        if encoding == "utf-8-sig":
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "boom")
        if encoding == "latin1":
            raise ValueError("simulated latin1 parse failure")
        return sentinel

    monkeypatch.setattr(parsers.pd, "read_csv", _fake_read_csv)

    df = await parsers.parse_csv(b"anything")

    assert df is sentinel
    # Three attempts in order: utf-8-sig -> latin1 -> utf-8 with errors=replace.
    assert calls[0]["encoding"] == "utf-8-sig"
    assert calls[1]["encoding"] == "latin1"
    assert calls[2]["encoding"] == "utf-8"
    assert calls[2]["errors"] == "replace"
