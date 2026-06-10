"""Dataset catalog caching and indexing."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, UTC, timedelta
from pathlib import Path
from typing import Any

from .models import CachedDataset
from .exceptions import CatalogBuildError, CatalogLoadError
from ..api.client import UDataClient
from ..api.models import Dataset

logger = logging.getLogger(__name__)

# Cache metadata version
CACHE_VERSION = "1.0"
# Default cache age limit (24 hours)
CACHE_AGE_LIMIT = timedelta(hours=24)


class DatasetCatalog:
    """Maintain indexed catalog of all datasets from data.gov.rs.

    The catalog fetches all datasets at startup and caches them locally
    for fast semantic search without hitting API rate limits.

    Example:
        catalog = DatasetCatalog()
        await catalog.initialize()
        results = catalog.search("population")
    """

    def __init__(self, cache_path: Path | None = None) -> None:
        """Initialize catalog.

        Args:
            cache_path: Path to cache directory. Defaults to ~/.serbian-data-mcp/cache/
        """
        if cache_path is None:
            cache_dir = Path.home() / ".serbian-data-mcp" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = cache_dir / "catalog.json"

        self.cache_path = cache_path
        self.datasets: dict[str, CachedDataset] = {}
        self._client: UDataClient | None = None
        self._initialized = False

    async def _get_client(self) -> UDataClient:
        """Get or create API client."""
        if self._client is None:
            self._client = UDataClient()
        return self._client

    async def initialize(self, force_refresh: bool = False) -> None:
        """Initialize catalog (load cache or build from API).

        Args:
            force_refresh: If True, rebuild catalog even if cache exists

        Raises:
            CatalogLoadError: If cache loading fails
            CatalogBuildError: If catalog building fails
        """
        if self._initialized:
            return

        if not force_refresh and await self._load_cache():
            logger.info(f"Loaded catalog from cache: {len(self.datasets)} datasets")
        else:
            logger.info("Building catalog from API...")
            await self.build_catalog()

        self._initialized = True

    async def _load_cache(self) -> bool:
        """Load catalog from JSON cache.

        Returns:
            True if cache loaded successfully, False otherwise

        Raises:
            CatalogLoadError: If cache file is corrupted
        """
        if not self.cache_path.exists():
            return False

        try:
            with open(self.cache_path, encoding="utf-8") as f:
                data = json.load(f)

            # Validate cache version
            if data.get("version") != CACHE_VERSION:
                logger.warning(f"Cache version mismatch: {data.get('version')} != {CACHE_VERSION}")
                return False

            # Check cache age
            built_at_str = data.get("built_at", "")
            if built_at_str:
                try:
                    built_at = datetime.fromisoformat(built_at_str)
                    age = datetime.now(UTC) - built_at
                    if age > CACHE_AGE_LIMIT:
                        logger.info(f"Cache is {age} old (limit: {CACHE_AGE_LIMIT}), rebuilding")
                        return False
                except ValueError:
                    logger.warning(f"Invalid built_at timestamp: {built_at_str}")
                    return False

            # Load datasets
            datasets_data = data.get("datasets", {})
            self.datasets = {
                dataset_id: CachedDataset(**ds_data)
                for dataset_id, ds_data in datasets_data.items()
            }

            logger.info(f"Loaded {len(self.datasets)} datasets from cache")
            return True

        except json.JSONDecodeError as e:
            raise CatalogLoadError(f"Cache file corrupted: {e}") from e
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return False

    async def build_catalog(self, page_size: int = 100) -> None:
        """Build catalog by fetching all datasets from API.

        Args:
            page_size: Number of datasets per page (default: 100)

        Raises:
            CatalogBuildError: If API fetching fails
        """
        client = await self._get_client()
        all_datasets: list[Dataset] = []

        try:
            # Get total count first
            first_page = await client.search_datasets(page_size=1)
            total = first_page.total
            logger.info(f"Fetching {total} datasets from data.gov.rs...")

            # Fetch all datasets with pagination
            page = 1
            while len(all_datasets) < total:
                try:
                    result = await client.search_datasets(
                        page_size=page_size,
                        page=page
                    )

                    if not result.datasets:
                        break

                    all_datasets.extend(result.datasets)
                    logger.info(f"Fetched {len(all_datasets)}/{total} datasets...")

                    page += 1

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error fetching page {page}: {e}")
                    raise CatalogBuildError(f"Failed to fetch datasets: {e}") from e

            # Index datasets
            self.datasets = {}
            for ds in all_datasets:
                cached = self._dataset_to_cached(ds)
                self.datasets[cached.id] = cached

            logger.info(f"Indexed {len(self.datasets)} datasets")

            # Save to cache
            await self._save_cache()

        except Exception as e:
            raise CatalogBuildError(f"Catalog building failed: {e}") from e

    def _dataset_to_cached(self, ds: Dataset) -> CachedDataset:
        """Convert API Dataset to CachedDataset.

        Args:
            ds: Dataset from API

        Returns:
            CachedDataset for indexing
        """
        org_name = ""
        if ds.organization:
            org_name = ds.organization.name or ""

        formats = []
        for r in ds.resources:
            if r.format:
                formats.append(r.format)

        return CachedDataset(
            id=ds.id,
            title=ds.title or "",
            description=ds.description or "",
            organization=org_name,
            formats=formats,
            tags=ds.tags or [],
            created_at=ds.created_at.isoformat() if ds.created_at else "",
            modified_at=ds.modified_at.isoformat() if ds.modified_at else "",
            resource_count=len(ds.resources),
            has_downloadable=any(f in ["csv", "json", "xlsx", "xls"] for f in formats)
        )

    async def _save_cache(self) -> None:
        """Save catalog to JSON cache file.

        Raises:
            CatalogBuildError: If saving fails
        """
        try:
            # Ensure cache directory exists
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare cache data
            data = {
                "version": CACHE_VERSION,
                "built_at": datetime.now(UTC).isoformat(),
                "total_datasets": len(self.datasets),
                "datasets": {
                    dataset_id: cached.to_dict()
                    for dataset_id, cached in self.datasets.items()
                }
            }

            # Write to temporary file first
            temp_path = self.cache_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_path.replace(self.cache_path)

            logger.info(f"Saved cache to {self.cache_path}")

        except Exception as e:
            raise CatalogBuildError(f"Failed to save cache: {e}") from e

    async def refresh(self) -> dict[str, Any]:
        """Refresh catalog with updated datasets.

        Returns:
            Dict with refresh statistics

        Raises:
            CatalogBuildError: If refresh fails
        """
        logger.info("Refreshing catalog...")
        await self.build_catalog()

        return {
            "total_datasets": len(self.datasets),
            "cache_path": str(self.cache_path),
            "built_at": datetime.now(UTC).isoformat()
        }

    def get(self, dataset_id: str) -> CachedDataset | None:
        """Get dataset by ID.

        Args:
            dataset_id: Dataset ID

        Returns:
            CachedDataset if found, None otherwise
        """
        return self.datasets.get(dataset_id)

    def get_all(self) -> list[CachedDataset]:
        """Get all datasets.

        Returns:
            List of all cached datasets
        """
        return list(self.datasets.values())

    def __len__(self) -> int:
        """Get number of datasets in catalog."""
        return len(self.datasets)

    def __contains__(self, dataset_id: str) -> bool:
        """Check if dataset ID is in catalog."""
        return dataset_id in self.datasets
