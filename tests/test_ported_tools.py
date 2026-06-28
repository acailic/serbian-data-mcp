"""Offline unit tests for tools ported from the retired tools.py monolith.

Covers iters 8-11 ports that previously had no direct test coverage:
  - get_config_tool      (resources.py)
  - get_catalog_stats     (resources.py)
  - refresh_catalog       (resources.py)
  - get_dataset_resources (data.py)
  - get_data_summary      (data.py)

All tests are deterministic and network-free: the API client and catalog
singletons are replaced with fakes via monkeypatch so behaviour is exercised
without hitting data.gov.rs.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest
from fastmcp.exceptions import ToolError

from serbian_data_mcp.tools import data as data_mod
from serbian_data_mcp.tools import resources as resources_mod


# ---------------------------------------------------------------------------
# Fake helpers
# ---------------------------------------------------------------------------


class _FakeClient:
    """Stand-in for UDataClient with scriptable async methods."""

    def __init__(
        self,
        *,
        resource_data: Any = None,
        resource_error: Exception | None = None,
        dataset: Any = None,
        dataset_error: Exception | None = None,
    ) -> None:
        self._resource_data = resource_data
        self._resource_error = resource_error
        self._dataset = dataset
        self._dataset_error = dataset_error

    async def get_resource_data(self, resource_id: str) -> Any:
        if self._resource_error is not None:
            raise self._resource_error
        return self._resource_data

    async def get_dataset(self, dataset_id: str) -> Any:
        if self._dataset_error is not None:
            raise self._dataset_error
        return self._dataset


class _FakeCatalog:
    """Stand-in for DatasetCatalog exercising stats/refresh code paths."""

    def __init__(self, datasets: list[Any], cache_path: Path) -> None:
        self._datasets = datasets
        self.cache_path = cache_path  # real Path → .exists()/.stat() work

    def get_all(self) -> list[Any]:
        return self._datasets

    def __len__(self) -> int:
        return len(self._datasets)

    async def refresh(self) -> dict[str, Any]:
        return {
            "total_datasets": len(self._datasets),
            "cache_path": str(self.cache_path),
            "built_at": "2026-01-01T00:00:00Z",
        }


def _fake_dataset(dataset_id: str = "ds-1", resources: list[Any] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=dataset_id,
        title=f"Dataset {dataset_id}",
        resources=resources if resources is not None else [],
    )


def _fake_resource(rid: str, fmt: str = "csv") -> SimpleNamespace:
    return SimpleNamespace(
        id=rid,
        title=f"Resource {rid}",
        description="d",
        format=fmt,
        url=f"https://x/{rid}",
        size=100,
        mime_type="text/csv",
    )


def _patch_client(monkeypatch: pytest.MonkeyPatch, client: _FakeClient) -> None:
    async def _factory() -> _FakeClient:
        return client

    monkeypatch.setattr(data_mod.h, "get_client", _factory)


def _patch_catalog(monkeypatch: pytest.MonkeyPatch, catalog: _FakeCatalog) -> None:
    async def _factory() -> _FakeCatalog:
        return catalog

    monkeypatch.setattr(resources_mod.h, "get_catalog", _factory)


# ===========================================================================
# get_config_tool
# ===========================================================================


@pytest.mark.asyncio
async def test_get_config_tool_returns_resolved_settings() -> None:
    from serbian_data_mcp.tools.resources import get_config_tool

    result = await get_config_tool()

    assert set(result) == {"api_base", "rate_limit", "timeout", "cache_dir", "export_dir"}
    assert isinstance(result["api_base"], str) and result["api_base"].startswith("http")
    assert all(isinstance(result[k], str) for k in ("cache_dir", "export_dir"))
    assert isinstance(result["rate_limit"], (int, float))
    assert isinstance(result["timeout"], (int, float))


# ===========================================================================
# get_dataset_resources
# ===========================================================================


@pytest.mark.asyncio
async def test_get_dataset_resources_lists_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_dataset_resources

    ds = _fake_dataset(resources=[_fake_resource("r1", "csv"), _fake_resource("r2", "json")])
    _patch_client(monkeypatch, _FakeClient(dataset=ds))

    result = await get_dataset_resources("ds-1")

    assert result["dataset_id"] == "ds-1"
    assert result["count"] == 2
    assert [r["id"] for r in result["resources"]] == ["r1", "r2"]
    assert result["resources"][0]["format"] == "csv"


@pytest.mark.asyncio
async def test_get_dataset_resources_not_found_none(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_dataset_resources

    _patch_client(monkeypatch, _FakeClient(dataset=None))

    with pytest.raises(ToolError, match="not found"):
        await get_dataset_resources("missing-ds")


@pytest.mark.asyncio
async def test_get_dataset_resources_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_dataset_resources

    _patch_client(monkeypatch, _FakeClient(dataset_error=RuntimeError("boom")))

    with pytest.raises(ToolError, match="not found"):
        await get_dataset_resources("ds-1")


# ===========================================================================
# get_data_summary
# ===========================================================================


@pytest.mark.asyncio
async def test_get_data_summary_tabular(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_data_summary

    df = pd.DataFrame({"region": ["BG", "NS", "NI"], "value": [1, 2, 3]})
    _patch_client(monkeypatch, _FakeClient(resource_data=df))

    result = await get_data_summary("r1")

    assert result["format"] == "tabular"
    assert result["estimated_rows"] == 3
    assert result["resource_id"] == "r1"
    assert [c["name"] for c in result["columns"]] == ["region", "value"]
    assert result["columns"][0]["sample_values"] == ["BG", "NS", "NI"]


@pytest.mark.asyncio
async def test_get_data_summary_json_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_data_summary

    payload = {"items": [1, 2, 3], "meta": {"page": 1}, "name": "x"}
    _patch_client(monkeypatch, _FakeClient(resource_data=payload))

    result = await get_data_summary("r1")

    assert result["format"] == "json-dict"
    assert result["estimated_rows"] == "N/A (dict structure)"
    assert result["sample"]["items"] == {"type": "list", "length": 3, "first_items": [1, 2, 3]}
    assert result["sample"]["meta"] == {"type": "dict", "keys": ["page"]}


@pytest.mark.asyncio
async def test_get_data_summary_json_list_of_dicts(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_data_summary

    payload = [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
    _patch_client(monkeypatch, _FakeClient(resource_data=payload))

    result = await get_data_summary("r1")

    assert result["format"] == "json-list"
    assert result["estimated_rows"] == 2
    assert sorted(c["name"] for c in result["columns"]) == ["id", "name"]


@pytest.mark.asyncio
async def test_get_data_summary_json_list_of_scalars(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_data_summary

    _patch_client(monkeypatch, _FakeClient(resource_data=[1, 2, 3]))

    result = await get_data_summary("r1")

    assert result["format"] == "json-list-scalar"
    assert result["estimated_rows"] == 3
    assert result["columns"] == []
    assert result["sample"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_get_data_summary_download_error_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_data_summary

    _patch_client(monkeypatch, _FakeClient(resource_error=RuntimeError("network down")))

    with pytest.raises(ToolError, match="Failed to summarize"):
        await get_data_summary("r1")


# ===========================================================================
# get_catalog_stats
# ===========================================================================


@pytest.mark.asyncio
async def test_get_catalog_stats_aggregates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from serbian_data_mcp.tools.resources import get_catalog_stats

    cache_file = tmp_path / "catalog.json"
    cache_file.write_text("[]")  # exists → cache_age_hours computed
    datasets = [
        SimpleNamespace(organization="РЗС", formats=["csv", "json"], has_downloadable=True),
        SimpleNamespace(organization="Министарство финансија", formats=["csv"], has_downloadable=False),
        SimpleNamespace(organization=None, formats=["xlsx"], has_downloadable=True),
    ]
    _patch_catalog(monkeypatch, _FakeCatalog(datasets, cache_path=cache_file))

    result = await get_catalog_stats()

    assert result["total_datasets"] == 3
    assert result["total_organizations"] == 2  # None excluded
    assert result["total_formats"] == 3  # csv, json, xlsx
    assert result["downloadable_datasets"] == 2
    assert "csv" in result["formats"]
    assert result["cache_exists"] is True
    assert result["cache_age_hours"] is not None


@pytest.mark.asyncio
async def test_get_catalog_stats_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from serbian_data_mcp.tools.resources import get_catalog_stats

    cache_file = tmp_path / "missing.json"  # does not exist
    _patch_catalog(monkeypatch, _FakeCatalog([], cache_path=cache_file))

    result = await get_catalog_stats()

    assert result["total_datasets"] == 0
    assert result["total_organizations"] == 0
    assert result["downloadable_datasets"] == 0
    assert result["cache_exists"] is False
    assert result["cache_age_hours"] is None


# ===========================================================================
# refresh_catalog
# ===========================================================================


@pytest.mark.asyncio
async def test_refresh_catalog_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from serbian_data_mcp.tools.resources import refresh_catalog

    datasets = [SimpleNamespace(organization="X", formats=["csv"], has_downloadable=True)]
    _patch_catalog(monkeypatch, _FakeCatalog(datasets, cache_path=tmp_path / "catalog.json"))

    result = await refresh_catalog()

    assert result["total_datasets"] == 1
    assert "duration_seconds" in result
    assert "timestamp" in result
    assert result["cache_path"].endswith("catalog.json")


@pytest.mark.asyncio
async def test_refresh_catalog_failure_raises_toolerror(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from serbian_data_mcp.tools.resources import refresh_catalog

    class _BrokenCatalog(_FakeCatalog):
        async def refresh(self) -> dict[str, Any]:
            raise RuntimeError("rate limited")

    _patch_catalog(monkeypatch, _BrokenCatalog([], cache_path=tmp_path / "catalog.json"))

    with pytest.raises(ToolError, match="Catalog refresh failed"):
        await refresh_catalog()
