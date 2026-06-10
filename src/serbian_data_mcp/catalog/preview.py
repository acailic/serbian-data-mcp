"""Dataset preview functionality."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from .cache import DatasetCatalog
from .exceptions import DatasetNotFound
from ..api.client import UDataClient

logger = logging.getLogger(__name__)


class DatasetPreview:
    """Preview dataset structure and sample data.

    Example:
        preview = DatasetPreview(catalog)
        result = await preview.preview_dataset("dataset-id")
    """

    def __init__(self, catalog: DatasetCatalog) -> None:
        """Initialize preview engine.

        Args:
            catalog: Dataset catalog
        """
        self.catalog = catalog
        self._client: UDataClient | None = None

    async def _get_client(self) -> UDataClient:
        """Get or create API client."""
        if self._client is None:
            self._client = UDataClient()
        return self._client

    async def preview_dataset(self, dataset_id: str, nrows: int = 10) -> dict[str, Any]:
        """Preview dataset with metadata and sample data.

        Args:
            dataset_id: Dataset ID to preview
            nrows: Number of rows to preview (default: 10)

        Returns:
            Dict with metadata and sample data

        Raises:
            DatasetNotFound: If dataset ID not in catalog

        Example:
            >>> result = await preview.preview_dataset("abc123")
            >>> result["metadata"]["title"]
            "Population by Age"
            >>> result["sample_data"]
            [{"age": "0-18", "count": 12345}, ...]
        """
        # Get dataset from catalog
        dataset = self.catalog.get(dataset_id)
        if not dataset:
            raise DatasetNotFound(dataset_id)

        # Build metadata response
        metadata = {
            "id": dataset.id,
            "title": dataset.title,
            "description": dataset.description,
            "organization": dataset.organization,
            "formats": dataset.formats,
            "tags": dataset.tags,
            "resource_count": dataset.resource_count,
            "has_downloadable": dataset.has_downloadable,
            "created_at": dataset.created_at,
            "modified_at": dataset.modified_at,
        }

        # Try to get sample data from first downloadable resource
        sample_data = None
        columns = None
        preview_reason = None

        if dataset.has_downloadable:
            try:
                client = await self._get_client()
                full_dataset = await client.get_dataset(dataset_id)

                if full_dataset and full_dataset.resources:
                    # Find CSV/JSON resource
                    csv_resource = next(
                        (r for r in full_dataset.resources if r.format in ["csv", "json"]),
                        None
                    )

                    if csv_resource:
                        # Download sample data
                        data = await client.get_resource_data(csv_resource.id)

                        if data is not None:
                            if isinstance(data, pd.DataFrame):
                                # Convert to dict for JSON serialization
                                sample_data = data.head(nrows).to_dict(orient="records")
                                columns = list(data.columns)
                                fmt = csv_resource.format or "unknown"
                                preview_reason = f"Showing first {nrows} rows from {fmt.upper()} resource"
                            elif isinstance(data, list):
                                sample_data = data[:nrows]
                                if sample_data:
                                    columns = list(sample_data[0].keys())
                                preview_reason = f"Showing first {len(sample_data)} rows from JSON resource"
                            elif isinstance(data, dict):
                                sample_data = data
                                columns = list(data.keys())
                                preview_reason = "Showing JSON object structure"
                        else:
                            preview_reason = "Resource available but data download failed"
                    else:
                        preview_reason = f"No CSV/JSON resource available (formats: {', '.join(dataset.formats)})"
                else:
                    preview_reason = "Dataset has no resources"

            except Exception as e:
                logger.warning(f"Failed to preview dataset {dataset_id}: {e}")
                preview_reason = f"Preview failed: {str(e)[:100]}"
        else:
            preview_reason = "Dataset has no downloadable resources (metadata only)"

        return {
            "metadata": metadata,
            "sample_data": sample_data,
            "columns": columns,
            "preview_reason": preview_reason
        }

    async def preview_by_query(self, query: str, max_results: int = 3) -> dict[str, Any]:
        """Preview multiple datasets matching a query.

        Args:
            query: Search query
            max_results: Maximum datasets to preview

        Returns:
            Dict with query, total matches, and previews

        Example:
            >>> result = await preview.preview_by_query("population", max_results=2)
            >>> result["query"]
            "population"
            >>> result["total_matches"]
            15
            >>> result["previews"][0]["metadata"]["title"]
            "Population by Age"
        """
        from .search import SearchEngine

        search_engine = SearchEngine(self.catalog)
        results = await search_engine.search(query, max_results=max_results)

        previews: list[dict[str, Any]] = []
        for result in results:
            try:
                preview = await self.preview_dataset(result.dataset.id)
                previews.append(preview)
            except Exception as e:
                logger.warning(f"Failed to preview {result.dataset.id}: {e}")
                # Still include metadata-only preview
                previews.append({
                    "metadata": result.dataset.to_dict(),
                    "sample_data": None,
                    "columns": None,
                    "preview_reason": f"Preview failed: {str(e)[:100]}"
                })

        return {
            "query": query,
            "total_matches": len(results),
            "previews": previews,
            "note": f"Showing top {len(previews)} of {len(results)} matches"
        }
