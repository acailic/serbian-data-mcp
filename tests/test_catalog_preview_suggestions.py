"""Offline unit tests for the catalog-layer preview + suggestion engines.

Covers catalog/preview.py and catalog/suggestions.py — both core MCP infra
that previously had only ~14-15% coverage (exercised indirectly via tool
wrappers with faked classes). All tests are deterministic and network-free:
the UDataClient and SearchEngine are replaced with fakes via monkeypatch.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from serbian_data_mcp.catalog import preview as preview_mod
from serbian_data_mcp.catalog import search as search_mod
from serbian_data_mcp.catalog.exceptions import DatasetNotFound
from serbian_data_mcp.catalog.models import CachedDataset, SearchResult
from serbian_data_mcp.catalog.preview import DatasetPreview
from serbian_data_mcp.catalog.suggestions import AlternativeSuggestions


# ---------------------------------------------------------------------------
# Shared fakes
# ---------------------------------------------------------------------------


def _dataset(
    ds_id: str = "ds-1",
    *,
    title: str = "Stanovništvo",
    formats: list[str] | None = None,
    has_downloadable: bool = True,
    resource_count: int = 1,
) -> CachedDataset:
    return CachedDataset(
        id=ds_id,
        title=title,
        description="Opis",
        organization="RZS",
        formats=formats if formats is not None else ["csv"],
        tags=["population"],
        created_at="2020-01-01",
        modified_at="2020-02-01",
        resource_count=resource_count,
        has_downloadable=has_downloadable,
    )


def _result(
    ds_id: str = "ds-1",
    score: float = 0.9,
    keywords: list[str] | None = None,
    dataset: CachedDataset | None = None,
) -> SearchResult:
    return SearchResult(
        dataset=dataset if dataset is not None else _dataset(ds_id),
        relevance_score=score,
        matched_keywords=keywords if keywords is not None else ["pop"],
        match_reason="title",
    )


class _FakeSearchEngine:
    """Stand-in for SearchEngine with a per-query scripted async search()."""

    def __init__(self, results: dict[str, list[SearchResult]] | None = None) -> None:
        self._results = results or {}
        self.calls: list[dict[str, Any]] = []

    async def search(self, query: str, max_results: int = 10, min_score: float = 0.0) -> list[SearchResult]:
        self.calls.append({"query": query, "max_results": max_results, "min_score": min_score})
        return list(self._results.get(query, []))


class _FakeClient:
    """Stand-in for UDataClient with scriptable async get_dataset/get_resource_data."""

    def __init__(
        self,
        *,
        dataset: Any = None,
        resource_data: Any = None,
        raise_on_dataset: Exception | None = None,
    ) -> None:
        self._dataset = dataset
        self._resource_data = resource_data
        self._raise = raise_on_dataset

    async def get_dataset(self, dataset_id: str) -> Any:
        if self._raise is not None:
            raise self._raise
        return self._dataset

    async def get_resource_data(self, resource_id: str) -> Any:
        return self._resource_data


class _FakeCatalog:
    """Stand-in for DatasetCatalog with a scriptable get()."""

    def __init__(self, datasets: dict[str, CachedDataset] | None = None) -> None:
        self._datasets = datasets or {}

    def get(self, dataset_id: str) -> CachedDataset | None:
        return self._datasets.get(dataset_id)


def _full_dataset(resources: list[Any] | None) -> SimpleNamespace:
    return SimpleNamespace(resources=resources if resources is not None else [])


def _resource(rid: str, fmt: str = "csv") -> SimpleNamespace:
    return SimpleNamespace(id=rid, title=f"R {rid}", description="d", format=fmt, url=f"https://x/{rid}")


# ===========================================================================
# AlternativeSuggestions
# ===========================================================================


@pytest.mark.asyncio
async def test_suggest_returns_partial_results_sorted_limited() -> None:
    eng = _FakeSearchEngine({"pop": [_result("a", 0.5), _result("b", 0.8), _result("c", 0.2)]})
    sug = AlternativeSuggestions(_FakeCatalog(), eng)  # type: ignore[arg-type]
    out = await sug.suggest("pop", max_alternatives=2)
    assert [d.dataset.id for d in out.datasets] == ["b", "a"]  # sorted desc, capped at 2
    assert out.total_alternatives == 2
    assert "No exact match" in out.explanation
    # strategy 1 used max_results = max_alternatives*2 with min_score=0.1
    assert eng.calls[0] == {"query": "pop", "max_results": 4, "min_score": 0.1}


@pytest.mark.asyncio
async def test_suggest_strategy2_terms_when_no_partial() -> None:
    # main query empty, but each term returns a result -> strategy 2 fires
    eng = _FakeSearchEngine({"pop popu": [], "pop": [_result("a", 0.6)], "popu": [_result("b", 0.4)]})
    sug = AlternativeSuggestions(_FakeCatalog(), eng)  # type: ignore[arg-type]
    out = await sug.suggest("pop popu", max_alternatives=5)
    assert sorted(d.dataset.id for d in out.datasets) == ["a", "b"]
    # strategy-2 calls use max_results=3, min_score=0.2
    term_calls = eng.calls[1:]
    assert all(c["max_results"] == 3 and c["min_score"] == 0.2 for c in term_calls)


@pytest.mark.asyncio
async def test_suggest_strategy2_breaks_at_max_alternatives() -> None:
    # each term returns 3 results; max_alternatives=2 → loop breaks after first term fills
    eng = _FakeSearchEngine(
        {
            "nope": [],
            "t1": [_result("a", 0.6), _result("b", 0.5), _result("c", 0.4)],
            "t2": [_result("d", 0.3)],
        }
    )
    sug = AlternativeSuggestions(_FakeCatalog(), eng)  # type: ignore[arg-type]
    out = await sug.suggest("t1 t2", max_alternatives=2)
    assert out.total_alternatives == 2
    assert len(eng.calls) == 2  # main "t1 t2" + only first term "t1" (broke at max)


@pytest.mark.asyncio
async def test_suggest_dedup_keeps_highest_score() -> None:
    dup_ds = _dataset("same")
    eng = _FakeSearchEngine({"q": [_result("same", 0.3, dataset=dup_ds), _result("same", 0.9, dataset=dup_ds)]})
    sug = AlternativeSuggestions(_FakeCatalog(), eng)  # type: ignore[arg-type]
    out = await sug.suggest("q", max_alternatives=5)
    assert len(out.datasets) == 1
    assert out.datasets[0].relevance_score == 0.9


@pytest.mark.asyncio
async def test_deduplicate_keeps_first_then_higher_score() -> None:
    sug = AlternativeSuggestions(_FakeCatalog(), _FakeSearchEngine())  # type: ignore[arg-type]
    ds = _dataset("x")
    kept = sug._deduplicate([_result("x", 0.2, dataset=ds), _result("x", 0.7, dataset=ds)])
    assert len(kept) == 1 and kept[0].relevance_score == 0.7
    # distinct ids preserved
    ds2 = _dataset("y")
    multi = sug._deduplicate([_result("x", 0.5, dataset=ds), _result("y", 0.4, dataset=ds2)])
    assert sorted(r.dataset.id for r in multi) == ["x", "y"]


@pytest.mark.asyncio
async def test_explain_no_datasets() -> None:
    sug = AlternativeSuggestions(_FakeCatalog(), _FakeSearchEngine())  # type: ignore[arg-type]
    msg = sug._explain_suggestion("zzz", [])
    assert msg == "No matching datasets found for 'zzz'. Try different keywords."


@pytest.mark.asyncio
async def test_explain_with_keywords() -> None:
    sug = AlternativeSuggestions(_FakeCatalog(), _FakeSearchEngine())  # type: ignore[arg-type]
    msg = sug._explain_suggestion("q", [_result("a", 1.0, keywords=["pop", "demo"])])
    assert "found 1 relevant dataset(s)" in msg
    assert "pop, demo" in msg or "demo, pop" in msg  # sorted join


@pytest.mark.asyncio
async def test_explain_with_more_than_five_keywords() -> None:
    sug = AlternativeSuggestions(_FakeCatalog(), _FakeSearchEngine())  # type: ignore[arg-type]
    kws = [f"k{i}" for i in range(7)]
    msg = sug._explain_suggestion("q", [_result("a", 1.0, keywords=kws)])
    assert "(and 2 more)" in msg


@pytest.mark.asyncio
async def test_explain_without_keywords() -> None:
    sug = AlternativeSuggestions(_FakeCatalog(), _FakeSearchEngine())  # type: ignore[arg-type]
    msg = sug._explain_suggestion("q", [_result("a", 1.0, keywords=[])])
    assert "potentially relevant datasets" in msg


@pytest.mark.asyncio
async def test_suggest_by_format_prioritizes_preferred() -> None:
    csv_res = _result("csv", 0.4, dataset=_dataset("csv", formats=["csv"]))
    xls_res = _result("xls", 0.9, dataset=_dataset("xls", formats=["xlsx"]))
    eng = _FakeSearchEngine({"q": [xls_res, csv_res]})
    sug = AlternativeSuggestions(_FakeCatalog(), eng)  # type: ignore[arg-type]
    out = await sug.suggest_by_format("q", preferred_format="csv")
    # csv result listed first despite lower score (format prioritized)
    assert out.datasets[0].dataset.id == "csv"
    assert "prioritizing CSV format" in out.explanation
    assert eng.calls[0]["max_results"] == 50 and eng.calls[0]["min_score"] == 0.1


@pytest.mark.asyncio
async def test_suggest_by_format_no_preferred_present_no_suffix() -> None:
    xls_res = _result("xls", 0.9, dataset=_dataset("xls", formats=["xlsx"]))
    eng = _FakeSearchEngine({"q": [xls_res]})
    sug = AlternativeSuggestions(_FakeCatalog(), eng)  # type: ignore[arg-type]
    out = await sug.suggest_by_format("q", preferred_format="csv")
    assert "prioritizing" not in out.explanation
    assert out.datasets[0].dataset.id == "xls"


@pytest.mark.asyncio
async def test_suggest_empty_query_no_results_anywhere() -> None:
    eng = _FakeSearchEngine({"": []})
    sug = AlternativeSuggestions(_FakeCatalog(), eng)  # type: ignore[arg-type]
    out = await sug.suggest("", max_alternatives=3)
    assert out.datasets == []
    assert "No matching datasets found" in out.explanation


# ===========================================================================
# DatasetPreview
# ===========================================================================


@pytest.mark.asyncio
async def test_preview_dataset_not_found_raises() -> None:
    catalog = _FakeCatalog({})  # no datasets
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    with pytest.raises(DatasetNotFound):
        await preview.preview_dataset("missing")


@pytest.mark.asyncio
async def test_preview_dataframe_resource_path(monkeypatch: pytest.MonkeyPatch) -> None:
    ds = _dataset("ds1", has_downloadable=True, formats=["csv"])
    catalog = _FakeCatalog({"ds1": ds})
    full = _full_dataset([_resource("r1", "csv")])
    df = pd.DataFrame({"age": ["0-18", "19-30", "31-50"], "count": [10, 20, 30]})
    client = _FakeClient(dataset=full, resource_data=df)
    monkeypatch.setattr(preview_mod, "UDataClient", lambda: client)
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    out = await preview.preview_dataset("ds1", nrows=2)
    assert out["sample_data"] == [{"age": "0-18", "count": 10}, {"age": "19-30", "count": 20}]
    assert out["columns"] == ["age", "count"]
    assert out["preview_reason"] == "Showing first 2 rows from CSV resource"
    assert out["metadata"]["title"] == "Stanovništvo"
    assert out["metadata"]["resource_count"] == 1


@pytest.mark.asyncio
async def test_preview_list_resource_path(monkeypatch: pytest.MonkeyPatch) -> None:
    ds = _dataset("ds1", has_downloadable=True, formats=["json"])
    catalog = _FakeCatalog({"ds1": ds})
    full = _full_dataset([_resource("r1", "json")])
    data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}, {"a": 5, "b": 6}]
    client = _FakeClient(dataset=full, resource_data=data)
    monkeypatch.setattr(preview_mod, "UDataClient", lambda: client)
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    out = await preview.preview_dataset("ds1", nrows=2)
    assert out["sample_data"] == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    assert out["columns"] == ["a", "b"]
    assert out["preview_reason"] == "Showing first 2 rows from JSON resource"


@pytest.mark.asyncio
async def test_preview_dict_resource_path(monkeypatch: pytest.MonkeyPatch) -> None:
    ds = _dataset("ds1", has_downloadable=True, formats=["json"])
    catalog = _FakeCatalog({"ds1": ds})
    full = _full_dataset([_resource("r1", "json")])
    client = _FakeClient(dataset=full, resource_data={"x": 1, "y": 2})
    monkeypatch.setattr(preview_mod, "UDataClient", lambda: client)
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    out = await preview.preview_dataset("ds1")
    assert out["sample_data"] == {"x": 1, "y": 2}
    assert out["columns"] == ["x", "y"]
    assert out["preview_reason"] == "Showing JSON object structure"


@pytest.mark.asyncio
async def test_preview_resource_data_none(monkeypatch: pytest.MonkeyPatch) -> None:
    ds = _dataset("ds1", has_downloadable=True, formats=["csv"])
    catalog = _FakeCatalog({"ds1": ds})
    full = _full_dataset([_resource("r1", "csv")])
    client = _FakeClient(dataset=full, resource_data=None)
    monkeypatch.setattr(preview_mod, "UDataClient", lambda: client)
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    out = await preview.preview_dataset("ds1")
    assert out["sample_data"] is None
    assert out["preview_reason"] == "Resource available but data download failed"


@pytest.mark.asyncio
async def test_preview_no_csv_json_resource(monkeypatch: pytest.MonkeyPatch) -> None:
    ds = _dataset("ds1", has_downloadable=True, formats=["xlsx", "pdf"])
    catalog = _FakeCatalog({"ds1": ds})
    full = _full_dataset([_resource("r1", "xlsx")])
    client = _FakeClient(dataset=full)
    monkeypatch.setattr(preview_mod, "UDataClient", lambda: client)
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    out = await preview.preview_dataset("ds1")
    assert out["sample_data"] is None
    assert out["preview_reason"] == "No CSV/JSON resource available (formats: xlsx, pdf)"


@pytest.mark.asyncio
async def test_preview_no_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    ds = _dataset("ds1", has_downloadable=True, formats=[])
    catalog = _FakeCatalog({"ds1": ds})
    full = _full_dataset([])  # empty resources
    client = _FakeClient(dataset=full)
    monkeypatch.setattr(preview_mod, "UDataClient", lambda: client)
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    out = await preview.preview_dataset("ds1")
    assert out["preview_reason"] == "Dataset has no resources"


@pytest.mark.asyncio
async def test_preview_no_downloadable_metadata_only() -> None:
    ds = _dataset("ds1", has_downloadable=False, formats=[])
    catalog = _FakeCatalog({"ds1": ds})
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    out = await preview.preview_dataset("ds1")
    assert out["sample_data"] is None
    assert out["preview_reason"] == "Dataset has no downloadable resources (metadata only)"
    assert out["metadata"]["has_downloadable"] is False


@pytest.mark.asyncio
async def test_preview_exception_path(monkeypatch: pytest.MonkeyPatch) -> None:
    ds = _dataset("ds1", has_downloadable=True, formats=["csv"])
    catalog = _FakeCatalog({"ds1": ds})
    client = _FakeClient(raise_on_dataset=RuntimeError("boom"))
    monkeypatch.setattr(preview_mod, "UDataClient", lambda: client)
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    out = await preview.preview_dataset("ds1")
    assert out["preview_reason"].startswith("Preview failed:")
    assert "boom" in out["preview_reason"]
    assert out["sample_data"] is None


@pytest.mark.asyncio
async def test_preview_metadata_keys_complete() -> None:
    ds = _dataset("ds1", has_downloadable=False)
    catalog = _FakeCatalog({"ds1": ds})
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    out = await preview.preview_dataset("ds1")
    md = out["metadata"]
    assert set(md.keys()) == {
        "id",
        "title",
        "description",
        "organization",
        "formats",
        "tags",
        "resource_count",
        "has_downloadable",
        "created_at",
        "modified_at",
    }
    assert md["id"] == "ds1" and md["organization"] == "RZS"


@pytest.mark.asyncio
async def test_preview_by_query_builds_previews(monkeypatch: pytest.MonkeyPatch) -> None:
    ds = _dataset("ds1", has_downloadable=False)
    catalog = _FakeCatalog({"ds1": ds})
    fake_engine = _FakeSearchEngine({"pop": [_result("ds1", 0.9, dataset=ds)]})
    monkeypatch.setattr(search_mod, "SearchEngine", lambda cat: fake_engine)
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    out = await preview.preview_by_query("pop", max_results=3)
    assert out["query"] == "pop"
    assert out["total_matches"] == 1
    assert len(out["previews"]) == 1
    assert out["previews"][0]["metadata"]["id"] == "ds1"
    assert "Showing top 1 of 1 matches" in out["note"]


@pytest.mark.asyncio
async def test_preview_by_query_result_not_in_catalog_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    # search returns a result whose dataset_id is NOT in the catalog → preview_dataset
    # raises DatasetNotFound inside the loop → caught → metadata-only preview appended
    catalog = _FakeCatalog({})  # catalog knows nothing
    orphan_ds = _dataset("orphan", has_downloadable=True)
    fake_engine = _FakeSearchEngine({"pop": [_result("orphan", 0.9, dataset=orphan_ds)]})
    monkeypatch.setattr(search_mod, "SearchEngine", lambda cat: fake_engine)
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    out = await preview.preview_by_query("pop")
    assert out["total_matches"] == 1
    assert len(out["previews"]) == 1
    # metadata-only fallback carries the result's dataset dict, not a None sample
    assert out["previews"][0]["metadata"]["id"] == "orphan"
    assert out["previews"][0]["sample_data"] is None
    assert out["previews"][0]["preview_reason"].startswith("Preview failed:")


@pytest.mark.asyncio
async def test_preview_client_cached_on_second_call(monkeypatch: pytest.MonkeyPatch) -> None:
    # _get_client lazily builds UDataClient on first call, reuses on second (36->38 branch)
    ds = _dataset("ds1", has_downloadable=True, formats=["xlsx"])
    catalog = _FakeCatalog({"ds1": ds})
    full = _full_dataset([_resource("r1", "xlsx")])  # no csv/json → no download
    client = _FakeClient(dataset=full)
    monkeypatch.setattr(preview_mod, "UDataClient", lambda: client)
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    await preview.preview_dataset("ds1")
    first = preview._client
    await preview.preview_dataset("ds1")  # reuses cached client, factory NOT re-invoked
    assert preview._client is first


@pytest.mark.asyncio
async def test_preview_list_resource_empty_after_slice(monkeypatch: pytest.MonkeyPatch) -> None:
    # list branch with sample_data empty after slice → columns stays None (106->108 branch)
    ds = _dataset("ds1", has_downloadable=True, formats=["json"])
    catalog = _FakeCatalog({"ds1": ds})
    full = _full_dataset([_resource("r1", "json")])
    client = _FakeClient(dataset=full, resource_data=[{"a": 1, "b": 2}])
    monkeypatch.setattr(preview_mod, "UDataClient", lambda: client)
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    out = await preview.preview_dataset("ds1", nrows=0)
    assert out["sample_data"] == []  # [:0]
    assert out["columns"] is None  # empty list → columns block skipped


@pytest.mark.asyncio
async def test_preview_by_query_empty_results(monkeypatch: pytest.MonkeyPatch) -> None:
    ds = _dataset("ds1", has_downloadable=False)
    catalog = _FakeCatalog({"ds1": ds})
    fake_engine = _FakeSearchEngine({"pop": []})
    monkeypatch.setattr(search_mod, "SearchEngine", lambda cat: fake_engine)
    preview = DatasetPreview(catalog)  # type: ignore[arg-type]
    out = await preview.preview_by_query("pop")
    assert out["total_matches"] == 0
    assert out["previews"] == []
