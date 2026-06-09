"""UData API client for Serbian data portal."""

import asyncio
import time
from typing import Any, Optional

import httpx

from .models import Dataset, Organization, Resource, SearchResult
from ..config import config
from ..exceptions import ConnectionError, DatasetNotFoundError, DataParsingError, RateLimitError, ResourceNotFoundError


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

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self._client

    async def _rate_limit_wait(self):
        """Wait if needed to respect rate limit."""
        now = time.time()
        time_since_last = now - self._last_request_time
        if time_since_last < self.rate_limit:
            await asyncio.sleep(self.rate_limit - time_since_last)
        self._last_request_time = time.time()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make an API request with rate limiting.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body

        Returns:
            Response data as dictionary

        Raises:
            ConnectionError: If the API cannot be reached
            RateLimitError: If rate limit is exceeded
        """
        await self._rate_limit_wait()

        client = await self._get_client()
        url = endpoint if endpoint.startswith("/") else f"/{endpoint}"

        try:
            response = await client.request(method, url, params=params, json=json_data)
            response.raise_for_status()
            return response.json()

        except httpx.ConnectError as e:
            raise ConnectionError(str(self.base_url), f"Connection failed: {str(e)}")

        except httpx.TimeoutException:
            raise ConnectionError(str(self.base_url), f"Request timed out after {self.timeout} seconds")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After", str(self.rate_limit))
                raise RateLimitError(self.rate_limit, float(retry_after))
            raise

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

        data = await self._request("GET", "/api/1/datasets/", params=params)

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
            data = await self._request("GET", f"/api/1/datasets/{dataset_id}/")
            return Dataset.from_dict(data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise DatasetNotFoundError(dataset_id)
            raise

    async def get_resource_data(self, resource_id: str) -> Any:
        """Download and parse resource data.

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

        try:
            data = await self._request("GET", f"/api/1/datasets/{resource_id}/")
            resource = Resource.from_dict(data)

            # Fetch actual data file
            client = await self._get_client()
            if resource.url and resource.format:
                response = await client.get(resource.url)
                try:
                    return await parse_resource(response, resource.format)
                except Exception as e:
                    raise DataParsingError(resource.format, f"Failed to parse resource data: {str(e)}")
            return None

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ResourceNotFoundError(resource_id)
            raise

    async def list_organizations(self, page_size: int = 50, page: int = 1) -> list[Organization]:
        """List all organizations.

        Args:
            page_size: Number of results per page
            page: Page number (1-indexed)

        Returns:
            List of Organization objects
        """
        params = {"rows": page_size, "start": (page - 1) * page_size}

        data = await self._request("GET", "/api/1/organizations/", params=params)

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
            data = await self._request("GET", "/api/1/datasets/suggest/", params=params)
            return data.get("results", [])
        except httpx.HTTPStatusError:
            return []

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Async context manager exit."""
        # Close the client even if exceptions occurred
        await self.close()
        await self.close()
