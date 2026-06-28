"""Offline tests for catalog/cache.py DatasetCatalog.

Covers the async load/build/save/refresh + helper paths that test_catalog.py
(get/len/contains/init) leaves untouched. All API I/O is faked; cache files are
written to tmp_path so no real network or home-dir pollution occurs.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from serbian_data_mcp.api.models import Dataset, Organization, Resource, SearchResult
from serbian_data_mcp.catalog import cache as cache_mod
from serbian_data_mcp.catalog.cache import CACHE_AGE_LIMIT, CACHE_VERSION, DatasetCatalog
from serbian_data_mcp.catalog.exceptions import CatalogBuildError, CatalogLoadError


# --------------------------------------------------------------------------- #
# Fakes / fixtures
# --------------------------------------------------------------------------- #


class _FakeClient:
    """Async UDataClient stand-in returning scripted search_datasets responses.

    ``responses`` is a list of dataset-lists consumed in call order (call 0 is
    the page_size=1 first_page probe inside build_catalog; calls 1..N are the
    pagination loop). ``raise_on_call`` is a set of call indices that raise.
    """

    def __init__(self, responses, total, raise_on_call=None):
        self._responses = list(responses)
        self._total = total
        self._raise_on_call = raise_on_call or set()
        self.calls: list[dict] = []

    async def search_datasets(self, page_size=10, page=1, **kwargs):
        idx = len(self.calls)
        self.calls.append({"page_size": page_size, "page": page})
        if idx in self._raise_on_call:
            raise RuntimeError(f"boom on call {idx}")
        datasets = self._responses.pop(0) if self._responses else []
        return SearchResult(datasets=datasets, total=self._total, page=page, page_size=page_size)


def _make_dataset(
    ds_id="ds-1",
    title="Demo",
    *,
    org_name="Org A",
    formats=("csv",),
    tags=("t1", "t2"),
    created_at=None,
    modified_at=None,
):
    resources = [Resource(id=f"r{i}", title=f"res{i}", format=fm) for i, fm in enumerate(formats)]
    org = Organization(id="o1", name=org_name) if org_name is not None else None
    return Dataset(
        id=ds_id,
        title=title,
        resources=resources,
        tags=list(tags),
        organization=org,
        created_at=created_at,
        modified_at=modified_at,
    )


@pytest.fixture
def cache_path(tmp_path):
    return tmp_path / "catalog.json"


@pytest.fixture
def fresh_catalog(cache_path):
    return DatasetCatalog(cache_path=cache_path)


# --------------------------------------------------------------------------- #
# __init__ default cache_path (lines 43-46)
# --------------------------------------------------------------------------- #


def test_init_default_cache_path_uses_home(monkeypatch, tmp_path):
    monkeypatch.setattr(cache_mod.Path, "home", lambda: tmp_path)
    catalog = DatasetCatalog()
    assert catalog.cache_path == tmp_path / ".serbian-data-mcp" / "cache" / "catalog.json"
    assert (tmp_path / ".serbian-data-mcp" / "cache").is_dir()


# --------------------------------------------------------------------------- #
# _get_client create + cache (lines 53-57)
# --------------------------------------------------------------------------- #


async def test_get_client_creates_and_caches_singleton(monkeypatch, fresh_catalog):
    created = []

    def _factory(*args, **kwargs):
        inst = object()
        created.append(inst)
        return inst

    monkeypatch.setattr(cache_mod, "UDataClient", _factory)
    c1 = await fresh_catalog._get_client()
    c2 = await fresh_catalog._get_client()
    assert c1 is c2
    assert len(created) == 1
    assert fresh_catalog._client is c1


# --------------------------------------------------------------------------- #
# initialize (lines 59-78)
# --------------------------------------------------------------------------- #


def _write_valid_cache(path, datasets_data=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": CACHE_VERSION,
        "built_at": datetime.now(UTC).isoformat(),
        "total_datasets": len(datasets_data or {}),
        "datasets": datasets_data or {},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


async def test_initialize_loads_from_cache(fresh_catalog, cache_path):
    _write_valid_cache(cache_path, {"ds-1": {"id": "ds-1", "title": "T", "description": "", "organization": ""}})
    await fresh_catalog.initialize()
    assert fresh_catalog._initialized is True
    assert len(fresh_catalog) == 1
    assert fresh_catalog.get("ds-1").title == "T"


async def test_initialize_idempotent_when_already_initialized(fresh_catalog):
    fresh_catalog._initialized = True
    fresh_catalog._client = None  # must NOT be touched (no build attempted)
    await fresh_catalog.initialize()
    assert fresh_catalog._initialized is True
    assert fresh_catalog._client is None  # initialize short-circuited, no client created


async def test_initialize_no_cache_builds_from_api(fresh_catalog):
    ds = _make_dataset("ds-1", formats=("csv",))
    fresh_catalog._client = _FakeClient(responses=[[], [ds]], total=1)
    await fresh_catalog.initialize()
    assert fresh_catalog._initialized is True
    assert len(fresh_catalog) == 1
    assert fresh_catalog.get("ds-1") is not None


async def test_initialize_force_refresh_builds_even_with_cache(fresh_catalog, cache_path):
    _write_valid_cache(cache_path, {"stale": {"id": "stale", "title": "old"}})
    ds = _make_dataset("ds-new", formats=("json",))
    fresh_catalog._client = _FakeClient(responses=[[], [ds]], total=1)
    await fresh_catalog.initialize(force_refresh=True)
    assert fresh_catalog.get("ds-new") is not None
    assert fresh_catalog.get("stale") is None  # cache discarded on force build


# --------------------------------------------------------------------------- #
# _load_cache branches (lines 80-125)
# --------------------------------------------------------------------------- #


async def test_load_cache_missing_file_returns_false(fresh_catalog):
    assert await fresh_catalog._load_cache() is False


async def test_load_cache_version_mismatch_returns_false(fresh_catalog, cache_path):
    cache_path.write_text(json.dumps({"version": "0.0", "built_at": "", "datasets": {}}))
    assert await fresh_catalog._load_cache() is False


async def test_load_cache_expired_returns_false(fresh_catalog, cache_path):
    stale = (datetime.now(UTC) - (CACHE_AGE_LIMIT + timedelta(hours=1))).isoformat()
    cache_path.write_text(json.dumps({"version": CACHE_VERSION, "built_at": stale, "datasets": {}}))
    assert await fresh_catalog._load_cache() is False


async def test_load_cache_invalid_timestamp_returns_false(fresh_catalog, cache_path):
    cache_path.write_text(json.dumps({"version": CACHE_VERSION, "built_at": "not-a-timestamp", "datasets": {}}))
    assert await fresh_catalog._load_cache() is False


async def test_load_cache_corrupt_json_raises(fresh_catalog, cache_path):
    cache_path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(CatalogLoadError):
        await fresh_catalog._load_cache()


async def test_load_cache_generic_read_failure_returns_false(fresh_catalog, tmp_path):
    # cache_path pointing at a directory -> open() raises non-JSONDecodeError
    fresh_catalog.cache_path = tmp_path
    assert await fresh_catalog._load_cache() is False


async def test_load_cache_valid_loads_datasets(fresh_catalog, cache_path):
    _write_valid_cache(
        cache_path,
        {
            "ds-1": {
                "id": "ds-1",
                "title": "T",
                "description": "desc",
                "organization": "Org",
                "formats": ["csv"],
                "has_downloadable": True,
            }
        },
    )
    assert await fresh_catalog._load_cache() is True
    assert fresh_catalog.get("ds-1").has_downloadable is True


# --------------------------------------------------------------------------- #
# build_catalog (lines 127-178)
# --------------------------------------------------------------------------- #


async def test_build_catalog_happy_multipage(fresh_catalog, cache_path):
    ds1 = _make_dataset("ds-1", formats=("csv",), org_name="Org A")
    ds2 = _make_dataset("ds-2", formats=("json", "pdf"), org_name="Org B")
    fresh_catalog._client = _FakeClient(responses=[[], [ds1, ds2]], total=2)
    await fresh_catalog.build_catalog()
    assert len(fresh_catalog) == 2
    assert fresh_catalog.get("ds-1").organization == "Org A"
    # pdf is not downloadable -> ds-2 has_downloadable True only because json counts
    assert fresh_catalog.get("ds-2").has_downloadable is True
    assert cache_path.exists()  # cache saved


async def test_build_catalog_empty_datasets_breaks_loop(fresh_catalog):
    fresh_catalog._client = _FakeClient(responses=[[], []], total=1)
    await fresh_catalog.build_catalog()
    assert len(fresh_catalog) == 0


async def test_build_catalog_inner_page_error_raises(fresh_catalog):
    ds1 = _make_dataset("ds-1")
    # call 0 (first_page) ok, call 1 (loop page) raises -> inner except
    fresh_catalog._client = _FakeClient(responses=[[ds1], []], total=1, raise_on_call={1})
    with pytest.raises(CatalogBuildError):
        await fresh_catalog.build_catalog()


async def test_build_catalog_outer_first_page_error_raises(fresh_catalog):
    # call 0 (first_page) raises -> outer except
    fresh_catalog._client = _FakeClient(responses=[[]], total=1, raise_on_call={0})
    with pytest.raises(CatalogBuildError):
        await fresh_catalog.build_catalog()


# --------------------------------------------------------------------------- #
# _dataset_to_cached (lines 180-209)
# --------------------------------------------------------------------------- #


def test_dataset_to_cached_full(fresh_catalog):
    ds = _make_dataset(
        "ds-1",
        title="Demo",
        org_name="Org A",
        formats=("csv", None, "pdf"),  # None format skipped
        created_at=datetime(2020, 1, 1),
        modified_at=datetime(2021, 6, 15),
    )
    cached = fresh_catalog._dataset_to_cached(ds)
    assert cached.id == "ds-1"
    assert cached.organization == "Org A"
    assert cached.formats == ["csv", "pdf"]  # None skipped
    assert cached.resource_count == 3  # all resources counted
    assert cached.has_downloadable is True  # csv present
    assert cached.created_at.startswith("2020-01-01")
    assert cached.modified_at.startswith("2021-06-15")


def test_dataset_to_cached_no_org_no_dates_non_downloadable(fresh_catalog):
    ds = _make_dataset("ds-2", org_name=None, formats=("pdf",), created_at=None, modified_at=None)
    cached = fresh_catalog._dataset_to_cached(ds)
    assert cached.organization == ""
    assert cached.created_at == ""
    assert cached.modified_at == ""
    assert cached.has_downloadable is False  # pdf only


def test_dataset_to_cached_title_description_none(fresh_catalog):
    ds = Dataset(id="x", title=None, description=None, organization=None, resources=[], tags=[])
    cached = fresh_catalog._dataset_to_cached(ds)
    assert cached.title == ""
    assert cached.description == ""


# --------------------------------------------------------------------------- #
# _save_cache (lines 211-240)
# --------------------------------------------------------------------------- #


async def test_save_cache_writes_atomic_file(fresh_catalog, cache_path):
    fresh_catalog.datasets["ds-1"] = fresh_catalog._dataset_to_cached(_make_dataset("ds-1"))
    await fresh_catalog._save_cache()
    assert cache_path.exists()
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    assert data["version"] == CACHE_VERSION
    assert data["total_datasets"] == 1
    assert "ds-1" in data["datasets"]
    # temp file replaced, not left behind
    assert not cache_path.with_suffix(".tmp").exists()


async def test_save_cache_failure_raises(tmp_path):
    # parent's parent is a file -> mkdir(parents=True) raises NotADirectoryError
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    bad_path = blocker / "sub" / "catalog.json"
    catalog = DatasetCatalog(cache_path=bad_path)
    with pytest.raises(CatalogBuildError):
        await catalog._save_cache()


# --------------------------------------------------------------------------- #
# refresh (lines 242-258)
# --------------------------------------------------------------------------- #


async def test_refresh_rebuilds_and_returns_stats(fresh_catalog, cache_path):
    ds1 = _make_dataset("ds-1", formats=("csv",))
    fresh_catalog._client = _FakeClient(responses=[[], [ds1]], total=1)
    stats = await fresh_catalog.refresh()
    assert stats["total_datasets"] == 1
    assert stats["cache_path"] == str(cache_path)
    assert "built_at" in stats
    assert cache_path.exists()
    assert fresh_catalog.get("ds-1") is not None


# --------------------------------------------------------------------------- #
# get_all / __contains__ / empty-built_at (lines 271-285, 103->115)
# --------------------------------------------------------------------------- #


def test_get_all_returns_values_list(fresh_catalog):
    fresh_catalog.datasets = {
        "ds-1": fresh_catalog._dataset_to_cached(_make_dataset("ds-1")),
        "ds-2": fresh_catalog._dataset_to_cached(_make_dataset("ds-2")),
    }
    all_ds = fresh_catalog.get_all()
    assert len(all_ds) == 2
    assert {d.id for d in all_ds} == {"ds-1", "ds-2"}
    # distinct objects each call (no shared mutable aliasing)
    assert fresh_catalog.get_all() is not fresh_catalog.get_all()


def test_contains_membership_check(fresh_catalog):
    fresh_catalog.datasets = {"ds-1": fresh_catalog._dataset_to_cached(_make_dataset("ds-1"))}
    assert "ds-1" in fresh_catalog
    assert "missing" not in fresh_catalog


async def test_load_cache_empty_built_at_skips_age_check(fresh_catalog, cache_path):
    # valid version + empty built_at -> skips age/expires branch (line 103->115),
    # still loads datasets
    cache_path.write_text(json.dumps({"version": CACHE_VERSION, "built_at": "", "datasets": {}}))
    assert await fresh_catalog._load_cache() is True
    assert len(fresh_catalog.datasets) == 0
