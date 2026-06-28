"""Offline unit tests for the client-backed tools/search.py MCP tools.

Covers the five tools that had no direct coverage (intelligent_search and
preview_dataset are already exercised by test_ported_tools.py):
  - search_datasets       (result serialization + page/page_size clamping + error)
  - list_organizations     (org serialization + count + echo + clamping + error)
  - suggest_datasets       (suggestions envelope + size clamping + error)
  - search_by_tag          (tag-join query + result serialization + error)
  - get_portal_statistics  (both _request calls + contextlib.suppress fallbacks)

All tests are deterministic and network-free: the UDataClient singleton is
replaced with a fake via monkeypatch so behaviour runs without hitting
data.gov.rs. Real api.models dataclasses are used (not SimpleNamespaces) so
the serializers in _helpers exercise every field.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp.exceptions import ToolError

from serbian_data_mcp.api.models import Dataset, Organization, Resource, SearchResult
from serbian_data_mcp.tools import search as search_mod


# ---------------------------------------------------------------------------
# Fake client
# ---------------------------------------------------------------------------


class _FakeClient:
    """Stand-in for UDataClient with scriptable async search/suggest/_request."""

    def __init__(
        self,
        *,
        base_url: str = "https://data.gov.rs",
        search_result: SearchResult | None = None,
        search_captured: dict[str, Any] | None = None,
        search_error: Exception | None = None,
        organizations: list[Organization] | None = None,
        orgs_captured: dict[str, Any] | None = None,
        orgs_error: Exception | None = None,
        suggestions: list[str] | None = None,
        suggest_captured: dict[str, Any] | None = None,
        suggest_error: Exception | None = None,
        request_responses: dict[tuple[str, str], Any] | None = None,
        request_captured: list[dict[str, Any]] | None = None,
    ) -> None:
        self.base_url = base_url
        self._search_result = search_result
        self._search_captured = search_captured
        self._search_error = search_error
        self._organizations = organizations
        self._orgs_captured = orgs_captured
        self._orgs_error = orgs_error
        self._suggestions = suggestions
        self._suggest_captured = suggest_captured
        self._suggest_error = suggest_error
        self._request_responses = request_responses or {}
        self._request_captured = request_captured

    async def search_datasets(
        self,
        query: str = "",
        format: str | None = None,
        organization: str | None = None,
        page_size: int = 20,
        page: int = 1,
    ) -> SearchResult:
        if self._search_error is not None:
            raise self._search_error
        if self._search_captured is not None:
            self._search_captured.update(
                query=query, format=format, organization=organization, page_size=page_size, page=page
            )
        return self._search_result or SearchResult(datasets=[], total=0, page=1, page_size=page_size)

    async def list_organizations(self, page_size: int = 50, page: int = 1) -> list[Organization]:
        if self._orgs_error is not None:
            raise self._orgs_error
        if self._orgs_captured is not None:
            self._orgs_captured.update(page_size=page_size, page=page)
        return self._organizations or []

    async def suggest_datasets(self, query: str, format: str | None = None, size: int = 10) -> list[str]:
        if self._suggest_error is not None:
            raise self._suggest_error
        if self._suggest_captured is not None:
            self._suggest_captured.update(query=query, format=format, size=size)
        return self._suggestions or []

    async def _request(self, method: str, path: str, params: dict[str, Any] | None = None) -> Any:
        if self._request_captured is not None:
            self._request_captured.append({"method": method, "path": path, "params": params})
        key = (method, path)
        if key in self._request_responses:
            resp = self._request_responses[key]
            if isinstance(resp, Exception):
                raise resp
            return resp
        return {"total": 0}


def _patch_client(monkeypatch: pytest.MonkeyPatch, client: _FakeClient) -> None:
    async def _factory() -> _FakeClient:
        return client

    monkeypatch.setattr(search_mod.h, "get_client", _factory)


def _org(name: str = "РЗС") -> Organization:
    return Organization(id="org-1", name=name, description="d", url="https://x", logo=None)


def _dataset(dataset_id: str = "ds-1", title: str = "Stanovništvo") -> Dataset:
    return Dataset(
        id=dataset_id,
        title=title,
        description="opis",
        organization=_org(),
        resources=[Resource(id="r1", title="R1", format="csv")],
        tags=["populacija"],
    )


def _search_result() -> SearchResult:
    return SearchResult(datasets=[_dataset()], total=1, page=1, page_size=10)


# ===========================================================================
# search_datasets
# ===========================================================================


@pytest.mark.asyncio
async def test_search_datasets_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    client = _FakeClient(search_result=_search_result(), search_captured=captured)
    _patch_client(monkeypatch, client)

    result = await search_mod.search_datasets("stanovnistvo", format="csv", organization="org-1")

    assert result["total"] == 1
    assert result["datasets"][0]["id"] == "ds-1"
    assert result["datasets"][0]["organization"]["name"] == "РЗС"
    assert captured["query"] == "stanovnistvo"
    assert captured["format"] == "csv"
    assert captured["organization"] == "org-1"


@pytest.mark.asyncio
async def test_search_datasets_clamps_page_and_size(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    client = _FakeClient(search_result=_search_result(), search_captured=captured)
    _patch_client(monkeypatch, client)

    await search_mod.search_datasets("", page_size=150, page=0)

    assert captured["page_size"] == 100  # clamped down from 150
    assert captured["page"] == 1  # clamped up from 0


@pytest.mark.asyncio
async def test_search_datasets_error_wraps_toolerror(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient(search_error=RuntimeError("boom"))
    _patch_client(monkeypatch, client)

    with pytest.raises(ToolError, match="Search failed: boom"):
        await search_mod.search_datasets("x")


# ===========================================================================
# list_organizations
# ===========================================================================


@pytest.mark.asyncio
async def test_list_organizations_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    orgs = [_org("A"), _org("B")]
    client = _FakeClient(organizations=orgs, orgs_captured=captured)
    _patch_client(monkeypatch, client)

    result = await search_mod.list_organizations(page_size=25, page=2)

    assert [o["name"] for o in result["organizations"]] == ["A", "B"]
    assert result["count"] == 2
    assert result["page"] == 2
    assert result["page_size"] == 25
    assert captured["page_size"] == 25
    assert captured["page"] == 2


@pytest.mark.asyncio
async def test_list_organizations_clamps_page_size(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    client = _FakeClient(organizations=[], orgs_captured=captured)
    _patch_client(monkeypatch, client)

    await search_mod.list_organizations(page_size=500, page=-3)

    assert captured["page_size"] == 100  # clamped down
    assert captured["page"] == 1  # clamped up


@pytest.mark.asyncio
async def test_list_organizations_error_wraps_toolerror(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient(orgs_error=RuntimeError("nope"))
    _patch_client(monkeypatch, client)

    with pytest.raises(ToolError, match="Failed to list organizations: nope"):
        await search_mod.list_organizations()


# ===========================================================================
# suggest_datasets
# ===========================================================================


@pytest.mark.asyncio
async def test_suggest_datasets_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    client = _FakeClient(suggestions=["Stanovništvo", "Stari"], suggest_captured=captured)
    _patch_client(monkeypatch, client)

    result = await search_mod.suggest_datasets("sta", format="csv", size=5)

    assert result["suggestions"] == ["Stanovništvo", "Stari"]
    assert result["count"] == 2
    assert captured["query"] == "sta"
    assert captured["format"] == "csv"
    assert captured["size"] == 5


@pytest.mark.asyncio
async def test_suggest_datasets_clamps_size(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    client = _FakeClient(suggestions=[], suggest_captured=captured)
    _patch_client(monkeypatch, client)

    await search_mod.suggest_datasets("x", size=99)
    assert captured["size"] == 20  # clamped down

    await search_mod.suggest_datasets("x", size=0)
    assert captured["size"] == 1  # clamped up


@pytest.mark.asyncio
async def test_suggest_datasets_error_wraps_toolerror(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient(suggest_error=RuntimeError("bad"))
    _patch_client(monkeypatch, client)

    with pytest.raises(ToolError, match="Suggestions failed: bad"):
        await search_mod.suggest_datasets("x")


# ===========================================================================
# search_by_tag
# ===========================================================================


@pytest.mark.asyncio
async def test_search_by_tag_joins_tags_as_query(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    client = _FakeClient(search_result=_search_result(), search_captured=captured)
    _patch_client(monkeypatch, client)

    result = await search_mod.search_by_tag(["zdravlje", "statistika"])

    assert result["total"] == 1
    assert captured["query"] == "zdravlje statistika"  # space-joined tags
    assert captured["page_size"] == 10


@pytest.mark.asyncio
async def test_search_by_tag_clamps_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    client = _FakeClient(search_result=_search_result(), search_captured=captured)
    _patch_client(monkeypatch, client)

    await search_mod.search_by_tag(["t"], page_size=0, page=-1)

    assert captured["page_size"] == 1
    assert captured["page"] == 1


@pytest.mark.asyncio
async def test_search_by_tag_error_wraps_toolerror(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient(search_error=RuntimeError("fail"))
    _patch_client(monkeypatch, client)

    with pytest.raises(ToolError, match="Tag search failed: fail"):
        await search_mod.search_by_tag(["t"])


# ===========================================================================
# get_portal_statistics
# ===========================================================================


@pytest.mark.asyncio
async def test_get_portal_statistics_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    client = _FakeClient(
        request_responses={
            ("GET", "/api/1/datasets/"): {"total": 1234},
            ("GET", "/api/1/organizations/"): {"total": 42},
        },
        request_captured=captured,
    )
    _patch_client(monkeypatch, client)

    result = await search_mod.get_portal_statistics()

    assert result["total_datasets"] == 1234
    assert result["total_organizations"] == 42
    assert result["api_base"] == "https://data.gov.rs"
    assert result["portal_url"] == "https://data.gov.rs"
    # both endpoints queried exactly once each
    paths = [c["path"] for c in captured]
    assert paths.count("/api/1/datasets/") == 1
    assert paths.count("/api/1/organizations/") == 1


@pytest.mark.asyncio
async def test_get_portal_statistics_both_request_fail_defaults_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient(
        request_responses={
            ("GET", "/api/1/datasets/"): ConnectionError("down"),
            ("GET", "/api/1/organizations/"): ConnectionError("down"),
        }
    )
    _patch_client(monkeypatch, client)

    result = await search_mod.get_portal_statistics()

    # contextlib.suppress swallows both -> defaults stay 0
    assert result["total_datasets"] == 0
    assert result["total_organizations"] == 0


@pytest.mark.asyncio
async def test_get_portal_statistics_mixed_success_and_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeClient(
        request_responses={
            ("GET", "/api/1/datasets/"): {"total": 99},
            ("GET", "/api/1/organizations/"): RuntimeError("orgs down"),
        }
    )
    _patch_client(monkeypatch, client)

    result = await search_mod.get_portal_statistics()

    assert result["total_datasets"] == 99  # datasets call succeeded
    assert result["total_organizations"] == 0  # orgs call suppressed


# ===========================================================================
# intelligent_search + preview_dataset exception paths
# ===========================================================================


def _async_return(value: Any) -> Any:
    """Build an async factory returning a fixed value (for get_catalog patches)."""

    async def _factory() -> Any:
        return value

    return _factory


class _RaisingSearchEngine:
    """Stand-in SearchEngine whose search() always raises (exercises the wrap)."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def search(self, query: str, max_results: int = 10, min_score: float = 0.3) -> list[Any]:
        raise self._exc


class _RaisingPreview:
    """Stand-in DatasetPreview whose preview_dataset() raises a non-NotFound error."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def preview_dataset(self, dataset_id: str, nrows: int = 10) -> dict[str, Any]:
        raise self._exc


@pytest.mark.asyncio
async def test_intelligent_search_error_wraps_toolerror(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(search_mod.h, "get_catalog", _async_return(object()))
    monkeypatch.setattr(search_mod, "SearchEngine", lambda catalog: _RaisingSearchEngine(RuntimeError("engine-down")))

    with pytest.raises(ToolError, match="Intelligent search failed: engine-down"):
        await search_mod.intelligent_search("population")


@pytest.mark.asyncio
async def test_preview_dataset_generic_error_wraps_toolerror(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(search_mod.h, "get_catalog", _async_return(object()))
    monkeypatch.setattr(search_mod, "DatasetPreview", lambda catalog: _RaisingPreview(ValueError("preview broken")))

    with pytest.raises(ToolError, match="Preview failed: preview broken"):
        await search_mod.preview_dataset("ds-1")
