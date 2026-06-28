"""Offline tests for the 6 MCP tools in tools/transform.py.

Covers transform_data (all 5 operation branches + every validation error +
the generic-except → ToolError wrap + numpy scalar casts) and the 5 shorthand
tool wrappers (filter_data_tool/group_data_tool/aggregate_data_tool/
sort_data_tool/select_columns_tool) for happy + exception→ToolError paths.
"""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from serbian_data_mcp.tools import transform as transform_mod

# -- fixtures -----------------------------------------------------------------


def _people() -> list[dict[str, object]]:
    return [
        {"name": "Ana", "city": "BG", "value": 10},
        {"name": "Bojan", "city": "NS", "value": 20},
        {"name": "Ceca", "city": "BG", "value": 30},
    ]


# == transform_data ==========================================================


@pytest.mark.asyncio
async def test_transform_filter_happy() -> None:
    """transform_data('filter') passes {column: True} literally to filter_data,
    which matches rows whose column value == True. For a boolean column this
    selects truthy rows; for string columns it yields 0. Locked as-is."""
    data = [
        {"name": "Ana", "flag": True},
        {"name": "Bojan", "flag": False},
        {"name": "Ceca", "flag": True},
    ]
    res = await transform_mod.transform_data(data, operation="filter", column="flag")
    assert res["rows"] == 2
    assert [rec["name"] for rec in res["data"]] == ["Ana", "Ceca"]


@pytest.mark.asyncio
async def test_transform_filter_string_column_yields_zero() -> None:
    """Quirk: filter op on a string column passes {column: True} → 0 matches."""
    res = await transform_mod.transform_data(_people(), operation="filter", column="city")
    assert res["rows"] == 0


@pytest.mark.asyncio
async def test_transform_group_happy() -> None:
    res = await transform_mod.transform_data(
        _people(), operation="group", group_by="city", aggregations={"value": "sum"}
    )
    # one row per city: BG=10+30=40, NS=20
    assert res["rows"] == 2
    sums = sorted(rec["value"] for rec in res["data"])
    assert sums == [20, 40]


@pytest.mark.asyncio
async def test_transform_group_missing_group_by() -> None:
    with pytest.raises(ToolError, match="Group operation requires 'group_by'"):
        await transform_mod.transform_data(_people(), operation="group")


@pytest.mark.asyncio
async def test_transform_aggregate_int_cast() -> None:
    """sum of ints → numpy int cast to python int."""
    res = await transform_mod.transform_data(_people(), operation="aggregate", column="value", function="sum")
    assert res["column"] == "value"
    assert res["function"] == "sum"
    assert res["value"] == 60
    assert type(res["value"]) is int  # np.integer coerced


@pytest.mark.asyncio
async def test_transform_aggregate_float_cast() -> None:
    """mean → numpy float cast to python float."""
    res = await transform_mod.transform_data(_people(), operation="aggregate", column="value", function="mean")
    assert res["value"] == pytest.approx(20.0)
    assert isinstance(res["value"], float)


@pytest.mark.asyncio
async def test_transform_aggregate_none_skips_cast() -> None:
    """Missing column → aggregate_data returns None → np cast skipped (line 70→77)."""
    res = await transform_mod.transform_data(_people(), operation="aggregate", column="missing", function="sum")
    assert res["value"] is None
    assert res["column"] == "missing"


@pytest.mark.asyncio
async def test_transform_aggregate_missing_column() -> None:
    with pytest.raises(ToolError, match="Aggregate operation requires 'column'"):
        await transform_mod.transform_data(_people(), operation="aggregate")


@pytest.mark.asyncio
async def test_transform_sort_happy() -> None:
    res = await transform_mod.transform_data(_people(), operation="sort", column="value", ascending=False)
    assert [rec["value"] for rec in res["data"]] == [30, 20, 10]


@pytest.mark.asyncio
async def test_transform_sort_missing_column() -> None:
    with pytest.raises(ToolError, match="Sort operation requires 'column'"):
        await transform_mod.transform_data(_people(), operation="sort")


@pytest.mark.asyncio
async def test_transform_select_happy() -> None:
    res = await transform_mod.transform_data(_people(), operation="select", columns=["name"])
    assert res["rows"] == 3
    assert res["columns"] == ["name"]


@pytest.mark.asyncio
async def test_transform_select_missing_columns() -> None:
    with pytest.raises(ToolError, match="Select operation requires 'columns'"):
        await transform_mod.transform_data(_people(), operation="select")


@pytest.mark.asyncio
async def test_transform_unknown_operation() -> None:
    with pytest.raises(ToolError, match="Unknown operation 'bogus'"):
        await transform_mod.transform_data(_people(), operation="bogus")


@pytest.mark.asyncio
async def test_transform_generic_exception_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-ToolError exception inside an op → generic 'Transform failed' ToolError."""

    def _raise(*_a: object, **_k: object) -> None:
        raise ValueError("boom")

    monkeypatch.setattr(transform_mod, "filter_data", _raise)
    with pytest.raises(ToolError, match="Transform failed \\(filter\\): boom"):
        await transform_mod.transform_data(_people(), operation="filter", column="city")


# == filter_data_tool =========================================================


@pytest.mark.asyncio
async def test_filter_data_tool_happy() -> None:
    res = await transform_mod.filter_data_tool(_people(), {"city": "BG"})
    assert res["rows"] == 2
    assert all(rec["city"] == "BG" for rec in res["data"])


@pytest.mark.asyncio
async def test_filter_data_tool_exception_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_a: object, **_k: object) -> None:
        raise ValueError("nope")

    monkeypatch.setattr(transform_mod, "filter_data", _raise)
    with pytest.raises(ToolError, match="Filter failed: nope"):
        await transform_mod.filter_data_tool(_people(), {"city": "BG"})


# == group_data_tool ==========================================================


@pytest.mark.asyncio
async def test_group_data_tool_happy() -> None:
    res = await transform_mod.group_data_tool(_people(), "city", {"value": "sum"})
    assert res["rows"] == 2


@pytest.mark.asyncio
async def test_group_data_tool_exception_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_a: object, **_k: object) -> None:
        raise ValueError("grp fail")

    monkeypatch.setattr(transform_mod, "group_data", _raise)
    with pytest.raises(ToolError, match="Group failed: grp fail"):
        await transform_mod.group_data_tool(_people(), "city")


# == aggregate_data_tool ======================================================


@pytest.mark.asyncio
async def test_aggregate_data_tool_int_cast() -> None:
    res = await transform_mod.aggregate_data_tool(_people(), "value", "sum")
    assert res["value"] == 60
    assert type(res["value"]) is int


@pytest.mark.asyncio
async def test_aggregate_data_tool_float_cast() -> None:
    res = await transform_mod.aggregate_data_tool(_people(), "value", "mean")
    assert isinstance(res["value"], float)


@pytest.mark.asyncio
async def test_aggregate_data_tool_none_skips_cast() -> None:
    res = await transform_mod.aggregate_data_tool(_people(), "missing", "sum")
    assert res["value"] is None


@pytest.mark.asyncio
async def test_aggregate_data_tool_exception_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_a: object, **_k: object) -> None:
        raise ValueError("agg fail")

    monkeypatch.setattr(transform_mod, "aggregate_data", _raise)
    with pytest.raises(ToolError, match="Aggregate failed: agg fail"):
        await transform_mod.aggregate_data_tool(_people(), "value")


# == sort_data_tool ===========================================================


@pytest.mark.asyncio
async def test_sort_data_tool_happy() -> None:
    res = await transform_mod.sort_data_tool(_people(), "value", ascending=True)
    assert [rec["value"] for rec in res["data"]] == [10, 20, 30]


@pytest.mark.asyncio
async def test_sort_data_tool_exception_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_a: object, **_k: object) -> None:
        raise ValueError("sort fail")

    monkeypatch.setattr(transform_mod, "sort_data", _raise)
    with pytest.raises(ToolError, match="Sort failed: sort fail"):
        await transform_mod.sort_data_tool(_people(), "value")


# == select_columns_tool ======================================================


@pytest.mark.asyncio
async def test_select_columns_tool_happy() -> None:
    res = await transform_mod.select_columns_tool(_people(), ["name", "value"])
    assert res["columns"] == ["name", "value"]
    assert res["rows"] == 3


@pytest.mark.asyncio
async def test_select_columns_tool_exception_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_a: object, **_k: object) -> None:
        raise ValueError("sel fail")

    monkeypatch.setattr(transform_mod, "select_columns", _raise)
    with pytest.raises(ToolError, match="Select failed: sel fail"):
        await transform_mod.select_columns_tool(_people(), ["name"])
