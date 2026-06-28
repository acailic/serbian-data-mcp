"""Offline unit tests for tools/_helpers.py.

Closes the last coverage gap in the tools package: the get_catalog singleton
build+cache paths (lines 34-38) and the dataframe_to_dict list/fallback
branches (lines 102-104), which no test exercised directly because every tool
module patches h.get_client / h.get_catalog at its own call site.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from serbian_data_mcp.tools import _helpers as helpers_mod


# ---------------------------------------------------------------------------
# get_catalog — singleton build + cache reuse
# ---------------------------------------------------------------------------


class _FakeCatalog:
    """Minimal DatasetCatalog stand-in: records initialize() calls."""

    def __init__(self) -> None:
        self.init_calls = 0

    async def initialize(self) -> None:
        self.init_calls += 1


async def test_get_catalog_builds_when_cache_empty(monkeypatch: Any) -> None:
    """First call builds the catalog, runs initialize, caches the instance."""
    monkeypatch.setattr(helpers_mod, "_catalog_instance", None)
    built: list[_FakeCatalog] = []
    monkeypatch.setattr(helpers_mod, "DatasetCatalog", lambda: built.append(_FakeCatalog()) or built[-1])

    catalog = await helpers_mod.get_catalog()

    assert isinstance(catalog, _FakeCatalog)
    assert catalog.init_calls == 1  # initialize awaited exactly once
    assert len(built) == 1  # DatasetCatalog constructed exactly once
    assert helpers_mod._catalog_instance is catalog  # cached on the module global


async def test_get_catalog_reuses_cached_instance(monkeypatch: Any) -> None:
    """Second call returns the cached instance without rebuilding (line 38 short-circuit)."""
    cached = _FakeCatalog()
    monkeypatch.setattr(helpers_mod, "_catalog_instance", cached)
    constructed: list[Any] = []
    monkeypatch.setattr(helpers_mod, "DatasetCatalog", lambda: constructed.append(object()))

    result = await helpers_mod.get_catalog()

    assert result is cached  # same instance, not a new build
    assert constructed == []  # DatasetCatalog never constructed on cache hit
    assert cached.init_calls == 0  # initialize NOT re-run on cache hit


# ---------------------------------------------------------------------------
# dataframe_to_dict — list + fallback branches
# ---------------------------------------------------------------------------


def test_dataframe_to_dict_dataframe_branch() -> None:
    """DataFrame branch (already covered) returns data/columns/rows envelope."""
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    out = helpers_mod.dataframe_to_dict(df)

    assert out == {
        "data": [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}],
        "columns": ["a", "b"],
        "rows": 2,
    }


def test_dataframe_to_dict_list_branch() -> None:
    """list-of-records branch returns data + rows, no columns key."""
    records = [{"a": 1}, {"a": 2}, {"a": 3}]
    out = helpers_mod.dataframe_to_dict(records)

    assert out == {"data": records, "rows": 3}
    assert "columns" not in out


def test_dataframe_to_dict_empty_list_branch() -> None:
    """Empty list still hits the list branch (isinstance check, not truthiness)."""
    out = helpers_mod.dataframe_to_dict([])

    assert out == {"data": [], "rows": 0}


def test_dataframe_to_dict_fallback_scalar() -> None:
    """Non-DataFrame, non-list input falls through to the bare {'data': x} envelope."""
    out = helpers_mod.dataframe_to_dict(42)

    assert out == {"data": 42}


def test_dataframe_to_dict_fallback_dict() -> None:
    """A bare dict is NOT a DataFrame/list, so it lands in the fallback branch wrapped as data."""
    payload = {"nested": [1, 2, 3]}
    out = helpers_mod.dataframe_to_dict(payload)

    assert out == {"data": payload}
    assert "rows" not in out
