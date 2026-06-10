"""UData API client for Serbian data portal."""

import asyncio
import logging
import re
import time
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from .cache import ResponseCache
from .models import Dataset, Organization, Resource, SearchResult
from ..config import config
from ..exceptions import ConnectionError, DatasetNotFoundError, DataParsingError, RateLimitError, ResourceNotFoundError

logger = logging.getLogger(__name__)

_USER_AGENT = "SerbianDataMCP/1.0 (+https://github.com/amplifier/serbian-data-mcp)"

# Whitelisted domains for resource downloads (SSRF protection still blocks private IPs)
_RESOURCE_DOMAIN_WHITELIST = {
    "data.gov.rs",
    "opendata.stat.gov.rs",
    "esttherm.rs",
    "data.rgz.gov.rs",
    "napomena.gov.rs",
}


class UDataClient:
    """Client for accessing Serbian data portal (data.gov.rs)."""

    def __init__(
        self, base_url: Optional[str] = None, rate_limit: Optional[float] = None, timeout: Optional[int] = None
    ):
        """Initialize the API client.

        Args:
            base_url: API base URL (defaults to config.api_base)
            rate_limit: Rate limit in seconds between requests
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or config.api_base
        self.rate_limit = rate_limit or config.rate_limit
        self.timeout = timeout or config.timeout
        self._last_request_time = 0
        self._client: Optional[httpx.AsyncClient] = None
        self._external_client: Optional[httpx.AsyncClient] = None
        self._cache = ResponseCache(cache_dir=config.cache_dir, default_ttl=300)
        logger.debug(
            f"UDataClient initialized: base_url={self.base_url}, rate_limit={self.rate_limit}s, "
            f"timeout={self.timeout}s, cache_dir={config.cache_dir}"
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for API requests (base_url-scoped)."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"User-Agent": _USER_AGENT},
                follow_redirects=True,
            )
            logger.debug(f"Created API client for {self.base_url}")
        return self._client

    async def _get_external_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for cross-domain resource downloads.

        This client has no base_url so it can fetch from any public domain.
        """
        if self._external_client is None:
            self._external_client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": _USER_AGENT},
                follow_redirects=True,
            )
            logger.debug("Created external client for cross-domain resource downloads")
        return self._external_client

    async def _rate_limit_wait(self):
        """Wait if needed to respect rate limit."""
        now = time.time()
        time_since_last = now - self._last_request_time
        if time_since_last < self.rate_limit:
            await asyncio.sleep(self.rate_limit - time_since_last)
        self._last_request_time = time.time()

    def _validate_url_safe(self, url: str) -> None:
        """Validate URL to prevent SSRF attacks.

        Args:
            url: URL to validate

        Raises:
            ConnectionError: If URL is potentially malicious
        """
        try:
            parsed = urlparse(url)

            # Only allow HTTP/HTTPS schemes
            if parsed.scheme not in ("http", "https"):
                raise ConnectionError(
                    url, f"Blocked: URL scheme '{parsed.scheme}' is not allowed. Only HTTP and HTTPS are permitted."
                )

            # Block private/local network addresses
            hostname = parsed.hostname or ""

            # Block localhost and local IP addresses
            local_patterns = [
                r"^(localhost|localhost\.localdomain|::1)$",
                r"^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$",  # 127.0.0.0/8 loopback
                r"^0\.0\.0\.0$",
                r"^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$",  # 10.0.0.0/8
                r"^172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}$",  # 172.16.0.0/12
                r"^192\.168\.\d{1,3}\.\d{1,3}$",  # 192.168.0.0/16
                r"^169\.254\.\d{1,3}\.\d{1,3}$",  # 169.254.0.0/16 (link-local)
            ]

            for pattern in local_patterns:
                if re.match(pattern, hostname, re.IGNORECASE):
                    raise ConnectionError(
                        url, f"Blocked: Access to private/local network '{hostname}' is not permitted."
                    )

        except Exception as e:
            if isinstance(e, ConnectionError):
                raise
            raise ConnectionError(url, f"Invalid URL: {str(e)}")

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        max_retries: int = 3,
        cache_ttl: Optional[int] = None,
    ) -> dict[str, Any]:
        """Make an API request with rate limiting, caching, and retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body
            max_retries: Maximum number of retry attempts for transient failures
            cache_ttl: Cache TTL in seconds. None means no caching, 0 uses default.

        Returns:
            Response data as dictionary

        Raises:
            ConnectionError: If the API cannot be reached after all retries
            RateLimitError: If rate limit is exceeded
        """
        url = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        full_url = f"{self.base_url}{url}"

        # Check cache for GET requests
        if method.upper() == "GET" and cache_ttl is not None:
            cached = self._cache.get(method, full_url, params=params, ttl=cache_ttl if cache_ttl > 0 else None)
            if cached is not None:
                return cached

        await self._rate_limit_wait()

        client = await self._get_client()
        logger.info(f"Requesting {method} {full_url}")

        # Retry logic with exponential backoff for transient failures
        retry_delay = 1.0  # Initial retry delay in seconds

        for attempt in range(max_retries):
            try:
                response = await client.request(method, url, params=params, json=json_data)
                response.raise_for_status()
                data = response.json()

                logger.debug(
                    f"Response {method} {full_url}: status={response.status_code}, size={len(response.content)} bytes"
                )

                # Cache successful GET responses
                if method.upper() == "GET" and cache_ttl is not None:
                    self._cache.set(method, full_url, params=params, data=data)

                return data

            except httpx.ConnectError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for {method} {full_url} (connection error)")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                logger.error(f"Connection failed for {method} {full_url} after {max_retries} retries: {e}")
                raise ConnectionError(str(self.base_url), f"Connection failed after {max_retries} retries: {str(e)}")

            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for {method} {full_url} (timeout)")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                logger.error(f"Request timed out for {method} {full_url} after {max_retries} retries")
                raise ConnectionError(str(self.base_url), f"Request timed out after {max_retries} retries")

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    retry_after = e.response.headers.get("Retry-After", str(self.rate_limit))
                    logger.warning(f"Rate limited on {method} {full_url}, Retry-After: {retry_after}")
                    raise RateLimitError(self.rate_limit, float(retry_after))
                if e.response.status_code >= 500 and attempt < max_retries - 1:
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {method} {full_url} (server error {e.response.status_code})"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                raise

        # Should not reach here, but just in case
        raise ConnectionError(str(self.base_url), "Request failed after all retry attempts")

    async def search_datasets(
        self,
        query: str = "",
        format: Optional[str] = None,
        organization: Optional[str] = None,
        page_size: int = 10,
        page: int = 1,
    ) -> SearchResult:
        """Search for datasets.

        Args:
            query: Search query string
            format: Filter by file format (json, csv, xml, xlsx)
            organization: Filter by organization ID
            page_size: Number of results per page
            page: Page number (1-indexed)

        Returns:
            SearchResult with list of Dataset objects
        """
        params = {"q": query, "rows": page_size, "start": (page - 1) * page_size}

        if format:
            params["format"] = format
        if organization:
            params["organization"] = organization

        data = await self._request("GET", "/api/1/datasets/", params=params, cache_ttl=300)

        datasets = [Dataset.from_dict(ds_data) for ds_data in data.get("data", [])]

        return SearchResult(datasets=datasets, total=data.get("total", 0), page=page, page_size=page_size)

    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get complete dataset details.

        Args:
            dataset_id: Dataset identifier

        Returns:
            Dataset object or None if not found

        Raises:
            DatasetNotFoundError: If dataset doesn't exist
            ConnectionError: If API cannot be reached
        """
        try:
            data = await self._request("GET", f"/api/1/datasets/{dataset_id}/", cache_ttl=300)
            return Dataset.from_dict(data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise DatasetNotFoundError(dataset_id)
            raise

    async def _find_resource(self, resource_id: str) -> Optional[Resource]:
        """Find a resource by its ID across datasets using multiple strategies.

        Args:
            resource_id: Resource identifier (UUID or slug)

        Returns:
            Resource object if found, None otherwise
        """
        # Strategy 1: Search for the resource ID in dataset search results
        logger.debug(f"Searching for resource {resource_id} across datasets")
        search_data = await self._request(
            "GET", "/api/1/datasets/", params={"q": resource_id, "rows": 20}, cache_ttl=300
        )
        for ds in search_data.get("data", []):
            for res in ds.get("resources", []):
                if res.get("id") == resource_id:
                    logger.debug(f"Found resource {resource_id} in dataset {ds.get('id')} via search")
                    return Resource.from_dict(res)

        # Strategy 2: Scan recent datasets (paginated, up to 3 pages of 50)
        logger.debug(f"Scanning recent datasets for resource {resource_id}")
        for page in range(1, 4):
            page_data = await self._request(
                "GET", "/api/1/datasets/", params={"rows": 50, "start": (page - 1) * 50}, cache_ttl=300
            )
            datasets_list = page_data.get("data", [])
            if not datasets_list:
                break
            for ds in datasets_list:
                for res in ds.get("resources", []):
                    if res.get("id") == resource_id:
                        logger.debug(f"Found resource {resource_id} in dataset {ds.get('id')} via paginated scan")
                        return Resource.from_dict(res)

        logger.warning(f"Resource {resource_id} not found in any dataset")
        return None

    async def get_resource_data(self, resource_id: str) -> Any:
        """Download and parse resource data.

        Looks up the resource metadata (including its download URL) from the
        API, then downloads and parses the actual data file using a
        cross-domain HTTP client.

        Args:
            resource_id: Resource identifier

        Returns:
            Parsed data (dict for JSON, DataFrame for CSV/Excel, etc.)

        Raises:
            ResourceNotFoundError: If resource doesn't exist
            DataParsingError: If data cannot be parsed
            ConnectionError: If API cannot be reached
        """
        from ..data.parsers import parse_resource

        resource = await self._find_resource(resource_id)
        if resource is None:
            raise ResourceNotFoundError(resource_id)

        if not resource.url or not resource.format:
            logger.error(f"Resource {resource_id} missing URL or format: url={resource.url}, format={resource.format}")
            raise DataParsingError(
                resource.format or "unknown", f"Resource {resource_id} is missing download URL or format"
            )

        self._validate_url_safe(resource.url)

        # Check resource data cache (1-hour TTL for bulk data)
        cache_key = f"resource:{resource_id}:{resource.format}"
        cached_data = self._cache.get("GET", cache_key, ttl=3600)
        if cached_data is not None:
            logger.info(f"Returning cached resource data for {resource_id} ({resource.format})")
            if resource.format in ("csv", "xlsx", "xls", "excel"):
                import pandas as pd

                return pd.DataFrame(cached_data)
            return cached_data

        # Download using the external client (handles cross-domain URLs)
        ext_client = await self._get_external_client()
        logger.info(f"Downloading resource {resource_id} from {resource.url}")
        retry_delay = 1.0
        for attempt in range(3):
            try:
                response = await ext_client.get(resource.url)
                response.raise_for_status()
                logger.debug(
                    f"Downloaded resource {resource_id}: status={response.status_code}, "
                    f"size={len(response.content)} bytes, format={resource.format}"
                )
                parsed = await parse_resource(response, resource.format)

                # Cache parsed data for future requests
                if resource.format in ("csv", "xlsx", "xls", "excel"):
                    import pandas as pd

                    cacheable = parsed.to_dict(orient="list") if isinstance(parsed, pd.DataFrame) else parsed
                else:
                    cacheable = parsed
                self._cache.set("GET", cache_key, data=cacheable)

                return parsed

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < 2:
                    logger.warning(f"Retry {attempt + 1}/3 for resource {resource_id} ({type(e).__name__})")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                raise ConnectionError(resource.url, f"Download failed after 3 retries: {e}")

            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to download resource {resource_id}: HTTP {e.response.status_code}")
                raise ConnectionError(resource.url, f"Download failed with HTTP {e.response.status_code}")

            except Exception as e:
                logger.error(f"Failed to download resource {resource_id}: {e}")
                raise DataParsingError(resource.format, f"Failed to download or parse resource data: {e}")

        raise ConnectionError(resource.url, "Download failed after all retries")

    async def list_organizations(self, page_size: int = 50, page: int = 1) -> list[Organization]:
        """List all organizations.

        Args:
            page_size: Number of results per page
            page: Page number (1-indexed)

        Returns:
            List of Organization objects
        """
        params = {"rows": page_size, "start": (page - 1) * page_size}

        data = await self._request("GET", "/api/1/organizations/", params=params, cache_ttl=300)

        return [Organization.from_dict(org_data) for org_data in data.get("data", [])]

    async def suggest_datasets(self, query: str, format: Optional[str] = None, size: int = 10) -> list[str]:
        """Get autocomplete suggestions for search.

        Args:
            query: Partial search query
            format: Filter by file format
            size: Number of suggestions

        Returns:
            List of suggestion strings
        """
        params = {"q": query, "size": size}

        if format:
            params["format"] = format

        try:
            data = await self._request("GET", "/api/1/datasets/suggest/", params=params, cache_ttl=300)
            # API returns list directly or dict with "results" key
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("results", [])
            return []
        except httpx.HTTPStatusError:
            return []

    async def get_dataset_resources(self, dataset_id: str) -> list[Resource]:
        """Get resources for a specific dataset.

        Args:
            dataset_id: Dataset identifier

        Returns:
            List of Resource objects

        Raises:
            DatasetNotFoundError: If dataset doesn't exist
            ConnectionError: If API cannot be reached
        """
        try:
            data = await self._request("GET", f"/api/1/datasets/{dataset_id}/", cache_ttl=300)
            resources = []
            for res_data in data.get("resources", []):
                resources.append(Resource.from_dict(res_data))
            return resources
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise DatasetNotFoundError(dataset_id)
            raise

    async def get_reuses(self, dataset_id: str) -> list[dict[str, Any]]:
        """Get reuses (applications using) a dataset.

        Args:
            dataset_id: Dataset identifier

        Returns:
            List of reuse dictionaries from the API

        Raises:
            DatasetNotFoundError: If dataset doesn't exist
            ConnectionError: If API cannot be reached
        """
        try:
            data = await self._request("GET", f"/api/1/datasets/{dataset_id}/reuses/", cache_ttl=300)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("data", [])
            return []
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise DatasetNotFoundError(dataset_id)
            raise

    async def get_organization_datasets(self, org_id: str, page_size: int = 50, page: int = 1) -> list[Dataset]:
        """Get datasets published by an organization.

        Args:
            org_id: Organization identifier
            page_size: Number of results per page
            page: Page number (1-indexed)

        Returns:
            List of Dataset objects

        Raises:
            ConnectionError: If API cannot be reached
        """
        params = {
            "rows": page_size,
            "start": (page - 1) * page_size,
            "organization": org_id,
        }
        data = await self._request("GET", "/api/1/datasets/", params=params, cache_ttl=300)
        return [Dataset.from_dict(ds_data) for ds_data in data.get("data", [])]

    async def search_with_facets(
        self,
        query: str = "",
        tags: Optional[list[str]] = None,
        organization: Optional[str] = None,
        schema: Optional[str] = None,
        format: Optional[str] = None,
        license: Optional[str] = None,
        temporal_coverage: Optional[str] = None,
        geozone: Optional[str] = None,
        page_size: int = 10,
        page: int = 1,
    ) -> SearchResult:
        """Advanced search with faceted filters.

        Args:
            query: Full-text search query string
            tags: Filter by tags (list of tag strings)
            organization: Filter by organization ID or name
            schema: Filter by data schema
            format: Filter by file format (json, csv, xml, xlsx)
            license: Filter by license identifier
            temporal_coverage: Filter by temporal coverage string
            geozone: Filter by geographic zone
            page_size: Number of results per page
            page: Page number (1-indexed)

        Returns:
            SearchResult with list of Dataset objects
        """
        params: dict[str, Any] = {"q": query, "rows": page_size, "start": (page - 1) * page_size}

        if tags:
            params["tag"] = tags
        if organization:
            params["organization"] = organization
        if schema:
            params["schema"] = schema
        if format:
            params["format"] = format
        if license:
            params["license"] = license
        if temporal_coverage:
            params["temporal_coverage"] = temporal_coverage
        if geozone:
            params["geozone"] = geozone

        data = await self._request("GET", "/api/1/datasets/", params=params, cache_ttl=300)
        datasets = [Dataset.from_dict(ds_data) for ds_data in data.get("data", [])]
        return SearchResult(datasets=datasets, total=data.get("total", 0), page=page, page_size=page_size)

    async def close(self):
        """Close all HTTP clients."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("Closed API client")
        if self._external_client:
            await self._external_client.aclose()
            self._external_client = None
            logger.debug("Closed external client")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Async context manager exit."""
        # Close the client even if exceptions occurred
        await self.close()
