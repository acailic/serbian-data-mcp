"""Tests for API client and models."""

from __future__ import annotations

import pytest
import httpx
from serbian_data_mcp.api import UDataClient, Dataset, Resource, Organization
from serbian_data_mcp.exceptions import ConnectionError, RateLimitError


@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization."""
    client = UDataClient()
    assert client.base_url == "https://data.gov.rs"
    assert client.rate_limit == 1.0
    assert client.timeout == 30


@pytest.mark.asyncio
async def test_client_custom_config():
    """Test client with custom configuration."""
    client = UDataClient(base_url="https://custom.example.com", rate_limit=2.0, timeout=60)
    assert client.base_url == "https://custom.example.com"
    assert client.rate_limit == 2.0
    assert client.timeout == 60


def test_resource_from_dict():
    """Test Resource model creation."""
    data = {
        "id": "test-resource",
        "title": "Test Resource",
        "description": "A test resource",
        "format": "json",
        "url": "https://example.com/data.json",
        "created_at": "2025-01-01T00:00:00Z",
        "size": 1024,
        "mime": "application/json",
        "checksum": "abc123",
    }

    resource = Resource.from_dict(data)

    assert resource.id == "test-resource"
    assert resource.title == "Test Resource"
    assert resource.format == "json"
    assert resource.url == "https://example.com/data.json"
    assert resource.size == 1024


def test_organization_from_dict():
    """Test Organization model creation."""
    data = {
        "id": "test-org",
        "name": "Test Organization",
        "description": "A test organization",
        "url": "https://example.com",
        "logo": "https://example.com/logo.png",
    }

    org = Organization.from_dict(data)

    assert org.id == "test-org"
    assert org.name == "Test Organization"
    assert org.description == "A test organization"


def test_dataset_from_dict():
    """Test Dataset model creation."""
    data = {
        "id": "test-dataset",
        "title": "Test Dataset",
        "description": "A test dataset",
        "organization": {"id": "test-org", "name": "Test Organization"},
        "resources": [{"id": "res1", "title": "Resource 1", "format": "json"}],
        "tags": ["tag1", "tag2"],
        "created_at": "2025-01-01T00:00:00Z",
        "modified_at": "2025-01-02T00:00:00Z",
        "frequency": "annual",
        "license": "CC-BY-4.0",
    }

    dataset = Dataset.from_dict(data)

    assert dataset.id == "test-dataset"
    assert dataset.title == "Test Dataset"
    assert dataset.organization is not None
    assert dataset.organization.name == "Test Organization"
    assert len(dataset.resources) == 1
    assert dataset.resources[0].title == "Resource 1"
    assert len(dataset.tags) == 2
    assert dataset.frequency == "annual"


def test_search_result():
    """Test SearchResult model."""
    from serbian_data_mcp.api.models import SearchResult

    datasets = [Dataset(id="1", title="Dataset 1"), Dataset(id="2", title="Dataset 2")]

    result = SearchResult(datasets=datasets, total=100, page=1, page_size=10)

    assert len(result.datasets) == 2
    assert result.total == 100
    assert result.total_pages == 10
    assert result.has_next is True
    assert result.has_previous is False


# -- URL validation tests -----------------------------------------------------


def test_url_validation_blocks_localhost() -> None:
    """localhost URLs should be blocked."""
    client = UDataClient()
    with pytest.raises(ConnectionError):
        client._validate_url_safe("http://localhost/data.csv")


def test_url_validation_blocks_127_0_0_1() -> None:
    """127.x.x.x loopback addresses should be blocked."""
    client = UDataClient()
    with pytest.raises(ConnectionError):
        client._validate_url_safe("http://127.0.0.1/data.csv")
    with pytest.raises(ConnectionError):
        client._validate_url_safe("http://127.0.0.2/data.csv")
    with pytest.raises(ConnectionError):
        client._validate_url_safe("http://127.255.255.255/data.csv")


def test_url_validation_blocks_10_range() -> None:
    """10.x.x.x private IPs should be blocked."""
    client = UDataClient()
    with pytest.raises(ConnectionError):
        client._validate_url_safe("http://10.0.0.1/data.csv")


def test_url_validation_blocks_192_168_range() -> None:
    """192.168.x.x private IPs should be blocked."""
    client = UDataClient()
    with pytest.raises(ConnectionError):
        client._validate_url_safe("http://192.168.1.1/data.csv")


def test_url_validation_blocks_172_range() -> None:
    """172.16-31.x.x private IPs should be blocked."""
    client = UDataClient()
    with pytest.raises(ConnectionError):
        client._validate_url_safe("http://172.16.0.1/data.csv")


def test_url_validation_blocks_169_254() -> None:
    """169.254.x.x link-local IPs should be blocked."""
    client = UDataClient()
    with pytest.raises(ConnectionError):
        client._validate_url_safe("http://169.254.1.1/data.csv")


def test_url_validation_blocks_0_0_0_0() -> None:
    """0.0.0.0 should be blocked."""
    client = UDataClient()
    with pytest.raises(ConnectionError):
        client._validate_url_safe("http://0.0.0.0/data.csv")


def test_url_validation_blocks_file_scheme() -> None:
    """file:// scheme should be blocked."""
    client = UDataClient()
    with pytest.raises(ConnectionError):
        client._validate_url_safe("file:///etc/passwd")


def test_url_validation_blocks_ftp_scheme() -> None:
    """ftp:// scheme should be blocked."""
    client = UDataClient()
    with pytest.raises(ConnectionError):
        client._validate_url_safe("ftp://example.com/data.csv")


def test_url_validation_allows_https_public() -> None:
    """Public HTTPS URLs should be allowed."""
    client = UDataClient()
    client._validate_url_safe("https://data.gov.rs/data.csv")  # should not raise


def test_url_validation_allows_cross_domain() -> None:
    """Cross-domain HTTPS URLs should be allowed."""
    client = UDataClient()
    client._validate_url_safe("https://opendata.stat.gov.rs/data.csv")  # should not raise


def test_url_validation_allows_http_public() -> None:
    """Public HTTP URLs should be allowed."""
    client = UDataClient()
    client._validate_url_safe("http://example.com/data.csv")  # should not raise


# -- Rate limit tests ----------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_initial_state() -> None:
    """Rate limit starts at zero."""
    client = UDataClient(rate_limit=0.1)
    assert client._last_request_time == 0


@pytest.mark.asyncio
async def test_rate_limit_wait_completes() -> None:
    """Rate limit wait should complete without error."""
    client = UDataClient(rate_limit=0.01)
    await client._rate_limit_wait()  # should not raise


# -- Retry logic tests ----------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_on_connection_error() -> None:
    """Client should retry on connection errors."""
    client = UDataClient(base_url="https://data.gov.rs")
    attempt = 0

    async def mock_request(method, url, **kwargs):
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            raise httpx.ConnectError("Connection refused")
        req = httpx.Request("GET", url)
        return httpx.Response(200, json={"data": [], "total": 0}, request=req)

    client._client = httpx.AsyncClient()
    client._client.request = mock_request  # type: ignore[assignment]

    result = await client._request("GET", "/api/1/datasets/")
    assert result == {"data": [], "total": 0}
    assert attempt == 3


@pytest.mark.asyncio
async def test_retry_on_timeout() -> None:
    """Client should retry on timeout."""
    client = UDataClient()
    attempt = 0

    async def mock_request(method, url, **kwargs):
        nonlocal attempt
        attempt += 1
        if attempt < 2:
            raise httpx.TimeoutException("timeout")
        req = httpx.Request("GET", url)
        return httpx.Response(200, json={"data": [], "total": 0}, request=req)

    client._client = httpx.AsyncClient()
    client._client.request = mock_request  # type: ignore[assignment]

    await client._request("GET", "/api/1/datasets/")
    assert attempt == 2


@pytest.mark.asyncio
async def test_retry_on_5xx_error() -> None:
    """Client should retry on 5xx server errors."""
    client = UDataClient()
    attempt = 0

    async def mock_request(method, url, **kwargs):
        nonlocal attempt
        attempt += 1
        req = httpx.Request("GET", url)
        if attempt < 3:
            return httpx.Response(500, request=req)
        return httpx.Response(200, json={"data": [], "total": 0}, request=req)

    client._client = httpx.AsyncClient()
    client._client.request = mock_request  # type: ignore[assignment]

    await client._request("GET", "/api/1/datasets/")
    assert attempt == 3


@pytest.mark.asyncio
async def test_rate_limit_error_on_429() -> None:
    """Client should raise RateLimitError on 429."""
    client = UDataClient()

    async def mock_request(method, url, **kwargs):
        req = httpx.Request("GET", url)
        return httpx.Response(
            429,
            request=req,
            headers={"Retry-After": "5"},
        )

    client._client = httpx.AsyncClient()
    client._client.request = mock_request  # type: ignore[assignment]

    with pytest.raises(RateLimitError):
        await client._request("GET", "/api/1/datasets/")


@pytest.mark.asyncio
async def test_connection_error_after_all_retries() -> None:
    """Client should raise ConnectionError after exhausting all retries."""
    client = UDataClient()

    async def mock_request(method, url, **kwargs):
        raise httpx.ConnectError("Connection refused")

    client._client = httpx.AsyncClient()
    client._client.request = mock_request  # type: ignore[assignment]

    with pytest.raises(ConnectionError):
        await client._request("GET", "/api/1/datasets/")


# -- Async context manager ------------------------------------------------------


@pytest.mark.asyncio
async def test_async_context_manager() -> None:
    """Client should work as async context manager (closes on exit)."""
    client = UDataClient()
    await client._get_client()  # ensure client is created
    assert client._client is not None
    await client.close()
    assert client._client is None


@pytest.mark.asyncio
async def test_async_context_manager_closes_external_client() -> None:
    """Client close should also close the external download client."""
    client = UDataClient()
    await client._get_external_client()
    assert client._external_client is not None
    await client.close()
    assert client._external_client is None


@pytest.mark.asyncio
async def test_cache_integration() -> None:
    """Client should have a working cache instance."""
    client = UDataClient()
    assert client._cache is not None
    # Cache should support get/set operations
    client._cache.set("GET", "test_url", data={"key": "value"})
    result = client._cache.get("GET", "test_url")
    assert result == {"key": "value"}
    await client.close()


@pytest.mark.asyncio
async def test_client_has_user_agent() -> None:
    """API client should set a User-Agent header."""
    client = UDataClient()
    api_client = await client._get_client()
    assert "User-Agent" in api_client.headers
    assert "SerbianDataMCP" in api_client.headers["User-Agent"]
    await client.close()
