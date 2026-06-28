"""Tests for API response caching."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from serbian_data_mcp.api.cache import ResponseCache


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Return a clean temp directory for cache tests."""
    d = tmp_path / "cache"
    d.mkdir()
    return d


class TestResponseCacheInit:
    """Test cache initialization."""

    def test_creates_cache_directory(self, cache_dir: Path) -> None:
        new_dir = cache_dir / "sub"
        ResponseCache(new_dir)
        assert new_dir.exists()

    def test_default_ttl(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        assert cache.default_ttl == 300

    def test_custom_ttl(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir, default_ttl=60)
        assert cache.default_ttl == 60


class TestCacheKeyGeneration:
    """Test deterministic cache key generation."""

    def test_same_params_same_key(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        key1 = cache._cache_key("GET", "/api/test", {"q": "hello"})
        key2 = cache._cache_key("GET", "/api/test", {"q": "hello"})
        assert key1 == key2

    def test_different_method_different_key(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        key1 = cache._cache_key("GET", "/api/test")
        key2 = cache._cache_key("POST", "/api/test")
        assert key1 != key2

    def test_different_url_different_key(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        key1 = cache._cache_key("GET", "/api/test1")
        key2 = cache._cache_key("GET", "/api/test2")
        assert key1 != key2

    def test_different_params_different_key(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        key1 = cache._cache_key("GET", "/api/test", {"q": "a"})
        key2 = cache._cache_key("GET", "/api/test", {"q": "b"})
        assert key1 != key2

    def test_no_params_same_as_empty_dict(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        key1 = cache._cache_key("GET", "/api/test")
        key2 = cache._cache_key("GET", "/api/test", {})
        assert key1 == key2

    def test_param_order_irrelevant(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        key1 = cache._cache_key("GET", "/api/test", {"b": 1, "a": 2})
        key2 = cache._cache_key("GET", "/api/test", {"a": 2, "b": 1})
        assert key1 == key2


class TestCacheGet:
    """Test cache retrieval."""

    def test_cache_miss(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        result = cache.get("GET", "/nonexistent")
        assert result is None

    def test_cache_hit(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        cache.set("GET", "/test", data={"key": "value"})
        result = cache.get("GET", "/test")
        assert result == {"key": "value"}

    def test_cache_hit_with_params(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        cache.set("GET", "/test", params={"q": "hello"}, data={"r": 1})
        result = cache.get("GET", "/test", params={"q": "hello"})
        assert result == {"r": 1}

    def test_cache_miss_wrong_params(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        cache.set("GET", "/test", params={"q": "hello"}, data={"r": 1})
        result = cache.get("GET", "/test", params={"q": "world"})
        assert result is None

    def test_cache_miss_wrong_method(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        cache.set("GET", "/test", data={"r": 1})
        result = cache.get("POST", "/test")
        assert result is None


class TestCacheExpiry:
    """Test TTL-based cache expiry."""

    def test_cache_not_expired_immediately(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir, default_ttl=1)
        cache.set("GET", "/test", data={"key": "value"})
        result = cache.get("GET", "/test")
        assert result is not None

    def test_cache_expired_after_ttl(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir, default_ttl=1)
        cache.set("GET", "/test", data={"key": "value"})
        time.sleep(1.1)
        result = cache.get("GET", "/test")
        assert result is None

    def test_expired_entry_file_removed(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir, default_ttl=1)
        cache.set("GET", "/test", data={"key": "value"})
        time.sleep(1.1)
        cache.get("GET", "/test")
        assert len(list(cache_dir.glob("*.json"))) == 0

    def test_custom_ttl_override(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir, default_ttl=1)
        cache.set("GET", "/test", data={"key": "value"})
        time.sleep(0.5)
        result = cache.get("GET", "/test", ttl=10)
        assert result is not None

    def test_custom_ttl_shorter_than_default(self, cache_dir: Path) -> None:
        """TTL=0 falls through to default_ttl since 0 is falsy in or-expression."""
        cache = ResponseCache(cache_dir, default_ttl=10)
        cache.set("GET", "/test", data={"key": "value"})
        time.sleep(0.5)
        # ttl=0 is falsy, so 0 or self.default_ttl uses default_ttl
        result = cache.get("GET", "/test", ttl=0)
        assert result is not None  # still valid because 0 falls through to default_ttl


class TestCacheSet:
    """Test cache storage."""

    def test_store_dict_data(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        cache.set("GET", "/test", data={"key": "value", "nested": {"a": 1}})
        result = cache.get("GET", "/test")
        assert result == {"key": "value", "nested": {"a": 1}}

    def test_store_list_data(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        cache.set("GET", "/test", data=[1, 2, 3])
        result = cache.get("GET", "/test")
        assert result == [1, 2, 3]

    def test_store_string_data(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        cache.set("GET", "/test", data="hello world")
        result = cache.get("GET", "/test")
        assert result == "hello world"

    def test_overwrite_existing_entry(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        cache.set("GET", "/test", data={"v": 1})
        cache.set("GET", "/test", data={"v": 2})
        result = cache.get("GET", "/test")
        assert result == {"v": 2}

    def test_different_params_different_entries(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        cache.set("GET", "/test", params={"q": "hello"}, data={"r": 1})
        cache.set("GET", "/test", params={"q": "world"}, data={"r": 2})
        assert cache.get("GET", "/test", params={"q": "hello"}) == {"r": 1}
        assert cache.get("GET", "/test", params={"q": "world"}) == {"r": 2}


class TestCacheClear:
    """Test cache clearing."""

    def test_clear_removes_all_entries(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        cache.set("GET", "/test1", data={"a": 1})
        cache.set("GET", "/test2", data={"b": 2})
        cache.set("POST", "/test3", data={"c": 3})
        assert len(list(cache_dir.glob("*.json"))) == 3
        cache.clear()
        assert len(list(cache_dir.glob("*.json"))) == 0

    def test_clear_on_empty_cache(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        cache.clear()

    def test_get_after_clear_returns_none(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        cache.set("GET", "/test", data={"key": "value"})
        cache.clear()
        assert cache.get("GET", "/test") is None


class TestCacheCorruptedEntry:
    """Test handling of corrupted cache files."""

    def test_corrupted_json_returns_none(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        key = cache._cache_key("GET", "/test")
        cache_file = cache_dir / f"{key}.json"
        cache_file.write_text("NOT VALID JSON{{{")
        result = cache.get("GET", "/test")
        assert result is None
        assert not cache_file.exists()

    def test_empty_json_file_returns_none(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        key = cache._cache_key("GET", "/test")
        cache_file = cache_dir / f"{key}.json"
        cache_file.write_text("")
        result = cache.get("GET", "/test")
        assert result is None


class TestCacheWithRealisticData:
    """Test cache with realistic API response data."""

    def test_cache_api_search_response(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        data = {
            "data": [
                {
                    "id": "ds-1",
                    "title": "\u0421\u0442\u0430\u043d\u043e\u0432\u043d\u0438\u0448\u0442\u0432\u043e \u0421\u0440\u0431\u0438\u0458\u0435",
                },
                {
                    "id": "ds-2",
                    "title": "\u041f\u0440\u0438\u0432\u0440\u0435\u0434\u0430 \u0421\u0440\u0431\u0438\u0458\u0435",
                },
            ],
            "total": 2,
            "page": 1,
            "page_size": 10,
        }
        cache.set("GET", "/api/1/datasets/search/", params={"q": "statistika"}, data=data)
        result = cache.get("GET", "/api/1/datasets/search/", params={"q": "statistika"})
        assert result == data

    def test_cache_dataset_detail_response(self, cache_dir: Path) -> None:
        cache = ResponseCache(cache_dir)
        data = {
            "id": "5e75b69b-8b0e-452c-a1e2-1234567890ab",
            "title": "Census 2022",
            "resources": [
                {"id": "r1", "title": "CSV data", "format": "csv"},
                {"id": "r2", "title": "JSON data", "format": "json"},
                {"id": "r3", "title": "XLSX data", "format": "xlsx"},
            ],
        }
        cache.set("GET", "/api/1/datasets/5e75b69b/", data=data)
        result = cache.get("GET", "/api/1/datasets/5e75b69b/")
        assert result["title"] == "Census 2022"
        assert len(result["resources"]) == 3
