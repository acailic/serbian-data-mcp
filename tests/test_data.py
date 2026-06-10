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
