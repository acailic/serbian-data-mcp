"""Offline unit tests for the untested tools/data.py MCP tools.

Covers the four data-retrieval tools that had no direct coverage:
  - get_dataset          (all 4 detail_levels + not-found paths)
  - get_resource_data    (DataFrame/dict/list/str + error)
  - compare_datasets     (success + per-dataset not-found paths)
  - browse_recent_datasets (recency filter + days/page_size clamping)

Also indirectly exercises the private _dataset_summary helper.

All tests are deterministic and network-free: the UDataClient singleton
is replaced with a fake via monkeypatch so behaviour runs without
hitting data.gov.rs. Real api.models dataclasses are used (not
SimpleNamespaces) so the serializers in _helpers exercise every field.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
import pytest
from fastmcp.exceptions import ToolError

from serbian_data_mcp.api.models import Dataset, Organization, Resource, SearchResult
from serbian_data_mcp.tools import data as data_mod


# ---------------------------------------------------------------------------
# Fake client
# ---------------------------------------------------------------------------


class _FakeClient:
    """Stand-in for UDataClient with scriptable async dataset/resource/search."""

    def __init__(
        self,
        *,
        dataset: Any = None,
        dataset_error: Exception | None = None,
        dataset_map: dict[str, Any] | None = None,
        resource_data: Any = None,
        resource_error: Exception | None = None,
        search_result: SearchResult | None = None,
        search_captured: dict[str, Any] | None = None,
    ) -> None:
        self._dataset = dataset
        self._dataset_error = dataset_error
        self._dataset_map = dataset_map or {}
        self._resource_data = resource_data
        self._resource_error = resource_error
        self._search_result = search_result
        self._search_captured = search_captured

    async def get_dataset(self, dataset_id: str) -> Any:
        if self._dataset_error is not None:
            raise self._dataset_error
        if dataset_id in self._dataset_map:
            return self._dataset_map[dataset_id]
        return self._dataset

    async def get_resource_data(self, resource_id: str) -> Any:
        if self._resource_error is not None:
            raise self._resource_error
        return self._resource_data

    async def search_datasets(
        self,
        query: str = "",
        page_size: int = 20,
        page: int = 1,
    ) -> SearchResult:
        if self._search_captured is not None:
            self._search_captured.update(query=query, page_size=page_size, page=page)
        return self._search_result or SearchResult(datasets=[], total=0, page=1, page_size=page_size)


def _patch_client(monkeypatch: pytest.MonkeyPatch, client: _FakeClient) -> None:
    async def _factory() -> _FakeClient:
        return client

    monkeypatch.setattr(data_mod.h, "get_client", _factory)


def _org(name: str = "РЗС") -> Organization:
    return Organization(id="org-1", name=name, description="d", url="https://x", logo=None)


_ORG_DEFAULT = object()  # sentinel so callers can pass organization=None explicitly


def _dataset(
    dataset_id: str = "ds-1",
    *,
    title: str = "Stanovništvo",
    resources: list[Resource] | None = None,
    tags: list[str] | None = None,
    organization: Any = _ORG_DEFAULT,
    quality: dict[str, Any] | None = None,
    modified_at: datetime | None = None,
) -> Dataset:
    return Dataset(
        id=dataset_id,
        title=title,
        description="opis",
        organization=_org() if organization is _ORG_DEFAULT else organization,
        resources=resources if resources is not None else [],
        tags=tags if tags is not None else ["populacija", "demografija"],
        modified_at=modified_at,
        frequency="annual",
        temporal_coverage="2020 to 2024",
        quality=quality,
    )


# ===========================================================================
# get_dataset
# ===========================================================================


@pytest.mark.asyncio
async def test_get_dataset_metadata_default(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_dataset

    ds = _dataset(resources=[Resource(id="r1", title="R1", format="csv")])
    _patch_client(monkeypatch, _FakeClient(dataset=ds))

    result = await get_dataset("ds-1")

    assert result["id"] == "ds-1"
    assert result["title"] == "Stanovništvo"
    assert result["organization"]["name"] == "РЗС"
    assert [r["id"] for r in result["resources"]] == ["r1"]


@pytest.mark.asyncio
async def test_get_dataset_resources_level(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_dataset

    ds = _dataset(
        resources=[Resource(id="r1", title="R1", format="csv"), Resource(id="r2", title="R2", format="json")],
    )
    _patch_client(monkeypatch, _FakeClient(dataset=ds))

    result = await get_dataset("ds-1", detail_level="resources")

    assert result["dataset_id"] == "ds-1"
    assert result["count"] == 2
    assert [r["format"] for r in result["resources"]] == ["csv", "json"]


@pytest.mark.asyncio
async def test_get_dataset_summary_level(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_dataset

    ds = _dataset(
        resources=[Resource(id="r1", title="R1", format="csv"), Resource(id="r2", title="R2", format="csv")],
        tags=["a", "b", "c"],
        quality={"score": 87},
    )
    _patch_client(monkeypatch, _FakeClient(dataset=ds))

    result = await get_dataset("ds-1", detail_level="summary")

    assert result["id"] == "ds-1"
    assert result["organization"] == "РЗС"
    assert result["resource_count"] == 2
    assert result["formats"] == ["csv"]
    assert result["quality_score"] == 87


@pytest.mark.asyncio
async def test_get_dataset_summary_no_org_uses_na(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_dataset

    ds = _dataset(organization=None, tags=[])
    _patch_client(monkeypatch, _FakeClient(dataset=ds))

    result = await get_dataset("ds-1", detail_level="summary")

    assert result["organization"] == "N/A"
    assert result["tags"] == []
    assert result["quality_score"] is None  # quality None → None


@pytest.mark.asyncio
async def test_get_dataset_preview_with_dataframe(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_dataset

    ds = _dataset(resources=[Resource(id="r1", title="R1", format="csv")])
    df = pd.DataFrame({"region": ["BG", "NS", "NI", "NS", "BG", "NI", "BG", "NS", "NI", "BG", "NS", "NI"]})
    _patch_client(monkeypatch, _FakeClient(dataset=ds, resource_data=df))

    result = await get_dataset("ds-1", detail_level="preview")

    assert result["id"] == "ds-1"
    assert len(result["preview_data"]) == 10  # head(10)
    assert result["preview_columns"] == ["region"]
    assert result["preview_rows"] == 12  # full row count


@pytest.mark.asyncio
async def test_get_dataset_preview_no_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_dataset

    ds = _dataset(resources=[])
    _patch_client(monkeypatch, _FakeClient(dataset=ds))

    result = await get_dataset("ds-1", detail_level="preview")

    assert result["preview_error"] == "No downloadable resources"


@pytest.mark.asyncio
async def test_get_dataset_preview_download_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_dataset

    ds = _dataset(resources=[Resource(id="r1", title="R1", format="csv")])
    _patch_client(monkeypatch, _FakeClient(dataset=ds, resource_error=RuntimeError("boom")))

    result = await get_dataset("ds-1", detail_level="preview")

    assert "boom" in result["preview_error"]


@pytest.mark.asyncio
async def test_get_dataset_not_found_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_dataset

    _patch_client(monkeypatch, _FakeClient(dataset_error=RuntimeError("404")))

    with pytest.raises(ToolError, match="not found"):
        await get_dataset("missing")


@pytest.mark.asyncio
async def test_get_dataset_not_found_none(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_dataset

    _patch_client(monkeypatch, _FakeClient(dataset=None))

    with pytest.raises(ToolError, match="not found"):
        await get_dataset("missing")


# ===========================================================================
# get_resource_data
# ===========================================================================


@pytest.mark.asyncio
async def test_get_resource_data_dataframe(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_resource_data

    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    _patch_client(monkeypatch, _FakeClient(resource_data=df))

    result = await get_resource_data("r1")

    assert result["columns"] == ["a", "b"]
    assert result["rows"] == 2
    assert result["data"][0]["a"] == 1


@pytest.mark.asyncio
async def test_get_resource_data_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_resource_data

    _patch_client(monkeypatch, _FakeClient(resource_data={"k": "v"}))

    result = await get_resource_data("r1")

    assert result == {"data": {"k": "v"}}


@pytest.mark.asyncio
async def test_get_resource_data_list(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_resource_data

    _patch_client(monkeypatch, _FakeClient(resource_data=[1, 2, 3]))

    result = await get_resource_data("r1")

    assert result == {"data": [1, 2, 3]}


@pytest.mark.asyncio
async def test_get_resource_data_scalar_string(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_resource_data

    _patch_client(monkeypatch, _FakeClient(resource_data=42))

    result = await get_resource_data("r1")

    assert result == {"data": "42"}


@pytest.mark.asyncio
async def test_get_resource_data_error_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import get_resource_data

    _patch_client(monkeypatch, _FakeClient(resource_error=RuntimeError("network down")))

    with pytest.raises(ToolError, match="Failed to download resource"):
        await get_resource_data("r1")


# ===========================================================================
# compare_datasets
# ===========================================================================


@pytest.mark.asyncio
async def test_compare_datasets_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import compare_datasets

    ds1 = _dataset(
        "ds-1",
        title="A",
        organization=_org("РЗС"),
        resources=[Resource(id="r1", title="R1", format="csv")],
        tags=["pop", "econ"],
    )
    ds2 = _dataset(
        "ds-2",
        title="B",
        organization=_org("РЗС"),
        resources=[Resource(id="r2", title="R2", format="json"), Resource(id="r3", title="R3", format="csv")],
        tags=["pop", "health"],
    )
    _patch_client(monkeypatch, _FakeClient(dataset_map={"ds-1": ds1, "ds-2": ds2}))

    result = await compare_datasets("ds-1", "ds-2")

    assert result["dataset_1"]["id"] == "ds-1"
    assert result["dataset_2"]["id"] == "ds-2"
    assert result["comparison"]["same_organization"] is True
    assert result["comparison"]["resource_count_diff"] == -1  # 1 - 2
    assert "csv" in result["comparison"]["shared_formats"]
    assert "json" in result["comparison"]["unique_formats_2"]
    assert "pop" in result["comparison"]["shared_tags"]


@pytest.mark.asyncio
async def test_compare_datasets_ds1_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import compare_datasets

    _patch_client(monkeypatch, _FakeClient(dataset_error=RuntimeError("404")))

    with pytest.raises(ToolError, match="Dataset 'ds-1' not found"):
        await compare_datasets("ds-1", "ds-2")


@pytest.mark.asyncio
async def test_compare_datasets_ds2_none(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import compare_datasets

    ds1 = _dataset("ds-1")
    # ds-1 returns ds1, ds-2 returns None (not in map, default dataset=None)
    _patch_client(monkeypatch, _FakeClient(dataset=None, dataset_map={"ds-1": ds1}))

    with pytest.raises(ToolError, match="Dataset 'ds-2' not found"):
        await compare_datasets("ds-1", "ds-2")


# ===========================================================================
# browse_recent_datasets
# ===========================================================================


@pytest.mark.asyncio
async def test_browse_recent_filters_and_clamps(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import browse_recent_datasets

    now = datetime.now(UTC)
    recent = _dataset("ds-recent", modified_at=now)
    stale = _dataset("ds-stale", modified_at=now - timedelta(days=400))
    result = SearchResult(datasets=[recent, stale], total=2, page=1, page_size=20)
    _patch_client(monkeypatch, _FakeClient(search_result=result))

    out = await browse_recent_datasets(days=9999, page_size=9999)

    # days/page_size clamped to [1,365] / [1,100]
    assert out["days_back"] == 365
    assert out["total_returned"] == 1  # only ds-recent passes midnight-today cutoff
    assert out["datasets"][0]["id"] == "ds-recent"


@pytest.mark.asyncio
async def test_browse_recent_clamps_page_size_search_arg(monkeypatch: pytest.MonkeyPatch) -> None:
    from serbian_data_mcp.tools.data import browse_recent_datasets

    captured: dict[str, Any] = {}
    result = SearchResult(datasets=[], total=0, page=1, page_size=20)
    _patch_client(monkeypatch, _FakeClient(search_result=result, search_captured=captured))

    await browse_recent_datasets(days=7, page_size=5000)

    assert captured["page_size"] == 100  # clamped
    assert captured["query"] == ""
    assert captured["page"] == 1
