"""Shared helpers for MCP tool modules.

Provides the API client singleton, dataset/organization serializers,
and DataFrame conversion utilities used across tool modules.
"""

from __future__ import annotations

from typing import Any, Optional, Union

import pandas as pd

from ..api.client import UDataClient
from ..api.models import Dataset, Organization, SearchResult
from ..catalog import DatasetCatalog

_client: Optional[UDataClient] = None
_catalog_instance: Optional[DatasetCatalog] = None


async def get_client() -> UDataClient:
    """Get a fresh API client (avoids event-loop reuse issues)."""
    return UDataClient()


async def get_catalog() -> DatasetCatalog:
    """Get the shared dataset catalog.

    Loads from local cache when fresh, otherwise builds from the data.gov.rs API.
    The same instance is reused across calls so the catalog is built at most once
    per process (unless explicitly refreshed).
    """
    global _catalog_instance
    if _catalog_instance is None:
        catalog = DatasetCatalog()
        await catalog.initialize()
        _catalog_instance = catalog
    return _catalog_instance


def dataset_to_dict(ds: Dataset) -> dict[str, Any]:
    """Convert Dataset to JSON-serializable dict."""
    org = org_to_dict(ds.organization) if ds.organization else None
    resources = [
        {
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "format": r.format,
            "url": r.url,
            "size": r.size,
            "mime_type": r.mime_type,
            "checksum": r.checksum,
        }
        for r in ds.resources
    ]
    return {
        "id": ds.id,
        "title": ds.title,
        "description": ds.description,
        "organization": org,
        "resources": resources,
        "tags": ds.tags,
        "created_at": ds.created_at.isoformat() if ds.created_at else None,
        "modified_at": ds.modified_at.isoformat() if ds.modified_at else None,
        "frequency": ds.frequency,
        "temporal_coverage": ds.temporal_coverage,
        "spatial_coverage": ds.spatial_coverage,
        "license": ds.license,
        "slug": getattr(ds, "slug", None),
        "page": getattr(ds, "page", None),
        "uri": getattr(ds, "uri", None),
        "quality": getattr(ds, "quality", None),
        "metrics": getattr(ds, "metrics", None),
        "acronym": getattr(ds, "acronym", None),
        "badges": getattr(ds, "badges", []),
    }


def search_result_to_dict(result: SearchResult) -> dict[str, Any]:
    """Convert SearchResult to JSON-serializable dict."""
    return {
        "datasets": [dataset_to_dict(ds) for ds in result.datasets],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
        "has_next": result.has_next,
        "has_previous": result.has_previous,
    }


def org_to_dict(org: Organization) -> dict[str, Any]:
    """Convert Organization to JSON-serializable dict."""
    return {"id": org.id, "name": org.name, "description": org.description, "url": org.url, "logo": org.logo}


def dataframe_to_dict(df: Union[pd.DataFrame, Any]) -> dict[str, Any]:
    """Convert DataFrame or list-of-dicts to JSON-serializable structure."""
    if isinstance(df, pd.DataFrame):
        return {"data": df.to_dict(orient="records"), "columns": list(df.columns), "rows": len(df)}
    if isinstance(df, list):
        return {"data": df, "rows": len(df)}
    return {"data": df}


def resource_to_dict(r: Any) -> dict[str, Any]:
    """Convert a Resource to a flat dict."""
    return {
        "id": r.id,
        "title": r.title,
        "description": r.description,
        "format": r.format,
        "url": r.url,
        "size": r.size,
        "mime_type": r.mime_type,
    }
