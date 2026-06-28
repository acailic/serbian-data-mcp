"""Offline tests for the untested public surface of api/client.py UDataClient.

Covers the 9 client methods (search_datasets, get_dataset, _find_resource,
get_resource_data, suggest_datasets, get_dataset_resources, get_reuses,
get_organization_datasets, search_with_facets) and the async context-manager
entry/exit, none of which had direct coverage in test_api.py (which only
exercised _request/retry/URL-validation). Uses the established mock-client
pattern: a fresh UDataClient with `_client` swapped for a fake whose
`request(method, url, **kw)` returns scripted httpx.Response objects, so the
real _request caching/retry/raise_for_status logic runs with no network.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import httpx
import pandas as pd
import pytest

from serbian_data_mcp.api import UDataClient
from serbian_data_mcp.api.models import Resource
from serbian_data_mcp.exceptions import (
    ConnectionError as SDConnectionError,
)
from serbian_data_mcp.exceptions import (
    DataParsingError,
    DatasetNotFoundError,
    ResourceNotFoundError,
)

_API = "https://data.gov.rs"


# -- Fakes -----------------------------------------------------------------


def _resp(status_code: int = 200, json_data: Any = None, headers: Optional[dict[str, str]] = None) -> httpx.Response:
    """Build a real httpx.Response so raise_for_status/json/status_code all work."""
    req = httpx.Request("GET", f"{_API}/api/1/x")
    return httpx.Response(
        status_code, json=json_data if json_data is not None else {}, headers=headers or {}, request=req
    )


class _FakeClient:
    """Stand-in for the API httpx.AsyncClient.

    `request` is an async callable returning scripted responses; `aclose` records
    whether the client was closed by UDataClient.close().
    """

    def __init__(self, request_handler: Callable[..., Any]) -> None:
        self.request = request_handler
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


class _FakeExtClient:
    """Stand-in for the cross-domain download client (only `.get` + aclose used)."""

    def __init__(self, get_handler: Callable[..., Any]) -> None:
        self._get_handler = get_handler
        self.closed = False

    async def get(self, url: str, **kw: Any) -> Any:
        return await self._get_handler(url)

    async def aclose(self) -> None:
        self.closed = True


class _MemCache:
    """In-memory cache stand-in so tests neither hit disk nor leak across clients.

    The real ResponseCache is backed by config.cache_dir on disk and keyed by
    URL+params, so GET responses persist across UDataClient instances; swapping to an
    in-memory per-instance cache here isolates each test and avoids disk pollution.
    Keys include the params (serialized) so distinct query strings to the same
    endpoint do not collide — matching the real cache's URL+params semantics.
    """

    def __init__(self) -> None:
        self.store: dict[tuple[str, str, str], Any] = {}

    @staticmethod
    def _pkey(params: Any) -> str:
        import json

        return json.dumps(params, sort_keys=True, default=str) if params else ""

    def get(self, method: str, url: str, params: Any = None, ttl: Any = None) -> Any:
        return self.store.get((method, url, self._pkey(params)))

    def set(self, method: str, url: str, params: Any = None, data: Any = None) -> None:
        self.store[(method, url, self._pkey(params))] = data


async def _ok(_url: str) -> httpx.Response:
    return _resp(200, json_data=None)


async def _not_found(_url: str) -> httpx.Response:
    return _resp(404)


def _wire_request(client: UDataClient, handler: Callable[..., Any]) -> None:
    """Replace the client's API transport + cache with fakes (no disk, no network)."""
    client._client = _FakeClient(handler)  # type: ignore[assignment]
    client._cache = _MemCache()  # type: ignore[assignment]


def _no_cache(client: UDataClient) -> None:
    """Swap the disk-backed ResponseCache for an in-memory one (no disk I/O, no leak)."""
    client._cache = _MemCache()  # type: ignore[assignment]


def _make_resource(**overrides: Any) -> Resource:
    base = {"id": "res-1", "title": "R", "format": "csv", "url": "https://data.gov.rs/d.csv"}
    base.update(overrides)
    return Resource.from_dict(base)


# -- search_datasets -------------------------------------------------------


@pytest.mark.asyncio
async def test_search_datasets_success_with_filters() -> None:
    captured: dict[str, Any] = {}

    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        captured.update(kw)
        captured["method"] = method
        return _resp(200, {"data": [{"id": "d1", "title": "D1"}], "total": 1})

    client = UDataClient()
    _wire_request(client, handler)
    result = await client.search_datasets(query="pop", format="csv", organization="org-x", page_size=5, page=2)
    assert captured["method"] == "GET"
    assert captured["params"] == {"q": "pop", "rows": 5, "start": 5, "format": "csv", "organization": "org-x"}
    assert len(result.datasets) == 1
    assert result.datasets[0].id == "d1"
    assert result.total == 1
    assert result.page == 2 and result.page_size == 5


@pytest.mark.asyncio
async def test_search_datasets_empty() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(200, {"data": [], "total": 0})

    client = UDataClient()
    _wire_request(client, handler)
    result = await client.search_datasets()
    assert result.datasets == []
    assert result.total == 0


# -- get_dataset -----------------------------------------------------------


@pytest.mark.asyncio
async def test_get_dataset_success() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(200, {"id": "ds-9", "title": "Niners", "tags": ["a", {"name": "b"}]})

    client = UDataClient()
    _wire_request(client, handler)
    ds = await client.get_dataset("ds-9")
    assert ds is not None
    assert ds.id == "ds-9"
    assert ds.title == "Niners"
    assert ds.tags == ["a", "b"]


@pytest.mark.asyncio
async def test_get_dataset_404_raises_not_found() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(404)

    client = UDataClient()
    _wire_request(client, handler)
    with pytest.raises(DatasetNotFoundError):
        await client.get_dataset("missing")


@pytest.mark.asyncio
async def test_get_dataset_propagates_other_http_errors() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(500)

    client = UDataClient()
    _wire_request(client, handler)
    with pytest.raises(httpx.HTTPStatusError):
        await client.get_dataset("boom")


# -- _find_resource --------------------------------------------------------


@pytest.mark.asyncio
async def test_find_resource_strategy_one_hit() -> None:
    payload = {"data": [{"id": "ds-1", "resources": [{"id": "res-1", "title": "R", "format": "csv"}]}]}

    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(200, payload)

    client = UDataClient()
    _wire_request(client, handler)
    res = await client._find_resource("res-1")
    assert res is not None
    assert res.id == "res-1"


@pytest.mark.asyncio
async def test_find_resource_strategy_two_paginated_hit() -> None:
    """Strategy-1 misses, strategy-2 paginated scan (page-1 non-empty, page-2 empty) finds it."""

    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        start = (kw.get("params") or {}).get("start", 0)
        if start == 0 and (kw.get("params") or {}).get("rows") == 20:
            return _resp(200, {"data": [{"id": "ds-x", "resources": []}]})  # strategy-1 miss
        # strategy-2 pagination: page-1 has the resource, page-2 empty stops the loop
        if start == 0:
            return _resp(200, {"data": [{"id": "ds-1", "resources": [{"id": "res-9", "title": "R", "format": "csv"}]}]})
        return _resp(200, {"data": []})

    client = UDataClient()
    _wire_request(client, handler)
    res = await client._find_resource("res-9")
    assert res is not None
    assert res.id == "res-9"


@pytest.mark.asyncio
async def test_find_resource_returns_none_when_not_found() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(200, {"data": []})  # all pages empty

    client = UDataClient()
    _wire_request(client, handler)
    res = await client._find_resource("ghost")
    assert res is None


# -- get_resource_data -----------------------------------------------------


@pytest.mark.asyncio
async def test_get_resource_data_missing_resource(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _none(_rid: str) -> None:
        return None

    client = UDataClient()
    monkeypatch.setattr(client, "_find_resource", _none)
    with pytest.raises(ResourceNotFoundError):
        await client.get_resource_data("ghost")


@pytest.mark.asyncio
async def test_get_resource_data_missing_url_or_format(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _ret(_rid: str) -> Resource:
        return Resource(id="res-1", title="R")  # no url/format

    client = UDataClient()
    monkeypatch.setattr(client, "_find_resource", _ret)
    with pytest.raises(DataParsingError):
        await client.get_resource_data("res-1")


@pytest.mark.asyncio
async def test_get_resource_data_csv_download_and_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

    async def _find(_rid: str) -> Resource:
        return _make_resource(format="csv", url="https://data.gov.rs/d.csv")

    async def _parse(response: Any, fmt: str) -> pd.DataFrame:
        assert fmt == "csv"
        return df

    client = UDataClient()
    _no_cache(client)
    monkeypatch.setattr(client, "_find_resource", _find)
    monkeypatch.setattr("serbian_data_mcp.data.parsers.parse_resource", _parse)

    ext = _FakeExtClient(_ok)
    client._external_client = ext  # type: ignore[assignment]

    out = await client.get_resource_data("res-1")
    assert isinstance(out, pd.DataFrame)
    # cached now: a second call must NOT re-download (parse_resource not re-invoked)
    calls = {"n": 0}

    async def _parse2(response: Any, fmt: str) -> pd.DataFrame:
        calls["n"] += 1
        return df

    monkeypatch.setattr("serbian_data_mcp.data.parsers.parse_resource", _parse2)
    cached = await client.get_resource_data("res-1")
    assert isinstance(cached, pd.DataFrame)
    assert calls["n"] == 0  # served from cache, parser not called


@pytest.mark.asyncio
async def test_get_resource_data_json_download(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _find(_rid: str) -> Resource:
        return _make_resource(format="json", url="https://data.gov.rs/d.json")

    async def _parse(response: Any, fmt: str) -> dict[str, Any]:
        return {"k": "v"}

    client = UDataClient()
    _no_cache(client)
    monkeypatch.setattr(client, "_find_resource", _find)
    monkeypatch.setattr("serbian_data_mcp.data.parsers.parse_resource", _parse)
    client._external_client = _FakeExtClient(_ok)  # type: ignore[assignment]
    out = await client.get_resource_data("res-1")
    assert out == {"k": "v"}


@pytest.mark.asyncio
async def test_get_resource_data_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _find(_rid: str) -> Resource:
        return _make_resource(url="https://data.gov.rs/d.csv")

    client = UDataClient()
    _no_cache(client)
    monkeypatch.setattr(client, "_find_resource", _find)
    client._external_client = _FakeExtClient(_not_found)  # type: ignore[assignment]
    with pytest.raises(SDConnectionError):
        await client.get_resource_data("res-1")


@pytest.mark.asyncio
async def test_get_resource_data_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _find(_rid: str) -> Resource:
        return _make_resource(url="https://data.gov.rs/d.csv")

    async def _boom(response: Any, fmt: str) -> None:
        raise ValueError("bad bytes")

    client = UDataClient()
    _no_cache(client)
    monkeypatch.setattr(client, "_find_resource", _find)
    monkeypatch.setattr("serbian_data_mcp.data.parsers.parse_resource", _boom)
    client._external_client = _FakeExtClient(_ok)  # type: ignore[assignment]
    with pytest.raises(DataParsingError):
        await client.get_resource_data("res-1")


@pytest.mark.asyncio
async def test_get_resource_data_connect_error_after_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover the ConnectError/Timeout retry-exhausted → ConnectionError branch without real sleeps."""

    async def _find(_rid: str) -> Resource:
        return _make_resource(url="https://data.gov.rs/d.csv")

    async def _sleep_noop(_delay: float) -> None:
        return None

    async def _get(url: str) -> httpx.Response:
        raise httpx.ConnectError("down")

    client = UDataClient()
    _no_cache(client)
    monkeypatch.setattr(client, "_find_resource", _find)
    monkeypatch.setattr("asyncio.sleep", _sleep_noop)
    client._external_client = _FakeExtClient(_get)  # type: ignore[assignment]
    with pytest.raises(SDConnectionError):
        await client.get_resource_data("res-1")


# -- suggest_datasets ------------------------------------------------------


@pytest.mark.asyncio
async def test_suggest_datasets_list_response() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        assert kw["params"] == {"q": "po", "size": 5, "format": "csv"}
        return _resp(200, ["pop", "populacija"])

    client = UDataClient()
    _wire_request(client, handler)
    out = await client.suggest_datasets("po", format="csv", size=5)
    assert out == ["pop", "populacija"]


@pytest.mark.asyncio
async def test_suggest_datasets_dict_response() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(200, {"results": ["a", "b"]})

    client = UDataClient()
    _wire_request(client, handler)
    out = await client.suggest_datasets("x")
    assert out == ["a", "b"]


@pytest.mark.asyncio
async def test_suggest_datasets_empty_other_type() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(200, 42)  # neither list nor dict -> []

    client = UDataClient()
    _wire_request(client, handler)
    assert await client.suggest_datasets("x") == []


@pytest.mark.asyncio
async def test_suggest_datasets_http_error_returns_empty() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(404)  # 4xx raises immediately (no retry), caught -> []

    client = UDataClient()
    _wire_request(client, handler)
    assert await client.suggest_datasets("x") == []


# -- get_dataset_resources -------------------------------------------------


@pytest.mark.asyncio
async def test_get_dataset_resources_success() -> None:
    payload = {
        "resources": [{"id": "r1", "title": "R1", "format": "csv"}, {"id": "r2", "title": "R2", "format": "json"}]
    }

    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(200, payload)

    client = UDataClient()
    _wire_request(client, handler)
    res = await client.get_dataset_resources("ds-1")
    assert [r.id for r in res] == ["r1", "r2"]


@pytest.mark.asyncio
async def test_get_dataset_resources_404() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(404)

    client = UDataClient()
    _wire_request(client, handler)
    with pytest.raises(DatasetNotFoundError):
        await client.get_dataset_resources("missing")


# -- get_reuses ------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_reuses_list_response() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(200, [{"id": "reuse-1"}])

    client = UDataClient()
    _wire_request(client, handler)
    assert await client.get_reuses("ds-1") == [{"id": "reuse-1"}]


@pytest.mark.asyncio
async def test_get_reuses_dict_response() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(200, {"data": [{"id": "reuse-2"}]})

    client = UDataClient()
    _wire_request(client, handler)
    assert await client.get_reuses("ds-1") == [{"id": "reuse-2"}]


@pytest.mark.asyncio
async def test_get_reuses_empty_other_type() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(200, "nope")

    client = UDataClient()
    _wire_request(client, handler)
    assert await client.get_reuses("ds-1") == []


@pytest.mark.asyncio
async def test_get_reuses_404() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        return _resp(404)

    client = UDataClient()
    _wire_request(client, handler)
    with pytest.raises(DatasetNotFoundError):
        await client.get_reuses("missing")


# -- get_organization_datasets --------------------------------------------


@pytest.mark.asyncio
async def test_get_organization_datasets_success() -> None:
    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        assert kw["params"]["organization"] == "org-x"
        assert kw["params"]["rows"] == 5
        assert kw["params"]["start"] == 5
        return _resp(200, {"data": [{"id": "d1", "title": "D1"}]})

    client = UDataClient()
    _wire_request(client, handler)
    out = await client.get_organization_datasets("org-x", page_size=5, page=2)
    assert len(out) == 1 and out[0].id == "d1"


# -- search_with_facets ----------------------------------------------------


@pytest.mark.asyncio
async def test_search_with_facets_all_filters() -> None:
    captured: dict[str, Any] = {}

    async def handler(method: str, url: str, **kw: Any) -> httpx.Response:
        captured.update(kw["params"])
        return _resp(200, {"data": [{"id": "d1", "title": "D1"}], "total": 1})

    client = UDataClient()
    _wire_request(client, handler)
    result = await client.search_with_facets(
        query="pop",
        tags=["t1", "t2"],
        organization="org",
        schema="sc",
        format="csv",
        license="CC-BY-4.0",
        temporal_coverage="2020-2024",
        geozone="RS",
        page_size=3,
        page=2,
    )
    assert captured["q"] == "pop"
    assert captured["tag"] == ["t1", "t2"]
    assert captured["organization"] == "org"
    assert captured["schema"] == "sc"
    assert captured["format"] == "csv"
    assert captured["license"] == "CC-BY-4.0"
    assert captured["temporal_coverage"] == "2020-2024"
    assert captured["geozone"] == "RS"
    assert captured["rows"] == 3 and captured["start"] == 3
    assert len(result.datasets) == 1 and result.total == 1


# -- async context manager -------------------------------------------------


@pytest.mark.asyncio
async def test_aenter_returns_self() -> None:
    client = UDataClient()
    assert await client.__aenter__() is client
    await client.close()


@pytest.mark.asyncio
async def test_aexit_closes_clients() -> None:
    client = UDataClient()
    await client._get_client()
    await client._get_external_client()
    assert client._client is not None
    assert client._external_client is not None
    await client.__aexit__(None, None, None)
    assert client._client is None
    assert client._external_client is None
